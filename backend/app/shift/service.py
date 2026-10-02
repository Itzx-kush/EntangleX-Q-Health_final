"""Service layer for distribution-shift and dataset-shift analysis."""

from __future__ import annotations

import hashlib
from time import perf_counter
from typing import Any
from uuid import uuid4
import numpy as np
import pandas as pd
from sqlalchemy import select

from ..artifacts.service import register_metadata
from ..data.service import load_versioned_frame
from ..dataset_versions.service import resolve_version
from ..storage.entities import (
    Dataset,
    DatasetVersion,
    DistributionShiftAnalysis,
    Experiment,
    ExternalValidation,
    ModelRecord,
    MultiSeedStudy,
)
from ..storage.files import load_model, safe_path, verify
from ..utils.errors import AppError
from ..utils.serialization import clean_json, software_versions, utcnow
from .constants import (
    DEFAULT_CATEGORICAL_DISTANCE_THRESHOLD,
    DEFAULT_CATEGORICAL_TEST,
    DEFAULT_MISSINGNESS_DELTA_THRESHOLD,
    DEFAULT_MULTIPLE_TESTING_CORRECTION,
    DEFAULT_NUMERIC_DISTANCE_THRESHOLD,
    DEFAULT_NUMERIC_TEST,
    DEFAULT_SIGNIFICANCE_THRESHOLD,
    DISTRIBUTION_SHIFT_POLICY_VERSION,
    SHIFT_DIRECTION_CONVENTION,
    SHIFT_LIMITATIONS,
)
from .statistics import (
    benjamini_hochberg_fdr,
    compute_categorical_shift,
    compute_missingness_shift,
    compute_numeric_shift,
)


def make_shift_operation_key(
    reference_dataset_id: str,
    comparison_dataset_id: str,
    reference_version_id: str | None = None,
    comparison_version_id: str | None = None,
    model_id: str | None = None,
    external_validation_id: str | None = None,
    idempotency_key: str | None = None,
) -> str:
    """Generate a deterministic operation key for shift analysis deduplication and idempotency."""
    if idempotency_key:
        return f"idemp:{idempotency_key}"
    parts = [
        str(reference_dataset_id),
        str(comparison_dataset_id),
        str(reference_version_id or "none"),
        str(comparison_version_id or "none"),
        str(model_id or "none"),
        str(external_validation_id or "none"),
    ]
    digest = hashlib.sha256(":".join(parts).encode()).hexdigest()[:32]
    return f"shift:{digest}"


def resolve_shift_preflight(
    session,
    *,
    reference_dataset_id: str,
    comparison_dataset_id: str,
    reference_dataset_version_id: str | None = None,
    comparison_dataset_version_id: str | None = None,
    model_id: str | None = None,
    external_validation_id: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute non-mutating preflight checks for distribution-shift analysis."""
    block_reasons: list[str] = []
    warnings: list[str] = []

    # 1. Reference dataset check
    ref_ds = session.scalar(select(Dataset).where(Dataset.id == reference_dataset_id))
    if ref_ds is None:
        raise AppError("dataset_not_found", f"Reference dataset {reference_dataset_id} does not exist.", 404)

    # 2. Comparison dataset check
    comp_ds = session.scalar(select(Dataset).where(Dataset.id == comparison_dataset_id))
    if comp_ds is None:
        raise AppError("dataset_not_found", f"Comparison dataset {comparison_dataset_id} does not exist.", 404)

    # 3. Reference version resolution
    ref_ver = None
    if reference_dataset_version_id:
        ref_ver = session.get(DatasetVersion, reference_dataset_version_id)
        if ref_ver is None or ref_ver.dataset_id != ref_ds.id:
            raise AppError("dataset_version_not_found", f"Reference dataset version {reference_dataset_version_id} not found.", 404)
    else:
        ref_ver = resolve_version(session, ref_ds)

    # 4. Comparison version resolution
    comp_ver = None
    if comparison_dataset_version_id:
        comp_ver = session.get(DatasetVersion, comparison_dataset_version_id)
        if comp_ver is None or comp_ver.dataset_id != comp_ds.id:
            raise AppError("dataset_version_not_found", f"Comparison dataset version {comparison_dataset_version_id} not found.", 404)
    else:
        comp_ver = resolve_version(session, comp_ds)

    # 5. Model validation if provided
    model_record: ModelRecord | None = None
    model_bundle: dict[str, Any] | None = None
    model_features: list[str] | None = None
    if model_id is not None:
        model_record = session.scalar(select(ModelRecord).where(ModelRecord.id == model_id))
        if model_record is None:
            raise AppError("model_not_found", f"Model {model_id} does not exist.", 404)
        if model_record.status != "ready" or not model_record.artifact_sha256:
            raise AppError("model_not_ready", f"Model {model_id} has status '{model_record.status}', expected 'ready'.", 409)
        try:
            model_bundle = load_model(model_record.id, model_record.artifact_sha256)
            model_features = list(model_bundle.get("features", []))
        except Exception as exc:
            raise AppError("integrity_error", f"Model artifact integrity verification failed: {str(exc)}", 409) from exc

    # 6. External validation validation if provided
    ext_val_record: ExternalValidation | None = None
    if external_validation_id is not None:
        ext_val_record = session.scalar(select(ExternalValidation).where(ExternalValidation.id == external_validation_id))
        if ext_val_record is None:
            raise AppError("validation_not_found", f"External validation {external_validation_id} does not exist.", 404)

    # 7. Check file integrity
    ref_hash = ref_ver.content_sha256 if ref_ver else ref_ds.sha256
    comp_hash = comp_ver.content_sha256 if comp_ver else comp_ds.sha256

    try:
        ref_path = safe_path("data/datasets", ref_ds.id, ".csv")
        verify(ref_path, ref_hash)
    except Exception as exc:
        raise AppError("integrity_error", f"Reference dataset file verification failed: {str(exc)}", 409) from exc

    try:
        comp_path = safe_path("data/datasets", comp_ds.id, ".csv")
        verify(comp_path, comp_hash)
    except Exception as exc:
        raise AppError("integrity_error", f"Comparison dataset file verification failed: {str(exc)}", 409) from exc

    # Load dataframes safely
    try:
        _, _, ref_df = load_versioned_frame(ref_ds.id, ref_ver.id if ref_ver else None, ref_hash)
    except Exception as exc:
        raise AppError("dataset_load_failed", f"Failed to load reference dataset frame: {str(exc)}", 409) from exc

    try:
        _, _, comp_df = load_versioned_frame(comp_ds.id, comp_ver.id if comp_ver else None, comp_hash)
    except Exception as exc:
        raise AppError("dataset_load_failed", f"Failed to load comparison dataset frame: {str(exc)}", 409) from exc

    # Check same dataset comparison
    is_same_dataset = (
        ref_ds.id == comp_ds.id
        and (ref_ver.id if ref_ver else None) == (comp_ver.id if comp_ver else None)
        and ref_hash == comp_hash
    )
    if is_same_dataset:
        warnings.append(
            "Reference and comparison datasets are identical; shift analysis will reflect zero difference baseline."
        )

    # 8. Schema Analysis Preview
    ref_cols = list(ref_df.columns)
    comp_cols = list(comp_df.columns)
    shared_cols = [c for c in ref_cols if c in comp_cols]
    missing_in_comp = [c for c in ref_cols if c not in comp_cols]
    extra_in_comp = [c for c in comp_cols if c not in ref_cols]

    # Type detection and mismatch identification
    type_mismatches: list[dict[str, str]] = []
    for col in shared_cols:
        ref_is_num = bool(pd.api.types.is_numeric_dtype(ref_df[col]))
        comp_is_num = bool(pd.api.types.is_numeric_dtype(comp_df[col]))
        if ref_is_num != comp_is_num:
            type_mismatches.append({
                "feature": col,
                "reference_type": "numeric" if ref_is_num else "categorical",
                "comparison_type": "numeric" if comp_is_num else "categorical",
            })
            warnings.append(
                f"Feature '{col}' has type mismatch: numeric in reference, categorical in comparison."
                if ref_is_num else
                f"Feature '{col}' has type mismatch: categorical in reference, numeric in comparison."
            )

    if extra_in_comp:
        warnings.append(
            f"Comparison dataset contains {len(extra_in_comp)} extra column(s) not in reference: {extra_in_comp[:5]}."
        )

    # Check model features if model supplied
    missing_model_features: list[str] = []
    if model_features is not None:
        missing_model_features = [f for f in model_features if f not in comp_cols]
        if missing_model_features:
            warnings.append(
                f"Comparison dataset is missing {len(missing_model_features)} feature(s) required by model: {missing_model_features[:5]}."
            )

    # 9. Target analysis
    ref_target = ref_ver.target if ref_ver else ref_ds.provenance.get("target")
    comp_target = comp_ver.target if comp_ver else comp_ds.provenance.get("target")

    target_evaluated = False
    target_compatible = False
    ref_classes: list[str] = []
    comp_classes: list[str] = []
    ref_counts: dict[str, int] = {}
    comp_counts: dict[str, int] = {}
    ref_pos_prev: float | None = None
    comp_pos_prev: float | None = None
    prev_delta: float | None = None
    target_interp: str | None = None

    if ref_target and comp_target and ref_target == comp_target:
        if ref_target in ref_df.columns and comp_target in comp_df.columns:
            target_evaluated = True
            ref_s = ref_df[ref_target].dropna().astype(str).str.strip()
            comp_s = comp_df[comp_target].dropna().astype(str).str.strip()

            ref_classes = sorted(ref_s.unique().tolist())
            comp_classes = sorted(comp_s.unique().tolist())

            ref_counts = {k: int(v) for k, v in ref_s.value_counts().to_dict().items()}
            comp_counts = {k: int(v) for k, v in comp_s.value_counts().to_dict().items()}

            ref_pos_label = ref_ver.positive_label if ref_ver else ref_ds.provenance.get("positive_label")
            comp_pos_label = comp_ver.positive_label if comp_ver else comp_ds.provenance.get("positive_label")

            if set(ref_classes) == set(comp_classes):
                target_compatible = True
                if ref_pos_label and ref_pos_label in ref_classes and comp_pos_label and comp_pos_label in comp_classes:
                    ref_pos_prev = float(ref_counts.get(ref_pos_label, 0) / len(ref_s)) if len(ref_s) > 0 else 0.0
                    comp_pos_prev = float(comp_counts.get(comp_pos_label, 0) / len(comp_s)) if len(comp_s) > 0 else 0.0
                    prev_delta = float(comp_pos_prev - ref_pos_prev)
                    target_interp = f"Observed positive-class prevalence differs by {prev_delta:+.4f} ({prev_delta * 100:+.2f}%)."
            else:
                warnings.append(
                    f"Target classes differ across cohorts: reference has {ref_classes}, comparison has {comp_classes}."
                )

    schema_preview = {
        "reference_columns": ref_cols,
        "comparison_columns": comp_cols,
        "shared_columns": shared_cols,
        "missing_in_comparison": missing_in_comp,
        "extra_in_comparison": extra_in_comp,
        "type_mismatches": type_mismatches,
        "reference_feature_count": len(ref_cols) - (1 if ref_target in ref_cols else 0),
        "comparison_feature_count": len(comp_cols) - (1 if comp_target in comp_cols else 0),
    }

    target_preview = {
        "target_evaluated": target_evaluated,
        "target_column": ref_target if target_evaluated else None,
        "reference_classes": ref_classes,
        "comparison_classes": comp_classes,
        "compatible": target_compatible,
        "reference_counts": ref_counts,
        "comparison_counts": comp_counts,
        "reference_positive_prevalence": ref_pos_prev,
        "comparison_positive_prevalence": comp_pos_prev,
        "prevalence_delta": prev_delta,
        "interpretation": target_interp,
    }

    ready = len(block_reasons) == 0

    return {
        "ready": ready,
        "reference_dataset": {
            "id": ref_ds.id,
            "name": ref_ds.name,
            "version_id": ref_ver.id if ref_ver else None,
            "version_label": ref_ver.version_label if ref_ver else None,
            "sha256": ref_hash,
            "row_count": len(ref_df),
        },
        "comparison_dataset": {
            "id": comp_ds.id,
            "name": comp_ds.name,
            "version_id": comp_ver.id if comp_ver else None,
            "version_label": comp_ver.version_label if comp_ver else None,
            "sha256": comp_hash,
            "row_count": len(comp_df),
        },
        "model": {
            "id": model_record.id,
            "model_type": model_record.model_type,
            "status": model_record.status,
            "feature_count": len(model_features) if model_features else 0,
        } if model_record else None,
        "external_validation": {
            "id": ext_val_record.id,
            "status": ext_val_record.status,
            "threshold": ext_val_record.threshold_metadata.get("threshold"),
        } if ext_val_record else None,
        "schema_preview": schema_preview,
        "target_preview": target_preview,
        "model_features": model_features,
        "missing_model_features": missing_model_features,
        "warnings": warnings,
        "block_reasons": block_reasons,
    }


def execute_shift_analysis(
    session,
    request: Any,
    *,
    idempotency_key: str | None = None,
) -> DistributionShiftAnalysis:
    """Execute comprehensive distribution-shift analysis between reference and comparison datasets."""
    start_time = perf_counter()

    ref_id = str(request.reference_dataset_id)
    comp_id = str(request.comparison_dataset_id)
    ref_ver_id = str(request.reference_dataset_version_id) if request.reference_dataset_version_id else None
    comp_ver_id = str(request.comparison_dataset_version_id) if request.comparison_dataset_version_id else None
    model_id = str(request.model_id) if request.model_id else None
    ext_val_id = str(request.external_validation_id) if request.external_validation_id else None

    op_key = make_shift_operation_key(
        ref_id, comp_id, ref_ver_id, comp_ver_id, model_id, ext_val_id, idempotency_key
    )

    # Check for existing completed analysis with same idempotency/operation key
    existing = session.scalar(
        select(DistributionShiftAnalysis).where(DistributionShiftAnalysis.operation_key == op_key)
    )
    if existing is not None and existing.status == "completed":
        return existing

    cfg_dict = request.config.model_dump(mode="json") if request.config else {}
    missingness_threshold = cfg_dict.get("missingness_delta_threshold", DEFAULT_MISSINGNESS_DELTA_THRESHOLD)
    numeric_dist_threshold = cfg_dict.get("numeric_distance_threshold", DEFAULT_NUMERIC_DISTANCE_THRESHOLD)
    categorical_dist_threshold = cfg_dict.get("categorical_distance_threshold", DEFAULT_CATEGORICAL_DISTANCE_THRESHOLD)
    significance_threshold = cfg_dict.get("statistical_significance_threshold", DEFAULT_SIGNIFICANCE_THRESHOLD)
    multiple_testing_correction = cfg_dict.get("multiple_testing_correction", DEFAULT_MULTIPLE_TESTING_CORRECTION)

    resolved_config = {
        "missingness_delta_threshold": missingness_threshold,
        "numeric_distance_threshold": numeric_dist_threshold,
        "categorical_distance_threshold": categorical_dist_threshold,
        "statistical_significance_threshold": significance_threshold,
        "multiple_testing_correction": multiple_testing_correction,
        "numeric_test": DEFAULT_NUMERIC_TEST,
        "categorical_test": DEFAULT_CATEGORICAL_TEST,
        "direction_convention": SHIFT_DIRECTION_CONVENTION,
    }

    # Execute preflight checks
    preflight = resolve_shift_preflight(
        session,
        reference_dataset_id=ref_id,
        comparison_dataset_id=comp_id,
        reference_dataset_version_id=ref_ver_id,
        comparison_dataset_version_id=comp_ver_id,
        model_id=model_id,
        external_validation_id=ext_val_id,
        config=resolved_config,
    )

    ref_hash = preflight["reference_dataset"]["sha256"]
    comp_hash = preflight["comparison_dataset"]["sha256"]

    # Load dataframes
    _, _, ref_df = load_versioned_frame(ref_id, ref_ver_id, ref_hash)
    _, _, comp_df = load_versioned_frame(comp_id, comp_ver_id, comp_hash)

    schema_preview = preflight["schema_preview"]
    target_preview = preflight["target_preview"]
    warnings = list(preflight["warnings"])
    model_features = set(preflight["model_features"]) if preflight.get("model_features") else None

    # Determine features to evaluate: exclude target from features
    target_col = target_preview.get("target_column")
    shared_features = [c for c in schema_preview["shared_columns"] if c != target_col]

    type_mismatch_features = {m["feature"] for m in schema_preview["type_mismatches"]}

    # Compute raw feature shifts and collect raw p-values for FDR correction
    raw_feature_shifts: list[dict[str, Any]] = []
    raw_p_values: dict[str, float | None] = {}

    missingness_summary: dict[str, Any] = {}

    for feature in shared_features:
        is_model_input = bool(model_features is not None and feature in model_features)
        ref_series = ref_df[feature]
        comp_series = comp_df[feature]

        # 1. Missingness shift
        miss_shift = compute_missingness_shift(ref_series, comp_series, threshold=missingness_threshold)
        missingness_summary[feature] = {
            "delta": miss_shift["delta"],
            "flagged": miss_shift["flagged"],
        }

        # 2. Type mismatch handling
        if feature in type_mismatch_features:
            record = {
                "feature": feature,
                "feature_type": "type_mismatch",
                "is_model_input": is_model_input,
                "missingness": miss_shift,
                "numeric": None,
                "categorical": None,
                "raw_p_value": None,
                "adjusted_p_value": None,
                "p_value_interpretation": "Statistical test not applicable due to data type mismatch.",
                "flagged": True,
                "flag_reasons": ["Data type mismatch between cohorts."],
                "warnings": [f"Feature '{feature}' data type differs across reference and comparison cohorts."],
            }
            raw_feature_shifts.append(record)
            raw_p_values[feature] = None
            continue

        ref_is_num = bool(pd.api.types.is_numeric_dtype(ref_series))
        comp_is_num = bool(pd.api.types.is_numeric_dtype(comp_series))

        if ref_is_num and comp_is_num:
            num_shift = compute_numeric_shift(
                ref_series, comp_series,
                significance_threshold=significance_threshold,
                distance_threshold=numeric_dist_threshold,
            )
            raw_p_values[feature] = num_shift.get("raw_p_value")
            record = {
                "feature": feature,
                "feature_type": "numeric",
                "is_model_input": is_model_input,
                "missingness": miss_shift,
                "numeric": num_shift,
                "categorical": None,
                "raw_p_value": num_shift.get("raw_p_value"),
                "adjusted_p_value": None,
                "p_value_interpretation": None,
                "flagged": False,
                "flag_reasons": [],
                "warnings": list(num_shift.get("warnings", [])),
            }
            raw_feature_shifts.append(record)
        else:
            cat_shift = compute_categorical_shift(
                ref_series, comp_series,
                significance_threshold=significance_threshold,
                distance_threshold=categorical_dist_threshold,
            )
            raw_p_values[feature] = cat_shift.get("raw_p_value")
            record = {
                "feature": feature,
                "feature_type": "categorical",
                "is_model_input": is_model_input,
                "missingness": miss_shift,
                "numeric": None,
                "categorical": cat_shift,
                "raw_p_value": cat_shift.get("raw_p_value"),
                "adjusted_p_value": None,
                "p_value_interpretation": None,
                "flagged": False,
                "flag_reasons": [],
                "warnings": list(cat_shift.get("warnings", [])),
            }
            raw_feature_shifts.append(record)

    # 3. Benjamini-Hochberg FDR correction across tested features
    adjusted_p_values = benjamini_hochberg_fdr(raw_p_values)

    # 4. Feature Flagging based on multiple-testing adjusted p-value and effect sizes
    flagged_features: list[str] = []
    shifted_numeric_count = 0
    shifted_categorical_count = 0
    missingness_shifted_count = 0

    for record in raw_feature_shifts:
        feature = record["feature"]
        adj_p = adjusted_p_values.get(feature)
        record["adjusted_p_value"] = adj_p

        if adj_p is not None:
            if adj_p < significance_threshold:
                record["p_value_interpretation"] = (
                    "Statistical evidence of distributional difference under the selected test and assumptions."
                )
            else:
                record["p_value_interpretation"] = (
                    "No statistical evidence of distributional difference under the selected test and FDR threshold."
                )
        else:
            record["p_value_interpretation"] = (
                "Statistical test was not applicable or could not be reliably computed."
            )

        flag_reasons = list(record.get("flag_reasons", []))

        # Check missingness flag
        if record["missingness"]["flagged"]:
            missingness_shifted_count += 1
            flag_reasons.append(
                f"Missingness difference {abs(record['missingness']['delta']):.4f} meets or exceeds threshold {missingness_threshold}."
            )

        # Check numeric shift criteria
        if record["feature_type"] == "numeric" and record["numeric"]:
            num = record["numeric"]
            ks_stat = num.get("statistic")
            smd = num.get("standardized_mean_difference")

            # Flag if significant AND distance or effect size is notable
            is_stat_sig = bool(adj_p is not None and adj_p < significance_threshold)
            is_dist_large = bool(ks_stat is not None and ks_stat >= numeric_dist_threshold)
            is_smd_large = bool(smd is not None and abs(smd) >= 0.5)

            if is_stat_sig and (is_dist_large or is_smd_large):
                shifted_numeric_count += 1
                flag_reasons.append(
                    f"Statistically significant Kolmogorov-Smirnov shift (statistic={ks_stat:.3f}, adjusted p={adj_p:.4f})"
                    if is_dist_large else
                    f"Statistically significant mean difference (SMD={smd:.3f}, adjusted p={adj_p:.4f})"
                )
            elif is_dist_large:
                shifted_numeric_count += 1
                flag_reasons.append(f"Large observed KS distribution distance ({ks_stat:.3f} >= {numeric_dist_threshold}).")

        # Check categorical shift criteria
        elif record["feature_type"] == "categorical" and record["categorical"]:
            cat = record["categorical"]
            tvd = cat.get("distance_value")
            is_stat_sig = bool(adj_p is not None and adj_p < significance_threshold)
            is_dist_large = bool(tvd is not None and tvd >= categorical_dist_threshold)

            if is_dist_large or (is_stat_sig and not cat.get("sparse_categories")):
                shifted_categorical_count += 1
                if is_dist_large:
                    flag_reasons.append(
                        f"Categorical total variation distance {tvd:.3f} meets or exceeds threshold {categorical_dist_threshold}."
                    )
                if is_stat_sig:
                    flag_reasons.append(
                        f"Statistically significant Chi-square contingency shift (adjusted p={adj_p:.4f})."
                    )

        record["flag_reasons"] = flag_reasons
        record["flagged"] = bool(len(flag_reasons) > 0)
        if record["flagged"]:
            flagged_features.append(feature)

    # 5. Overall Summary
    total_tested_hypotheses = len([p for p in raw_p_values.values() if p is not None])
    numeric_tested_count = len([r for r in raw_feature_shifts if r["feature_type"] == "numeric"])
    categorical_tested_count = len([r for r in raw_feature_shifts if r["feature_type"] == "categorical"])

    target_shift_detected = bool(
        target_preview.get("target_evaluated")
        and target_preview.get("prevalence_delta") is not None
        and abs(target_preview["prevalence_delta"]) >= 0.05
    )

    summary = {
        "total_features_reference": schema_preview["reference_feature_count"],
        "total_features_comparison": schema_preview["comparison_feature_count"],
        "shared_features_count": len(shared_features),
        "model_features_count": len(model_features) if model_features else 0,
        "model_features_missing_count": len(preflight["missing_model_features"]),
        "shifted_features_count": len(flagged_features),
        "missingness_shifted_count": missingness_shifted_count,
        "numeric_features_tested_count": numeric_tested_count,
        "numeric_features_shifted_count": shifted_numeric_count,
        "categorical_features_tested_count": categorical_tested_count,
        "categorical_features_shifted_count": shifted_categorical_count,
        "target_shift_detected": target_shift_detected,
        "target_prevalence_delta": target_preview.get("prevalence_delta"),
        "schema_mismatch_count": len(schema_preview["missing_in_comparison"]) + len(schema_preview["extra_in_comparison"]),
        "type_mismatch_count": len(schema_preview["type_mismatches"]),
        "multiple_testing_correction": multiple_testing_correction,
        "tested_hypotheses_count": total_tested_hypotheses,
    }

    # 6. Provenance metadata
    model_record = preflight.get("model")
    ext_val_record = preflight.get("external_validation")

    parent_study_id = None
    model_seed = None
    if model_id is not None:
        db_model = session.scalar(select(ModelRecord).where(ModelRecord.id == model_id))
        if db_model is not None and db_model.experiment_id:
            study = session.scalar(select(MultiSeedStudy).where(MultiSeedStudy.base_experiment_id == db_model.experiment_id))
            if study is not None:
                parent_study_id = study.id
                model_seed = db_model.hyperparameters.get("random_state", db_model.hyperparameters.get("seed"))

    provenance = {
        "policy_version": DISTRIBUTION_SHIFT_POLICY_VERSION,
        "direction": SHIFT_DIRECTION_CONVENTION,
        "reference": {
            "dataset_id": ref_id,
            "version_id": ref_ver_id,
            "content_sha256": ref_hash,
            "row_count": len(ref_df),
        },
        "comparison": {
            "dataset_id": comp_id,
            "version_id": comp_ver_id,
            "content_sha256": comp_hash,
            "row_count": len(comp_df),
        },
        "model": {
            "id": model_id,
            "model_type": model_record["model_type"] if model_record else None,
            "features": list(model_features) if model_features else None,
        } if model_id else None,
        "external_validation_id": ext_val_id,
        "parent_study_id": parent_study_id,
        "model_seed": model_seed,
        "software_versions": software_versions(),
        "executed_at": utcnow().isoformat(),
    }

    execution_time = float(perf_counter() - start_time)

    # 7. Persist Entity
    analysis_id = str(uuid4())
    analysis = DistributionShiftAnalysis(
        id=analysis_id,
        reference_dataset_id=ref_id,
        reference_dataset_version_id=ref_ver_id,
        reference_content_sha256=ref_hash,
        comparison_dataset_id=comp_id,
        comparison_dataset_version_id=comp_ver_id,
        comparison_content_sha256=comp_hash,
        model_id=model_id,
        external_validation_id=ext_val_id,
        parent_study_id=parent_study_id,
        model_seed=model_seed,
        status="completed",
        operation_key=op_key,
        policy_version=DISTRIBUTION_SHIFT_POLICY_VERSION,
        configuration=clean_json(resolved_config),
        schema_analysis=clean_json(schema_preview),
        target_analysis=clean_json(target_preview),
        missingness_analysis=clean_json(missingness_summary),
        feature_shifts=clean_json(raw_feature_shifts),
        summary=clean_json(summary),
        flagged_features=flagged_features,
        warnings=warnings,
        limitations=SHIFT_LIMITATIONS,
        provenance=clean_json(provenance),
        artifact_id=None,
        failure=None,
        execution_time_seconds=execution_time,
        created_at=utcnow(),
        completed_at=utcnow(),
    )
    session.add(analysis)
    session.flush()

    # 8. Register Immutable Artifact
    artifact_payload = {
        "analysis_id": analysis.id,
        "policy_version": DISTRIBUTION_SHIFT_POLICY_VERSION,
        "configuration": resolved_config,
        "reference": {
            "dataset_id": ref_id,
            "version_id": ref_ver_id,
            "content_sha256": ref_hash,
        },
        "comparison": {
            "dataset_id": comp_id,
            "version_id": comp_ver_id,
            "content_sha256": comp_hash,
        },
        "model_id": model_id,
        "external_validation_id": ext_val_id,
        "schema_analysis": schema_preview,
        "target_analysis": target_preview,
        "summary": summary,
        "flagged_features": flagged_features,
        "feature_shifts": raw_feature_shifts,
        "limitations": SHIFT_LIMITATIONS,
        "provenance": provenance,
    }

    try:
        exp_id = None
        run_id = None
        if model_id is not None:
            db_model = session.scalar(select(ModelRecord).where(ModelRecord.id == model_id))
            if db_model is not None:
                exp_id = db_model.experiment_id
                run_id = db_model.run_id

        if exp_id is None:
            exp = session.scalar(select(Experiment).where(Experiment.dataset_id == ref_id))
            if exp is None:
                exp = session.scalar(select(Experiment).where(Experiment.dataset_id == comp_id))
            if exp is None:
                exp = session.scalar(select(Experiment))
            if exp is None:
                exp = Experiment(
                    id=str(uuid4()),
                    dataset_id=ref_id,
                    config={"purpose": "distribution_shift_analysis"},
                    created_at=utcnow(),
                )
                session.add(exp)
                session.flush()
            exp_id = exp.id

        artifact = register_metadata(
            session,
            experiment_id=exp_id,
            run_id=run_id,
            model_id=model_id,
            artifact_type="distribution_shift_report",
            name=f"Distribution Shift Report - {ref_id[:8]} vs {comp_id[:8]}",
            description="Immutable distribution shift analysis report and statistical evidence.",
            payload=clean_json(artifact_payload),
            operation_key=f"shift_artifact:{analysis.id}",
        )
        analysis.artifact_id = artifact.id
        session.flush()
    except Exception as exc:
        warnings.append(f"Shift artifact registration failed: {str(exc)}")
        analysis.warnings = warnings
        session.flush()

    return analysis


def get_shift_analysis(session, analysis_id: str) -> DistributionShiftAnalysis:
    """Retrieve an existing distribution-shift analysis by ID."""
    analysis = session.scalar(
        select(DistributionShiftAnalysis).where(DistributionShiftAnalysis.id == analysis_id)
    )
    if analysis is None:
        raise AppError("shift_analysis_not_found", f"Shift analysis {analysis_id} not found.", 404)
    return analysis


def list_shift_analyses(
    session,
    *,
    reference_dataset_id: str | None = None,
    comparison_dataset_id: str | None = None,
    model_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[DistributionShiftAnalysis]:
    """Retrieve paginated distribution-shift analyses with optional filtering."""
    stmt = select(DistributionShiftAnalysis).order_by(DistributionShiftAnalysis.created_at.desc())
    if reference_dataset_id is not None:
        stmt = stmt.where(DistributionShiftAnalysis.reference_dataset_id == reference_dataset_id)
    if comparison_dataset_id is not None:
        stmt = stmt.where(DistributionShiftAnalysis.comparison_dataset_id == comparison_dataset_id)
    if model_id is not None:
        stmt = stmt.where(DistributionShiftAnalysis.model_id == model_id)
    stmt = stmt.limit(min(limit, 500)).offset(offset)
    return list(session.scalars(stmt))


def get_dataset_shift_analyses(
    session,
    dataset_id: str,
    limit: int = 100,
    offset: int = 0,
) -> list[DistributionShiftAnalysis]:
    """Retrieve all shift analyses where the specified dataset is either reference or comparison."""
    stmt = (
        select(DistributionShiftAnalysis)
        .where(
            (DistributionShiftAnalysis.reference_dataset_id == dataset_id)
            | (DistributionShiftAnalysis.comparison_dataset_id == dataset_id)
        )
        .order_by(DistributionShiftAnalysis.created_at.desc())
        .limit(min(limit, 500))
        .offset(offset)
    )
    return list(session.scalars(stmt))
