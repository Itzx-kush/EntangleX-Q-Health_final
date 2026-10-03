from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.controlled_comparison.service import (
    CONTROLLED_COMPARISON_SCHEMA_VERSION,
    _pair_checks,
    _required_status,
    create_protocol,
    preflight_protocol,
    protocol_payload,
)
from app.database import session_scope
from app.storage.entities import Artifact, ControlledComparisonProtocol, Experiment, ModelRecord, Run
from app.utils.serialization import fingerprint


def _configuration(dataset_id, version_id):
    pipeline = {
        "imputer": "median", "scaler": "standard", "outlier_strategy": "none",
        "log_features": [], "ratios": [], "selection": "anova", "k_features": 4,
        "variance_threshold": 0.0, "pca_components": 4, "pca_whiten": False,
        "angle_scaling": True,
    }
    return {
        "dataset_id": dataset_id, "dataset_version_id": version_id,
        "features": ["a", "b", "c", "d"], "models": ["logistic_regression", "vqc"],
        "pipeline": pipeline, "parameters": {"logistic_c": 1.0},
        "quantum": {"provider_id": "qiskit_local", "backend": "statevector", "execution_mode": "local_simulator", "qubits": 4},
        "hybrid": {"provider_id": "pennylane_local", "backend": "default.qubit", "qubits": 4},
        "seed": 42, "test_size": 0.2, "cv_folds": 3, "max_samples": 100,
        "duplicate_policy": "reject", "sampling_unit": "independent_samples",
        "group_column": None, "threshold_strategy": "target_sensitivity",
        "target_sensitivity": 0.9, "calibration": "none",
    }


def _conditions(dataset_id, version_id, dataset_hash, *, split="split", scaler="standard"):
    pipeline = _configuration(dataset_id, version_id)["pipeline"]
    pipeline["scaler"] = scaler
    representation = {
        "raw_input_features": ["a", "b", "c", "d"],
        "selected_feature_count": 4,
        "feature_selection": {"method": "anova", "k_features": 4, "variance_threshold": 0.0},
        "pca_components": 4, "angle_scaling": True, "final_representation_dimension": 4,
        "pipeline": pipeline,
    }
    result = {
        "dataset_id": dataset_id, "dataset_version_id": version_id, "dataset_hash": dataset_hash,
        "target": "observed_class", "positive_label": "positive", "negative_label": "negative",
        "source_row_count": 120, "evaluated_row_count": 100,
        "sample_pool_hash": "pool", "sampled_row_indices": list(range(100)),
        "train_indices": list(range(80)), "test_indices": list(range(80, 100)),
        "split_hash": split, "seed": 42, "test_size": 0.2, "cv_folds": 3,
        "duplicate_policy": "reject", "max_samples": 100, "representation": representation,
        "threshold_strategy": "target_sensitivity", "target_sensitivity": 0.9,
    }
    result["comparison_fingerprint"] = fingerprint(result)
    return result


def _persist_pair(registered, *, mutate_quantum=None, model_types=("logistic_regression", "vqc")):
    experiment_id, run_id = str(uuid4()), str(uuid4())
    version_id = registered.current_version_id
    config = _configuration(registered.id, version_id)
    base = _conditions(registered.id, version_id, registered.sha256)
    quantum_conditions = deepcopy(base)
    if mutate_quantum:
        mutate_quantum(quantum_conditions)
    operating = {
        "selection_strategy": "target_sensitivity", "target_sensitivity": 0.9,
        "selected_threshold": 0.42, "threshold_feasible": True,
        "threshold_source": "out_of_fold_training_validation",
        "validation_metrics": {"sensitivity": 0.9}, "holdout_metrics": {"accuracy": 0.7},
        "number_of_oof_samples": 80, "cv_fold_count": 3, "curve": [],
        "interpretation": "Research operating point.",
    }
    timing = {
        "final_training_seconds": 1.0, "cv_total_seconds": 2.0,
        "cv_fold_seconds": [0.6, 0.7, 0.7], "test_inference_seconds": 0.1,
        "test_inference_seconds_per_sample": 0.005,
    }
    ids = [str(uuid4()) for _ in model_types]
    uses_hybrid = "hybrid_pennylane_torch" in model_types
    with session_scope() as session:
        session.add(Experiment(id=experiment_id, dataset_id=registered.id, name=f"Controlled fixture {experiment_id[:8]}", status="completed", config=config, summary={"split": {}}))
        session.flush()
        session.add(Run(
            id=run_id, experiment_id=experiment_id, dataset_id=registered.id,
            dataset_version_id=version_id, status="completed", operation_key=f"controlled-test:{run_id}",
            config=config, execution_metadata={"quantum_providers": [{
                "provider_id": "pennylane_local" if uses_hybrid else "qiskit_local",
                "backend_id": "default.qubit" if uses_hybrid else "statevector",
                "execution_mode": "local_simulator", "capabilities": {"hardware_execution": "UNSUPPORTED"},
                "configuration_fingerprint": "provider-fingerprint",
            }]}, reproducibility_metadata={}, result_summary={},
            configuration_fingerprint="run-fingerprint", reproducibility_status="complete",
        ))
        session.flush()
        for index, model_type in enumerate(model_types):
            conditions = base if index == 0 else quantum_conditions
            details = {
                "configuration": config, "comparison_conditions": conditions,
                "common_representation": conditions["representation"],
                "split": {}, "positive_label": "positive", "negative_label": "negative",
                "supports_probability": True, "operating_point": operating,
            }
            if model_type in {"vqc", "qsvc", "qnn", "hybrid_pennylane_torch"}:
                hybrid = model_type == "hybrid_pennylane_torch"
                details["quantum"] = {
                    "provider_id": "pennylane_local" if hybrid else "qiskit_local",
                    "backend": "default.qubit" if hybrid else "statevector",
                    "execution_kind": "local_simulator", "real_hardware": False,
                    "qubits": 4, "api_key": "must-not-leak",
                }
            session.add(ModelRecord(
                id=ids[index], experiment_id=experiment_id, run_id=run_id,
                dataset_id=registered.id, model_type=model_type, status="ready",
                artifact_sha256=str(index + 1) * 64, details=details,
                metrics={"test": {"accuracy": 0.7 + index / 10, "sensitivity": 0.8, "specificity": 0.6, "sample_count": 20}, "timing": timing, "operating_point": operating},
            ))
    return experiment_id, ids


def test_pair_matrix_preflight_and_idempotent_artifact(registered):
    experiment_id, ids = _persist_pair(registered)
    with session_scope() as session:
        preflight = preflight_protocol(session, experiment_id)
        assert preflight["preflight"] is True
        assert len(preflight["comparison_pairs"]) == 1
        assert session.scalar(select(func.count()).select_from(ControlledComparisonProtocol)) == 0
        first = create_protocol(session, experiment_id)
        first_id = first.id
    with session_scope() as session:
        second = create_protocol(session, experiment_id)
        assert second.id == first_id
        assert session.scalar(select(func.count()).select_from(Artifact).where(Artifact.artifact_type == "controlled_comparison_protocol")) == 1
        payload = protocol_payload(second)
        assert second.protocol_fingerprint == first.protocol_fingerprint
    assert payload["schema_version"] == CONTROLLED_COMPARISON_SCHEMA_VERSION
    assert payload["status"] == "CONTROLLED_WITH_LIMITATIONS"
    assert payload["comparison_pairs"][0]["quantum_provider_provenance"]["real_hardware"] is False
    assert "must-not-leak" not in str(payload)
    assert "patient" not in str(payload).lower()


def test_multiple_classical_quantum_pairs_are_supported(registered):
    experiment_id, _ = _persist_pair(registered, model_types=("logistic_regression", "random_forest", "vqc"))
    with session_scope() as session:
        result = preflight_protocol(session, experiment_id)
    assert len(result["classical_model_ids"]) == 2
    assert len(result["quantum_model_ids"]) == 1
    assert len(result["comparison_pairs"]) == 2


def test_hybrid_pair_is_supported_without_hardware_claim(registered):
    experiment_id, _ = _persist_pair(registered, model_types=("logistic_regression", "hybrid_pennylane_torch"))
    with session_scope() as session:
        result = preflight_protocol(session, experiment_id)
    pair = result["comparison_pairs"][0]
    assert pair["quantum_model"]["family"] == "hybrid"
    assert pair["quantum_provider_provenance"]["provider_id"] == "pennylane_local"
    assert pair["quantum_provider_provenance"]["real_hardware"] is False
    assert pair["quantum_provider_provenance"]["runtime_semantics"] == "local_or_remote_simulator_not_qpu_runtime"


@pytest.mark.parametrize("mutation,failed_check", [
    (lambda value: value.update(dataset_id=str(uuid4())), "dataset_match"),
    (lambda value: value.update(dataset_version_id=str(uuid4())), "dataset_version_match"),
    (lambda value: value.update(dataset_hash="different"), "dataset_hash_match"),
    (lambda value: value.update(sample_pool_hash="different"), "sample_pool_match"),
    (lambda value: value.update(test_indices=[90, 91]), "test_population_match"),
    (lambda value: value.update(evaluated_row_count=50), "sample_budget_match"),
    (lambda value: value.update(split_hash="different"), "split_hash_match"),
    (lambda value: value["representation"]["pipeline"].update(scaler="robust"), "preprocessing_match"),
    (lambda value: value["representation"].update(pca_components=3), "feature_representation_match"),
    (lambda value: value.update(threshold_strategy="fixed"), "threshold_protocol_match"),
])
def test_required_mismatch_is_not_controlled(registered, mutation, failed_check):
    experiment_id, _ = _persist_pair(registered, mutate_quantum=mutation)
    with session_scope() as session:
        result = preflight_protocol(session, experiment_id)
    pair = result["comparison_pairs"][0]
    assert pair["status"] == "NOT_CONTROLLED"
    assert next(item for item in pair["control_checks"] if item["name"] == failed_check)["status"] == "FAIL"


def test_invalid_roles_and_missing_pair_are_rejected(registered):
    experiment_id, ids = _persist_pair(registered)
    with session_scope() as session:
        with pytest.raises(Exception) as wrong_role:
            create_protocol(session, experiment_id, classical_ids=[ids[1]], quantum_ids=[ids[0]])
        assert getattr(wrong_role.value, "code", None) == "invalid_classical_role"
    experiment_id_2, _ = _persist_pair(registered, model_types=("logistic_regression", "random_forest"))
    with session_scope() as session:
        blocked = preflight_protocol(session, experiment_id_2)
        assert blocked["status"] == "BLOCKED"
        assert blocked["blockers"][0]["code"] == "comparison_pair_unavailable"


def test_status_derivation_distinguishes_controlled_incomplete_and_failed():
    pass_check = {"name": "dataset_match", "status": "PASS", "passed": True}
    unknown = {"name": "split_hash_match", "status": "UNKNOWN", "passed": None}
    failed = {"name": "split_hash_match", "status": "FAIL", "passed": False}
    assert _required_status([pass_check]) == "CONTROLLED"
    assert _required_status([pass_check, unknown]) == "INCOMPLETE_EVIDENCE"
    assert _required_status([pass_check, failed]) == "NOT_CONTROLLED"


def test_group_calibration_and_threshold_provenance_mismatches(registered):
    experiment_id, ids = _persist_pair(registered)
    with session_scope() as session:
        quantum = session.get(ModelRecord, ids[1])
        details = deepcopy(quantum.details)
        details["configuration"]["sampling_unit"] = "grouped_samples"
        details["configuration"]["group_column"] = "patient_id"
        details["configuration"]["calibration"] = "sigmoid"
        details["operating_point"]["threshold_source"] = "legacy_fixed_configuration"
        quantum.details = details
        metrics = deepcopy(quantum.metrics)
        metrics["operating_point"]["threshold_source"] = "legacy_fixed_configuration"
        quantum.metrics = metrics
    with session_scope() as session:
        result = preflight_protocol(session, experiment_id)
    checks = {item["name"]: item["status"] for item in result["comparison_pairs"][0]["control_checks"]}
    assert checks["grouping_match"] == "FAIL"
    assert checks["calibration_protocol_match"] == "FAIL"
    assert checks["threshold_lock_verified"] == "UNKNOWN"
    assert result["comparison_pairs"][0]["status"] == "NOT_CONTROLLED"


def test_api_persists_and_integrates_protocol(client, registered):
    experiment_id, _ = _persist_pair(registered)
    preflight = client.post(f"/api/experiments/{experiment_id}/controlled-comparison/preflight", json={})
    assert preflight.status_code == 200
    created = client.post(f"/api/experiments/{experiment_id}/controlled-comparison", json={})
    assert created.status_code == 201
    protocol = created.json()
    assert client.get(f"/api/experiments/{experiment_id}/controlled-comparison").status_code == 200
    assert client.get(f"/api/experiments/{experiment_id}/controlled-comparison/{protocol['protocol_id']}/provenance").status_code == 200
    comparison = client.get(f"/api/experiments/{experiment_id}/comparison")
    assert comparison.status_code == 200
    body = comparison.json()
    assert body["controlled_protocol"]["protocol_id"] == protocol["protocol_id"]
    assert body["pairs"][0]["controlled_protocol_pair"]["status"] == "CONTROLLED_WITH_LIMITATIONS"
    assert len(body["controlled_benchmarks"]) == 1