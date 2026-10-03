import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
import time

from app.main import app

client = TestClient(app)

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer research-test-token-778899"}

def test_threshold_preflight_validation(auth_headers):
    # Testing preflight blocks invalid targets
    res = client.post("/api/threshold-analysis/preflight", headers=auth_headers, json={
        "model_id": str(uuid4()),
        "dataset_id": str(uuid4()),
        "selection_method": "target_sensitivity",
        "target_value": 1.5 # Invalid
    })
    
    assert res.status_code == 422
    assert res.json().get("error", {}).get("code") == "validation_error"

def test_threshold_uncalibrated_baseline(auth_headers):
    # Missing model should return 422 model_unavailable (mapped by AppError)
    res = client.post("/api/threshold-analysis/preflight", headers=auth_headers, json={
        "model_id": str(uuid4()),
        "dataset_id": str(uuid4()),
        "selection_method": "youden_j"
    })
    
    assert res.status_code == 422
    data = res.json()
    assert data.get("error", {}).get("code") == "model_unavailable"
