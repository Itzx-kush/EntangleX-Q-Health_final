import pytest
from app.config import get_settings
from app.database import session_scope, engine
from app.jobs.manager import manager
from app.migrations import apply_migrations, PLATFORM_OBSERVABILITY_INDEXES_MIGRATION_ID
from app.telemetry.db_probe import probe_database, probe_storage


def test_probe_database_success():
    res = probe_database()
    assert res["available"] is True
    assert res["error"] is None
    assert isinstance(res["latency_ms"], float)
    assert res["latency_ms"] >= 0.0
    assert "journal_mode" in res


def test_probe_storage_success():
    settings = get_settings()
    res = probe_storage(settings)
    assert res["available"] is True
    assert isinstance(res["directories"], dict)
    assert "data" in res["directories"]
    assert "models" in res["directories"]
    assert "experiments" in res["directories"]
    assert res["disk_free_bytes"] > 0
    assert res["disk_total_bytes"] > 0


def test_job_manager_health_telemetry():
    with session_scope() as session:
        telemetry = manager.get_health_telemetry(session)

    assert "queued" in telemetry
    assert "running" in telemetry
    assert "recoverable" in telemetry
    assert "failed" in telemetry
    assert "cancelled" in telemetry
    assert "succeeded" in telemetry
    assert "active" in telemetry
    assert "stale_leases" in telemetry
    assert "queue_capacity" in telemetry
    assert "queue_utilization_pct" in telemetry
    assert "worker" in telemetry
    assert telemetry["worker"]["worker_id"] == manager.worker_id
    assert isinstance(telemetry["worker"]["started"], bool)


def test_platform_indexes_migration_idempotent():
    # Running migrations again should execute cleanly without error
    apply_migrations()
    # Re-running must be completely idempotent
    apply_migrations()
