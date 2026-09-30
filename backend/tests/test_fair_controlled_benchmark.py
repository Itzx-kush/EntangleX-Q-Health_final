from copy import deepcopy
from uuid import uuid4

import pytest

from app.experiments.comparison import build_evidence_pair
from app.storage.entities import Experiment, ModelRecord
from app.utils.serialization import fingerprint


def conditions():
    value = {
        "dataset_id": "dataset-1", "dataset_hash": "a" * 64, "target": "diabetes_status",
        "positive_label": "positive", "negative_label": "negative", "source_row_count": 520,
        "evaluated_row_count": 40, "sample_pool_hash": "pool", "sampled_row_indices": list(range(40)),
        "train_indices": list(range(30)), "test_indices": list(range(30, 40)), "split_hash": "split",
        "seed": 23, "test_size": .25, "cv_folds": 2, "duplicate_policy": "drop_exact", "max_samples": 40,
        "representation": {"raw_input_features": ["age", "polyuria"], "selected_feature_count": 2,
            "feature_selection": {"method": "anova", "k_features": 2, "variance_threshold": 0.0},
            "pca_components": 2, "angle_scaling": True, "final_representation_dimension": 2,
            "hybrid_qubits": 2, "hybrid_quantum_layers": 1, "pipeline": {"pca_components": 2, "angle_scaling": True}},
        "threshold_strategy": "target_sensitivity", "target_sensitivity": .8,
    }
    value["comparison_fingerprint"] = fingerprint(value)
    return value


def record(kind, condition, *, missing_timing=False):
    timing = {"final_training_seconds": 1.0, "cv_total_seconds": 2.0, "cv_fold_seconds": [1.0, 1.0],
              "test_inference_seconds": .02, "test_inference_seconds_per_sample": .002}
    if missing_timing:
        timing["test_inference_seconds"] = None
    quantum = None if kind == "random_forest" else {"framework": "PennyLane", "classical_framework": "PyTorch",
        "backend": "default.qubit", "execution_kind": "local PennyLane quantum simulation", "real_hardware": False,
        "qubits": 2, "quantum_layers": 1, "optimizer": "adam", "learning_rate": .001, "epochs": 2,
        "quantum_parameter_count": 6, "total_parameter_count": 23, "circuit": {"logical_depth": 5, "gate_counts": {"RY": 2}}}
    return ModelRecord(id=str(uuid4()), experiment_id="experiment-1", dataset_id=condition["dataset_id"],
        model_type=kind, status="ready", metrics={"test": {"accuracy": .8, "sensitivity": .8, "specificity": .8,
        "precision": .8, "recall": .8, "f1": .8, "roc_auc": .8, "true_positives": 4, "true_negatives": 4,
        "false_positives": 1, "false_negatives": 1, "sample_count": 10}, "timing": timing},
        details={"comparison_conditions": condition, "quantum": quantum, "supports_probability": True})


def experiment():
    return Experiment(id="experiment-1", dataset_id="dataset-1", config={"threshold_strategy": "target_sensitivity"}, summary={})


def pair_with(change=None, *, missing_timing=False):
    classical_conditions, hybrid_conditions = conditions(), deepcopy(conditions())
    if change:
        target, key, value = change
        selected = hybrid_conditions if target == "hybrid" else classical_conditions
        if key.startswith("representation."):
            selected["representation"][key.split(".", 1)[1]] = value
        else:
            selected[key] = value
        selected["comparison_fingerprint"] = fingerprint({k: v for k, v in selected.items() if k != "comparison_fingerprint"})
    return build_evidence_pair(experiment(), record("hybrid_pennylane_torch", hybrid_conditions, missing_timing=missing_timing), record("random_forest", classical_conditions))


def test_fair_random_forest_hybrid_pair_is_controlled_and_complete():
    pair = pair_with()
    fairness = pair["fairness"]
    assert fairness["controlled_comparison"] is True
    assert fairness["status"] == "CONTROLLED COMPARISON"
    assert all(fairness[key] for key in ["dataset_match", "dataset_hash_match", "sample_pool_match", "split_match",
        "split_hash_match", "preprocessing_match", "feature_representation_match", "pca_dimension_match",
        "sample_budget_match", "cv_fold_match", "seed_match", "threshold_strategy_match", "holdout_match"])
    assert pair["benchmark_type"] == "fair_controlled_diabetes_benchmark"
    assert pair["holdout_results"]["hybrid"]["true_positives"] == 4
    assert pair["quantum_resources"]["backend"] == "default.qubit"
    assert pair["quantum_resources"]["shots"] is None
    assert pair["quantum_resources"]["real_hardware"] is False
    assert "winner" not in pair["conclusion"].lower()
    assert "do not establish" in pair["conclusion"]


@pytest.mark.parametrize("change,failed_check", [
    (("hybrid", "dataset_hash", "b" * 64), "dataset_hash_match"),
    (("hybrid", "split_hash", "different"), "split_hash_match"),
    (("hybrid", "test_indices", [29, *range(31, 40)]), "holdout_match"),
    (("hybrid", "evaluated_row_count", 39), "sample_budget_match"),
    (("hybrid", "representation.pca_components", 3), "pca_dimension_match"),
    (("hybrid", "threshold_strategy", "fixed"), "threshold_strategy_match"),
    (("hybrid", "cv_folds", 3), "cv_fold_match"),
    (("hybrid", "seed", 42), "seed_match"),
])
def test_fairness_mismatch_prevents_controlled_label(change, failed_check):
    pair = pair_with(change)
    assert pair["fairness"]["controlled_comparison"] is False
    assert pair["fairness"]["status"] == "NOT CONTROLLED"
    assert pair["fairness"][failed_check] is False
    assert pair["fairness"]["mismatch_reasons"]


def test_missing_measurement_remains_null_and_is_disclosed():
    pair = pair_with(missing_timing=True)
    assert pair["computational_cost"]["quantum"]["test_inference_seconds"] is None
    assert pair["computational_cost"]["deltas_quantum_minus_classical"]["test_inference_seconds"] is None
    assert pair["fairness"]["status"] == "CONTROLLED COMPARISON WITH LIMITATIONS"
