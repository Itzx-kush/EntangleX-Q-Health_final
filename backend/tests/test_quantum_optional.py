"""Opt-in genuine circuit/model tests; no fabricated quantum outputs."""
import os
import time
import numpy as np
import pytest
pytestmark = [pytest.mark.quantum, pytest.mark.skipif(os.getenv("RUN_QUANTUM_TESTS") != "1", reason="Set RUN_QUANTUM_TESTS=1 to execute quantum tests explicitly.")]

def quantum_config():
    from app.api.schemas import QuantumConfig
    return QuantumConfig(qubits=2, maxiter=5)

def test_quantum_circuit_structure():
    pytest.importorskip("qiskit_machine_learning")
    from app.quantum.circuits import circuit_description
    result = circuit_description(quantum_config(), "vqc", 42)
    assert result["qubits"] == 2
    assert result["logical_depth"] > 0
    assert result["gates"]

def test_quantum_circuit_is_deterministic():
    pytest.importorskip("qiskit_machine_learning")
    from app.quantum.circuits import circuit_description
    first = circuit_description(quantum_config(), "qsvc", 42)
    second = circuit_description(quantum_config(), "qsvc", 42)
    assert first == second

@pytest.mark.parametrize("kind", ["vqc", "qsvc"])
def test_small_actual_quantum_prediction(kind):
    pytest.importorskip("qiskit_machine_learning")
    from sklearn.base import clone
    from app.quantum.estimator import QuantumClassifier
    X = np.array([[.1, .2], [.2, .1], [2., 2.1], [2.2, 2.]])
    y = np.array([0, 0, 1, 1])
    estimator = QuantumClassifier(kind=kind, quantum=quantum_config().model_dump(), seed=42)
    model = clone(estimator).fit(X, y)
    assert model.predict(X).shape == (4,)
    if kind == "vqc":
        probabilities = model.predict_proba(X)
        np.testing.assert_allclose(probabilities.sum(axis=1), 1, atol=1e-6)
    else:
        assert model.decision_function(X).shape == (4,)

@pytest.mark.parametrize("kind", ["vqc", "qsvc"])
def test_aer_quantum_prediction(kind):
    pytest.importorskip("qiskit_aer")
    from app.quantum.estimator import QuantumClassifier
    X = np.array([[.1, .2], [.2, .1], [2., 2.1], [2.2, 2.]])
    y = np.array([0, 0, 1, 1])
    from app.api.schemas import QuantumConfig
    config = QuantumConfig(backend="aer", qubits=2, maxiter=5, shots=128)
    model = QuantumClassifier(kind=kind, quantum=config.model_dump(), seed=42).fit(X, y)
    assert model.predict(X).shape == (4,)

@pytest.mark.parametrize("kind", ["vqc", "qsvc"])
def test_quantum_model_artifact_reload(kind, tmp_path, monkeypatch):
    pytest.importorskip("qiskit_machine_learning")
    from app.quantum.estimator import QuantumClassifier
    from app.storage.files import load_model, save_model
    X = np.array([[.1, .2], [.2, .1], [2., 2.1], [2.2, 2.]])
    y = np.array([0, 0, 1, 1])
    monkeypatch.setenv("QHEALTH_STORAGE_ROOT", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    model = QuantumClassifier(kind=kind, quantum=quantum_config().model_dump(), seed=42).fit(X, y)
    identity = "11111111-1111-1111-1111-111111111111" if kind == "vqc" else "22222222-2222-2222-2222-222222222222"
    digest = save_model(identity, {"estimator": model})
    restored = load_model(identity, digest)["estimator"]
    np.testing.assert_array_equal(restored.predict(X), model.predict(X))
    get_settings.cache_clear()

def test_quantum_invalid_input_is_controlled():
    pytest.importorskip("qiskit_machine_learning")
    from app.quantum.estimator import QuantumClassifier
    model = QuantumClassifier(kind="vqc", quantum=quantum_config().model_dump(), seed=42)
    with pytest.raises(ValueError, match="dimensions"):
        model.fit(np.zeros((4, 3)), np.array([0, 0, 1, 1]))
    with pytest.raises(ValueError, match="labels"):
        model.fit(np.zeros((4, 2)), np.array([0, 0, 0, 0]))

def test_quantum_api_smoke(client):
    capabilities = client.get("/api/quantum/capabilities")
    assert capabilities.status_code == 200
    assert capabilities.json()["available"] is True
    response = client.post("/api/quantum/circuit", json={"model_type": "qsvc", "quantum": quantum_config().model_dump(), "seed": 42})
    assert response.status_code == 200, response.text
    assert response.json()["model_type"] == "qsvc"
    invalid = client.post("/api/quantum/circuit", json={"model_type": "vqc", "quantum": {"qubits": 1}, "seed": 42})
    assert invalid.status_code == 422

@pytest.mark.parametrize("kind", ["vqc", "qsvc"])
def test_quantum_pipeline_training_with_shared_preprocessing(kind, config):
    pytest.importorskip("qiskit_machine_learning")
    from app.api.schemas import TrainingConfig
    from app.data.splitting import prepare_data
    from app.models.training import train_model
    values = config.model_dump(mode="json")
    values["models"] = [kind]
    values["max_samples"] = 30
    values["cv_folds"] = 2
    values["pipeline"]["k_features"] = 4
    values["pipeline"]["pca_components"] = 2
    values["quantum"] = {**values["quantum"], "qubits": 2, "maxiter": 5}
    quantum_configured = TrainingConfig.model_validate(values)
    data = prepare_data(quantum_configured)
    bundle, metrics, details = train_model(kind, quantum_configured, data, lambda _state: None)
    assert metrics["test"]["sample_count"] == len(data.test)
    assert details["quantum"]["circuit"]["qubits"] == 2
    assert bundle["estimator"].predict(data.X.iloc[data.test]).shape == (len(data.test),)

def test_quantum_training_job_api(client, config, registered):
    values = config.model_dump(mode="json")
    values["models"] = ["vqc"]
    values["max_samples"] = 30
    values["cv_folds"] = 2
    values["pipeline"]["k_features"] = 4
    values["pipeline"]["pca_components"] = 2
    values["quantum"] = {**values["quantum"], "qubits": 2, "maxiter": 5}
    created = client.post("/api/training/jobs", json=values)
    assert created.status_code == 202, created.text
    job_id = created.json()["job"]["id"]
    end = time.monotonic() + 120
    while time.monotonic() < end:
        job = client.get(f"/api/training/jobs/{job_id}").json()
        if job["status"] not in {"queued", "running", "cancel_requested"}:
            break
        time.sleep(0.1)
    assert job["status"] == "succeeded", job
    experiment_id = created.json()["experiment"]["id"]
    detail = client.get(f"/api/experiments/{experiment_id}")
    assert detail.status_code == 200
    model = next(item for item in detail.json()["models"] if item["status"] == "ready")
    assert model["model_type"] == "vqc"
    assert model["details"]["quantum"]["circuit"]["qubits"] == 2
    from app.data.service import load_frame
    _, frame = load_frame(registered.id)
    sample = frame[registered.provenance["features"]].iloc[0].to_dict()
    prediction = client.post(f"/api/models/{model['id']}/predict", json={"samples": [sample]})
    assert prediction.status_code == 200, prediction.text
    circuit = client.get(f"/api/models/{model['id']}/circuit")
    assert circuit.status_code == 200
