import time
from uuid import uuid4
import pytest
from app.telemetry.registry import TelemetryRegistry
from app.telemetry.schemas import TelemetryResponse, DiagnosticsResponse


def test_normalize_route():
    assert TelemetryRegistry.normalize_route("GET", "/api/health") == "GET /api/health"
    assert TelemetryRegistry.normalize_route("GET", "/api/experiments/9b3f46f4-ec0a-4849-8c5e-851978250ea5") == "GET /api/experiments/{id}"
    assert TelemetryRegistry.normalize_route("GET", "/api/experiments/9b3f46f4-ec0a-4849-8c5e-851978250ea5/report") == "GET /api/experiments/{id}/report"
    assert TelemetryRegistry.normalize_route("GET", "/api/artifacts/a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90") == "GET /api/artifacts/{hash}"
    assert TelemetryRegistry.normalize_route("GET", "/api/models/42") == "GET /api/models/{id}"
    assert TelemetryRegistry.normalize_route("GET", "/api/models?page=1&limit=10") == "GET /api/models"


def test_telemetry_registry_aggregates_and_percentiles():
    registry = TelemetryRegistry(max_recent_samples=1000)
    registry.record_request("GET", "/api/health", 200, 10.0)
    registry.record_request("GET", "/api/health", 200, 20.0)
    registry.record_request("GET", "/api/health", 200, 30.0)
    registry.record_request("POST", "/api/datasets", 500, 40.0)

    summary = registry.get_summary(window_seconds=60)
    requests_stat = summary["requests"]
    assert requests_stat["total"] == 4
    assert requests_stat["errors"] == 1
    assert requests_stat["error_rate"] == 0.25
    assert requests_stat["avg_ms"] == 25.0
    assert requests_stat["p50_ms"] >= 20.0
    assert requests_stat["p95_ms"] >= 35.0

    # Route breakdown
    by_route = summary["by_route"]
    assert "GET /api/health" in by_route
    assert by_route["GET /api/health"]["total"] == 3
    assert by_route["GET /api/health"]["errors"] == 0

    assert "POST /api/datasets" in by_route
    assert by_route["POST /api/datasets"]["total"] == 1
    assert by_route["POST /api/datasets"]["errors"] == 1


def test_telemetry_registry_bounded_memory():
    registry = TelemetryRegistry(max_samples=10)
    for i in range(25):
        registry.record_request("GET", "/api/ping", 200, float(i))

    summary = registry.get_summary(window_seconds=60)
    # Total count tracks all requests
    assert summary["requests"]["lifetime_total"] == 25
    # But recent samples buffer is bounded by max_samples
    assert len(registry.global_metric.samples) <= 10


def test_http_telemetry_and_diagnostics_endpoints(client):
    # Make a couple requests first to populate telemetry
    client.get("/api/health")
    client.get("/api/health/ready")

    # Query telemetry endpoint
    resp = client.get("/api/system/telemetry")
    assert resp.status_code == 200
    data = resp.json()

    # Validate against TelemetryResponse schema
    validated = TelemetryResponse.model_validate(data)
    assert validated.schema_version == "platform_telemetry_v1"
    assert validated.status in {"healthy", "degraded"}
    assert validated.requests.total >= 2
    assert validated.database.available is True
    assert validated.database.latency_ms >= 0.0
    assert validated.storage.available is True
    assert validated.worker.worker_id is not None
    assert validated.cache.cache_backend == "in_memory"

    # Dependency statuses must be safe strings, never tokens or keys
    assert validated.dependencies.redis in {"available", "unavailable", "disabled"}
    assert validated.dependencies.groq in {"configured", "not_configured"}
    assert validated.dependencies.supabase in {"configured", "not_configured"}
    assert validated.dependencies.quantum in {"available", "unavailable"}


def test_http_diagnostics_endpoint(client):
    resp = client.get("/api/system/diagnostics")
    assert resp.status_code == 200
    data = resp.json()

    # Validate against DiagnosticsResponse schema
    validated = DiagnosticsResponse.model_validate(data)
    assert validated.schema_version == "platform_diagnostics_v1"
    assert validated.status in {"healthy", "degraded"}
    assert validated.version == "0.1.0"
    assert validated.database.available is True
    assert validated.storage.available is True
    assert validated.dependencies.redis in {"available", "unavailable", "disabled"}
    assert validated.dependencies.groq in {"configured", "not_configured"}


def test_http_readiness_probe(client):
    resp = client.get("/api/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["database"] is True
    assert data["storage"] is True
    assert "disclaimer" in data
