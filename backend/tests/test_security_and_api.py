from uuid import uuid4
import pytest
from app.config import get_settings
from app.storage.files import atomic_bytes, safe_path, sanitize_filename, verify
from app.utils.errors import AppError

def test_safe_paths_and_filename():
    assert sanitize_filename("../../records.csv") == "records.csv"
    assert sanitize_filename("C:\\private\\records.csv") == "records.csv"
    with pytest.raises(AppError):
        safe_path("data/datasets", "../../etc/passwd", ".csv")
    with pytest.raises(AppError):
        safe_path("../../", str(uuid4()), ".csv")

def test_integrity_detects_modified_bytes():
    path = safe_path("data/datasets", str(uuid4()), ".csv")
    digest = atomic_bytes(path, b"fixture")
    verify(path, digest)
    path.write_bytes(b"changed")
    with pytest.raises(AppError, match="integrity"):
        verify(path, digest)

def test_health_and_private_origin(client):
    assert client.get("/api/health").status_code == 200
    blocked = client.get("/api/datasets", headers={"Origin": "https://untrusted.invalid"})
    assert blocked.status_code == 403

def test_bearer_token_is_enforced_when_configured(client, monkeypatch):
    # Runtime-generated test credential; no credential is embedded in source.
    import secrets
    token = secrets.token_urlsafe(32)
    monkeypatch.setattr(get_settings(), "api_token", token)
    assert client.get("/api/datasets").status_code == 401
    assert client.get("/api/datasets", headers={"Authorization": f"Bearer {token}"}).status_code == 200

def test_unknown_ids_and_validation_are_sanitized(client):
    response = client.get(f"/api/datasets/{uuid4()}")
    assert response.status_code == 404
    response = client.post("/api/training/jobs", json={"dataset_id": "private-record-marker"})
    assert response.status_code == 422
    assert "private-record-marker" not in response.text

def test_public_model_upload_route_does_not_exist(client):
    response = client.post("/api/models/upload", files={"file": ("model.dill", b"not-code", "application/octet-stream")})
    assert response.status_code in (404, 405, 422)

def test_original_records_not_exposed_in_dataset_summary(client, registered):
    result = client.get(f"/api/datasets/{registered.id}")
    assert result.status_code == 200
    assert "rows" not in result.json()
    assert "records" not in result.json()

def test_body_size_limit_is_enforced(client):
    response = client.post("/api/datasets/upload", content=b"", headers={"Content-Length": str(1024 * 1024 * 500)})
    assert response.status_code == 413

def test_list_datasets_limit_validation(client):
    assert client.get("/api/datasets?limit=501").status_code == 422
    assert client.get("/api/datasets?limit=0").status_code == 422
    assert client.get("/api/datasets?limit=500").status_code == 200
