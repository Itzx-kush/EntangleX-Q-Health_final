from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from ..artifacts.service import register_metadata
from ..storage.entities import (
    Artifact,
    CalibrationStudy,
    ConditionTask,
    ControlledComparisonProtocol,
    Dataset,
    DatasetVersion,
    DistributionShiftAnalysis,
    Experiment,
    ExperimentProtocolVersion,
    ExternalValidation,
    ModelRecord,
    MultiSeedStudy,
    PipelineVersion,
    RobustnessRecord,
    Run,
    ThresholdAnalysisStudy,
    QuantumDiagnosticReport,
)
from ..storage.repository import require
from ..utils.serialization import clean_json, fingerprint

MODEL_CARD_SCHEMA_VERSION = "model_card_v1"
MISSING = "not_available"

CLASSICAL = {"logistic_regression", "svm", "random_forest"}
QUANTUM = {"vqc", "qsvc", "qnn"}
HYBRID = {"hybrid_pennylane_torch"}

METRIC_KEYS = {
    "accuracy", "balanced_accuracy", "sensitivity", "specificity", "precision",
    "recall", "f1", "roc_auc", "pr_auc", "brier_score", "log_loss", "mcc",
    "true_positive", "true_negative", "false_positive", "false_negative",
    "confusion_matrix", "sample_count", "undefined_metrics",
}


def _value(value: Any, state: str = MISSING) -> Any:
    return value if value is not None else state


def _pick(source: dict | None, keys: set[str] | tuple[str, ...] | list[str]) -> dict:
    source = source or {}
    return clean_json({key: source[key] for key in keys if key in source and source[key] is not None})


def _metrics(source: dict | None) -> dict:
    return _pick(source, METRIC_KEYS)


def _time(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _latest_time(records: list[Any], fallback: datetime) -> str:
    values = [fallback]
    for record in records:
        for field in ("completed_at", "updated_at", "created_at"):
            value = getattr(record, field, None)
            if value is not None:
                values.append(value)
                break
    # SQLite may return naive timestamps while normal runs use aware timestamps.
    return max(value.replace(tzinfo=None) for value in values).isoformat() + "Z"


def _family(model_type: str) -> str:
    if model_type in CLASSICAL:
        return "classical"
    if model_type in QUANTUM:
        return "quantum"
    if model_type in HYBRID:
        return "hybrid_quantum_classical"
    return "unknown"


def _condition(task: ConditionTask | None) -> dict:
    if task is None:
        return {"condition_task_status": "not_configured"}
    metadata = _pick(task.metadata_, (
        "terminology_system", "terminology_code", "terminology_display",
        "case_definition", "population_description", "prediction_horizon",
        "label_source", "feature_domain",
    ))
    return {
        "condition_task_status": "configured",
        "condition_task_id": task.id,
        "condition_name": task.condition_name,
        "standardized_code": metadata.get("terminology_code", MISSING),
        "terminology_system": metadata.get("terminology_system", MISSING),
        "task_type": task.task_type,
        "target_column": task.target_column,
        "positive_label": _value(task.positive_label, "not_recorded"),
        "negative_label": _value(task.negative_label, "not_recorded"),
        "case_definition": metadata.get("case_definition", "not_recorded"),
        "prediction_horizon": metadata.get("prediction_horizon", "not_recorded"),
        "population_description": metadata.get("population_description", "not_recorded"),
        "label_source": metadata.get("label_source", "not_recorded"),
        "feature_domain": metadata.get("feature_domain", "not_recorded"),
        "dataset_id": task.dataset_id,
        "dataset_version_id": _value(task.dataset_version_id),
        "task_status": task.status,
        "readiness_status": _value(task.readiness_status, "not_yet_evaluated"),
    }


def _dataset(dataset: Dataset, version: DatasetVersion | None) -> dict:
    if version:
        return {
            "dataset_id": dataset.id,
            "dataset_name": dataset.name,
            "dataset_version_id": version.id,
            "version": version.version_number,
            "version_label": version.version_label,
            "content_hash": version.content_sha256,
            "schema_fingerprint": version.schema_fingerprint,
            "row_count": version.row_count,
            "feature_count": version.feature_count,
            "target": version.target,
            "target_type": version.target_type,
            "class_distribution": clean_json(version.class_distribution),
            "positive_label": version.positive_label,
            "negative_label": version.negative_label,
            "source_metadata": _pick(version.source_metadata, ("source", "source_url", "version", "license", "domain", "origin")),
            "provenance": _pick(version.provenance, ("source", "source_url", "version", "license", "domain", "origin", "deidentified", "sampling_unit")),
            "quality_summary": _pick(version.quality_summary, ("scope", "row_count", "feature_count", "minority_fraction", "class_imbalance", "duplicate_rows", "warnings", "blockers")),
            "sampling_unit": version.provenance.get("sampling_unit", "not_recorded"),
            "immutable": version.immutable,
            "version_status": version.status,
        }
    provenance = dataset.provenance or {}
    quality = dataset.quality or {}
    return {
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "dataset_version_id": MISSING,
        "version": provenance.get("version", "not_recorded"),
        "version_label": "not_recorded",
        "content_hash": dataset.sha256,
        "schema_fingerprint": MISSING,
        "row_count": provenance.get("row_count", quality.get("row_count", MISSING)),
        "feature_count": provenance.get("feature_count", quality.get("feature_count", MISSING)),
        "target": provenance.get("target", "not_recorded"),
        "target_type": provenance.get("target_type", "not_recorded"),
        "class_distribution": clean_json(provenance.get("class_distribution", MISSING)),
        "positive_label": provenance.get("positive_label", "not_recorded"),
        "negative_label": provenance.get("negative_label", "not_recorded"),
        "source_metadata": _pick(provenance, ("source", "source_url", "version", "license", "domain", "origin")),
        "provenance": _pick(provenance, ("source", "source_url", "version", "license", "domain", "origin", "deidentified", "sampling_unit")),
        "quality_summary": _pick(quality, ("scope", "row_count", "feature_count", "minority_fraction", "class_imbalance", "duplicate_rows", "warnings", "blockers")),
        "sampling_unit": provenance.get("sampling_unit", "not_recorded"),
        "immutable": "not_recorded",
        "version_status": "legacy_unversioned",
    }


def _training(config: dict) -> dict:
    pipeline = config.get("pipeline") or {}
    return {
        "selected_features": clean_json(config.get("features", "all_documented_features")),
        "feature_selection_strategy": pipeline.get("selection", "not_recorded"),
        "imputation": pipeline.get("imputer", "not_recorded"),
        "scaling": pipeline.get("scaler", "not_recorded"),
        "outlier_strategy": pipeline.get("outlier_strategy", "not_recorded"),
        "transformations": {"log_features": clean_json(pipeline.get("log_features", [])), "ratios": clean_json(pipeline.get("ratios", []))},
        "feature_selection": _pick(pipeline, ("selection", "k_features", "variance_threshold")),
        "pca": _pick(pipeline, ("pca_components", "pca_whiten")),
        "angle_scaling": _value(pipeline.get("angle_scaling"), "not_recorded"),
        "sampling": _pick(config, ("max_samples", "sampling_unit", "group_column")),
        "split": _pick(config, ("test_size", "cv_folds")),
        "duplicate_policy": config.get("duplicate_policy", "not_recorded"),
        "random_seed": config.get("seed", "not_recorded"),
        "calibration_configuration": _pick(config, ("calibration", "calibration_folds")),
        "threshold_configuration": _pick(config, ("probability_threshold", "threshold_strategy", "target_sensitivity")),
        "condition_task_id": _value(config.get("condition_task_id"), "not_configured"),
    }


def _model_details(model: ModelRecord, config: dict) -> dict:
    family = _family(model.model_type)
    result: dict[str, Any] = {"model_type": model.model_type, "model_family": family}
    if family == "classical":
        parameters = config.get("parameters") or {}
        names = {
            "logistic_regression": ("logistic_c",),
            "svm": ("svm_c", "svm_kernel"),
            "random_forest": ("forest_trees", "forest_max_depth"),
        }
        result.update({
            "algorithm": model.model_type,
            "hyperparameters": _pick(parameters, names.get(model.model_type, ())),
            "class_weight": parameters.get("class_weight", "not_recorded"),
            "feature_representation": _pick(config.get("pipeline"), ("selection", "pca_components", "angle_scaling")),
            "probability_support": model.details.get("supports_probability", model.details.get("probability_status", "not_recorded")),
        })
    elif family == "quantum":
        quantum = config.get("quantum") or {}
        persisted = model.details.get("quantum") or {}
        result.update(_pick(quantum, (
            "provider_id", "execution_mode", "backend", "qubits", "feature_map_reps",
            "ansatz_reps", "entanglement", "optimizer", "maxiter", "shots",
            "noise_probability",
        )))
        result["execution_evidence"] = _pick(persisted, (
            "provider_id", "backend_id", "backend", "execution_mode", "execution_kind",
            "real_hardware", "configuration_fingerprint", "logical_depth", "gate_counts",
            "parameter_count",
        ))
    elif family == "hybrid_quantum_classical":
        hybrid = config.get("hybrid") or {}
        result.update(_pick(hybrid, (
            "provider_id", "execution_mode", "backend", "qubits", "quantum_layers",
            "feature_map", "classical_hidden_dimensions", "classical_activation",
            "optimizer", "learning_rate", "epochs", "batch_size",
            "deterministic_seed", "sample_cap",
        )))
        result["execution_evidence"] = _pick(model.details.get("quantum"), (
            "provider_id", "framework", "classical_framework", "backend",
            "execution_mode", "execution_kind", "real_hardware", "qubits",
            "quantum_layers", "configuration_fingerprint",
        ))
    return clean_json(result)


def _evaluation(model: ModelRecord) -> dict:
    metrics = model.metrics or {}
    evidence: list[dict] = []
    for context in ("training", "test"):
        if isinstance(metrics.get(context), dict):
            evidence.append({"context": context, "source": "model_record.metrics", "metrics": _metrics(metrics[context])})
    validation = metrics.get("validation")
    if isinstance(validation, dict):
        evidence.append({
            "context": "cross_validation",
            "source": "model_record.metrics",
            "summary": clean_json(validation.get("summary", {})),
            "fold_count": len(validation.get("folds", [])),
            "std_definition": validation.get("std_definition", "not_recorded"),
        })
    return {"status": "available" if evidence else MISSING, "evidence": evidence}


def _multi_seed(studies: list[MultiSeedStudy]) -> dict:
    rows = []
    for study in studies:
        rows.append({
            "study_id": study.id, "status": study.status,
            "requested_seeds": clean_json(study.requested_seeds),
            "completed_seeds": clean_json(study.completed_seeds),
            "failed_seeds": clean_json(study.failed_seeds),
            "cancelled_seeds": clean_json(study.cancelled_seeds),
            "aggregate_statistics": clean_json(study.aggregate_summary),
            "limitations": clean_json(study.limitations),
            "artifact_id": _value(study.study_artifact_id),
        })
    return {"status": "available" if rows else MISSING, "studies": rows}


def _calibration(studies: list[CalibrationStudy]) -> dict:
    rows = [{
        "study_id": item.id, "status": item.status,
        "method": (item.configuration or {}).get("calibration_method", "not_recorded"),
        "protocol": (item.configuration or {}).get("calibration_protocol", "not_recorded"),
        "dataset_id": item.dataset_id, "dataset_version_id": _value(item.dataset_version_id),
        "metrics": clean_json(item.metrics), "summary": clean_json(item.summary),
        "limitations": clean_json(item.limitations), "provenance": clean_json(item.provenance),
        "artifact_id": _value(item.artifact_id),
    } for item in studies]
    return {"status": "available" if any(item.status == "completed" for item in studies) else MISSING, "studies": rows}


def _threshold(studies: list[ThresholdAnalysisStudy]) -> dict:
    rows = []
    for item in studies:
        results = item.results or {}
        rows.append({
            "study_id": item.id, "status": item.status,
            "probability_source": (item.configuration or {}).get("probability_source", "not_recorded"),
            "selection_protocol": (item.configuration or {}).get("selection_protocol", "not_recorded"),
            "selection_method": (item.configuration or {}).get("selection_method", "not_recorded"),
            "selected_operating_point": clean_json(results.get("selected_operating_point", "not_yet_evaluated")),
            "selection_operating_point": clean_json(results.get("selection_operating_point", "not_yet_evaluated")),
            "summary": clean_json(item.summary or {}),
            "limitations": clean_json(item.limitations or []),
            "provenance": clean_json(item.provenance or {}),
        })
    return {"status": "available" if any(item.status == "completed" for item in studies) else MISSING, "studies": rows}


def _external(studies: list[ExternalValidation]) -> dict:
    rows = [{
        "validation_id": item.id, "status": item.status,
        "external_dataset_id": item.external_dataset_id,
        "external_dataset_version_id": _value(item.external_dataset_version_id),
        "compatibility": clean_json(item.compatibility), "metrics": _metrics(item.metrics),
        "internal_metrics": _metrics(item.internal_metrics),
        "comparison": clean_json(item.comparison),
        "generalization_gap": clean_json(item.generalization_gap),
        "warnings": clean_json(item.warnings), "limitations": clean_json(item.limitations),
        "artifact_id": _value(item.artifact_id),
    } for item in studies]
    return {"status": "available" if rows else MISSING, "validations": rows}


def _shift(studies: list[DistributionShiftAnalysis]) -> dict:
    rows = [{
        "analysis_id": item.id, "status": item.status,
        "reference_dataset_id": item.reference_dataset_id,
        "reference_dataset_version_id": _value(item.reference_dataset_version_id),
        "comparison_dataset_id": item.comparison_dataset_id,
        "comparison_dataset_version_id": _value(item.comparison_dataset_version_id),
        "schema_changes": clean_json(item.schema_analysis),
        "missingness_changes": clean_json(item.missingness_analysis),
        "target_distribution_changes": clean_json(item.target_analysis),
        "feature_shift_summary": clean_json(item.summary),
        "multiple_testing": _pick(item.configuration, ("multiple_testing", "correction_method", "alpha")),
        "warnings": clean_json(item.warnings), "limitations": clean_json(item.limitations),
        "artifact_id": _value(item.artifact_id),
    } for item in studies]
    return {"status": "available" if rows else MISSING, "analyses": rows}


def _group(run: Run | None, config: dict) -> dict:
    if config.get("sampling_unit") != "grouped_samples":
        return {"status": "not_applicable", "sampling_unit": config.get("sampling_unit", "not_recorded")}
    split = (run.reproducibility_metadata or {}).get("split", {}) if run else {}
    return {
        "status": "available" if run else MISSING,
        "sampling_unit": "grouped_samples",
        "grouping_strategy": config.get("group_column", "not_recorded"),
        "validation_protocol": {"holdout": split.get("holdout_strategy", "not_recorded"), "cross_validation": split.get("cv_strategy", "not_recorded")},
        "group_counts": _pick(split, ("total_groups", "train_group_count", "test_group_count", "singleton_groups", "rows_per_group")),
        "aggregate_metrics_source": "evaluation",
        "limitations": ["Group identifiers are intentionally excluded from the Model Card."],
    }


def _robustness(records: list[RobustnessRecord]) -> dict:
    rows = [{
        "record_id": item.id, "perturbation_type": item.perturbation_type,
        "perturbation_level": item.perturbation_level, "seed": item.random_seed,
        "measured_result": _pick(item.result, (
            "status", "reason", "sample_count", "baseline_metrics", "perturbed_metrics",
            "degradation_delta", "relative_degradation", "undefined_metrics",
            "threshold_used", "threshold_source", "perturbation_metadata",
            "execution_timing", "reproducibility_metadata",
        )),
        "limitations": clean_json((item.result or {}).get("limitations", [])),
    } for item in records]
    return {"status": "available" if rows else MISSING, "records": rows}


def _quantum(model: ModelRecord, run: Run | None, config: dict, reports: list[QuantumDiagnosticReport]) -> dict:
    family = _family(model.model_type)
    if family == "classical":
        return {"status": "not_applicable"}
    model_config = config.get("hybrid" if family.startswith("hybrid") else "quantum") or {}
    persisted_plan = []
    if run:
        persisted_plan = (run.execution_metadata or {}).get("quantum_providers", [])
    matching = [plan for plan in persisted_plan if plan.get("provider_id") == model_config.get("provider_id")]
    execution = model.details.get("quantum") or {}
    compatible = [
        report for report in reports
        if report.status == "completed" and report.model_type == model.model_type
    ]
    return {
        "status": "available" if compatible else MISSING,
        "configuration_provenance_status": "available" if model_config or execution or matching else MISSING,
        "diagnostic_report_ids": [report.id for report in compatible],
        "provider_id": model_config.get("provider_id", execution.get("provider_id", "not_recorded")),
        "provider_display_name": execution.get("provider_display_name", "not_recorded"),
        "execution_mode": model_config.get("execution_mode", execution.get("execution_mode", "not_recorded")),
        "backend": model_config.get("backend", execution.get("backend", execution.get("backend_id", "not_recorded"))),
        "capability_information": clean_json(matching[0].get("capabilities", {})) if matching else MISSING,
        "configuration_fingerprint": (matching[0].get("configuration_fingerprint") if matching else execution.get("configuration_fingerprint", MISSING)),
        "actual_execution_evidence": _pick(execution, ("execution_kind", "real_hardware", "provider_id", "backend_id", "backend")),
        "runtime_limitations": ["Quantum provider use does not establish quantum advantage.", "Hardware execution is not claimed unless real_hardware is explicitly recorded as true."],
    }


def _gaps(*, task, run, source_context_type, version, multi, calibration, threshold, external, shift, group, robustness, quantum) -> list[dict]:
    candidates = [
        ("condition_task", task.get("condition_task_status") != "configured", "No ConditionTask is associated with this model."),
        ("run", run is None and source_context_type != "verified_demo_experiment", "No Run record is associated with this model."),
        ("dataset_version", version is None, "No immutable DatasetVersion is associated with this model."),
        ("multi_seed", multi["status"] == MISSING, "No multi-seed stability study is associated with this model."),
        ("calibration", calibration["status"] == MISSING, "No calibration study is associated with this model; probabilities must not be described as calibrated."),
        ("threshold", threshold["status"] == MISSING, "No threshold-analysis study is associated with this model."),
        ("external_validation", external["status"] == MISSING, "No external validation study is associated with this model."),
        ("distribution_shift", shift["status"] == MISSING, "No distribution-shift analysis is associated with this model."),
        ("group_validation", group["status"] == MISSING, "Grouped-validation evidence is unavailable."),
        ("robustness", robustness["status"] == MISSING, "No robustness record is associated with this model."),
        ("quantum_provenance", quantum["status"] == MISSING, "Quantum/provider provenance is unavailable for this quantum-family model."),
    ]
    return [{"category": category, "status": "not_available", "description": description} for category, missing, description in candidates if missing]


def assemble_card(session, model_id: str) -> tuple[dict, dict, list[Any]]:
    model = require(session, ModelRecord, model_id)
    experiment = session.get(Experiment, model.experiment_id)
    dataset = require(session, Dataset, model.dataset_id)
    run = session.get(Run, model.run_id) if model.run_id else None
    pipeline_version = (
        session.get(PipelineVersion, experiment.pipeline_version_id)
        if experiment and experiment.pipeline_version_id else None
    )
    protocol_version = (
        session.get(ExperimentProtocolVersion, experiment.protocol_version_id)
        if experiment and experiment.protocol_version_id else None
    )
    source_context_type = "live_run" if run else (
        "verified_demo_experiment"
        if (model.details or {}).get("experiment_kind") == "precomputed_verified_demo"
        else "unresolved"
    )
    config = clean_json((run.config if run else (experiment.config if experiment else {})) or {})
    version_id = run.dataset_version_id if run else config.get("dataset_version_id")
    version = session.get(DatasetVersion, version_id) if version_id else None
    task_id = config.get("condition_task_id")
    task = session.get(ConditionTask, str(task_id)) if task_id else None

    calibrations = list(session.scalars(select(CalibrationStudy).where(CalibrationStudy.model_id == model.id).order_by(CalibrationStudy.created_at)))
    thresholds = list(session.scalars(select(ThresholdAnalysisStudy).where(ThresholdAnalysisStudy.model_id == model.id).order_by(ThresholdAnalysisStudy.created_at)))
    externals = list(session.scalars(select(ExternalValidation).where(ExternalValidation.model_id == model.id).order_by(ExternalValidation.created_at)))
    shifts = list(session.scalars(select(DistributionShiftAnalysis).where(DistributionShiftAnalysis.model_id == model.id).order_by(DistributionShiftAnalysis.created_at)))
    robustness_records = list(session.scalars(select(RobustnessRecord).where(RobustnessRecord.model_id == model.id).order_by(RobustnessRecord.created_at)))
    studies = list(session.scalars(select(MultiSeedStudy).where(MultiSeedStudy.base_experiment_id == model.experiment_id).order_by(MultiSeedStudy.created_at)))
    diagnostic_reports = list(session.scalars(
        select(QuantumDiagnosticReport)
        .where(QuantumDiagnosticReport.model_record_id == model.id)
        .order_by(QuantumDiagnosticReport.created_at)
    ))
    studies = [study for study in studies if not study.model_identities or model.id in clean_json(study.model_identities) or model.model_type in clean_json(study.model_identities)]
    controlled_protocol = session.scalar(
        select(ControlledComparisonProtocol)
        .where(ControlledComparisonProtocol.experiment_id == model.experiment_id)
        .order_by(ControlledComparisonProtocol.created_at.desc())
    )
    controlled_pairs = [
        item for item in (controlled_protocol.comparison_pairs if controlled_protocol else [])
        if model.id in {item.get("classical_model", {}).get("id"), item.get("quantum_model", {}).get("id")}
    ]
    controlled_comparison = {
        "status": controlled_protocol.status,
        "protocol_id": controlled_protocol.id,
        "protocol_fingerprint": controlled_protocol.protocol_fingerprint,
        "artifact_id": controlled_protocol.artifact_id,
        "pair_statuses": [{"pair_id": item.get("pair_id"), "status": item.get("status")} for item in controlled_pairs],
    } if controlled_protocol and controlled_pairs else {"status": MISSING}

    condition = _condition(task)
    multi = _multi_seed(studies)
    calibration = _calibration(calibrations)
    threshold = _threshold(thresholds)
    external = _external(externals)
    shift = _shift(shifts)
    group = _group(run, config)
    robust = _robustness(robustness_records)
    quantum = _quantum(model, run, config, diagnostic_reports)
    data_section = _dataset(dataset, version)
    training_section = _training(config)
    model_section = _model_details(model, config)
    evaluation_section = _evaluation(model)
    gaps = _gaps(task=condition, run=run, source_context_type=source_context_type, version=version, multi=multi, calibration=calibration, threshold=threshold, external=external, shift=shift, group=group, robustness=robust, quantum=quantum)

    records: list[Any] = [model, *studies, *calibrations, *thresholds, *externals, *shifts, *robustness_records, *diagnostic_reports]
    if run:
        records.append(run)
    if controlled_protocol and controlled_pairs:
        records.append(controlled_protocol)
    card_status = (
        "INCOMPLETE_EVIDENCE"
        if not experiment or source_context_type == "unresolved"
        else ("COMPLETE_WITH_LIMITATIONS" if gaps else "COMPLETE")
    )
    limitations = [
        {"category": gap["category"], "description": gap["description"], "source": "evidence_availability"}
        for gap in gaps
    ]
    limitations.append({
        "category": "research_use",
        "description": "Research evaluation only. Documented evidence does not establish clinical safety, diagnostic efficacy, or prospective population generalization.",
        "source": "platform_boundary",
    })
    if quantum["status"] not in {"not_applicable", MISSING}:
        limitations.append({"category": "quantum", "description": "Provider execution evidence does not establish quantum advantage.", "source": "scientific_boundary"})

    generated_at = _latest_time(records, model.created_at)
    source = {
        "generated_at": generated_at,
        "model_identity": {
            "id": model.id, "type": model.model_type, "status": model.status,
            "artifact_sha256": model.artifact_sha256, "created_at": _time(model.created_at),
        },
        "experiment_identity": {
            "id": experiment.id if experiment else model.experiment_id,
            "name": experiment.name if experiment else "not_available",
            "status": experiment.status if experiment else "not_available",
        },
        "source_context_type": source_context_type,
        "condition": condition,
        "data": data_section,
        "training": training_section,
        "model": model_section,
        "evaluation": evaluation_section,
        "multi_seed": multi,
        "calibration": calibration,
        "threshold": threshold,
        "external_validation": external,
        "distribution_shift": shift,
        "group_validation": group,
        "robustness": robust,
        "quantum": quantum,
        "controlled_comparison": controlled_comparison,
        "pipeline": {
            "status": "available" if pipeline_version else MISSING,
            "pipeline_version_id": pipeline_version.id if pipeline_version else None,
            "version": pipeline_version.version_label if pipeline_version else None,
            "pipeline_fingerprint": pipeline_version.definition_fingerprint if pipeline_version else None,
        },
        "protocol": {
            "status": "available" if protocol_version else MISSING,
            "protocol_version_id": protocol_version.id if protocol_version else None,
            "version": protocol_version.version_label if protocol_version else None,
            "protocol_fingerprint": protocol_version.definition_fingerprint if protocol_version else None,
        },
        "run_provenance": {
            "id": run.id,
            "configuration_fingerprint": run.configuration_fingerprint,
            "reproducibility_status": run.reproducibility_status,
            "manifest_artifact_id": run.manifest_artifact_id,
            "software": clean_json((run.reproducibility_metadata or {}).get("software", MISSING)),
        } if run else None,
    }
    source_fingerprint = fingerprint(source)
    card_id = str(uuid5(NAMESPACE_URL, f"{MODEL_CARD_SCHEMA_VERSION}:{model.id}:{source_fingerprint}"))
    card = {
        "schema_version": MODEL_CARD_SCHEMA_VERSION,
        "card_id": card_id,
        "generated_at": generated_at,
        "card_status": card_status,
        "intended_use": {
            "use": "research evaluation workflow",
            "boundary": "Research evaluation only.",
            "disclaimer": "Does not establish clinical safety, diagnostic efficacy, deployment readiness, or prospective population generalization.",
        },
        "model_identity": {
            "model_id": model.id, "model_type": model.model_type, "model_family": _family(model.model_type),
            "model_status": model.status, "experiment_id": model.experiment_id,
            "run_id": _value(model.run_id), "dataset_id": model.dataset_id,
            "dataset_version_id": _value(version.id if version else None),
            "created_at": _time(model.created_at), "artifact_integrity_hash": _value(model.artifact_sha256),
            "configuration_fingerprint": _value(
                run.configuration_fingerprint if run else fingerprint(config) if config else None
            ),
            "provider_identity": quantum.get("provider_id", "not_applicable"),
        },
        "task": condition,
        "data": data_section,
        "training": training_section,
        "model": model_section,
        "evaluation": evaluation_section,
        "multi_seed_evidence": multi,
        "calibration": calibration,
        "threshold": threshold,
        "robustness": robust,
        "external_validation": external,
        "distribution_shift": shift,
        "group_validation": group,
        "quantum": quantum,
        "controlled_comparison": controlled_comparison,
        "provenance": {
            "source_fingerprint": source_fingerprint,
            "source_context": {
                "type": source_context_type,
                "experiment_id": model.experiment_id,
                "model_id": model.id,
                "dataset_id": dataset.id,
                "dataset_hash": version.content_sha256 if version else dataset.sha256,
                "configuration_fingerprint": (
                    run.configuration_fingerprint if run and run.configuration_fingerprint
                    else fingerprint(config) if config else MISSING
                ),
                "pipeline_version_id": pipeline_version.id if pipeline_version else None,
                "pipeline_fingerprint": pipeline_version.definition_fingerprint if pipeline_version else None,
                "verified_demo": clean_json((experiment.summary or {}) if experiment and source_context_type == "verified_demo_experiment" else {}),
            },
            "model_artifact_hash": _value(model.artifact_sha256),
            "manifest_artifact_id": _value(run.manifest_artifact_id if run else None),
            "evidence_sources": {
                "model_record_id": model.id,
                "run_id": _value(model.run_id),
                "experiment_id": model.experiment_id,
                "calibration_study_ids": [item.id for item in calibrations],
                "threshold_study_ids": [item.id for item in thresholds],
                "external_validation_ids": [item.id for item in externals],
                "distribution_shift_ids": [item.id for item in shifts],
                "robustness_record_ids": [item.id for item in robustness_records],
                "multi_seed_study_ids": [item.id for item in studies],
                "quantum_diagnostic_report_ids": [item.id for item in diagnostic_reports if item.status == "completed"],
                "controlled_comparison_protocol_id": controlled_protocol.id if controlled_protocol and controlled_pairs else None,
            },
        },
        "limitations": limitations,
        "evidence_gaps": gaps,
        "reproducibility": {
            "status": (
                _value(run.reproducibility_status, "incomplete") if run
                else "verified_precomputed_package" if source_context_type == "verified_demo_experiment"
                else "incomplete"
            ),
            "source_context_type": source_context_type,
            "configuration_fingerprint": _value(
                run.configuration_fingerprint if run else fingerprint(config) if config else None
            ),
            "pipeline_version_id": _value(pipeline_version.id if pipeline_version else None),
            "pipeline_fingerprint": _value(pipeline_version.definition_fingerprint if pipeline_version else None),
            "protocol_version_id": _value(protocol_version.id if protocol_version else None),
            "protocol_fingerprint": _value(protocol_version.definition_fingerprint if protocol_version else None),
            "run_id": _value(model.run_id), "experiment_id": model.experiment_id,
            "dataset_id": dataset.id, "dataset_version_id": _value(version.id if version else None),
            "dataset_hash": version.content_sha256 if version else dataset.sha256,
            "model_artifact_hash": _value(model.artifact_sha256),
            "manifest_artifact_id": _value(run.manifest_artifact_id if run else None),
            "software_runtime_metadata": clean_json((run.reproducibility_metadata or {}).get("software", MISSING)) if run else MISSING,
            "random_seed": config.get("seed", "not_recorded"),
            "provider_backend_metadata": clean_json((run.execution_metadata or {}).get("quantum_providers", "not_applicable")) if run else MISSING,
            "missing_provenance_fields": [gap["category"] for gap in gaps if gap["category"] in {"run", "dataset_version", "quantum_provenance"}],
        },
    }
    return clean_json(card), source, records


def get_or_create_card(session, model_id: str) -> tuple[dict, Artifact]:
    card, _, _ = assemble_card(session, model_id)
    source_fingerprint = card["provenance"]["source_fingerprint"]
    artifact = register_metadata(
        session,
        experiment_id=card["model_identity"]["experiment_id"],
        run_id=None if card["model_identity"]["run_id"] == MISSING else card["model_identity"]["run_id"],
        model_id=model_id,
        artifact_type="model_card",
        name=f"{card['model_identity']['model_type']} model card",
        description="Canonical evidence-only Model Card for research evaluation.",
        payload=card,
        operation_key=f"model-card:{MODEL_CARD_SCHEMA_VERSION}:{model_id}:{source_fingerprint}",
    )
    return card, artifact


def card_summary(card: dict, artifact: Artifact) -> dict:
    return {
        "schema_version": card["schema_version"],
        "card_id": card["card_id"],
        "artifact_id": artifact.id,
        "integrity_hash": artifact.integrity_hash,
        "generated_at": card["generated_at"],
        "card_status": card["card_status"],
        "model_identity": card["model_identity"],
        "task_status": card["task"]["condition_task_status"],
        "dataset": _pick(card["data"], ("dataset_id", "dataset_name", "dataset_version_id", "content_hash")),
        "evidence_availability": {
            key: card[key]["status"]
            for key in ("evaluation", "multi_seed_evidence", "calibration", "threshold", "robustness", "external_validation", "distribution_shift", "group_validation", "quantum")
        },
        "limitation_count": len(card["limitations"]),
        "evidence_gap_count": len(card["evidence_gaps"]),
        "research_only": True,
    }