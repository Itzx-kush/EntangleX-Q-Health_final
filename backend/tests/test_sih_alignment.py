from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.alignment import HYBRID_MODEL_ID, alignment_contract
from app.api.schemas import ExplanationRequest, RobustnessRequest, TrainingConfig


def config(**overrides):
    values = {"dataset_id": uuid4(), "models": [HYBRID_MODEL_ID]}
    values.update(overrides)
    return TrainingConfig(**values)


def test_hybrid_capability_is_present_but_not_executable():
    contract = alignment_contract()
    hybrid = next(item for item in contract["models"] if item["model_id"] == HYBRID_MODEL_ID)
    assert hybrid["implementation_status"] == "NOT_YET_IMPLEMENTED"
    assert hybrid["executable"] is False
    assert "not executable" in hybrid["explainability"].lower()


def test_hybrid_configuration_is_bounded_and_dimensionally_coherent():
    accepted = config()
    assert accepted.hybrid.qubits == accepted.pipeline.pca_components == accepted.quantum.qubits
    with pytest.raises(ValidationError):
        config(hybrid={"qubits": 9})
    with pytest.raises(ValidationError):
        config(hybrid={"qubits": 3})
    with pytest.raises(ValidationError):
        config(hybrid={"classical_hidden_dimensions": [256]})


def test_showcase_metadata_is_deterministic_and_references_catalog_dataset():
    first, second = alignment_contract(), alignment_contract()
    assert first == second
    assert first["showcase"]["id"] == "early-stage-diabetes"
    assert first["showcase"]["target"] == "diabetes_status"
    assert first["showcase"]["positive_class"] == "positive"
    assert first["flagship_experiment_preset"]["auto_start_training"] is False


def test_hybrid_uses_existing_threshold_contract_and_existing_models_still_validate():
    hybrid = config(threshold_strategy="target_sensitivity", target_sensitivity=0.97)
    assert hybrid.threshold_strategy == "target_sensitivity"
    assert hybrid.target_sensitivity == 0.97
    for model in ["logistic_regression", "svm", "random_forest", "vqc", "qsvc", "qnn"]:
        assert TrainingConfig(dataset_id=uuid4(), models=[model]).models == [model]


def test_comparison_robustness_and_explanation_contracts_remain_compatible():
    assert config(models=["random_forest", HYBRID_MODEL_ID]).models[-1] == HYBRID_MODEL_ID
    assert RobustnessRequest().max_samples == 32
    assert ExplanationRequest(method="shap").method == "shap"


def test_alignment_api_reports_pending_hybrid_and_training_is_guarded(client):
    response = client.get("/api/alignment")
    assert response.status_code == 200
    payload = response.json()
    hybrid = next(item for item in payload["models"] if item["model_id"] == HYBRID_MODEL_ID)
    assert hybrid["executable"] is False
    assert payload["flagship_architecture"]["status"] == "NOT_YET_IMPLEMENTED"

    blocked = client.post("/api/training/jobs", json={"dataset_id": str(uuid4()), "models": [HYBRID_MODEL_ID]})
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "model_not_yet_implemented"
