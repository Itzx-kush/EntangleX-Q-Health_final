"""Focused genuine QNN tests; all runs are bounded and use synthetic data."""
import os
import time

import numpy as np
import pytest

pytestmark = [
    pytest.mark.quantum,
    pytest.mark.skipif(
        os.getenv("RUN_QUANTUM_TESTS") != "1",
        reason="Set RUN_QUANTUM_TESTS=1 to execute quantum tests explicitly.",
    ),
]


def qnn_config():
    from app.api.schemas import QuantumConfig

    return QuantumConfig(qubits=2, maxiter=5)


def small_data():
    return (
        np.array([[0.1, 0.2], [0.2, 0.1], [2.0, 2.1], [2.2, 2.0]]),
        np.array([0, 0, 1, 1]),
    )


def test_qnn_dependency_import():
    qiskit = pytest.importorskip("qiskit")
    qml = pytest.importorskip("qiskit_machine_learning")
    pytest.importorskip("qiskit_aer")
    assert qiskit.__version__ == "2.5.2"
    assert qml.__version__ == "0.9.1"


def test_qnn_primitive_and_classifier_construction():
    pytest.importorskip("qiskit_machine_learning")
    from app.quantum.estimator import QuantumClassifier

    model = QuantumClassifier(kind="qnn", quantum=qnn_config().model_dump(), seed=42)
    assert model.kind == "qnn"


def test_qnn_input_dimension_and_binary_label_validation():
    pytest.importorskip("qiskit_machine_learning")
    from app.quantum.estimator import QuantumClassifier

    model = QuantumClassifier(kind="qnn", quantum=qnn_config().model_dump(), seed=42)
    with pytest.raises(ValueError, match="dimensions"):
        model.fit(np.zeros((4, 3)), np.array([0, 0, 1, 1]))
    with pytest.raises(ValueError, match="labels"):
        model.fit(np.zeros((4, 2)), np.array([0, 0, 0, 0]))


def test_qnn_deterministic_fit_prediction_and_probabilities():
    pytest.importorskip("qiskit_machine_learning")
    from app.quantum.estimator import QuantumClassifier

    X, y = small_data()
    first = QuantumClassifier(kind="qnn", quantum=qnn_config().model_dump(), seed=42).fit(X, y)
    second = QuantumClassifier(kind="qnn", quantum=qnn_config().model_dump(), seed=42).fit(X, y)
    np.testing.assert_array_equal(first.predict(X), second.predict(X))
    np.testing.assert_allclose(first.predict_proba(X), second.predict_proba(X), atol=1e-12)
    np.testing.assert_allclose(first.predict_proba(X).sum(axis=1), 1.0, atol=1e-10)
    assert first.decision_function(X).shape == (4,)


def test_qnn_metadata_and_circuit_structure():
    pytest.importorskip("qiskit_machine_learning")
    from app.quantum.circuits import circuit_description
    from app.quantum.estimator import QuantumClassifier

    X, y = small_data()
    model = QuantumClassifier(kind="qnn", quantum=qnn_config().model_dump(), seed=42).fit(X, y)
    metadata = model.quantum_metadata_
    assert metadata["model_type"] == "qnn"
    assert metadata["real_hardware"] is False
    assert metadata["trainable_parameter_count"] == 4
    assert "probabilities" in metadata["output_semantics"]
    circuit = circuit_description(qnn_config(), "qnn", 42)
    assert circuit["model_type"] == "qnn"
    assert circuit["parameter_count"] > 0
    assert circuit["gates"]


def test_qnn_aer_prediction():
    pytest.importorskip("qiskit_aer")
    from app.api.schemas import QuantumConfig
    from app.quantum.estimator import QuantumClassifier

    X, y = small_data()
    config = QuantumConfig(backend="aer", qubits=2, maxiter=5, shots=128)
    model = QuantumClassifier(kind="qnn", quantum=config.model_dump(), seed=42).fit(X, y)
    probabilities = model.predict_proba(X)
    assert model.predict(X).shape == (4,)
    np.testing.assert_allclose(probabilities.sum(axis=1), 1.0, atol=1e-6)


def test_qnn_artifact_persistence_and_reload(tmp_path, monkeypatch):
    pytest.importorskip("qiskit_machine_learning")
    from app.config import get_settings
    from app.quantum.estimator import QuantumClassifier
    from app.storage.files import load_model, save_model

    monkeypatch.setenv("QHEALTH_STORAGE_ROOT", str(tmp_path))
    get_settings.cache_clear()
    X, y = small_data()
    model = QuantumClassifier(kind="qnn", quantum=qnn_config().model_dump(), seed=42).fit(X, y)
    identity = "33333333-3333-3333-3333-333333333333"
    digest = save_model(identity, {"estimator": model})
    restored = load_model(identity, digest)["estimator"]
    np.testing.assert_array_equal(restored.predict(X), model.predict(X))
    np.testing.assert_allclose(restored.predict_proba(X), model.predict_proba(X), atol=1e-12)
    get_settings.cache_clear()


def test_qnn_invalid_configuration_is_rejected():
    from app.api.schemas import TrainingConfig

    with pytest.raises(ValueError, match="PCA components"):
        TrainingConfig(
            dataset_id="00000000-0000-0000-0000-000000000000",
            models=["qnn"],
            pipeline={"pca_components": 3, "angle_scaling": True},
            quantum=qnn_config(),
        )
    with pytest.raises(ValueError, match="class weights"):
        TrainingConfig(
            dataset_id="00000000-0000-0000-0000-000000000000",
            models=["qnn"],
            pipeline={"pca_components": 2, "angle_scaling": True},
            quantum=qnn_config(),
            parameters={"class_weight": "balanced"},
        )


def test_qnn_missing_dependency_error_is_controlled(monkeypatch):
    from app.quantum import backends
    from app.utils.errors import AppError

    monkeypatch.setattr(
        backends,
        "availability",
        lambda: {
            "packages_present": {"qiskit": False, "qiskit_machine_learning": False, "qiskit_aer": False},
            "available": False,
            "runtime_verified": False,
            "execution": "local quantum simulation only; no hardware credentials or hardware execution",
        },
    )
    with pytest.raises(AppError, match="Install backend/requirements-quantum"):
        backends.require_quantum()


def test_qnn_circuit_api_smoke(client):
    response = client.post(
        "/api/quantum/circuit",
        json={"model_type": "qnn", "quantum": qnn_config().model_dump(), "seed": 42},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["model_type"] == "qnn"
    assert body["backend"] == "statevector"
    assert body["qubits"] == 2
    assert body["parameter_count"] > 0


def qnn_training_values(config):
    values = config.model_dump(mode="json")
    values["models"] = ["qnn"]
    values["max_samples"] = 30
    values["cv_folds"] = 2
    values["pipeline"]["k_features"] = 4
    values["pipeline"]["pca_components"] = 2
    values["quantum"] = {**values["quantum"], "qubits": 2, "maxiter": 5}
    return values


def test_qnn_shared_pipeline_training(config):
    pytest.importorskip("qiskit_machine_learning")
    from app.api.schemas import TrainingConfig
    from app.data.splitting import prepare_data
    from app.models.training import train_model

    configured = TrainingConfig.model_validate(qnn_training_values(config))
    data = prepare_data(configured)
    bundle, metrics, details = train_model("qnn", configured, data, lambda _state: None)
    assert metrics["test"]["sample_count"] == len(data.test)
    assert details["quantum"]["model_type"] == "qnn"
    assert bundle["estimator"].predict(data.X.iloc[data.test]).shape == (len(data.test),)


def test_qnn_training_job_registry_prediction_report_and_comparison(client, config, registered):
    values = qnn_training_values(config)
    values["models"] = ["logistic_regression", "qnn"]
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
    qnn_model = next(item for item in detail.json()["models"] if item["model_type"] == "qnn")
    assert qnn_model["status"] == "ready"
    assert qnn_model["details"]["quantum"]["model_type"] == "qnn"
    circuit = client.get(f"/api/models/{qnn_model['id']}/circuit")
    assert circuit.status_code == 200
    assert circuit.json()["model_type"] == "qnn"
    comparison = client.get(f"/api/experiments/{experiment_id}/comparison")
    assert comparison.status_code == 200
    assert any(pair["quantum_type"] == "qnn" for pair in comparison.json()["pairs"])
    report = client.get(f"/api/experiments/{experiment_id}/report?format=json")
    assert report.status_code == 200
    assert '"qnn"' in report.text
    from app.data.service import load_frame

    _, frame = load_frame(registered.id)
    sample = frame[registered.provenance["features"]].iloc[0].to_dict()
    prediction = client.post(f"/api/models/{qnn_model['id']}/predict", json={"samples": [sample]})
    assert prediction.status_code == 200, prediction.text
    output = prediction.json()["predictions"][0]
    assert output["probability_positive"] is not None
    assert output["decision_score"] is None