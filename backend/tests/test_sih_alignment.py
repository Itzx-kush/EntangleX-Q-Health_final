from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.alignment import HYBRID_MODEL_ID, alignment_contract
from app.api.schemas import ExplanationRequest, RobustnessRequest, TrainingConfig


def config(**overrides):
    values = {"dataset_id": uuid4(), "models": [HYBRID_MODEL_ID]}
    values.update(overrides)
    return TrainingConfig(**values)


def test_hybrid_capability_is_available_when_dependencies_import():
    contract = alignment_contract()
    hybrid = next(item for item in contract["models"] if item["model_id"] == HYBRID_MODEL_ID)
    assert hybrid["implementation_status"] == "AVAILABLE"
    assert hybrid["executable"] is True
    assert contract["frameworks"]["pennylane"]["package_importable"] is True
    assert contract["frameworks"]["torch"]["package_importable"] is True
    assert contract["frameworks"]["pennylane"]["runtime_verified"] is False
    assert contract["flagship_architecture"]["status"] == "IMPLEMENTED"


def test_hybrid_and_qiskit_dimension_rules_are_separate_and_bounded():
    accepted = config(pipeline={"pca_components": 3}, quantum={"qubits": 4}, hybrid={"qubits": 3})
    assert accepted.hybrid.qubits == accepted.pipeline.pca_components
    with pytest.raises(ValidationError):
        config(hybrid={"qubits": 9})
    with pytest.raises(ValidationError):
        config(pipeline={"pca_components": 4}, hybrid={"qubits": 3})
    with pytest.raises(ValidationError):
        config(hybrid={"classical_hidden_dimensions": [256]})
    with pytest.raises(ValidationError):
        config(max_samples=161, hybrid={"sample_cap": 160})
    both = config(models=["vqc", HYBRID_MODEL_ID])
    assert both.quantum.qubits == both.hybrid.qubits == both.pipeline.pca_components
    with pytest.raises(ValidationError):
        config(models=["vqc", HYBRID_MODEL_ID], pipeline={"pca_components": 3}, quantum={"qubits": 3}, hybrid={"qubits": 4})


def test_showcase_metadata_is_deterministic_and_references_catalog_dataset():
    first, second = alignment_contract(), alignment_contract()
    assert first == second
    assert first["showcase"]["id"] == "early-stage-diabetes"
    assert first["showcase"]["target"] == "diabetes_status"
    assert first["showcase"]["positive_class"] == "positive"
    assert first["flagship_experiment_preset"]["auto_start_training"] is False
    assert first["flagship_experiment_preset"]["models"] == [
        "logistic_regression", "svm", "random_forest",
        "vqc", "qsvc", "qnn", HYBRID_MODEL_ID,
    ]


def test_hybrid_uses_existing_threshold_contract_and_existing_models_still_validate():
    hybrid = config(threshold_strategy="target_sensitivity", target_sensitivity=0.97)
    assert hybrid.threshold_strategy == "target_sensitivity"
    for model in ["logistic_regression", "svm", "random_forest", "vqc", "qsvc", "qnn"]:
        assert TrainingConfig(dataset_id=uuid4(), models=[model]).models == [model]


def test_comparison_robustness_and_explanation_contracts_remain_compatible():
    assert config(models=["random_forest", HYBRID_MODEL_ID]).models[-1] == HYBRID_MODEL_ID
    assert RobustnessRequest().max_samples == 32
    assert ExplanationRequest(method="shap").method == "shap"


def test_alignment_api_reports_available_hybrid_and_training_request_is_accepted(client, monkeypatch):
    response = client.get("/api/alignment")
    assert response.status_code == 200
    hybrid = next(item for item in response.json()["models"] if item["model_id"] == HYBRID_MODEL_ID)
    assert hybrid["executable"] is True

    from app.jobs.manager import manager
    from app.storage.entities import Experiment, Job
    from app.utils.serialization import utcnow
    job_id, experiment_id = str(uuid4()), str(uuid4())
    job = Job(id=job_id, experiment_id=experiment_id, status="queued", progress=0, state="Queued", errors=[], created_at=utcnow(), updated_at=utcnow())
    experiment = Experiment(id=experiment_id, dataset_id=str(uuid4()), parent_id=None, status="created", config={}, summary={}, created_at=utcnow())
    monkeypatch.setattr(manager, "enqueue", lambda value: (job, experiment))
    accepted = client.post("/api/training/jobs", json={"dataset_id": experiment.dataset_id, "models": [HYBRID_MODEL_ID]})
    assert accepted.status_code == 202
