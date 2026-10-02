import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.storage.files import safe_path

ROOT = Path(__file__).resolve().parents[2]
CLIENT_ROUTES = {
    "/", "/datasets", "/quality", "/preprocessing", "/features", "/pca",
    "/training", "/comparison", "/robustness", "/quantum", "/explainability", "/prediction",
    "/experiments", "/experiments/:id", "/demo", "/settings",
}


def test_render_blueprint_has_backend_static_frontend_and_spa_fallback():
    rendered = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "name: entanglex-q-health\n    rootDir: frontend" in rendered
    assert "buildCommand: npm ci && npm run build" in rendered
    assert "staticPublishPath: dist" in rendered
    assert "source: /*\n        destination: /index.html" in rendered
    assert "name: entanglex-q-health-api\n    rootDir: backend" in rendered
    assert "runtime: docker" in rendered
    assert "healthCheckPath: /api/health" in rendered
    assert "VITE_API_BASE\n        value: https://entanglex-q-health-api.onrender.com/api" in rendered
    assert "QHEALTH_CORS_ORIGINS\n        value: https://entanglex-q-health.onrender.com" in rendered


def test_browser_router_and_every_supported_direct_route_remain_declared():
    main = (ROOT / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    assert "BrowserRouter" in main
    assert "HashRouter" not in main + app
    for route in CLIENT_ROUTES:
        assert f'path="{route}"' in app


def test_frontend_runtime_is_pinned_without_changing_lockfile_authority():
    package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "frontend" / "package-lock.json").read_text(encoding="utf-8"))
    assert package["engines"] == {"node": "22.12.x", "npm": "10.x"}
    assert lock["lockfileVersion"] == 3
    assert (ROOT / ".nvmrc").read_text(encoding="utf-8").strip() == "22.12.0"


def test_production_settings_require_explicit_https_origin_and_hosts():
    with pytest.raises(ValidationError, match="explicit HTTPS origins"):
        Settings(_env_file=None, deployment_mode="production", cors_origins="*", trusted_hosts="api.example.test")
    with pytest.raises(ValidationError, match="explicit HTTPS origins"):
        Settings(_env_file=None, deployment_mode="production", cors_origins="http://localhost:5173", trusted_hosts="api.example.test")
    with pytest.raises(ValidationError, match="trusted hosts"):
        Settings(_env_file=None, deployment_mode="production", cors_origins="https://app.example.test", trusted_hosts="*")
    settings = Settings(
        _env_file=None,
        deployment_mode="production",
        cors_origins="https://app.example.test",
        trusted_hosts="api.example.test",
    )
    assert settings.deployment_mode == "production"


def test_health_startup_and_verified_demo_counts_are_deployment_safe(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    readiness = client.get("/api/datasets/readiness")
    assert readiness.status_code == 200
    assert readiness.json()["total"] == 5
    assert readiness.json()["verified_demo_ready"] == 1
    assert readiness.json()["requires_processing"] == 4
    assert client.get("/api/experiments").status_code == 200


def test_missing_runtime_model_file_returns_truthful_integrity_error(client):
    model = next(item for item in client.get("/api/models").json() if item["status"] == "ready")
    path = safe_path("models", model["id"], ".dill")
    original = path.read_bytes()
    path.unlink()
    try:
        response = client.get(f"/api/models/{model['id']}/input-schema")
        assert response.status_code == 409
        assert response.json()["error"]["code"] in {"demo_artifact_integrity", "integrity_error"}
    finally:
        path.write_bytes(original)
