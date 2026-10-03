from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.database import session_scope
from app.model_cards.service import MODEL_CARD_SCHEMA_VERSION, assemble_card, get_or_create_card
from app.storage.entities import Artifact, Experiment, ModelRecord, Run


def _persist_model(registered, model_type="logistic_regression", *, with_run=True, details=None):
    experiment_id, run_id, model_id = str(uuid4()), str(uuid4()), str(uuid4())
    config = {
        "dataset_id": registered.id,
        "dataset_version_id": registered.current_version_id,
        "condition_task_id": None,
        "features": None,
        "models": [model_type],
        "pipeline": {
            "imputer": "median", "scaler": "standard", "outlier_strategy": "none",
            "selection": "anova", "k_features": 6, "pca_components": 4,
            "pca_whiten": False, "angle_scaling": True, "log_features": [], "ratios": [],
        },
        "parameters": {
            "logistic_c": 1.0, "svm_c": 1.0, "svm_kernel": "rbf",
            "forest_trees": 100, "forest_max_depth": None, "class_weight": None,
        },
        "quantum": {
            "provider_id": "qiskit_local", "execution_mode": "local_simulator",
            "backend": "statevector", "qubits": 4, "feature_map_reps": 1,
            "ansatz_reps": 1, "entanglement": "linear", "optimizer": "COBYLA",
            "maxiter": 30, "shots": 1024, "noise_probability": 0.0,
        },
        "hybrid": {
            "provider_id": "pennylane_local", "execution_mode": "local_simulator",
            "backend": "default.qubit", "qubits": 4, "quantum_layers": 2,
            "feature_map": "angle", "classical_hidden_dimensions": [16, 8],
            "classical_activation": "relu", "optimizer": "adam", "learning_rate": 0.001,
            "epochs": 5, "batch_size": 16, "deterministic_seed": 42, "sample_cap": 160,
        },
        "seed": 42, "test_size": 0.2, "cv_folds": 3, "max_samples": 100,
        "duplicate_policy": "reject", "calibration": "none", "calibration_folds": 3,
        "probability_threshold": 0.5, "threshold_strategy": "fixed",
        "target_sensitivity": 0.95, "sampling_unit": "independent_samples", "group_column": None,
    }
    with session_scope() as session:
        session.add(Experiment(
            id=experiment_id, dataset_id=registered.id, name="Card fixture",
            status="completed", config=config, summary={"limitations": []},
        ))
        session.flush()
        if with_run:
            session.add(Run(
                id=run_id, experiment_id=experiment_id, dataset_id=registered.id,
                dataset_version_id=registered.current_version_id, status="completed",
                operation_key=f"test-card-run:{run_id}", config=config,
                execution_metadata={"quantum_providers": [{
                    "provider_id": "qiskit_local" if model_type in {"vqc", "qsvc", "qnn"} else "pennylane_local",
                    "backend_id": "statevector" if model_type in {"vqc", "qsvc", "qnn"} else "default.qubit",
                    "execution_mode": "local_simulator",
                    "capabilities": {"hardware_execution": "UNSUPPORTED"},
                    "configuration_fingerprint": "provider-fingerprint",
                }]} if model_type not in {"logistic_regression", "svm", "random_forest"} else {},
                reproducibility_metadata={"software": {"python": "test"}, "dataset_hash": registered.sha256},
                result_summary={"models_persisted": 1},
                configuration_fingerprint="configuration-fingerprint",
                reproducibility_status="complete",
            ))
            session.flush()
        session.add(ModelRecord(
            id=model_id, experiment_id=experiment_id, run_id=run_id if with_run else None,
            dataset_id=registered.id, model_type=model_type, status="ready",
            artifact_sha256="a" * 64,
            details=details or {"supports_probability": True, "secret": "must-not-leak"},
            metrics={"test": {"accuracy": 0.75, "sensitivity": 0.7, "raw_rows": ["must-not-leak"]}},
        ))
    return model_id


@pytest.mark.parametrize("model_type,expected_family", [
    ("logistic_regression", "classical"),
    ("vqc", "quantum"),
    ("hybrid_pennylane_torch", "hybrid_quantum_classical"),
])
def test_model_card_model_families_and_missing_evidence(registered, model_type, expected_family):
    details = {"quantum": {
        "provider_id": "qiskit_local" if model_type == "vqc" else "pennylane_local",
        "backend": "statevector" if model_type == "vqc" else "default.qubit",
        "execution_kind": "local_simulator", "real_hardware": False,
        "api_key": "must-not-leak",
    }} if expected_family != "classical" else {"supports_probability": True}
    model_id = _persist_model(registered, model_type, details=details)
    with session_scope() as session:
        card, _, _ = assemble_card(session, model_id)
    assert card["schema_version"] == MODEL_CARD_SCHEMA_VERSION
    assert card["model_identity"]["model_family"] == expected_family
    assert card["task"]["condition_task_status"] == "not_configured"
    assert card["calibration"]["status"] == "not_available"
    assert card["threshold"]["status"] == "not_available"
    assert card["external_validation"]["status"] == "not_available"
    assert card["distribution_shift"]["status"] == "not_available"
    assert card["multi_seed_evidence"]["status"] == "not_available"
    text = str(card)
    assert "must-not-leak" not in text
    assert "api_key" not in text
    assert "raw_rows" not in text
    assert "quantum advantage" in text.lower() if expected_family != "classical" else True


def test_card_is_deterministic_and_artifact_is_idempotent(registered):
    model_id = _persist_model(registered)
    with session_scope() as session:
        first_card, first_artifact = get_or_create_card(session, model_id)
        first_id = first_artifact.id
        first_hash = first_artifact.integrity_hash
    with session_scope() as session:
        second_card, second_artifact = get_or_create_card(session, model_id)
        count = session.scalar(select(func.count()).select_from(Artifact).where(
            Artifact.model_id == model_id, Artifact.artifact_type == "model_card"
        ))
    assert first_card == second_card
    assert second_artifact.id == first_id
    assert second_artifact.integrity_hash == first_hash
    assert count == 1


def test_legacy_model_without_run_reports_incomplete_provenance(registered):
    model_id = _persist_model(registered, with_run=False)
    with session_scope() as session:
        card, _, _ = assemble_card(session, model_id)
    assert card["card_status"] == "INCOMPLETE_EVIDENCE"
    assert card["model_identity"]["run_id"] == "not_available"
    assert "run" in card["reproducibility"]["missing_provenance_fields"]


def test_verified_demo_model_without_run_has_canonical_card(registered):
    model_id = _persist_model(
        registered, with_run=False,
        details={
            "experiment_kind": "precomputed_verified_demo",
            "dataset_provenance": {"library_slug": "early-stage-diabetes"},
            "supports_probability": True,
        },
    )
    with session_scope() as session:
        first, _, _ = assemble_card(session, model_id)
        second, _, _ = assemble_card(session, model_id)
    assert first == second
    assert first["card_status"] == "COMPLETE_WITH_LIMITATIONS"
    assert first["provenance"]["source_context"]["type"] == "verified_demo_experiment"
    assert first["reproducibility"]["status"] == "verified_precomputed_package"
    assert first["calibration"]["status"] == "not_available"
    assert first["threshold"]["status"] == "not_available"
    assert "run" not in first["reproducibility"]["missing_provenance_fields"]


def test_model_card_api_not_found_and_pagination(client, registered):
    missing = client.get(f"/api/models/{uuid4()}/card")
    assert missing.status_code == 404
    model_id = _persist_model(registered)
    response = client.get(f"/api/models/{model_id}/card")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == MODEL_CARD_SCHEMA_VERSION
    assert body["artifact"]["immutable"] is True
    assert client.get(f"/api/models/{model_id}/card/summary").status_code == 200
    evidence = client.get(f"/api/models/{model_id}/card/evidence")
    assert evidence.status_code == 200
    listing = client.get("/api/model-cards?limit=1&offset=0")
    assert listing.status_code == 200
    assert listing.json()["pagination"]["limit"] == 1
    assert listing.json()["pagination"]["total"] >= 1
    assert len(listing.json()["items"]) == 1