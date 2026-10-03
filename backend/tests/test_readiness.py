import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer research-test-token-778899"}

def test_create_and_evaluate_condition_task(auth_headers):
    lines = ["feature1,feature2,target,feature3"]
    for i in range(100):
        lines.append(f"{i*0.1},{i*0.2},{i%2},P{i}")
    csv_content = "\n".join(lines)

    meta = {
        "name": "Readiness Test",
        "target": "target",
        "positive_label": "1",
        "source": "test",
        "deidentified": True
    }

    res = client.post(
        "/api/datasets/upload",
        files={"file": ("test.csv", csv_content, "text/csv")},
        data={"metadata_json": json.dumps(meta)},
        headers=auth_headers
    )
    dataset = res.json()
    dataset_id = dataset["id"]
    dataset_version_id = dataset["current_version_id"]

    res = client.post(
        "/api/condition-tasks",
        json={
            "condition_name": "Test Disease",
            "task_type": "binary_classification",
            "target_column": "missing_target",
            "positive_label": "1",
            "negative_label": "0",
            "dataset_id": dataset_id,
            "dataset_version_id": dataset_version_id
        },
        headers=auth_headers
    )
    task1 = res.json()
    
    res = client.post(
        "/api/condition-tasks",
        json={
            "condition_name": "Test Disease",
            "task_type": "binary_classification",
            "target_column": "target",
            "positive_label": "1",
            "negative_label": "0",
            "dataset_id": dataset_id,
            "dataset_version_id": dataset_version_id
        },
        headers=auth_headers
    )
    task2 = res.json()
    
    res = client.post("/api/training/jobs", json={
        "dataset_id": dataset_id,
        "dataset_version_id": dataset_version_id,
        "condition_task_id": task1["id"],
        
        "models": ["logistic_regression"],
        "max_samples": 40
    }, headers=auth_headers)
    if res.status_code != 400:
        print(res.json())
    assert res.status_code == 422
    assert "task_blocked" in res.text
