from __future__ import annotations

from statistics import mean
from sqlalchemy import select

from ..api.schemas import ModelOut
from ..database import session_scope
from ..storage.entities import ControlledComparisonProtocol, Experiment, ModelRecord, RobustnessRecord
from ..storage.repository import require
from ..utils.serialization import clean_json, fingerprint

COMPARE_METRICS = ["accuracy", "sensitivity", "specificity", "precision", "recall", "f1", "roc_auc"]
QUANTUM_MODELS = {"vqc", "qsvc", "qnn", "hybrid_pennylane_torch"}
MODEL_NAMES = {
    "random_forest": "Random Forest",
    "hybrid_pennylane_torch": "PennyLane + PyTorch hybrid",
    "logistic_regression": "Logistic Regression",
    "svm": "SVM",
    "vqc": "VQC",
    "qsvc": "QSVC",
    "qnn": "QNN",
}


def _difference(hybrid, classical):
    return hybrid - classical if hybrid is not None and classical is not None else None


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
        "framework": quantum.get("framework"),
        "classical_framework": quantum.get("classical_framework"),
        "backend": quantum.get("backend", circuit.get("backend")),
        "execution_kind": quantum.get("execution_kind", circuit.get("execution_kind")),
        "timing_label": "Measured local simulator/runtime timing",
        "qubits": quantum.get("qubits", circuit.get("qubits", configuration.get("qubits"))),
        "quantum_layers": quantum.get("quantum_layers", configuration.get("quantum_layers")),
        "shots": quantum.get("shots", configuration.get("shots")),
        "logical_depth": circuit.get("logical_depth"),
        "gate_counts": circuit.get("gate_counts"),
        "total_parameter_count": quantum.get("total_parameter_count", circuit.get("parameter_count")),
        "trainable_parameter_count": quantum.get("quantum_parameter_count", quantum.get("trainable_parameter_count")),
        "optimizer": quantum.get("optimizer", configuration.get("optimizer")),
        "learning_rate": quantum.get("learning_rate", configuration.get("learning_rate")),
        "epochs": quantum.get("epochs", configuration.get("epochs")),
        "optimizer_objective_evaluations": quantum.get("objective_evaluations"),
        "noise_probability": quantum.get("noise_probability", configuration.get("noise_probability")),
        "real_hardware": bool(quantum.get("real_hardware", False)),
        "resource_semantics": "Logical/simulator resources are not equivalent to real-QPU wall-clock cost.",
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
        "holdout_metrics": {key: (model.metrics or {}).get("test", {}).get(key) for key in COMPARE_METRICS},
        "number_of_oof_samples": None,
        "cv_fold_count": configured.get("cv_folds"),
        "curve": [],
        "interpretation": "Legacy fixed research threshold; not a clinically validated cutoff.",
    }


def _operating_point(model: ModelRecord, experiment: Experiment) -> dict:
    return ((model.metrics or {}).get("operating_point") or (model.details or {}).get("operating_point") or _legacy_operating_point(model, experiment))


def _fallback_conditions(experiment: Experiment, model: ModelRecord) -> dict:
    summary, config, details = experiment.summary or {}, experiment.config or {}, model.details or {}
    split = details.get("split") or summary.get("split") or {}
    provenance = details.get("dataset_provenance") or summary.get("dataset_provenance") or {}
    pipeline = config.get("pipeline") or {}
    hybrid = config.get("hybrid") or {}
    representation = details.get("common_representation") or {
        "raw_input_features": details.get("input_features"),
        "selected_feature_count": pipeline.get("k_features"),
        "feature_selection": {key: pipeline.get(key) for key in ("selection", "k_features", "variance_threshold")},
        "pca_components": pipeline.get("pca_components"),
        "angle_scaling": pipeline.get("angle_scaling"),
        "final_representation_dimension": pipeline.get("pca_components"),
        "hybrid_qubits": hybrid.get("qubits") or ((details.get("quantum") or {}).get("qubits")),
        "hybrid_quantum_layers": hybrid.get("quantum_layers"),
        "pipeline": pipeline,
    }
    dataset_hash = provenance.get("dataset_hash") or provenance.get("sha256")
    conditions = {
        "dataset_id": model.dataset_id,
        "dataset_hash": dataset_hash,
        "target": provenance.get("target"),
        "positive_label": details.get("positive_label") or provenance.get("positive_label"),
        "negative_label": details.get("negative_label") or provenance.get("negative_label"),
        "source_row_count": split.get("source_sample_count") or provenance.get("row_count"),
        "evaluated_row_count": split.get("evaluated_sample_count"),
        "sample_pool_hash": split.get("sample_pool_hash"),
        "sampled_row_indices": split.get("sampled_row_indices"),
        "train_indices": split.get("train_indices"),
        "test_indices": split.get("test_indices"),
        "split_hash": split.get("split_hash"),
        "seed": config.get("seed"),
        "test_size": config.get("test_size"),
        "cv_folds": config.get("cv_folds"),
        "duplicate_policy": config.get("duplicate_policy"),
        "max_samples": config.get("max_samples"),
        "representation": representation,
        "threshold_strategy": config.get("threshold_strategy", "fixed"),
        "target_sensitivity": config.get("target_sensitivity"),
    }
    conditions["comparison_fingerprint"] = summary.get("comparison_fingerprint") or fingerprint(conditions)
    return conditions


def _conditions(experiment: Experiment, model: ModelRecord) -> dict:
    return (model.details or {}).get("comparison_conditions") or _fallback_conditions(experiment, model)


def _verified_equal(left, right, key) -> bool:
    return left.get(key) is not None and right.get(key) is not None and left.get(key) == right.get(key)


def _fairness(experiment: Experiment, hybrid: ModelRecord, classical: ModelRecord) -> dict:
    h, c = _conditions(experiment, hybrid), _conditions(experiment, classical)
    hr, cr = h.get("representation") or {}, c.get("representation") or {}
    checks = {
        "dataset_match": _verified_equal(h, c, "dataset_id"),
        "dataset_hash_match": _verified_equal(h, c, "dataset_hash"),
        "sample_pool_match": (_verified_equal(h, c, "sample_pool_hash") or (
            h.get("sampled_row_indices") is not None and h.get("sampled_row_indices") == c.get("sampled_row_indices")
        )),
        "split_match": h.get("train_indices") is not None and h.get("train_indices") == c.get("train_indices") and h.get("test_indices") == c.get("test_indices"),
        "split_hash_match": _verified_equal(h, c, "split_hash"),
        "preprocessing_match": hr.get("pipeline") is not None and hr.get("pipeline") == cr.get("pipeline"),
        "feature_representation_match": hr.get("raw_input_features") is not None and hr == cr,
        "pca_dimension_match": hr.get("pca_components") is not None and hr.get("pca_components") == cr.get("pca_components") == hr.get("hybrid_qubits"),
        "sample_budget_match": h.get("evaluated_row_count") is not None and h.get("evaluated_row_count") == c.get("evaluated_row_count"),
        "cv_fold_match": _verified_equal(h, c, "cv_folds"),
        "seed_match": _verified_equal(h, c, "seed"),
        "threshold_strategy_match": _verified_equal(h, c, "threshold_strategy") and h.get("target_sensitivity") == c.get("target_sensitivity"),
        "holdout_match": h.get("test_indices") is not None and h.get("test_indices") == c.get("test_indices"),
        "duplicate_policy_match": _verified_equal(h, c, "duplicate_policy"),
        "test_size_match": _verified_equal(h, c, "test_size"),
    }
    mismatch_reasons = [name.replace("_", " ") for name, passed in checks.items() if not passed]
    controlled = all(checks.values())
    missing_measurements = []
    for label, value in {**_timing(hybrid.metrics or {}), **{f"classical_{k}": v for k, v in _timing(classical.metrics or {}).items()}}.items():
        if value is None:
            missing_measurements.append(label)
    status = "NOT CONTROLLED" if not controlled else ("CONTROLLED COMPARISON WITH LIMITATIONS" if missing_measurements else "CONTROLLED COMPARISON")
    return {
        **checks,
        "controlled_comparison": controlled,
        "status": status,
        "mismatch_reasons": mismatch_reasons,
        "missing_measurements": missing_measurements,
        "dataset_id": h.get("dataset_id"),
        "dataset_hash": h.get("dataset_hash"),
        "target": h.get("target"),
        "positive_label": h.get("positive_label"),
        "negative_label": h.get("negative_label"),
        "source_sample_count": h.get("source_row_count"),
        "common_sample_count": h.get("evaluated_row_count"),
        "same_sample_budget": checks["sample_budget_match"],
        "sample_pool_hash": h.get("sample_pool_hash"),
        "split_hash": h.get("split_hash"),
        "train_partition_fingerprint": fingerprint(h.get("train_indices")) if h.get("train_indices") is not None else None,
        "test_population_fingerprint": fingerprint(h.get("test_indices")) if h.get("test_indices") is not None else None,
        "cv_fold_count": h.get("cv_folds"),
        "seed": h.get("seed"),
        "test_size": h.get("test_size"),
        "threshold_strategy": h.get("threshold_strategy"),
        "target_sensitivity": h.get("target_sensitivity"),
        "preprocessing_fingerprint": h.get("comparison_fingerprint"),
        "comparison_fingerprint": h.get("comparison_fingerprint") if h.get("comparison_fingerprint") == c.get("comparison_fingerprint") else None,
        "common_representation": hr,
        "selected_feature_representation": {"features": hr.get("raw_input_features"), "preprocessing": hr.get("pipeline")},
    }


def _neutral_conclusion(performance: dict, cost: dict, quantum_type: str, classical_type: str) -> str:
    h_name, c_name = MODEL_NAMES.get(quantum_type, "quantum model"), MODEL_NAMES.get(classical_type, "classical model")
    h_s, c_s = performance["sensitivity"]["quantum"], performance["sensitivity"]["classical"]
    if h_s is None or c_s is None:
        sensitivity = "Sensitivity could not be compared because one or both values are undefined."
    else:
        relation = "higher" if h_s > c_s else "lower" if h_s < c_s else "equal"
        sensitivity = f"On this shared held-out benchmark, the {h_name} produced {relation} sensitivity ({h_s:.4f}) than the {c_name} ({c_s:.4f})." if relation != "equal" else f"On this shared held-out benchmark, the {h_name} and {c_name} produced equal sensitivity ({h_s:.4f})."
        if quantum_type != "hybrid_pennylane_torch" and h_s < c_s:
            sensitivity += " The classical model produced higher sensitivity than the quantum model."
    h_t, c_t = cost["quantum"].get("final_training_seconds"), cost["classical"].get("final_training_seconds")
    timing = "Comparable final-training timing was not available." if h_t is None or c_t is None else f"Measured final-training time was {h_t:.6f} seconds for {h_name} versus {c_t:.6f} seconds for {c_name}."
    return f"{sensitivity} {timing} These are observed benchmark differences and do not establish clinical validity, statistical superiority, or general quantum advantage."


def _robustness_evidence(quantum: ModelRecord, classical: ModelRecord, records=()) -> dict:
    latest = {}
    for record in records:
        result = record.result or {}
        reproducibility = result.get("reproducibility_metadata") or {}
        affected = (result.get("affected_sample_rows_hash") or result.get("sample_indices_hash")
                    or reproducibility.get("test_indices_fingerprint") or result.get("sample_count"))
        perturbation_fingerprint = reproducibility.get("perturbation_fingerprint")
        key = (
            record.model_id, record.perturbation_type, record.perturbation_level,
            record.random_seed, affected, perturbation_fingerprint,
            result.get("threshold_source"),
        )
        latest.setdefault(key, result)
    scenario_keys = {key[1:] for key in latest if key[0] in {quantum.id, classical.id}}
    scenarios = []
    for scenario_key in sorted(scenario_keys, key=lambda value: tuple(str(v) for v in value)):
        q_result, c_result = latest.get((quantum.id, *scenario_key)), latest.get((classical.id, *scenario_key))
        delta_difference = {metric: _difference((q_result or {}).get("degradation_delta", {}).get(metric), (c_result or {}).get("degradation_delta", {}).get(metric)) for metric in COMPARE_METRICS}
        scenarios.append({
            "perturbation_type": scenario_key[0], "perturbation_level": scenario_key[1], "random_seed": scenario_key[2],
            "affected_samples_hash": scenario_key[3], "perturbation_fingerprint": scenario_key[4],
            "threshold_source": scenario_key[5],
            "locked_thresholds": {"classical": (c_result or {}).get("threshold_used"), "hybrid": (q_result or {}).get("threshold_used")},
            "classical": c_result, "quantum": q_result,
            "delta_difference_quantum_minus_classical": delta_difference,
            "interpretation": "Observed degradation difference under the paired perturbation; no clinical robustness conclusion or quantum robustness advantage is inferred.",
        })
    if not scenarios:
        return {"status": "not_evaluated", "scenarios": [], "note": "No controlled robustness record is available for this model pair."}
    complete = all(item["classical"] is not None and item["quantum"] is not None for item in scenarios)
    return {"status": "evaluated" if complete else "partial", "scenarios": scenarios, "note": "Pairs require the same perturbation, level, seed, affected samples, and locked threshold.", "limitations": ["Synthetic benchmark perturbations are not clinical robustness evidence.", "No robustness ranking is produced."]}


def build_evidence_pair(experiment: Experiment, quantum: ModelRecord, classical: ModelRecord, robustness_records=()) -> dict:
    q_test, c_test = (quantum.metrics or {}).get("test") or {}, (classical.metrics or {}).get("test") or {}
    performance = {metric: {"classical": c_test.get(metric), "quantum": q_test.get(metric), "delta_quantum_minus_classical": _difference(q_test.get(metric), c_test.get(metric))} for metric in COMPARE_METRICS}
    q_timing, c_timing = _timing(quantum.metrics or {}), _timing(classical.metrics or {})
    cost = {"classical": c_timing, "quantum": q_timing, "deltas_quantum_minus_classical": {key: _difference(q_timing.get(key), c_timing.get(key)) for key in q_timing}, "semantics": "Measured runtime from this experiment; simulator runtime is not real-QPU runtime."}
    fairness = _fairness(experiment, quantum, classical)
    flagship = quantum.model_type == "hybrid_pennylane_torch" and classical.model_type == "random_forest"
    pair = {
        "benchmark_type": "fair_controlled_diabetes_benchmark" if flagship else "historical_model_comparison",
        "model_identities": {"classical": {"id": classical.id, "type": classical.model_type, "display_name": MODEL_NAMES.get(classical.model_type, classical.model_type)}, "hybrid": {"id": quantum.id, "type": quantum.model_type, "display_name": MODEL_NAMES.get(quantum.model_type, quantum.model_type)}},
        "quantum_model": quantum.id, "classical_model": classical.id, "quantum_type": quantum.model_type, "classical_type": classical.model_type,
        "performance": performance, "metric_deltas": {key: value["delta_quantum_minus_classical"] for key, value in performance.items()},
        "holdout_results": {"classical": c_test, "hybrid": q_test, "evaluation_population": "Untouched holdout evaluation"},
        "computational_cost": cost, "timing_deltas": cost["deltas_quantum_minus_classical"], "quantum_resources": _quantum_resources(quantum),
        "fairness": fairness, "common_representation": fairness["common_representation"],
        "operating_points": {"classical": _operating_point(classical, experiment), "quantum": _operating_point(quantum, experiment), "protocol": "OOF validation threshold → frozen threshold → untouched holdout evaluation"},
        "robustness": _robustness_evidence(quantum, classical, robustness_records),
        "neutrality": "Observed differences only; no model ranking is produced.",
        "limitations": ["Benchmark evidence only; no clinical validation.", "Simulator execution is not real quantum hardware execution.", "A single benchmark does not establish statistical superiority or general quantum advantage."],
    }
    pair["conclusion"] = _neutral_conclusion(performance, cost, quantum.model_type, classical.model_type)
    pair["test_metric_delta_quantum_minus_classical"] = pair["metric_deltas"]
    pair["final_training_seconds_delta"] = cost["deltas_quantum_minus_classical"]["final_training_seconds"]
    return clean_json(pair)


def comparison(identity: str) -> dict:
    with session_scope() as session:
        experiment = require(session, Experiment, identity)
        models = list(session.scalars(select(ModelRecord).where(ModelRecord.experiment_id == identity).order_by(ModelRecord.created_at)))
        robustness_records = list(session.scalars(select(RobustnessRecord).where(RobustnessRecord.experiment_id == identity).order_by(RobustnessRecord.created_at.desc())))
        protocol = session.scalar(
            select(ControlledComparisonProtocol)
            .where(ControlledComparisonProtocol.experiment_id == identity)
            .order_by(ControlledComparisonProtocol.created_at.desc())
        )
    ready = [model for model in models if model.status == "ready"]
    classical = [model for model in ready if model.model_type not in QUANTUM_MODELS]
    quantum = [model for model in ready if model.model_type in QUANTUM_MODELS]
    pairs = [build_evidence_pair(experiment, q, c, robustness_records) for q in quantum for c in classical]
    protocol_pairs = {
        (item["quantum_model"]["id"], item["classical_model"]["id"]): item
        for item in (protocol.comparison_pairs if protocol else [])
    }
    for pair in pairs:
        pair["controlled_protocol_pair"] = protocol_pairs.get((pair["quantum_model"], pair["classical_model"]))
    controlled = [
        pair for pair in pairs
        if (pair.get("controlled_protocol_pair") or {}).get("status") in {"CONTROLLED", "CONTROLLED_WITH_LIMITATIONS"}
    ]
    return {
        "experiment_id": identity, "dataset_id": experiment.dataset_id,
        "comparison_fingerprint": (experiment.summary or {}).get("comparison_fingerprint"), "split": (experiment.summary or {}).get("split"),
        "models": [ModelOut.model_validate(model).model_dump(mode="json") for model in models], "pairs": pairs,
        "controlled_benchmarks": controlled,
        "controlled_protocol": None if protocol is None else {
            "protocol_id": protocol.id,
            "schema_version": protocol.schema_version,
            "status": protocol.status,
            "protocol_fingerprint": protocol.protocol_fingerprint,
            "artifact_id": protocol.artifact_id,
            "control_summary": protocol.control_summary,
            "created_at": protocol.created_at,
        },
        "conclusion": "No completed classical-hybrid pair is available." if not pairs else "Completed pairs are reported without ranking; only verified matched pairs receive controlled-comparison status.",
        "limitations": ["Fairness fields are verified from persisted per-model experiment metadata.", "A benchmark is not clinical validation, statistical significance, or proof of quantum advantage."],
    }
