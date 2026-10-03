from __future__ import annotations

from collections import Counter
from uuid import uuid4

from sqlalchemy import select

from ..artifacts.service import register_metadata
from ..experiments.comparison import (
    QUANTUM_MODELS,
    _conditions,
    _operating_point,
    build_evidence_pair,
)
from ..storage.entities import (
    CalibrationStudy,
    ConditionTask,
    ControlledComparisonProtocol,
    Dataset,
    DatasetVersion,
    Experiment,
    ModelRecord,
    MultiSeedStudy,
    QuantumDiagnosticReport,
    RobustnessRecord,
    Run,
    ThresholdAnalysisStudy,
)
from ..storage.repository import require
from ..utils.errors import AppError
from ..utils.serialization import clean_json, fingerprint

CONTROLLED_COMPARISON_SCHEMA_VERSION = "controlled_comparison_protocol_v1"
CLASSICAL_MODELS = {"logistic_regression", "svm", "random_forest"}
METRICS = (
    "accuracy", "balanced_accuracy", "sensitivity", "specificity", "precision",
    "recall", "f1", "roc_auc", "pr_auc", "brier_score", "log_loss", "mcc",
    "true_positive", "true_negative", "false_positive", "false_negative",
    "confusion_matrix", "sample_count", "undefined_metrics",
)


def _eq(left, right):
    if left is None or right is None:
        return None
    return left == right


def _tuple_eq(left: tuple, right: tuple):
    if any(value is None for value in (*left, *right)):
        return None
    return left == right


def _check(name: str, passed: bool | None, *, mismatch: str, missing: str, evidence: dict | None = None) -> dict:
    status = "PASS" if passed is True else "FAIL" if passed is False else "UNKNOWN"
    return {
        "name": name,
        "status": status,
        "passed": passed,
        "reason": "Verified from persisted evidence." if passed is True else mismatch if passed is False else missing,
        "evidence": clean_json(evidence or {}),
    }


def _index_fingerprint(value):
    return fingerprint(value) if isinstance(value, list) else None


def _model_context(session, experiment: Experiment, model: ModelRecord) -> dict:
    conditions = clean_json(_conditions(experiment, model))
    details = model.details or {}
    config = details.get("configuration") or experiment.config or {}
    split = details.get("split") or (experiment.summary or {}).get("split") or {}
    run = session.get(Run, model.run_id) if model.run_id else None
    version_id = conditions.get("dataset_version_id") or (run.dataset_version_id if run else config.get("dataset_version_id"))
    version = session.get(DatasetVersion, version_id) if version_id else None
    dataset = session.get(Dataset, model.dataset_id)
    task_id = config.get("condition_task_id")
    task = session.get(ConditionTask, str(task_id)) if task_id else None
    representation = conditions.get("representation") or {}
    pipeline = representation.get("pipeline") or config.get("pipeline") or {}
    operating = _operating_point(model, experiment)
    calibration = config.get("calibration")
    calibration_study = session.scalar(
        select(CalibrationStudy)
        .where(CalibrationStudy.model_id == model.id, CalibrationStudy.status == "completed")
        .order_by(CalibrationStudy.created_at.desc())
    )
    threshold_study = session.scalar(
        select(ThresholdAnalysisStudy)
        .where(ThresholdAnalysisStudy.model_id == model.id, ThresholdAnalysisStudy.status == "completed")
        .order_by(ThresholdAnalysisStudy.created_at.desc())
    )
    diagnostic = session.scalar(
        select(QuantumDiagnosticReport)
        .where(QuantumDiagnosticReport.model_record_id == model.id)
        .order_by(QuantumDiagnosticReport.created_at.desc())
    )
    provider_plans = (run.execution_metadata or {}).get("quantum_providers", []) if run else []
    quantum = details.get("quantum") or {}
    return {
        "model": model,
        "run": run,
        "conditions": conditions,
        "config": config,
        "split": split,
        "dataset": dataset,
        "version": version,
        "task": task,
        "representation": representation,
        "pipeline": pipeline,
        "operating": operating,
        "calibration": {
            "method": calibration if calibration is not None else "not_recorded",
            "applied": calibration not in (None, "none"),
            "study_id": calibration_study.id if calibration_study else None,
            "protocol": (calibration_study.configuration or {}).get("calibration_protocol") if calibration_study else None,
            "dataset_id": calibration_study.dataset_id if calibration_study else None,
            "dataset_version_id": calibration_study.dataset_version_id if calibration_study else None,
        },
        "threshold": {
            "strategy": conditions.get("threshold_strategy"),
            "target_sensitivity": conditions.get("target_sensitivity"),
            "source": operating.get("threshold_source"),
            "selection_population_count": operating.get("number_of_oof_samples"),
            "selected_threshold": operating.get("selected_threshold"),
            "feasible": operating.get("threshold_feasible"),
            "validation_metrics": clean_json(operating.get("validation_metrics")),
            "holdout_metrics": clean_json(operating.get("holdout_metrics")),
            "study_id": threshold_study.id if threshold_study else None,
            "study_protocol": (threshold_study.configuration or {}).get("selection_protocol") if threshold_study else None,
        },
        "group": {
            "sampling_unit": config.get("sampling_unit"),
            "group_column": config.get("group_column"),
            "holdout_strategy": split.get("holdout_strategy"),
            "cv_strategy": split.get("cv_strategy"),
            "train_group_count": split.get("train_group_count"),
            "test_group_count": split.get("test_group_count"),
            "test_groups_fingerprint": split.get("test_groups_fingerprint"),
            "group_split_fingerprint": split.get("group_split_fingerprint"),
        },
        "provider": {
            "provider_id": quantum.get("provider_id") or (provider_plans[0].get("provider_id") if provider_plans else None),
            "backend_id": quantum.get("backend_id") or quantum.get("backend") or (provider_plans[0].get("backend_id") if provider_plans else None),
            "execution_mode": quantum.get("execution_mode") or quantum.get("execution_kind") or (provider_plans[0].get("execution_mode") if provider_plans else None),
            "capabilities": clean_json(provider_plans[0].get("capabilities")) if provider_plans else None,
            "configuration_fingerprint": provider_plans[0].get("configuration_fingerprint") if provider_plans else quantum.get("configuration_fingerprint"),
            "logical_qubits": quantum.get("qubits") or (quantum.get("circuit") or {}).get("qubits"),
            "circuit_depth": (quantum.get("circuit") or {}).get("logical_depth"),
            "parameter_count": (quantum.get("circuit") or {}).get("parameter_count") or quantum.get("total_parameter_count"),
            "shots": quantum.get("shots"),
            "noise_configuration": quantum.get("noise_probability"),
            "real_hardware": True if quantum.get("real_hardware") is True else False,
            "runtime_semantics": "real_quantum_hardware" if quantum.get("real_hardware") is True else "local_or_remote_simulator_not_qpu_runtime",
            "diagnostic_report_id": diagnostic.id if diagnostic else None,
        },
    }


def _common_representation(representation: dict) -> dict:
    return {
        "raw_input_features": representation.get("raw_input_features"),
        "selected_feature_count": representation.get("selected_feature_count"),
        "feature_selection": representation.get("feature_selection"),
        "pca_components": representation.get("pca_components"),
        "angle_scaling": representation.get("angle_scaling"),
        "final_representation_dimension": representation.get("final_representation_dimension"),
        "pipeline": representation.get("pipeline"),
    }


def _pair_checks(classical: dict, quantum: dict) -> list[dict]:
    c, q = classical["conditions"], quantum["conditions"]
    cr, qr = _common_representation(classical["representation"]), _common_representation(quantum["representation"])
    cp, qp = classical["pipeline"], quantum["pipeline"]
    ct, qt = classical["threshold"], quantum["threshold"]
    cg, qg = classical["group"], quantum["group"]
    c_task, q_task = classical["task"], quantum["task"]
    target_type_c = c_task.task_type if c_task else (classical["version"].target_type if classical["version"] else None)
    target_type_q = q_task.task_type if q_task else (quantum["version"].target_type if quantum["version"] else None)
    condition_c = c_task.id if c_task else None
    condition_q = q_task.id if q_task else None
    threshold_policy = None
    if ct["strategy"] is not None and qt["strategy"] is not None:
        threshold_policy = (
            ct["strategy"] == qt["strategy"]
            and ct["target_sensitivity"] == qt["target_sensitivity"]
        )
    threshold_lock_c = ct["source"] not in (None, "legacy_fixed_configuration") and ct["selected_threshold"] is not None
    threshold_lock_q = qt["source"] not in (None, "legacy_fixed_configuration") and qt["selected_threshold"] is not None
    threshold_lock = None if not threshold_lock_c or not threshold_lock_q else True
    calibration_match = None if "not_recorded" in {classical["calibration"]["method"], quantum["calibration"]["method"]} else _eq(classical["calibration"]["method"], quantum["calibration"]["method"])
    preprocessing_match = None if not cp or not qp else cp == qp
    representation_match = None if not cr.get("raw_input_features") or not qr.get("raw_input_features") else cr == qr
    grouped = cg["sampling_unit"] == "grouped_samples" or qg["sampling_unit"] == "grouped_samples"
    grouping_match = _eq(cg["sampling_unit"], qg["sampling_unit"])
    if grouping_match and grouped:
        values = (
            _eq(cg["group_column"], qg["group_column"]),
            _eq(cg["holdout_strategy"], qg["holdout_strategy"]),
            _eq(cg["cv_strategy"], qg["cv_strategy"]),
            _eq(cg["group_split_fingerprint"], qg["group_split_fingerprint"]),
        )
        grouping_match = False if False in values else None if None in values else True
    test_c, test_q = _index_fingerprint(c.get("test_indices")), _index_fingerprint(q.get("test_indices"))
    train_c, train_q = _index_fingerprint(c.get("train_indices")), _index_fingerprint(q.get("train_indices"))
    tests = [
        _check("dataset_match", _eq(c.get("dataset_id"), q.get("dataset_id")), mismatch="Dataset IDs differ.", missing="Dataset identity is unavailable.", evidence={"classical": c.get("dataset_id"), "quantum": q.get("dataset_id")}),
        _check("dataset_version_match", _eq(c.get("dataset_version_id"), q.get("dataset_version_id")), mismatch="Dataset versions differ.", missing="Dataset version evidence is unavailable.", evidence={"classical": c.get("dataset_version_id"), "quantum": q.get("dataset_version_id")}),
        _check("dataset_hash_match", _eq(c.get("dataset_hash"), q.get("dataset_hash")), mismatch="Dataset content hashes differ.", missing="Dataset content hash evidence is unavailable."),
        _check("target_match", _eq(c.get("target"), q.get("target")), mismatch="Target columns differ.", missing="Target-column evidence is unavailable.", evidence={"classical": c.get("target"), "quantum": q.get("target")}),
        _check("target_type_match", _eq(target_type_c, target_type_q), mismatch="Target types differ.", missing="Target-type evidence is unavailable."),
        _check("label_semantics_match", _tuple_eq((c.get("positive_label"), c.get("negative_label")), (q.get("positive_label"), q.get("negative_label"))), mismatch="Positive/negative label semantics differ.", missing="Label semantics are unavailable."),
        _check("condition_task_match", _eq(condition_c, condition_q) if condition_c or condition_q else None, mismatch="ConditionTask identities differ.", missing="ConditionTask semantics are not configured."),
        _check("sample_pool_match", _eq(c.get("sample_pool_hash"), q.get("sample_pool_hash")), mismatch="Sample-pool fingerprints differ.", missing="Sample-pool fingerprints are unavailable."),
        _check("test_population_match", _eq(test_c, test_q), mismatch="Held-out row fingerprints differ.", missing="Held-out row identity evidence is unavailable.", evidence={"classical_fingerprint": test_c, "quantum_fingerprint": test_q}),
        _check("train_partition_match", _eq(train_c, train_q), mismatch="Training partition fingerprints differ.", missing="Training partition identity evidence is unavailable.", evidence={"classical_fingerprint": train_c, "quantum_fingerprint": train_q}),
        _check("split_hash_match", _eq(c.get("split_hash"), q.get("split_hash")), mismatch="Split hashes differ.", missing="Split hashes are unavailable."),
        _check("sampling_policy_match", _tuple_eq((c.get("max_samples"), c.get("duplicate_policy"), c.get("test_size")), (q.get("max_samples"), q.get("duplicate_policy"), q.get("test_size"))), mismatch="Sampling, duplicate, or test-size policy differs.", missing="Sampling policy evidence is unavailable."),
        _check("sample_budget_match", _eq(c.get("evaluated_row_count"), q.get("evaluated_row_count")), mismatch="Actual evaluated sample counts differ.", missing="Evaluated sample counts are unavailable."),
        _check("seed_policy_match", _eq(c.get("seed"), q.get("seed")), mismatch="External randomization seeds differ.", missing="Seed evidence is unavailable."),
        _check("cv_fold_match", _eq(c.get("cv_folds"), q.get("cv_folds")), mismatch="CV fold counts differ.", missing="CV fold evidence is unavailable."),
        _check("preprocessing_match", preprocessing_match, mismatch="Preprocessing contracts differ.", missing="Preprocessing evidence is unavailable.", evidence={"classical_fingerprint": fingerprint(cp) if cp else None, "quantum_fingerprint": fingerprint(qp) if qp else None}),
        _check("feature_representation_match", representation_match, mismatch="Common pre-model representations differ.", missing="Common representation evidence is unavailable.", evidence={"classical_fingerprint": fingerprint(cr) if cr.get("raw_input_features") else None, "quantum_fingerprint": fingerprint(qr) if qr.get("raw_input_features") else None}),
        _check("pca_dimension_match", _eq(cr.get("pca_components"), qr.get("pca_components")), mismatch="PCA dimensions differ.", missing="PCA dimension evidence is unavailable."),
        _check("angle_scaling_match", _eq(cr.get("angle_scaling"), qr.get("angle_scaling")), mismatch="Angle-scaling contracts differ.", missing="Angle-scaling evidence is unavailable."),
        _check("grouping_match", grouping_match, mismatch="Sampling unit, group column, or grouped partition policy differs.", missing="Grouped partition evidence is incomplete.", evidence={"classical": cg, "quantum": qg}),
        _check("threshold_protocol_match", threshold_policy, mismatch="Threshold-selection policies differ.", missing="Threshold protocol evidence is unavailable.", evidence={"classical": ct, "quantum": qt}),
        _check("threshold_lock_verified", threshold_lock, mismatch="A threshold was not locked before holdout evaluation.", missing="Frozen threshold provenance is unavailable."),
        _check("calibration_protocol_match", calibration_match, mismatch="Calibration methods differ.", missing="Calibration configuration is unavailable.", evidence={"classical": classical["calibration"], "quantum": quantum["calibration"]}),
    ]
    return tests


def _required_status(checks: list[dict]) -> str:
    required = [item for item in checks if item["name"] != "condition_task_match"]
    if any(item["status"] == "FAIL" for item in required):
        return "NOT_CONTROLLED"
    if any(item["status"] == "UNKNOWN" for item in required):
        return "INCOMPLETE_EVIDENCE"
    return "CONTROLLED"


def _metrics(model: ModelRecord) -> dict:
    test = (model.metrics or {}).get("test") or {}
    return {
        key: {
            "status": "undefined" if key in (test.get("undefined_metrics") or []) else "available" if test.get(key) is not None else "unavailable",
            "value": clean_json(test.get(key)),
        }
        for key in METRICS
    }


def _metric_deltas(classical: ModelRecord, quantum: ModelRecord) -> dict:
    c_test, q_test = (classical.metrics or {}).get("test") or {}, (quantum.metrics or {}).get("test") or {}
    result = {}
    for key in METRICS:
        c_value, q_value = c_test.get(key), q_test.get(key)
        result[key] = q_value - c_value if isinstance(q_value, (int, float)) and isinstance(c_value, (int, float)) else None
    return result


def _assemble(session, experiment_id: str, classical_ids: list[str] | None, quantum_ids: list[str] | None) -> dict:
    experiment = require(session, Experiment, experiment_id)
    models = list(session.scalars(
        select(ModelRecord).where(ModelRecord.experiment_id == experiment_id, ModelRecord.status == "ready")
    ))
    by_id = {item.id: item for item in models}
    requested = set((classical_ids or []) + (quantum_ids or []))
    if requested - set(by_id):
        raise AppError("comparison_model_not_found", "One or more requested ready models are not part of this experiment.", 404)
    if any(by_id[item].model_type not in CLASSICAL_MODELS for item in classical_ids or []):
        raise AppError("invalid_classical_role", "A requested classical role is not a classical model.", 422)
    if any(by_id[item].model_type not in QUANTUM_MODELS for item in quantum_ids or []):
        raise AppError("invalid_quantum_role", "A requested quantum role is not a quantum-family model.", 422)
    classical = [item for item in models if item.model_type in CLASSICAL_MODELS and (not classical_ids or item.id in classical_ids)]
    quantum = [item for item in models if item.model_type in QUANTUM_MODELS and (not quantum_ids or item.id in quantum_ids)]
    if not classical or not quantum:
        raise AppError("comparison_pair_unavailable", "At least one ready classical and one ready quantum-family model are required.", 409)
    robustness = list(session.scalars(select(RobustnessRecord).where(RobustnessRecord.experiment_id == experiment_id)))
    multi_seed = list(session.scalars(select(MultiSeedStudy).where(MultiSeedStudy.base_experiment_id == experiment_id)))
    pairs = []
    for c_model in classical:
        for q_model in quantum:
            c_ctx, q_ctx = _model_context(session, experiment, c_model), _model_context(session, experiment, q_model)
            checks = _pair_checks(c_ctx, q_ctx)
            status = _required_status(checks)
            evidence_pair = build_evidence_pair(experiment, q_model, c_model, robustness)
            comparable_studies = [
                item for item in multi_seed
                if {c_model.model_type, q_model.model_type}.issubset(set(item.model_identities or []))
            ]
            nonblocking = []
            if evidence_pair["robustness"]["status"] != "evaluated":
                nonblocking.append("Matched robustness evidence is incomplete.")
            if not comparable_studies:
                nonblocking.append("Comparable multi-seed evidence is not available.")
            if q_ctx["provider"]["diagnostic_report_id"] is None:
                nonblocking.append("Quantum diagnostics are not available for this model.")
            timing_values = list(evidence_pair["computational_cost"]["classical"].values()) + list(evidence_pair["computational_cost"]["quantum"].values())
            if any(value is None for value in timing_values):
                nonblocking.append("Measured timing evidence is incomplete.")
            if status == "CONTROLLED" and nonblocking:
                status = "CONTROLLED_WITH_LIMITATIONS"
            pairs.append({
                "pair_id": fingerprint({"classical_model_id": c_model.id, "quantum_model_id": q_model.id})[:24],
                "classical_model": {"id": c_model.id, "model_type": c_model.model_type, "family": "classical", "run_id": c_model.run_id, "artifact_hash": c_model.artifact_sha256},
                "quantum_model": {"id": q_model.id, "model_type": q_model.model_type, "family": "hybrid" if q_model.model_type == "hybrid_pennylane_torch" else "quantum", "run_id": q_model.run_id, "artifact_hash": q_model.artifact_sha256},
                "status": status,
                "control_checks": checks,
                "control_matrix": {item["name"]: item["passed"] for item in checks},
                "common_representation": _common_representation(c_ctx["representation"]),
                "model_specific_variables": {
                    "classical": {"model_type": c_model.model_type, "configuration_fingerprint": fingerprint(c_ctx["config"].get("parameters", {}))},
                    "quantum": {"model_type": q_model.model_type, "configuration_fingerprint": fingerprint(q_ctx["config"].get("hybrid" if q_model.model_type == "hybrid_pennylane_torch" else "quantum", {}))},
                },
                "threshold_protocol": {"classical": c_ctx["threshold"], "quantum": q_ctx["threshold"]},
                "calibration_protocol": {"classical": c_ctx["calibration"], "quantum": q_ctx["calibration"]},
                "quantum_provider_provenance": q_ctx["provider"],
                "performance": {"classical": _metrics(c_model), "quantum": _metrics(q_model), "delta_quantum_minus_classical": _metric_deltas(c_model, q_model)},
                "computational_cost": evidence_pair["computational_cost"],
                "robustness": evidence_pair["robustness"],
                "multi_seed_evidence": {"status": "available" if comparable_studies else "not_available", "study_ids": [item.id for item in comparable_studies]},
                "limitations": nonblocking,
            })
    statuses = Counter(item["status"] for item in pairs)
    if statuses["NOT_CONTROLLED"]:
        overall = "NOT_CONTROLLED"
    elif statuses["INCOMPLETE_EVIDENCE"]:
        overall = "INCOMPLETE_EVIDENCE"
    elif statuses["CONTROLLED_WITH_LIMITATIONS"]:
        overall = "CONTROLLED_WITH_LIMITATIONS"
    else:
        overall = "CONTROLLED"
    config = {
        "experiment_id": experiment_id,
        "classical_model_ids": sorted(item.id for item in classical),
        "quantum_model_ids": sorted(item.id for item in quantum),
        "schema_version": CONTROLLED_COMPARISON_SCHEMA_VERSION,
    }
    configuration_fingerprint = fingerprint(config)
    protocol_source = {"configuration": config, "pairs": pairs}
    protocol_fingerprint = fingerprint(protocol_source)
    return clean_json({
        "schema_version": CONTROLLED_COMPARISON_SCHEMA_VERSION,
        "experiment_id": experiment_id,
        "status": overall,
        "configuration_fingerprint": configuration_fingerprint,
        "protocol_fingerprint": protocol_fingerprint,
        "classical_model_ids": config["classical_model_ids"],
        "quantum_model_ids": config["quantum_model_ids"],
        "comparison_pairs": pairs,
        "control_summary": {
            "pair_count": len(pairs),
            "status_counts": dict(statuses),
            "controlled_pair_count": sum(item["status"] in {"CONTROLLED", "CONTROLLED_WITH_LIMITATIONS"} for item in pairs),
        },
        "provenance": {
            "experiment_id": experiment_id,
            "model_ids": sorted([*config["classical_model_ids"], *config["quantum_model_ids"]]),
            "evidence_policy": "persisted_evidence_only",
        },
        "limitations": [
            "A controlled comparison demonstrates experimental matching under persisted evidence; it does not establish clinical validity, statistical superiority, or quantum computational advantage.",
            "No ranking or overall model score is produced.",
        ],
        "warnings": [],
    })


def preflight_protocol(session, experiment_id: str, classical_ids=None, quantum_ids=None) -> dict:
    try:
        return {"preflight": True, **_assemble(session, experiment_id, classical_ids, quantum_ids)}
    except AppError as exc:
        if exc.code not in {
            "comparison_model_not_found", "comparison_pair_unavailable",
            "invalid_classical_role", "invalid_quantum_role",
        }:
            raise
        configuration = {
            "schema_version": CONTROLLED_COMPARISON_SCHEMA_VERSION,
            "experiment_id": experiment_id,
            "classical_model_ids": sorted(classical_ids or []),
            "quantum_model_ids": sorted(quantum_ids or []),
        }
        return {
            "preflight": True,
            **configuration,
            "status": "BLOCKED",
            "configuration_fingerprint": fingerprint(configuration),
            "protocol_fingerprint": None,
            "comparison_pairs": [],
            "control_summary": {"pair_count": 0, "status_counts": {"BLOCKED": 1}, "controlled_pair_count": 0},
            "provenance": {"experiment_id": experiment_id, "evidence_policy": "persisted_evidence_only"},
            "limitations": [exc.message],
            "warnings": [],
            "blockers": [{"code": exc.code, "description": exc.message}],
        }


def create_protocol(session, experiment_id: str, classical_ids=None, quantum_ids=None) -> ControlledComparisonProtocol:
    payload = _assemble(session, experiment_id, classical_ids, quantum_ids)
    operation_key = f"controlled-comparison:{experiment_id}:{payload['protocol_fingerprint']}"
    existing = session.scalar(select(ControlledComparisonProtocol).where(ControlledComparisonProtocol.operation_key == operation_key))
    if existing:
        return existing
    protocol = ControlledComparisonProtocol(
        id=str(uuid4()),
        experiment_id=experiment_id,
        schema_version=payload["schema_version"],
        status=payload["status"],
        operation_key=operation_key,
        configuration_fingerprint=payload["configuration_fingerprint"],
        protocol_fingerprint=payload["protocol_fingerprint"],
        classical_model_ids=payload["classical_model_ids"],
        quantum_model_ids=payload["quantum_model_ids"],
        comparison_pairs=payload["comparison_pairs"],
        control_summary=payload["control_summary"],
        provenance=payload["provenance"],
        limitations=payload["limitations"],
        warnings=payload["warnings"],
    )
    session.add(protocol)
    session.flush()
    artifact = register_metadata(
        session,
        experiment_id=experiment_id,
        run_id=None,
        model_id=None,
        artifact_type="controlled_comparison_protocol",
        name="Controlled classical-vs-quantum comparison protocol",
        description="Immutable scientific control checks for persisted classical/quantum model pairs.",
        payload={"protocol_id": protocol.id, **payload},
        operation_key=f"artifact:{operation_key}",
    )
    protocol.artifact_id = artifact.id
    return protocol


def protocol_payload(protocol: ControlledComparisonProtocol) -> dict:
    return clean_json({
        "protocol_id": protocol.id,
        "experiment_id": protocol.experiment_id,
        "schema_version": protocol.schema_version,
        "status": protocol.status,
        "created_at": protocol.created_at,
        "configuration_fingerprint": protocol.configuration_fingerprint,
        "protocol_fingerprint": protocol.protocol_fingerprint,
        "classical_model_ids": protocol.classical_model_ids,
        "quantum_model_ids": protocol.quantum_model_ids,
        "comparison_pairs": protocol.comparison_pairs,
        "control_summary": protocol.control_summary,
        "provenance": protocol.provenance,
        "limitations": protocol.limitations,
        "warnings": protocol.warnings,
        "artifact_id": protocol.artifact_id,
    })


def latest_protocol(session, experiment_id: str) -> ControlledComparisonProtocol | None:
    return session.scalar(
        select(ControlledComparisonProtocol)
        .where(ControlledComparisonProtocol.experiment_id == experiment_id)
        .order_by(ControlledComparisonProtocol.created_at.desc())
    )