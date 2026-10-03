from __future__ import annotations

from typing import Any
from sqlalchemy import select

from ..storage.entities import (
    AblationStudy,
    CalibrationStudy,
    ControlledComparisonProtocol,
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
)
from ..storage.repository import require
from ..utils.serialization import clean_json


def evaluate_experiment_compliance(session, experiment_id: str) -> dict[str, Any]:
    experiment = require(session, Experiment, experiment_id)
    if not experiment.protocol_version_id:
        return {
            "experiment_id": experiment.id,
            "status": "UNAVAILABLE",
            "protocol_version_id": None,
            "protocol_name": None,
            "protocol_version": None,
            "protocol_fingerprint": None,
            "compliance_summary": {
                "matched": 0,
                "missing": 0,
                "mismatched": 0,
                "not_applicable": 0,
                "unverifiable": 0,
                "total_checks": 0,
            },
            "checks": [],
            "reason": "This experiment does not have an assigned protocol version.",
            "interpretation": "Protocol compliance cannot be evaluated for an experiment without an assigned protocol.",
        }

    version = require(session, ExperimentProtocolVersion, experiment.protocol_version_id)
    family = version.protocol if hasattr(version, "protocol") and version.protocol else None
    family_name = family.name if family else "Experiment Protocol"
    canonical = version.canonical_definition or {}

    config = clean_json(experiment.config or {})
    models = list(session.scalars(select(ModelRecord).where(ModelRecord.experiment_id == experiment.id)))
    model_ids = {m.id for m in models}
    runs = list(session.scalars(select(Run).where(Run.experiment_id == experiment.id)))

    multi_seed_studies = list(session.scalars(select(MultiSeedStudy).where(MultiSeedStudy.base_experiment_id == experiment.id)))
    external_validations = list(session.scalars(select(ExternalValidation).where(ExternalValidation.experiment_id == experiment.id)))
    external_ids = {ev.id for ev in external_validations}
    shift_analyses = list(session.scalars(select(DistributionShiftAnalysis).where(
        (DistributionShiftAnalysis.model_id.in_(model_ids) if model_ids else False)
        | (DistributionShiftAnalysis.external_validation_id.in_(external_ids) if external_ids else False)
    )))
    calibration_studies = list(session.scalars(select(CalibrationStudy).where(
        CalibrationStudy.model_id.in_(model_ids) if model_ids else False
    )))
    threshold_studies = list(session.scalars(select(ThresholdAnalysisStudy).where(
        ThresholdAnalysisStudy.model_id.in_(model_ids) if model_ids else False
    )))
    robustness_records = list(session.scalars(select(RobustnessRecord).where(RobustnessRecord.experiment_id == experiment.id)))
    ablation_studies = list(session.scalars(select(AblationStudy).where(AblationStudy.base_experiment_id == experiment.id)))
    controlled_protocols = list(session.scalars(select(ControlledComparisonProtocol).where(ControlledComparisonProtocol.experiment_id == experiment.id)))

    checks: list[dict[str, Any]] = []

    # 1. Dataset Policy
    ds_policy = canonical.get("dataset_policy") or {}
    expected_ds_id = ds_policy.get("dataset_id")
    if expected_ds_id:
        matched = str(experiment.dataset_id) == str(expected_ds_id)
        checks.append({
            "rule": "dataset_id",
            "category": "dataset_policy",
            "requirement": "REQUIRED",
            "expected": str(expected_ds_id),
            "actual": str(experiment.dataset_id),
            "status": "MATCHED" if matched else "MISMATCHED",
            "details": "Dataset matches declared protocol." if matched else "Dataset does not match declared protocol dataset lock.",
        })
    else:
        checks.append({
            "rule": "dataset_id",
            "category": "dataset_policy",
            "requirement": "OPTIONAL",
            "expected": None,
            "actual": str(experiment.dataset_id),
            "status": "NOT_APPLICABLE",
            "details": "No specific dataset was locked by the protocol.",
        })

    # 2. Dataset Version
    expected_ver_id = ds_policy.get("dataset_version_id")
    req_ver = ds_policy.get("required_dataset_version", False)
    actual_ver_id = config.get("dataset_version_id") or (runs[0].dataset_version_id if runs else None)
    if expected_ver_id:
        matched = str(actual_ver_id) == str(expected_ver_id) if actual_ver_id else False
        checks.append({
            "rule": "dataset_version_id",
            "category": "dataset_policy",
            "requirement": "REQUIRED",
            "expected": str(expected_ver_id),
            "actual": str(actual_ver_id) if actual_ver_id else None,
            "status": "MATCHED" if matched else ("MISSING" if not actual_ver_id else "MISMATCHED"),
            "details": "Exact dataset version was applied." if matched else "Declared dataset version was not applied.",
        })
    elif req_ver:
        matched = actual_ver_id is not None
        checks.append({
            "rule": "dataset_version_lock",
            "category": "dataset_policy",
            "requirement": "REQUIRED",
            "expected": "locked_version",
            "actual": str(actual_ver_id) if actual_ver_id else None,
            "status": "MATCHED" if matched else "MISSING",
            "details": "Immutable dataset version is locked." if matched else "Protocol requires locking an immutable dataset version.",
        })
    else:
        checks.append({
            "rule": "dataset_version_lock",
            "category": "dataset_policy",
            "requirement": "OPTIONAL",
            "expected": None,
            "actual": str(actual_ver_id) if actual_ver_id else None,
            "status": "NOT_APPLICABLE",
            "details": "Dataset version locking was optional.",
        })

    # 3. Task Type
    study_meta = canonical.get("study_metadata") or {}
    expected_task = study_meta.get("task_type", "binary_classification")
    actual_task = config.get("task_type", "binary_classification")
    matched = expected_task == actual_task
    checks.append({
        "rule": "task_type",
        "category": "study_metadata",
        "requirement": "REQUIRED",
        "expected": expected_task,
        "actual": actual_task,
        "status": "MATCHED" if matched else "MISMATCHED",
        "details": f"Task type matches ({expected_task})." if matched else f"Expected {expected_task}, actual {actual_task}.",
    })

    # 4. Split Policy (test_size)
    split_policy = canonical.get("split_policy") or {}
    expected_test_size = split_policy.get("test_size")
    actual_test_size = config.get("test_size")
    if actual_test_size is None:
        checks.append({
            "rule": "test_size",
            "category": "split_policy",
            "requirement": "REQUIRED",
            "expected": expected_test_size,
            "actual": None,
            "status": "UNVERIFIABLE",
            "details": "Test split fraction is not recorded in experiment configuration.",
        })
    elif expected_test_size is not None and abs(float(actual_test_size) - float(expected_test_size)) < 1e-4:
        checks.append({
            "rule": "test_size",
            "category": "split_policy",
            "requirement": "REQUIRED",
            "expected": expected_test_size,
            "actual": actual_test_size,
            "status": "MATCHED",
            "details": f"Test split fraction matched ({expected_test_size}).",
        })
    else:
        checks.append({
            "rule": "test_size",
            "category": "split_policy",
            "requirement": "REQUIRED",
            "expected": expected_test_size,
            "actual": actual_test_size,
            "status": "MISMATCHED",
            "details": f"Test split fraction mismatch: expected {expected_test_size}, actual {actual_test_size}.",
        })

    # 5. Split Policy (cv_folds)
    expected_cv = split_policy.get("cv_folds")
    actual_cv = config.get("cv_folds")
    if actual_cv is None:
        checks.append({
            "rule": "cv_folds",
            "category": "split_policy",
            "requirement": "REQUIRED",
            "expected": expected_cv,
            "actual": None,
            "status": "UNVERIFIABLE",
            "details": "Cross-validation fold count is not recorded in experiment configuration.",
        })
    elif expected_cv is not None and int(actual_cv) == int(expected_cv):
        checks.append({
            "rule": "cv_folds",
            "category": "split_policy",
            "requirement": "REQUIRED",
            "expected": expected_cv,
            "actual": actual_cv,
            "status": "MATCHED",
            "details": f"Cross-validation fold count matched ({expected_cv}).",
        })
    else:
        checks.append({
            "rule": "cv_folds",
            "category": "split_policy",
            "requirement": "REQUIRED",
            "expected": expected_cv,
            "actual": actual_cv,
            "status": "MISMATCHED",
            "details": f"CV folds mismatch: expected {expected_cv}, actual {actual_cv}.",
        })

    # 6. Randomness Policy (primary_seed)
    rand_policy = canonical.get("randomness_policy") or {}
    expected_seed = rand_policy.get("primary_seed")
    actual_seed = config.get("seed")
    if actual_seed is None:
        checks.append({
            "rule": "primary_seed",
            "category": "randomness_policy",
            "requirement": "REQUIRED",
            "expected": expected_seed,
            "actual": None,
            "status": "UNVERIFIABLE",
            "details": "Seed is not explicitly recorded in configuration.",
        })
    elif expected_seed is not None and int(actual_seed) == int(expected_seed):
        checks.append({
            "rule": "primary_seed",
            "category": "randomness_policy",
            "requirement": "REQUIRED",
            "expected": expected_seed,
            "actual": actual_seed,
            "status": "MATCHED",
            "details": f"Primary random seed matched ({expected_seed}).",
        })
    else:
        checks.append({
            "rule": "primary_seed",
            "category": "randomness_policy",
            "requirement": "REQUIRED",
            "expected": expected_seed,
            "actual": actual_seed,
            "status": "MISMATCHED",
            "details": f"Seed mismatch: expected {expected_seed}, actual {actual_seed}.",
        })

    # 7. Evaluation Policy (primary_metric)
    eval_policy = canonical.get("evaluation_policy") or {}
    primary_metric = eval_policy.get("primary_metric", "roc_auc")
    if not models:
        checks.append({
            "rule": "primary_metric",
            "category": "evaluation_policy",
            "requirement": "REQUIRED",
            "expected": primary_metric,
            "actual": None,
            "status": "UNVERIFIABLE",
            "details": "No models have completed evaluation yet.",
        })
    else:
        metric_found = any(
            isinstance(m.metrics, dict)
            and isinstance(m.metrics.get("test"), dict)
            and primary_metric in m.metrics["test"]
            for m in models
        )
        checks.append({
            "rule": "primary_metric",
            "category": "evaluation_policy",
            "requirement": "REQUIRED",
            "expected": primary_metric,
            "actual": primary_metric if metric_found else "missing_from_models",
            "status": "MATCHED" if metric_found else "MISSING",
            "details": f"Primary metric '{primary_metric}' is evaluated on held-out test data." if metric_found else f"Metric '{primary_metric}' was not evaluated on held-out test data.",
        })

    # Helper for requirement-based validation
    def _eval_requirement(rule_name: str, category: str, requirement: str, actual_present: bool, details_matched: str, details_missing: str):
        if requirement == "REQUIRED":
            status = "MATCHED" if actual_present else "MISSING"
            checks.append({
                "rule": rule_name,
                "category": category,
                "requirement": "REQUIRED",
                "expected": True,
                "actual": actual_present,
                "status": status,
                "details": details_matched if actual_present else details_missing,
            })
        elif requirement == "DISABLED":
            status = "MATCHED" if not actual_present else "MISMATCHED"
            checks.append({
                "rule": rule_name,
                "category": category,
                "requirement": "DISABLED",
                "expected": False,
                "actual": actual_present,
                "status": status,
                "details": "Component correctly excluded." if not actual_present else "Component was forbidden by protocol but found.",
            })
        else: # OPTIONAL
            checks.append({
                "rule": rule_name,
                "category": category,
                "requirement": "OPTIONAL",
                "expected": "optional",
                "actual": actual_present,
                "status": "MATCHED" if actual_present else "NOT_APPLICABLE",
                "details": "Optional requirement fulfilled." if actual_present else "Optional component was omitted without protocol failure.",
            })

    # 8. Threshold Policy
    thresh_policy = canonical.get("threshold_policy") or {}
    thresh_req = thresh_policy.get("requirement", "REQUIRED")
    has_threshold = len(threshold_studies) > 0 or bool(config.get("probability_threshold") or config.get("threshold_strategy"))
    _eval_requirement(
        "threshold_policy", "threshold_policy", thresh_req, has_threshold,
        "Threshold analysis / operating point evidence is recorded.",
        "Operating threshold evaluation required by protocol is missing."
    )

    # 9. Calibration Policy
    calib_policy = canonical.get("calibration_policy") or {}
    calib_req = calib_policy.get("requirement", "REQUIRED")
    has_calibration = len(calibration_studies) > 0 or bool(config.get("calibration"))
    _eval_requirement(
        "calibration_policy", "calibration_policy", calib_req, has_calibration,
        "Probability calibration evidence is recorded.",
        "Calibration study required by protocol is missing."
    )

    # 10. Multi-Seed Extension
    val_ext = canonical.get("validation_extensions") or {}
    multi_seed_spec = val_ext.get("multi_seed") or {}
    ms_req = multi_seed_spec.get("requirement", "OPTIONAL")
    min_seeds = multi_seed_spec.get("min_seed_count", 5)
    has_multi_seed = len(multi_seed_studies) > 0
    if ms_req == "REQUIRED":
        if has_multi_seed:
            study = multi_seed_studies[0]
            actual_seed_count = len(study.seed_runs) if hasattr(study, "seed_runs") and study.seed_runs else (
                (study.configuration or {}).get("n_seeds", 0)
            )
            seed_ok = actual_seed_count >= min_seeds
            checks.append({
                "rule": "multi_seed_evaluation",
                "category": "validation_extensions",
                "requirement": "REQUIRED",
                "expected": f">={min_seeds} seeds",
                "actual": f"{actual_seed_count} seeds",
                "status": "MATCHED" if seed_ok else "MISMATCHED",
                "details": f"Multi-seed study completed with {actual_seed_count} seeds." if seed_ok else f"Multi-seed count {actual_seed_count} is less than required {min_seeds}.",
            })
        else:
            checks.append({
                "rule": "multi_seed_evaluation",
                "category": "validation_extensions",
                "requirement": "REQUIRED",
                "expected": f">={min_seeds} seeds",
                "actual": None,
                "status": "MISSING",
                "details": f"Required multi-seed evaluation study is missing.",
            })
    else:
        _eval_requirement(
            "multi_seed_evaluation", "validation_extensions", ms_req, has_multi_seed,
            "Multi-seed evaluation study is present.",
            "Multi-seed evaluation was not executed."
        )

    # 11. External Validation Extension
    ext_spec = val_ext.get("external_validation") or {}
    ext_req = ext_spec.get("requirement", "OPTIONAL")
    has_external = len(external_validations) > 0
    _eval_requirement(
        "external_validation", "validation_extensions", ext_req, has_external,
        "External validation study is recorded.",
        "External cohort validation required by protocol is missing."
    )

    # 12. Distribution Shift Extension
    shift_spec = val_ext.get("distribution_shift") or {}
    shift_req = shift_spec.get("requirement", "OPTIONAL")
    has_shift = len(shift_analyses) > 0
    _eval_requirement(
        "distribution_shift", "validation_extensions", shift_req, has_shift,
        "Distribution shift analysis is recorded.",
        "Distribution shift analysis required by protocol is missing."
    )

    # 13. Group Validation Extension
    group_spec = val_ext.get("group_validation") or {}
    group_req = group_spec.get("requirement", "OPTIONAL")
    has_group = bool(config.get("group_column") or config.get("sampling_unit") == "grouped_samples")
    _eval_requirement(
        "group_validation", "validation_extensions", group_req, has_group,
        "Group-aware validation constraints are configured.",
        "Group-aware validation required by protocol is missing."
    )

    # 14. Robustness Extension
    rob_spec = val_ext.get("robustness") or {}
    rob_req = rob_spec.get("requirement", "OPTIONAL")
    has_robustness = len(robustness_records) > 0
    _eval_requirement(
        "robustness_analysis", "validation_extensions", rob_req, has_robustness,
        "Perturbation robustness records are present.",
        "Robustness stress testing required by protocol is missing."
    )

    # 15. Ablation Extension
    abl_spec = val_ext.get("ablation") or {}
    abl_req = abl_spec.get("requirement", "OPTIONAL")
    has_ablation = len(ablation_studies) > 0
    _eval_requirement(
        "ablation_study", "validation_extensions", abl_req, has_ablation,
        "Controlled component ablation study is recorded.",
        "Ablation study required by protocol is missing."
    )

    # 16. Quantum Controls
    qc_spec = canonical.get("quantum_controls") or {}
    qc_req = qc_spec.get("requirement", "OPTIONAL")
    has_ctrl = len(controlled_protocols) > 0
    _eval_requirement(
        "controlled_comparison", "quantum_controls", qc_req, has_ctrl,
        "Controlled classical-vs-quantum comparison protocol is present.",
        "Controlled comparison evidence required by protocol is missing."
    )

    # 17. Pipeline Version Lock
    pipeline_policy = canonical.get("pipeline_policy") or {}
    expected_pipe_id = pipeline_policy.get("pipeline_version_id")
    pipe_req = pipeline_policy.get("requirement", "OPTIONAL")
    actual_pipe_id = experiment.pipeline_version_id
    if expected_pipe_id:
        matched = str(actual_pipe_id) == str(expected_pipe_id) if actual_pipe_id else False
        checks.append({
            "rule": "pipeline_version",
            "category": "pipeline_policy",
            "requirement": "REQUIRED",
            "expected": str(expected_pipe_id),
            "actual": str(actual_pipe_id) if actual_pipe_id else None,
            "status": "MATCHED" if matched else ("MISSING" if not actual_pipe_id else "MISMATCHED"),
            "details": "Experiment executed with exact declared pipeline version." if matched else "Pipeline version does not match declared protocol lock.",
        })
    elif pipe_req == "REQUIRED":
        matched = actual_pipe_id is not None
        checks.append({
            "rule": "pipeline_version",
            "category": "pipeline_policy",
            "requirement": "REQUIRED",
            "expected": "locked_pipeline_version",
            "actual": str(actual_pipe_id) if actual_pipe_id else None,
            "status": "MATCHED" if matched else "MISSING",
            "details": "Pipeline version is locked." if matched else "Protocol requires a locked Pipeline Version.",
        })
    else:
        checks.append({
            "rule": "pipeline_version",
            "category": "pipeline_policy",
            "requirement": "OPTIONAL",
            "expected": None,
            "actual": str(actual_pipe_id) if actual_pipe_id else None,
            "status": "MATCHED" if actual_pipe_id else "NOT_APPLICABLE",
            "details": "Pipeline version present." if actual_pipe_id else "Pipeline version reference was optional.",
        })

    # Summary counts (Strictly factual diagnostic numbers, NEVER a percentage score)
    counts = {
        "matched": sum(1 for c in checks if c["status"] == "MATCHED"),
        "missing": sum(1 for c in checks if c["status"] == "MISSING"),
        "mismatched": sum(1 for c in checks if c["status"] == "MISMATCHED"),
        "not_applicable": sum(1 for c in checks if c["status"] == "NOT_APPLICABLE"),
        "unverifiable": sum(1 for c in checks if c["status"] == "UNVERIFIABLE"),
        "total_checks": len(checks),
    }

    return {
        "experiment_id": experiment.id,
        "status": "AVAILABLE",
        "protocol_version_id": version.id,
        "protocol_name": family_name,
        "protocol_version": version.version_label,
        "protocol_fingerprint": version.definition_fingerprint,
        "compliance_summary": counts,
        "checks": checks,
        "interpretation": "Protocol compliance verifies whether explicit pre-declared experimental rules were fulfilled. It does not establish scientific validity, model quality, or performance ranking.",
    }
