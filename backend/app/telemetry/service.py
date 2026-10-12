from __future__ import annotations

import time
from typing import Any

from ..cache.service import cache
from ..config import get_settings
from ..database import session_scope
from ..jobs.manager import manager
from ..quantum.backends import availability
from ..redis_bridge import get_status as get_redis_status
from ..utils.serialization import utcnow
from .db_probe import probe_database, probe_storage
from .registry import telemetry_registry
from .schemas import (
    CacheTelemetryOut,
    DatabaseTelemetryOut,
    DependencyStatusOut,
    DiagnosticsResponse,
    JobTelemetryOut,
    RequestTelemetryOut,
    StorageTelemetryOut,
    TelemetryResponse,
    WorkerTelemetryOut,
)


def _safe_dependency_status() -> dict[str, Any]:
    settings = get_settings()

    # Redis status
    redis_info = get_redis_status(settings)
    redis_status = redis_info.get("status", "disabled")

    # Groq status
    groq_status = "configured" if bool(settings.groq_api_key) else "not_configured"

    # Supabase status
    supabase_status = (
        "configured"
        if bool(settings.supabase_url and settings.supabase_service_role_key)
        else "not_configured"
    )

    # Quantum status (cached capability lookup)
    cached_quantum = cache.get("quantum:availability")
    if cached_quantum is None:
        try:
            cached_quantum = availability()
            cache.set("quantum:availability", cached_quantum, ttl_seconds=60.0)
        except Exception:
            cached_quantum = {"available": False}
    quantum_status = "available" if cached_quantum.get("available") else "unavailable"

    return {
        "redis": redis_status,
        "groq": groq_status,
        "supabase": supabase_status,
        "quantum": quantum_status,
    }


def get_system_telemetry() -> TelemetryResponse:
    """Produce dashboard-ready aggregate telemetry.

    Caches recent probe results for 2 seconds to prevent DB churn from rapid polling.
    """
    settings = get_settings()

    cached_probes = cache.get("telemetry:probes")
    if cached_probes is not None:
        db_probe, storage_probe, job_worker_data = cached_probes
    else:
        db_probe = probe_database()
        storage_probe = probe_storage(settings)

        try:
            with session_scope() as session:
                job_worker_data = manager.get_health_telemetry(session)
        except Exception:
            job_worker_data = {
                "queued": 0,
                "running": 0,
                "recoverable": 0,
                "failed": 0,
                "cancelled": 0,
                "succeeded": 0,
                "active": 0,
                "stale_leases": 0,
                "queue_capacity": settings.max_queued_jobs,
                "queue_utilization_pct": 0.0,
                "avg_duration_seconds": 0.0,
                "worker": {
                    "started": manager.executor is not None,
                    "available": False,
                    "worker_id": manager.worker_id,
                    "queue_depth": 0,
                    "active_job_ids": [],
                    "last_activity": None,
                },
            }
        cache.set("telemetry:probes", (db_probe, storage_probe, job_worker_data), ttl_seconds=2.0)

    dep_status = _safe_dependency_status()
    req_summary = telemetry_registry.get_summary(window_seconds=settings.telemetry_window_seconds)
    cache_stats = cache.stats()

    is_healthy = db_probe["available"] and storage_probe["available"]
    overall_status = "healthy" if is_healthy else "degraded"

    payload = {
        "schema_version": "platform_telemetry_v1",
        "status": overall_status,
        "generated_at": utcnow().isoformat(),
        "uptime_seconds": telemetry_registry.uptime_seconds(),
        "requests": req_summary["requests"],
        "database": db_probe,
        "jobs": {
            "queued": job_worker_data["queued"],
            "running": job_worker_data["running"],
            "recoverable": job_worker_data["recoverable"],
            "failed": job_worker_data["failed"],
            "cancelled": job_worker_data["cancelled"],
            "succeeded": job_worker_data["succeeded"],
            "active": job_worker_data["active"],
            "stale_leases": job_worker_data["stale_leases"],
            "queue_capacity": job_worker_data["queue_capacity"],
            "queue_utilization_pct": job_worker_data["queue_utilization_pct"],
            "avg_duration_seconds": job_worker_data["avg_duration_seconds"],
        },
        "worker": job_worker_data["worker"],
        "cache": cache_stats,
        "storage": storage_probe,
        "dependencies": dep_status,
        "by_route": req_summary.get("by_route", {}),
    }

    return TelemetryResponse.model_validate(payload)


def get_system_diagnostics() -> DiagnosticsResponse:
    """Safe, read-only system diagnostics for operators and researchers."""
    settings = get_settings()
    db_probe = probe_database()
    storage_probe = probe_storage(settings)

    try:
        with session_scope() as session:
            job_worker_data = manager.get_health_telemetry(session)
    except Exception:
        job_worker_data = {
            "queued": 0,
            "running": 0,
            "recoverable": 0,
            "failed": 0,
            "cancelled": 0,
            "succeeded": 0,
            "active": 0,
            "stale_leases": 0,
            "queue_capacity": settings.max_queued_jobs,
            "queue_utilization_pct": 0.0,
            "avg_duration_seconds": 0.0,
            "worker": {
                "started": manager.executor is not None,
                "available": False,
                "worker_id": manager.worker_id,
                "queue_depth": 0,
                "active_job_ids": [],
                "last_activity": None,
            },
        }

    dep_status = _safe_dependency_status()
    cache_stats = cache.stats()
    is_healthy = db_probe["available"] and storage_probe["available"]

    payload = {
        "schema_version": "platform_diagnostics_v1",
        "status": "healthy" if is_healthy else "degraded",
        "version": "0.1.0",
        "mode": "single-workstation research prototype",
        "generated_at": utcnow().isoformat(),
        "uptime_seconds": telemetry_registry.uptime_seconds(),
        "deployment_mode": settings.deployment_mode,
        "database": db_probe,
        "storage": storage_probe,
        "worker": job_worker_data["worker"],
        "jobs": {
            "queued": job_worker_data["queued"],
            "running": job_worker_data["running"],
            "recoverable": job_worker_data["recoverable"],
            "failed": job_worker_data["failed"],
            "cancelled": job_worker_data["cancelled"],
            "succeeded": job_worker_data["succeeded"],
            "active": job_worker_data["active"],
            "stale_leases": job_worker_data["stale_leases"],
            "queue_capacity": job_worker_data["queue_capacity"],
            "queue_utilization_pct": job_worker_data["queue_utilization_pct"],
            "avg_duration_seconds": job_worker_data["avg_duration_seconds"],
        },
        "cache": cache_stats,
        "dependencies": dep_status,
    }

    return DiagnosticsResponse.model_validate(payload)
