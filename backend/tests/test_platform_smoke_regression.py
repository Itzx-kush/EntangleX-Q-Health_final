import pytest


def test_platform_smoke_scenario_and_telemetry_capture(client):
    # 1. Liveness
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers

    # 2. Readiness
    resp = client.get("/api/health/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"

    # 3. Summary & system status
    resp = client.get("/api/summary")
    assert resp.status_code == 200
    assert "counts" in resp.json()

    resp = client.get("/api/system/status")
    assert resp.status_code == 200
    status_data = resp.json()
    assert status_data["status"] in {"ok", "degraded"}
    assert "jobs" in status_data

    # 4. Built-in dataset library
    resp = client.get("/api/datasets/library")
    assert resp.status_code == 200
    library = resp.json()
    assert len(library) >= 5

    # 5. Verify Telemetry reflects the requests made
    resp = client.get("/api/system/telemetry")
    assert resp.status_code == 200
    telemetry = resp.json()
    assert telemetry["requests"]["total"] >= 4
    assert telemetry["requests"]["avg_ms"] >= 0.0

    # Verify route breakdown includes normalized routes
    routes = telemetry["by_route"]
    assert "GET /api/health" in routes
    assert "GET /api/health/ready" in routes
    assert "GET /api/summary" in routes
    assert "GET /api/system/status" in routes
    assert "GET /api/datasets/library" in routes
