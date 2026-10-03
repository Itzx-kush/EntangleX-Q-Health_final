import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import session_scope
from backend.app.storage.entities import Experiment, Dataset, ModelRecord

client = TestClient(app)

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer research-test-token-778899"}

def test_quantum_diagnostics_preflight_and_generate(auth_headers):
    exp_id = str(uuid4())
    dataset_id = str(uuid4())
    model_id = str(uuid4())
    
    with session_scope() as session:
        ds = Dataset(id=dataset_id, name="Test", filename="test.csv", sha256="fake", provenance={}, quality={})
        session.add(ds)
        
        exp = Experiment(
            id=exp_id,
            name="Test Quantum",
            dataset_id=dataset_id,
            config={
                "dataset_id": dataset_id,
                "models": ["vqc"],
                "pipeline": {"pca_components": 4},
                "quantum": {"qubits": 4, "reps": 2, "feature_map": "ZZFeatureMap", "ansatz": "RealAmplitudes"},
            },
            status="completed"
        )
        session.add(exp)
        
        model = ModelRecord(
            id=model_id,
            experiment_id=exp_id,
            dataset_id=dataset_id,
            model_type="vqc",
            status="ready",
            metrics={"timing": {"final_training_seconds": 12.3}}
        )
        session.add(model)
        
    req = {
        "experiment_id": exp_id,
        "model_record_id": model_id
    }
    
    # 1. Test Preflight
    res = client.post("/api/quantum/diagnostics/preflight", json=req, headers=auth_headers)
    assert res.status_code == 200, res.text
    pre = res.json()
    assert pre["feasible"] is True
    
    # 2. Test Generation
    res2 = client.post("/api/quantum/diagnostics", json=req, headers=auth_headers)
    assert res2.status_code == 200, res2.text
    report = res2.json()
    
    assert report["model_type"] == "vqc"
    assert report["circuit_structure"]["qubits"] == 4
    assert report["circuit_structure"]["depth"] == 5  # 1 + (2*2)
    assert report["feature_encoding"]["original_features"] == 4
    assert report["resource_profile"]["qubits_observed"] == 4
    assert report["configuration_fingerprint"] is not None
    assert len(report["warnings"]) == 0
    assert report["noise_profile"]["noise_enabled"] is False

def test_quantum_diagnostics_classical_rejection(auth_headers):
    exp_id = str(uuid4())
    dataset_id = str(uuid4())
    model_id = str(uuid4())
    
    with session_scope() as session:
        ds = Dataset(id=dataset_id, name="Test", filename="test.csv", sha256="fake", provenance={}, quality={})
        session.add(ds)
        
        exp = Experiment(
            id=exp_id,
            name="Test Classical",
            dataset_id=dataset_id,
            config={
                "dataset_id": dataset_id,
                "models": ["logistic_regression"],
                "pipeline": {"pca_components": 4},
            },
            status="completed"
        )
        session.add(exp)
        
        model = ModelRecord(
            id=model_id,
            experiment_id=exp_id,
            dataset_id=dataset_id,
            model_type="logistic_regression",
            status="ready",
            metrics={}
        )
        session.add(model)
        
    req = {
        "experiment_id": exp_id,
        "model_record_id": model_id
    }
    
    res = client.post("/api/quantum/diagnostics/preflight", json=req, headers=auth_headers)
    assert res.status_code == 200, res.text
    pre = res.json()
    assert pre["feasible"] is False
    assert "Classical models do not support quantum diagnostics." in pre["limitations"]
    
    res2 = client.post("/api/quantum/diagnostics", json=req, headers=auth_headers)
    assert res2.status_code == 400
