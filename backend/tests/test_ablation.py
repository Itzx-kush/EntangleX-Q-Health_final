import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import session_scope
from backend.app.storage.entities import Experiment, Dataset

client = TestClient(app)

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer research-test-token-778899"}

def test_ablation_preflight(auth_headers):
    exp_id = str(uuid4())
    dataset_id = str(uuid4())
    
    with session_scope() as session:
        ds = Dataset(id=dataset_id, name="Test", filename="test.csv", sha256="fake", provenance={}, quality={})
        session.add(ds)
        
        exp = Experiment(
            id=exp_id,
            name="Test Baseline",
            dataset_id=dataset_id,
            config={
                "dataset_id": dataset_id,
                "models": ["logistic_regression"],
                "pipeline": {"pca_components": 4, "scaler": "standard", "selection": "none"},
                "quantum": {"qubits": 4},
                "calibration": "none",
                "threshold_strategy": "fixed"
            },
            status="completed"
        )
        session.add(exp)
        
    req = {
        "base_experiment_id": exp_id,
        "ablation_configs": [
            {
                "component": "preprocessing.pca",
                "operator": "DISABLE"
            },
            {
                "component": "preprocessing.scaler",
                "operator": "SUBSTITUTE",
                "ablation_value": "minmax"
            }
        ]
    }
    res = client.post("/api/ablation-studies/preflight", json=req, headers=auth_headers)
    assert res.status_code == 200, res.text
    pre = res.json()
    assert pre["feasible"] is True
    assert pre["estimated_run_count"] == 2
    
    changed = pre["changed_components"]
    assert any("pipeline.pca_components=none" in c for c in changed)
    assert any("pipeline.scaler=minmax" in c for c in changed)
    
    # Test Quantum compatibility failure
    with session_scope() as session:
        exp_q = Experiment(
            id=str(uuid4()), name="Q", dataset_id=dataset_id, status="completed",
            config={
                "dataset_id": dataset_id, "models": ["vqc"],
                "pipeline": {"pca_components": 4}, "quantum": {"qubits": 4}
            }
        )
        session.add(exp_q)
        exp_q_id = exp_q.id

    req_quantum = {
        "base_experiment_id": exp_q_id,
        "ablation_configs": [
            {
                "component": "preprocessing.pca",
                "operator": "SUBSTITUTE",
                "ablation_value": 2
            }
        ]
    }
    res2 = client.post("/api/ablation-studies/preflight", json=req_quantum, headers=auth_headers)
    assert res2.status_code == 200, res2.text
    pre2 = res2.json()
    assert pre2["feasible"] is False
    assert any("Qiskit comparisons require PCA components equal to QuantumConfig qubits" in b for b in pre2["blockers"]), str(pre2)
