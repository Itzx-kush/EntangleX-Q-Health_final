from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class RequestTelemetryOut(BaseModel):
    total: int = 0
    errors: int = 0
    error_rate: float = 0.0
    avg_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    lifetime_total: int = 0
    lifetime_errors: int = 0


class DatabaseTelemetryOut(BaseModel):
    available: bool = True
    latency_ms: float | None = None
    journal_mode: str | None = "wal"
    error: str | None = None


class WorkerTelemetryOut(BaseModel):
    started: bool = True
    available: bool = True
    worker_id: str | None = None
    queue_depth: int = 0
    active_job_ids: list[str] = Field(default_factory=list)
    last_activity: str | None = None


class JobTelemetryOut(BaseModel):
    queued: int = 0
    running: int = 0
    recoverable: int = 0
    failed: int = 0
    cancelled: int = 0
    succeeded: int = 0
    active: int = 0
    stale_leases: int = 0
    queue_capacity: int = 3
    queue_utilization_pct: float = 0.0
    avg_duration_seconds: float = 0.0


class CacheTelemetryOut(BaseModel):
    hits: int = 0
    misses: int = 0
    hit_rate: float = 0.0
    hit_ratio_pct: float = 0.0
    evictions: int = 0
    size: int = 0
    max_entries: int = 2000
    cache_backend: str = "in_memory"


class StorageTelemetryOut(BaseModel):
    available: bool = True
    directories: dict[str, bool] = Field(default_factory=dict)
    disk_free_bytes: int | None = None
    disk_total_bytes: int | None = None


class DependencyStatusOut(BaseModel):
    redis: str = "disabled"
    groq: str = "not_configured"
    supabase: str = "not_configured"
    quantum: str = "available"


class TelemetryResponse(BaseModel):
    schema_version: str = "platform_telemetry_v1"
    status: str = "healthy"
    generated_at: str
    uptime_seconds: float
    requests: RequestTelemetryOut
    database: DatabaseTelemetryOut
    jobs: JobTelemetryOut
    worker: WorkerTelemetryOut
    cache: CacheTelemetryOut
    storage: StorageTelemetryOut
    dependencies: DependencyStatusOut
    by_route: dict[str, Any] = Field(default_factory=dict)


class DiagnosticsResponse(BaseModel):
    schema_version: str = "platform_diagnostics_v1"
    status: str = "healthy"
    version: str = "0.1.0"
    mode: str = "single-workstation research prototype"
    generated_at: str
    uptime_seconds: float
    deployment_mode: str = "local"
    database: DatabaseTelemetryOut
    storage: StorageTelemetryOut
    worker: WorkerTelemetryOut
    jobs: JobTelemetryOut
    cache: CacheTelemetryOut
    dependencies: DependencyStatusOut = Field(default_factory=DependencyStatusOut)
