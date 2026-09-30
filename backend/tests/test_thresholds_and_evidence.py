import numpy as np
import pytest

from app.api.schemas import TrainingConfig
from app.data.splitting import prepare_data
from app.evaluation.thresholds import (
    operating_point,
    predictions_at_threshold,
    select_operating_point,
)
from app.experiments.comparison import build_evidence_pair
from app.models.training import train_model
from app.storage.entities import Experiment, ModelRecord


def test_fixed_threshold_behavior_remains_unchanged():
    result = select_operating_point(
        [0, 0, 1, 1], [.1, .4, .6, .9],
        strategy="fixed", fixed_threshold=.5, target_sensitivity=.95,
        threshold_units="positive_class_probability", cv_fold_count=2,
    )
    assert result["selected_threshold"] == .5
    assert result["threshold_source"] == "configured_fixed_threshold"
    assert predictions_at_threshold([.49, .5], .5).tolist() == [0, 1]


def test_sensitivity_target_maximizes_specificity_and_satisfies_target():
    y = [0, 0, 0, 1, 1, 1]
    scores = [.1, .2, .8, .4, .7, .9]
    result = select_operating_point(
        y, scores, strategy="target_sensitivity", fixed_threshold=.5,
        target_sensitivity=2 / 3, threshold_units="positive_class_probability",
        cv_fold_count=3,
    )
    feasible = [row for row in result["curve"] if row["sensitivity"] >= 2 / 3]
    assert result["threshold_feasible"] is True
    assert result["validation_metrics"]["sensitivity"] >= 2 / 3
    assert result["validation_metrics"]["specificity"] == max(row["specificity"] for row in feasible)
    assert result["threshold_source"] == "out_of_fold_validation"


def test_threshold_tie_breaking_is_deterministic():
    args = dict(
        y_true=[0, 0, 1, 1], scores=[.1, .2, .8, .8],
        strategy="target_sensitivity", fixed_threshold=.5, target_sensitivity=1,
        threshold_units="positive_class_probability", cv_fold_count=2,
    )
    first = select_operating_point(**args)
    second = select_operating_point(**args)
    assert first["selected_threshold"] == second["selected_threshold"] == .8


def test_infeasible_validation_evidence_is_truthful():
    result = select_operating_point(
        [0, 0, 0], [.1, .2, .3],
        strategy="target_sensitivity", fixed_threshold=.5, target_sensitivity=.95,
        threshold_units="positive_class_probability", cv_fold_count=3,
    )
    assert result["threshold_feasible"] is False
    assert result["selected_threshold"] is None
    assert "not achievable" in result["infeasible_reason"]


def test_training_selects_from_oof_only_and_locks_holdout_threshold(config, monkeypatch):
    configured = config.model_copy(update={"threshold_strategy": "target_sensitivity", "target_sensitivity": .8})
    data = prepare_data(configured)
    captured = {}
    from app.models import training as module
    actual = module.select_operating_point

    def spy(y_true, scores, **kwargs):
        captured["labels"] = len(y_true)
        captured["scores"] = len(scores)
        return actual(y_true, scores, **kwargs)

    monkeypatch.setattr(module, "select_operating_point", spy)
    bundle, metrics, details = train_model("logistic_regression", configured, data, lambda _: None)
    assert captured["labels"] == captured["scores"] == len(data.train)
    assert captured["labels"] != len(data.test)
    point = metrics["operating_point"]
    assert point["threshold_source"] == "out_of_fold_validation"
    assert bundle["operating_threshold"] == point["selected_threshold"]
    assert details["operating_point"]["selected_threshold"] == point["selected_threshold"]
    expected = operating_point(data.y[data.test], np.asarray(bundle["estimator"].predict_proba(data.X.iloc[data.test]))[:, 1], point["selected_threshold"])
    assert metrics["test"]["sensitivity"] == expected["sensitivity"]
    assert metrics["test"]["specificity"] == expected["specificity"]


def _record(identity, kind, sensitivity, training, quantum=None):
    return ModelRecord(
        id=identity, experiment_id="00000000-0000-0000-0000-000000000010",
        dataset_id="00000000-0000-0000-0000-000000000020", model_type=kind,
        status="ready",
        metrics={
            "test": {"accuracy": .7, "sensitivity": sensitivity, "specificity": .8, "precision": .75, "recall": sensitivity, "f1": .72, "roc_auc": .78},
            "timing": {"final_training_seconds": training, "cv_total_seconds": training * 2, "cv_fold_seconds": [training, training], "test_inference_seconds": .2, "test_inference_seconds_per_sample": .01},
        },
        details={"supports_probability": True, "quantum": quantum} if quantum is not None else {"supports_probability": True},
    )


def test_evidence_pair_contains_deltas_resources_fairness_and_neutral_result():
    experiment = Experiment(
        id="00000000-0000-0000-0000-000000000010",
        dataset_id="00000000-0000-0000-0000-000000000020",
        config={"probability_threshold": .5, "cv_folds": 2, "seed": 42, "pipeline": {"pca_components": 2}},
        summary={"comparison_fingerprint": "fingerprint", "split": {"split_hash": "split", "evaluated_sample_count": 30}, "dataset_provenance": {"dataset_hash": "hash"}},
    )
    classical = _record("00000000-0000-0000-0000-000000000001", "logistic_regression", .9, 1)
    quantum = _record(
        "00000000-0000-0000-0000-000000000002", "qnn", .7, 4,
        {"backend": "aer", "execution_kind": "finite-shot local quantum simulation", "shots": 128, "real_hardware": False,
         "configuration": {"optimizer": "COBYLA", "noise_probability": 0}, "objective_evaluations": 5,
         "trainable_parameter_count": 4, "circuit": {"qubits": 2, "logical_depth": 7, "gate_counts": {"cx": 2}, "parameter_count": 6}},
    )
    pair = build_evidence_pair(experiment, quantum, classical)
    assert pair["performance"]["sensitivity"]["delta_quantum_minus_classical"] == pytest.approx(-.2)
    assert pair["computational_cost"]["deltas_quantum_minus_classical"]["final_training_seconds"] == 3
    assert pair["computational_cost"]["quantum"]["test_inference_seconds_per_sample"] == .01
    assert pair["quantum_resources"]["logical_depth"] == 7
    assert pair["quantum_resources"]["real_hardware"] is False
    assert pair["fairness"]["preprocessing_fingerprint"] == "fingerprint"
    assert "classical model produced higher sensitivity" in pair["conclusion"]
    assert "general quantum advantage" in pair["conclusion"]
    assert pair["test_metric_delta_quantum_minus_classical"]["sensitivity"] < 0


def test_missing_quantum_resources_are_safe():
    experiment = Experiment(id="00000000-0000-0000-0000-000000000010", dataset_id="00000000-0000-0000-0000-000000000020", config={}, summary={})
    pair = build_evidence_pair(
        experiment,
        _record("00000000-0000-0000-0000-000000000002", "qsvc", .5, 2, {}),
        _record("00000000-0000-0000-0000-000000000001", "svm", .5, 1),
    )
    assert pair["quantum_resources"]["logical_depth"] is None
    assert pair["quantum_resources"]["real_hardware"] is False