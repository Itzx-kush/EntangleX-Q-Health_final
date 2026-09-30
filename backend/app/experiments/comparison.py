from __future__ import annotations

from statistics import mean

from sqlalchemy import select

from ..api.schemas import ModelOut
from ..database import session_scope
from ..storage.entities import Experiment, ModelRecord, RobustnessRecord
from ..storage.repository import require
from ..utils.serialization import clean_json


COMPARE_METRICS = ["accuracy", "sensitivity", "specificity", "precision", "recall", "f1", "roc_auc"]
QUANTUM_MODELS = {"vqc", "qsvc", "qnn", "hybrid_pennylane_torch"}


def _difference(quantum, classical):
    return quantum - classical if quantum is not None and classical is not None else None


def _timing(metrics: dict) -> dict:
    timing = metrics.get("timing") or {}
    folds = timing.get("cv_fold_seconds") or []
    return {
        "final_training_seconds": timing.get("final_training_seconds"),
        "cv_total_seconds": timing.get("cv_total_seconds"),
        "cv_mean_fold_seconds": mean(folds) if folds else None,
        "test_inference_seconds": timing.get("test_inference_seconds"),
        "test_inference_seconds_per_sample": timing.get("test_inference_seconds_per_sample"),
    }


def _quantum_resources(model: ModelRecord) -> dict:
    quantum = (model.details or {}).get("quantum") or {}
    circuit = quantum.get("circuit") or {}
    configuration = quantum.get("configuration") or {}
    return {
        "backend": quantum.get("backend"),
        "execution_kind": quantum.get("execution_kind"),
        "qubits": circuit.get("qubits", configuration.get("qubits")),
        "shots": quantum.get("shots", configuration.get("shots")),
        "logical_depth": circuit.get("logical_depth"),
        "gate_counts": circuit.get("gate_counts"),
        "total_parameter_count": circuit.get("parameter_count"),
        "trainable_parameter_count": quantum.get("trainable_parameter_count"),
        "optimizer": configuration.get("optimizer"),
        "optimizer_objective_evaluations": quantum.get("objective_evaluations"),
        "noise_probability": quantum.get("noise_probability", configuration.get("noise_probability")),
        "real_hardware": quantum.get("real_hardware", False),
        "resource_semantics": "Logical circuit resources and simulator settings; not actual hardware wall-clock cost.",
    }


def _legacy_operating_point(model: ModelRecord, experiment: Experiment) -> dict:
    configured = experiment.config or {}
    probability = bool((model.details or {}).get("supports_probability"))
    threshold = configured.get("probability_threshold", 0.5) if probability else 0.0
    return {
        "selection_strategy": configured.get("threshold_strategy", "fixed"),
        "target_sensitivity": configured.get("target_sensitivity"),
        "selected_threshold": threshold,
        "threshold_units": "positive_class_probability" if probability else "decision_score",
        "threshold_feasible": True,
        "threshold_source": "legacy_fixed_configuration",
        "validation_metrics": None,
        "holdout_metrics": {
            key: (model.metrics or {}).get("test", {}).get(key)
            for key in ["sensitivity", "specificity", "precision", "recall", "f1", "accuracy", "roc_auc"]
        },
        "number_of_oof_samples": None,
        "cv_fold_count": configured.get("cv_folds"),
        "curve": [],
        "interpretation": "Legacy fixed research threshold; not a clinically validated screening cutoff.",
    }


def _operating_point(model: ModelRecord, experiment: Experiment) -> dict:
    return (
        (model.metrics or {}).get("operating_point")
        or (model.details or {}).get("operating_point")
        or _legacy_operating_point(model, experiment)
    )


def _fairness(experiment: Experiment, q: ModelRecord, c: ModelRecord) -> dict:
    summary = experiment.summary or {}
    split = summary.get("split") or {}
    provenance = summary.get("dataset_provenance") or {}
    config = experiment.config or {}
    return {
        "dataset_id": experiment.dataset_id,
        "dataset_hash": provenance.get("dataset_hash"),
        "experiment_id": experiment.id,
        "split_hash": split.get("split_hash"),
        "common_sample_count": split.get("evaluated_sample_count"),
        "source_sample_count": split.get("source_sample_count"),
        "selected_feature_representation": {
            "features": (q.details or {}).get("input_features") or (c.details or {}).get("input_features"),
            "preprocessing": config.get("pipeline"),
        },
        "preprocessing_fingerprint": summary.get("comparison_fingerprint"),
        "cv_fold_count": config.get("cv_folds"),
        "seed": config.get("seed"),
        "threshold_strategy": config.get("threshold_strategy", "fixed"),
        "controlled_comparison": True,
    }


def _neutral_conclusion(performance: dict, cost: dict) -> str:
    delta = performance["sensitivity"]["delta_quantum_minus_classical"]
    if delta is None:
        sensitivity = "Sensitivity could not be compared because one or both values are undefined."
    elif delta > 0:
        sensitivity = "On this shared held-out benchmark, the quantum model produced higher sensitivity than the classical model."
    elif delta < 0:
        sensitivity = "On this shared held-out benchmark, the classical model produced higher sensitivity than the quantum model."
    else:
        sensitivity = "The models produced equal sensitivity on this shared held-out benchmark."
    training_delta = cost["deltas_quantum_minus_classical"]["final_training_seconds"]
    if training_delta is None:
        cost_text = "Comparable final-training timing was not available."
    elif training_delta > 0:
        cost_text = "The quantum model required more measured final-training time in this run."
    elif training_delta < 0:
        cost_text = "The quantum model required less measured final-training time in this run."
    else:
        cost_text = "The models had equal measured final-training time in this run."
    return (
        f"{sensitivity} {cost_text} This is an observed benchmark difference, not clinical validation, "
        "statistical superiority, or evidence of general quantum advantage."
    )


def _robustness_evidence(quantum: ModelRecord, classical: ModelRecord, records=()) -> dict:
    latest = {}
    for record in records:
        result = record.result or {}
        key = (
            record.model_id,
            record.perturbation_type,
            record.perturbation_level,
            record.random_seed,
            result.get("sample_count"),
        )
        latest.setdefault(key, result)
    scenario_keys = {
        key[1:] for key in latest
        if key[0] in {quantum.id, classical.id}
    }
    scenarios = []
    for scenario_key in sorted(scenario_keys, key=lambda value: (value[0], value[1], value[2])):
        q_result = latest.get((quantum.id, *scenario_key))
        c_result = latest.get((classical.id, *scenario_key))
        delta_difference = {}
        for metric in COMPARE_METRICS:
            q_delta = (q_result or {}).get("degradation_delta", {}).get(metric)
            c_delta = (c_result or {}).get("degradation_delta", {}).get(metric)
            delta_difference[metric] = _difference(q_delta, c_delta)
        scenarios.append({
            "perturbation_type": scenario_key[0],
            "perturbation_level": scenario_key[1],
            "random_seed": scenario_key[2],
            "sample_count": scenario_key[3],
            "classical": c_result,
            "quantum": q_result,
            "delta_difference_quantum_minus_classical": delta_difference,
            "interpretation": "Observed degradation differences only; no robustness winner or quantum advantage is inferred.",
        })
    if not scenarios:
        return {
            "status": "not_evaluated",
            "scenarios": [],
            "note": "No controlled robustness record is available for this model pair.",
        }
    complete = all(item["classical"] is not None and item["quantum"] is not None for item in scenarios)
    return {
        "status": "evaluated" if complete else "partial",
        "scenarios": scenarios,
        "note": "Paired models use matching perturbation type, level, seed, bounded held-out samples, and locked thresholds.",
        "limitations": [
            "Controlled synthetic benchmark perturbations are not clinical robustness evidence.",
            "No model ranking or quantum robustness advantage is claimed.",
        ],
    }


def build_evidence_pair(experiment: Experiment, quantum: ModelRecord, classical: ModelRecord, robustness_records=()) -> dict:
    q_test = (quantum.metrics or {}).get("test") or {}
    c_test = (classical.metrics or {}).get("test") or {}
    performance = {
        metric: {
            "classical": c_test.get(metric),
            "quantum": q_test.get(metric),
            "delta_quantum_minus_classical": _difference(q_test.get(metric), c_test.get(metric)),
        }
        for metric in COMPARE_METRICS
    }
    q_timing, c_timing = _timing(quantum.metrics or {}), _timing(classical.metrics or {})
    cost = {
        "classical": c_timing,
        "quantum": q_timing,
        "deltas_quantum_minus_classical": {
            key: _difference(q_timing.get(key), c_timing.get(key))
            for key in q_timing
        },
        "semantics": "Measured runtime from this experiment; circuit depth is not used to estimate runtime.",
    }
    pair = {
        "quantum_model": quantum.id,
        "classical_model": classical.id,
        "quantum_type": quantum.model_type,
        "classical_type": classical.model_type,
        "performance": performance,
        "computational_cost": cost,
        "quantum_resources": _quantum_resources(quantum),
        "fairness": _fairness(experiment, quantum, classical),
        "operating_points": {
            "classical": _operating_point(classical, experiment),
            "quantum": _operating_point(quantum, experiment),
        },
        "robustness": _robustness_evidence(quantum, classical, robustness_records),
        "limitations": [
            "Benchmark evidence only; no clinical validation.",
            "Quantum execution is simulator-only unless the recorded backend explicitly states otherwise.",
            "Logical circuit resources are not actual hardware wall-clock cost.",
            "No general quantum advantage is established.",
        ],
    }
    pair["conclusion"] = _neutral_conclusion(performance, cost)
    # Preserve the original public fields for existing API clients.
    pair["test_metric_delta_quantum_minus_classical"] = {
        key: performance[key]["delta_quantum_minus_classical"] for key in COMPARE_METRICS
    }
    pair["final_training_seconds_delta"] = cost["deltas_quantum_minus_classical"]["final_training_seconds"]
    return clean_json(pair)


def comparison(identity: str) -> dict:
    with session_scope() as session:
        experiment = require(session, Experiment, identity)
        models = list(session.scalars(
            select(ModelRecord)
            .where(ModelRecord.experiment_id == identity)
            .order_by(ModelRecord.created_at)
        ))
        robustness_records = list(session.scalars(
            select(RobustnessRecord)
            .where(RobustnessRecord.experiment_id == identity)
            .order_by(RobustnessRecord.created_at.desc())
        ))
    ready = [model for model in models if model.status == "ready"]
    classical = [model for model in ready if model.model_type not in QUANTUM_MODELS]
    quantum = [model for model in ready if model.model_type in QUANTUM_MODELS]
    pairs = [build_evidence_pair(experiment, q, c, robustness_records) for q in quantum for c in classical]
    return {
        "experiment_id": identity,
        "dataset_id": experiment.dataset_id,
        "comparison_fingerprint": (experiment.summary or {}).get("comparison_fingerprint"),
        "split": (experiment.summary or {}).get("split"),
        "models": [ModelOut.model_validate(model).model_dump(mode="json") for model in models],
        "pairs": pairs,
        "conclusion": (
            "No completed classical-quantum pair is available."
            if not pairs else
            "All completed pairs are shown, including unfavorable quantum results. Review measured performance, operating points, timing, logical resources, and limitations together."
        ),
        "limitations": [
            "Comparison is restricted to one experiment to enforce shared data, target, selected features, preprocessing and splits.",
            "A benchmark result is not clinical validation, statistical significance, or proof of quantum advantage.",
        ],
    }
