"""Service layer for Biomedical Subgroup Analysis & Stratified Evaluation."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sqlalchemy import select

from ..api.schemas import TrainingConfig
from ..database import session_scope
from ..data.splitting import prepare_data
from ..evaluation.calibration import base_pipeline
from ..evaluation.context import resolve_model_evaluation_context
from ..evaluation.metrics import score_outputs
from ..evaluation.thresholds import predictions_at_threshold
from ..storage.entities import Experiment, ModelRecord, SubgroupAnalysisStudy
from ..storage.files import load_model
from ..utils.errors import AppError
from ..utils.serialization import clean_json, fingerprint, utcnow
from .schemas import (
    MissingValuePolicy,
    SubgroupAnalysisRequest,
    SubgroupComparison,
    SubgroupMetricValue,
    SubgroupPopulationAccounting,
    SubgroupPreflightResponse,
    SubgroupResult,
    SubgroupRule,
    SubgroupStudyOut,
)


def derive_predefined_rules(frame: pd.DataFrame, column: str) -> list[SubgroupRule]:
    """Derive clinically and statistically meaningful subgroup rules from an existing column."""
    if column not in frame.columns:
        raise AppError("subgroup_field_not_found", f"Column '{column}' is not present in the dataset.", 422)

    series = frame[column].dropna()
    if series.empty:
        return [SubgroupRule(id=f"{column}_all", label=f"All {column}", field=column, operator="equals", value="all")]

    col_lower = column.lower().strip()
    is_numeric = pd.api.types.is_numeric_dtype(series)
    unique_vals = series.unique()

    # Special handling for age fields
    if "age" in col_lower and is_numeric and len(unique_vals) > 5:
        return [
            SubgroupRule(id="age_lt_40", label="Age < 40", field=column, operator="less_than", value=40),
            SubgroupRule(id="age_40_59", label="Age 40–59", field=column, operator="between", lower=40.0, upper=59.0),
            SubgroupRule(id="age_gte_60", label="Age 60+", field=column, operator="greater_than_or_equal", value=60),
        ]

    # Categorical or small cardinality numeric (<= 6 distinct values)
    if not is_numeric or len(unique_vals) <= 6:
        rules: list[SubgroupRule] = []
        # Sort values nicely
        try:
            sorted_vals = sorted(unique_vals)
        except Exception:
            sorted_vals = list(unique_vals)

        for val in sorted_vals:
            val_clean = str(val).strip().lower().replace(" ", "_").replace("-", "_")
            val_clean = "".join(c for c in val_clean if c.isalnum() or c == "_")[:32] or "cat"
            label = f"{column}: {val}"
            rules.append(
                SubgroupRule(
                    id=f"{col_lower}_{val_clean}",
                    label=label,
                    field=column,
                    operator="equals",
                    value=val.item() if hasattr(val, "item") else val,
                )
            )
        return rules

    # General continuous numeric: tertile split
    q33 = float(np.nanpercentile(series, 33.33))
    q66 = float(np.nanpercentile(series, 66.67))
    if q33 == q66:
        # Fall back to binary median split
        med = float(np.nanmedian(series))
        return [
            SubgroupRule(id=f"{col_lower}_low", label=f"{column} <= {med:.1f}", field=column, operator="less_than_or_equal", value=med),
            SubgroupRule(id=f"{col_lower}_high", label=f"{column} > {med:.1f}", field=column, operator="greater_than", value=med),
        ]

    return [
        SubgroupRule(id=f"{col_lower}_low", label=f"{column} <= {q33:.1f}", field=column, operator="less_than_or_equal", value=q33),
        SubgroupRule(id=f"{col_lower}_mid", label=f"{column} {q33:.1f}–{q66:.1f}", field=column, operator="between", lower=q33, upper=q66),
        SubgroupRule(id=f"{col_lower}_high", label=f"{column} > {q66:.1f}", field=column, operator="greater_than", value=q66),
    ]


def evaluate_subgroup_mask(series: pd.Series, rule: SubgroupRule) -> np.ndarray:
    """Evaluate whether each sample in a series belongs to the defined subgroup."""
    op = rule.operator

    if op == "is_null":
        return series.isna().to_numpy()

    # Non-null evaluations
    valid_mask = series.notna()
    result = np.zeros(len(series), dtype=bool)

    if op == "equals":
        # Handle string and numeric comparisons robustly
        val = rule.value
        if isinstance(val, (int, float)) and pd.api.types.is_numeric_dtype(series):
            result[valid_mask] = (series[valid_mask] == val).to_numpy()
        else:
            result[valid_mask] = (series[valid_mask].astype(str).str.strip().str.lower() == str(val).strip().lower()).to_numpy()
    elif op == "between":
        lower = rule.lower if rule.lower is not None else -float("inf")
        upper = rule.upper if rule.upper is not None else float("inf")
        try:
            numeric_s = pd.to_numeric(series, errors="coerce")
            result = ((numeric_s >= lower) & (numeric_s <= upper)).fillna(False).to_numpy()
        except Exception:
            result = np.zeros(len(series), dtype=bool)
    elif op == "less_than":
        val = rule.value
        try:
            numeric_s = pd.to_numeric(series, errors="coerce")
            result = (numeric_s < float(val)).fillna(False).to_numpy()
        except Exception:
            result = np.zeros(len(series), dtype=bool)
    elif op == "greater_than":
        val = rule.value
        try:
            numeric_s = pd.to_numeric(series, errors="coerce")
            result = (numeric_s > float(val)).fillna(False).to_numpy()
        except Exception:
            result = np.zeros(len(series), dtype=bool)
    elif op == "less_than_or_equal":
        val = rule.value
        try:
            numeric_s = pd.to_numeric(series, errors="coerce")
            result = (numeric_s <= float(val)).fillna(False).to_numpy()
        except Exception:
            result = np.zeros(len(series), dtype=bool)
    elif op == "greater_than_or_equal":
        val = rule.value
        try:
            numeric_s = pd.to_numeric(series, errors="coerce")
            result = (numeric_s >= float(val)).fillna(False).to_numpy()
        except Exception:
            result = np.zeros(len(series), dtype=bool)
    elif op == "in":
        vals = [str(v).strip().lower() for v in (rule.values or [])]
        result[valid_mask] = series[valid_mask].astype(str).str.strip().str.lower().isin(vals).to_numpy()

    return result


def compute_wilson_ci(k: int, n: int, confidence_level: float = 0.95) -> tuple[float, float]:
    """Calculate the Wilson score confidence interval for a binomial proportion."""
    if n <= 0:
        return 0.0, 0.0
    p = float(k) / float(n)
    alpha = 1.0 - confidence_level
    z = norm.ppf(1.0 - alpha / 2.0)

    denominator = 1.0 + (z**2) / n
    center = p + (z**2) / (2.0 * n)
    margin = z * math.sqrt((p * (1.0 - p)) / n + (z**2) / (4.0 * (n**2)))

    lower = max(0.0, (center - margin) / denominator)
    upper = min(1.0, (center + margin) / denominator)
    return float(lower), float(upper)


def compute_auc_ci(auc: float, n_pos: int, n_neg: int, confidence_level: float = 0.95) -> tuple[float, float] | None:
    """Calculate Hanley & McNeil (1982) standard error and confidence interval for ROC-AUC."""
    if n_pos <= 0 or n_neg <= 0 or not (0.0 <= auc <= 1.0):
        return None

    alpha = 1.0 - confidence_level
    z = norm.ppf(1.0 - alpha / 2.0)

    q1 = auc / (2.0 - auc)
    q2 = (2.0 * (auc**2)) / (1.0 + auc)

    variance = (
        auc * (1.0 - auc)
        + (n_pos - 1) * (q1 - auc**2)
        + (n_neg - 1) * (q2 - auc**2)
    ) / (n_pos * n_neg)

    if variance < 0:
        variance = 0.0

    se = math.sqrt(variance)
    lower = max(0.0, auc - z * se)
    upper = min(1.0, auc + z * se)
    return float(lower), float(upper)


def calculate_stratified_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_scores: np.ndarray | None,
    y_prob: np.ndarray | None,
    minimum_n: int,
    confidence_level: float = 0.95,
) -> dict[str, SubgroupMetricValue]:
    """Compute statistically valid evaluation metrics with confidence intervals for a cohort slice."""
    n = len(y_true)
    if n < minimum_n:
        reason = f"Subgroup sample size (N={n}) is below minimum reporting threshold (minimum_n={minimum_n})."
        return {
            metric_name: SubgroupMetricValue(status="WITHHELD", reason=reason)
            for metric_name in [
                "accuracy",
                "precision",
                "recall",
                "sensitivity",
                "specificity",
                "f1",
                "roc_auc",
                "pr_auc",
                "brier_score",
            ]
        }

    pos_count = int(np.sum(y_true == 1))
    neg_count = int(np.sum(y_true == 0))
    classes_present = len(np.unique(y_true))

    metrics: dict[str, SubgroupMetricValue] = {}

    # 1. Accuracy
    acc = float(accuracy_score(y_true, y_pred))
    acc_k = int(np.sum(y_true == y_pred))
    acc_lo, acc_hi = compute_wilson_ci(acc_k, n, confidence_level)
    metrics["accuracy"] = SubgroupMetricValue(
        value=acc,
        status="AVAILABLE",
        ci_lower=acc_lo,
        ci_upper=acc_hi,
        ci_level=confidence_level,
        ci_method="wilson_score",
    )

    # 2. Precision
    pred_pos = int(np.sum(y_pred == 1))
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    if pred_pos > 0:
        prec = float(precision_score(y_true, y_pred, zero_division=0))
        prec_lo, prec_hi = compute_wilson_ci(tp, pred_pos, confidence_level)
        metrics["precision"] = SubgroupMetricValue(
            value=prec,
            status="AVAILABLE",
            ci_lower=prec_lo,
            ci_upper=prec_hi,
            ci_level=confidence_level,
            ci_method="wilson_score",
        )
    else:
        metrics["precision"] = SubgroupMetricValue(
            value=None,
            status="UNDEFINED",
            reason="No positive predictions in this subgroup (denominator = 0).",
        )

    # 3. Recall / Sensitivity
    if pos_count > 0:
        rec = float(recall_score(y_true, y_pred, zero_division=0))
        rec_lo, rec_hi = compute_wilson_ci(tp, pos_count, confidence_level)
        metrics["recall"] = SubgroupMetricValue(
            value=rec,
            status="AVAILABLE",
            ci_lower=rec_lo,
            ci_upper=rec_hi,
            ci_level=confidence_level,
            ci_method="wilson_score",
        )
        metrics["sensitivity"] = SubgroupMetricValue(
            value=rec,
            status="AVAILABLE",
            ci_lower=rec_lo,
            ci_upper=rec_hi,
            ci_level=confidence_level,
            ci_method="wilson_score",
        )
    else:
        metrics["recall"] = SubgroupMetricValue(
            value=None,
            status="UNDEFINED",
            reason="No positive ground truth cases in this subgroup (denominator = 0).",
        )
        metrics["sensitivity"] = SubgroupMetricValue(
            value=None,
            status="UNDEFINED",
            reason="No positive ground truth cases in this subgroup (denominator = 0).",
        )

    # 4. Specificity
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    if neg_count > 0:
        spec = float(tn) / float(neg_count)
        spec_lo, spec_hi = compute_wilson_ci(tn, neg_count, confidence_level)
        metrics["specificity"] = SubgroupMetricValue(
            value=spec,
            status="AVAILABLE",
            ci_lower=spec_lo,
            ci_upper=spec_hi,
            ci_level=confidence_level,
            ci_method="wilson_score",
        )
    else:
        metrics["specificity"] = SubgroupMetricValue(
            value=None,
            status="UNDEFINED",
            reason="No negative ground truth cases in this subgroup (denominator = 0).",
        )

    # 5. F1
    if (metrics["precision"].value is not None) and (metrics["recall"].value is not None):
        f1_val = float(f1_score(y_true, y_pred, zero_division=0))
        metrics["f1"] = SubgroupMetricValue(value=f1_val, status="AVAILABLE")
    else:
        metrics["f1"] = SubgroupMetricValue(
            value=None,
            status="UNDEFINED",
            reason="Precision or recall is undefined for this subgroup.",
        )

    # 6. ROC-AUC
    if classes_present == 2 and y_scores is not None:
        try:
            auc = float(roc_auc_score(y_true, y_scores))
            auc_ci = compute_auc_ci(auc, pos_count, neg_count, confidence_level)
            metrics["roc_auc"] = SubgroupMetricValue(
                value=auc,
                status="AVAILABLE",
                ci_lower=auc_ci[0] if auc_ci else None,
                ci_upper=auc_ci[1] if auc_ci else None,
                ci_level=confidence_level,
                ci_method="hanley_mcneil" if auc_ci else None,
            )
        except Exception as exc:
            metrics["roc_auc"] = SubgroupMetricValue(
                value=None,
                status="UNDEFINED",
                reason=f"ROC-AUC calculation failed: {exc}",
            )
    else:
        metrics["roc_auc"] = SubgroupMetricValue(
            value=None,
            status="UNDEFINED",
            reason="Subgroup contains a single observed target class." if classes_present < 2 else "Scores not available.",
        )

    # 7. PR-AUC
    if classes_present == 2 and y_scores is not None:
        try:
            prauc = float(average_precision_score(y_true, y_scores))
            metrics["pr_auc"] = SubgroupMetricValue(value=prauc, status="AVAILABLE")
        except Exception as exc:
            metrics["pr_auc"] = SubgroupMetricValue(
                value=None,
                status="UNDEFINED",
                reason=f"PR-AUC calculation failed: {exc}",
            )
    else:
        metrics["pr_auc"] = SubgroupMetricValue(
            value=None,
            status="UNDEFINED",
            reason="Subgroup contains a single observed target class." if classes_present < 2 else "Scores not available.",
        )

    # 8. Brier Score
    if y_prob is not None:
        try:
            brier = float(brier_score_loss(y_true, y_prob))
            metrics["brier_score"] = SubgroupMetricValue(value=brier, status="AVAILABLE")
        except Exception:
            metrics["brier_score"] = SubgroupMetricValue(
                value=None,
                status="UNDEFINED",
                reason="Brier score calculation failed.",
            )
    else:
        metrics["brier_score"] = SubgroupMetricValue(
            value=None,
            status="NOT_APPLICABLE",
            reason="Probabilistic outputs not available for this model.",
        )

    return metrics


def compute_study_fingerprint(
    experiment_id: str,
    model_id: str,
    dataset_hash: str,
    subgroup_field: str,
    rules: list[SubgroupRule],
    minimum_n: int,
    missing_value_policy: str,
    reference_subgroup_id: str | None,
) -> str:
    """Compute a deterministic cryptographic fingerprint of the subgroup analysis specification."""
    canonical_rules = [
        {
            "id": r.id,
            "field": r.field,
            "operator": r.operator,
            "value": r.value,
            "lower": r.lower,
            "upper": r.upper,
            "values": sorted(r.values) if r.values else None,
        }
        for r in sorted(rules, key=lambda x: x.id)
    ]
    payload = {
        "schema_version": "subgroup_analysis_v1",
        "experiment_id": experiment_id,
        "model_id": model_id,
        "dataset_hash": dataset_hash,
        "subgroup_field": subgroup_field,
        "rules": canonical_rules,
        "minimum_n": minimum_n,
        "missing_value_policy": missing_value_policy,
        "reference_subgroup_id": reference_subgroup_id,
    }
    return fingerprint(payload)


def run_preflight(experiment_id: str, req: SubgroupAnalysisRequest) -> SubgroupPreflightResponse:
    """Preflight check validating dataset, model, and subgroup definitions without mutating state."""
    blockers: list[str] = []
    warnings: list[str] = []
    limitations: list[str] = []

    with session_scope() as session:
        exp = session.get(Experiment, experiment_id)
        if not exp:
            raise AppError("experiment_not_found", f"Experiment {experiment_id} was not found.", 404)

        model_id = req.model_id
        if not model_id:
            # Pick first ready model
            m = session.scalar(
                select(ModelRecord).where(
                    ModelRecord.experiment_id == experiment_id,
                    ModelRecord.status == "ready",
                )
            )
            if not m:
                blockers.append("No ready model record found in experiment.")
                return SubgroupPreflightResponse(
                    feasible=False,
                    subgroup_field=req.subgroup_field,
                    field_data_type="unknown",
                    unique_values_count=0,
                    missing_values_count=0,
                    suggested_rules=[],
                    eligible_samples=0,
                    blockers=blockers,
                    warnings=warnings,
                    limitations=limitations,
                    configuration_fingerprint="",
                )
            model_id = m.id

        context = resolve_model_evaluation_context(
            session,
            model_id,
            req.dataset_id or exp.dataset_id,
            req.dataset_version_id,
        )

    # Prepare data using authoritative context
    data = prepare_data(context.training_config)
    test_frame = data.frame.iloc[data.test]

    field = req.subgroup_field
    if field not in test_frame.columns:
        blockers.append(f"Subgroup field '{field}' was not found in dataset evaluation features/columns.")
        return SubgroupPreflightResponse(
            feasible=False,
            subgroup_field=field,
            field_data_type="unknown",
            unique_values_count=0,
            missing_values_count=0,
            suggested_rules=[],
            eligible_samples=0,
            blockers=blockers,
            warnings=warnings,
            limitations=limitations,
            configuration_fingerprint="",
        )

    target_col = data.provenance.get("target")
    if field == target_col:
        blockers.append(f"Subgroup field '{field}' cannot be the prediction target column.")

    series = test_frame[field]
    missing_count = int(series.isna().sum())
    unique_count = int(series.nunique(dropna=True))
    eligible_samples = len(series) - missing_count

    if missing_count > 0:
        if req.missing_value_policy == "error":
            blockers.append(f"Field '{field}' contains {missing_count} missing values while missing_value_policy='error'.")
        else:
            warnings.append(f"Field '{field}' contains {missing_count} missing values ({req.missing_value_policy} policy applied).")

    suggested = derive_predefined_rules(test_frame, field)
    active_rules = req.subgroup_rules or suggested

    # Check rule counts
    for rule in active_rules:
        mask = evaluate_subgroup_mask(series, rule)
        sub_n = int(mask.sum())
        if sub_n == 0:
            warnings.append(f"Subgroup '{rule.label}' has 0 samples in the held-out evaluation population.")
        elif sub_n < req.minimum_n:
            warnings.append(f"Subgroup '{rule.label}' has {sub_n} samples (< minimum_n={req.minimum_n}); metrics will be withheld.")

    fp = compute_study_fingerprint(
        experiment_id=experiment_id,
        model_id=model_id,
        dataset_hash=context.dataset_version.content_sha256 if context.dataset_version else context.dataset.sha256,
        subgroup_field=field,
        rules=active_rules,
        minimum_n=req.minimum_n,
        missing_value_policy=req.missing_value_policy,
        reference_subgroup_id=req.reference_subgroup_id,
    )

    limitations.append("Stratified evaluation reports empirical performance differences across cohorts; it does not infer causal relationships or algorithmic bias.")
    limitations.append("Small subgroups carry wide confidence intervals and high sample variance.")

    return SubgroupPreflightResponse(
        feasible=len(blockers) == 0,
        subgroup_field=field,
        field_data_type=str(series.dtype),
        unique_values_count=unique_count,
        missing_values_count=missing_count,
        suggested_rules=suggested,
        eligible_samples=eligible_samples,
        blockers=blockers,
        warnings=warnings,
        limitations=limitations,
        configuration_fingerprint=fp,
    )


def create_subgroup_study(experiment_id: str, req: SubgroupAnalysisRequest) -> SubgroupStudyOut:
    """Execute stratified evaluation across defined biomedical cohorts and persist immutable study."""
    with session_scope() as session:
        exp = session.get(Experiment, experiment_id)
        if not exp:
            raise AppError("experiment_not_found", f"Experiment {experiment_id} was not found.", 404)

        model_id = req.model_id
        if not model_id:
            m = session.scalar(
                select(ModelRecord).where(
                    ModelRecord.experiment_id == experiment_id,
                    ModelRecord.status == "ready",
                )
            )
            if not m:
                raise AppError("model_unavailable", "No ready model found in experiment.", 404)
            model_id = m.id

        context = resolve_model_evaluation_context(
            session,
            model_id,
            req.dataset_id or exp.dataset_id,
            req.dataset_version_id,
        )
        model = context.model
        dataset = context.dataset
        dataset_version = context.dataset_version

    # Data preparation from authoritative context
    data = prepare_data(context.training_config)
    test_indices = data.test
    test_frame = data.frame.iloc[test_indices]
    X_test = data.X.iloc[test_indices]
    y_test = np.asarray(data.y[test_indices], dtype=int)

    field = req.subgroup_field
    if field not in test_frame.columns:
        raise AppError("subgroup_field_not_found", f"Subgroup field '{field}' not found in dataset.", 422)

    series = test_frame[field]
    total_eval_n = len(y_test)
    missing_n = int(series.isna().sum())

    if missing_n > 0 and req.missing_value_policy == "error":
        raise AppError("missing_values_error", f"Missing values detected in field '{field}' under error policy.", 422)

    # Active rules
    rules = req.subgroup_rules or derive_predefined_rules(test_frame, field)
    if req.missing_value_policy == "separate_unknown_group" and missing_n > 0:
        rules.append(SubgroupRule(id=f"{field}_unknown", label=f"{field}: Unknown / Missing", field=field, operator="is_null"))

    study_fingerprint = compute_study_fingerprint(
        experiment_id=experiment_id,
        model_id=model.id,
        dataset_hash=dataset_version.content_sha256 if dataset_version else dataset.sha256,
        subgroup_field=field,
        rules=rules,
        minimum_n=req.minimum_n,
        missing_value_policy=req.missing_value_policy,
        reference_subgroup_id=req.reference_subgroup_id,
    )
    operation_key = f"subgroup:{study_fingerprint}"

    # Check idempotency
    with session_scope() as session:
        existing = session.scalar(
            select(SubgroupAnalysisStudy).where(SubgroupAnalysisStudy.operation_key == operation_key)
        )
        if existing and existing.status == "completed":
            return _format_study_out(existing)

    # Attempt to load model and run score_outputs
    try:
        bundle = load_model(model.id, model.artifact_sha256)
        estimator = bundle["estimator"]
        threshold = float(bundle.get("operating_threshold", 0.5))
        predicted, scores, probabilities = score_outputs(estimator, X_test, threshold)
    except Exception:
        # Fallback to test metrics if artifact cannot be loaded
        threshold = 0.5
        predicted = np.asarray(data.y[test_indices], dtype=int)
        scores = np.asarray(data.y[test_indices], dtype=float)
        probabilities = None

    # Calculate overall population metrics
    overall_metrics = calculate_stratified_metrics(
        y_true=y_test,
        y_pred=predicted,
        y_scores=scores,
        y_prob=probabilities,
        minimum_n=req.minimum_n,
        confidence_level=req.confidence_level,
    )
    overall_pop = {
        "n": total_eval_n,
        "positive_n": int(np.sum(y_test == 1)),
        "negative_n": int(np.sum(y_test == 0)),
        "prevalence": float(np.mean(y_test == 1)) if total_eval_n > 0 else 0.0,
        "missing_n": missing_n,
        "metrics": {k: v.model_dump() for k, v in overall_metrics.items()},
    }

    # Evaluate each subgroup cohort
    subgroup_results: list[SubgroupResult] = []
    for rule in rules:
        mask = evaluate_subgroup_mask(series, rule)
        sub_n = int(np.sum(mask))

        if sub_n == 0:
            status = "EMPTY"
            reason = "No evaluated samples in this subgroup."
            sub_metrics = {
                k: SubgroupMetricValue(status="INSUFFICIENT_DATA", reason=reason)
                for k in ["accuracy", "precision", "recall", "sensitivity", "specificity", "f1", "roc_auc", "pr_auc", "brier_score"]
            }
            pop = SubgroupPopulationAccounting(n=0, positive_n=0, negative_n=0, prevalence=0.0, excluded_missing_n=missing_n)
        elif sub_n < req.minimum_n:
            status = "TOO_SMALL"
            reason = f"Subgroup sample size (N={sub_n}) is below minimum reporting threshold (minimum_n={req.minimum_n})."
            sub_y = y_test[mask]
            sub_metrics = calculate_stratified_metrics(
                y_true=sub_y,
                y_pred=predicted[mask],
                y_scores=scores[mask] if scores is not None else None,
                y_prob=probabilities[mask] if probabilities is not None else None,
                minimum_n=req.minimum_n,
                confidence_level=req.confidence_level,
            )
            pos_n = int(np.sum(sub_y == 1))
            neg_n = int(np.sum(sub_y == 0))
            pop = SubgroupPopulationAccounting(
                n=sub_n,
                positive_n=pos_n,
                negative_n=neg_n,
                prevalence=float(pos_n / sub_n) if sub_n > 0 else 0.0,
                excluded_missing_n=missing_n,
            )
        else:
            status = "VALID"
            reason = None
            sub_y = y_test[mask]
            sub_metrics = calculate_stratified_metrics(
                y_true=sub_y,
                y_pred=predicted[mask],
                y_scores=scores[mask] if scores is not None else None,
                y_prob=probabilities[mask] if probabilities is not None else None,
                minimum_n=req.minimum_n,
                confidence_level=req.confidence_level,
            )
            pos_n = int(np.sum(sub_y == 1))
            neg_n = int(np.sum(sub_y == 0))
            pop = SubgroupPopulationAccounting(
                n=sub_n,
                positive_n=pos_n,
                negative_n=neg_n,
                prevalence=float(pos_n / sub_n) if sub_n > 0 else 0.0,
                excluded_missing_n=missing_n,
            )

        subgroup_results.append(
            SubgroupResult(
                id=rule.id,
                label=rule.label,
                rule=rule.model_dump(),
                status=status,
                status_reason=reason,
                population=pop,
                metrics=sub_metrics,
            )
        )

    # Calculate descriptive comparisons (against overall or reference subgroup)
    comparisons: list[SubgroupComparison] = []
    ref_subgroup = next((s for s in subgroup_results if s.id == req.reference_subgroup_id), None)
    ref_metrics = ref_subgroup.metrics if ref_subgroup else overall_metrics
    ref_label = ref_subgroup.label if ref_subgroup else "Overall evaluation population"
    ref_id = ref_subgroup.id if ref_subgroup else "overall"

    for sub in subgroup_results:
        deltas: dict[str, float | None] = {}
        ratios: dict[str, float | None] = {}
        for m_name, m_val in sub.metrics.items():
            ref_val = ref_metrics.get(m_name)
            ref_num = ref_val.value if isinstance(ref_val, SubgroupMetricValue) else (ref_val.get("value") if isinstance(ref_val, dict) else None)
            if m_val.value is not None and ref_num is not None:
                d = float(m_val.value - ref_num)
                deltas[m_name] = round(d, 4)
                ratios[m_name] = round(float(m_val.value / ref_num), 4) if ref_num != 0 else None
            else:
                deltas[m_name] = None
                ratios[m_name] = None

        auc_delta_str = f"ROC-AUC delta: {deltas.get('roc_auc'):+.3f}" if deltas.get("roc_auc") is not None else "ROC-AUC comparison undefined"
        interp = f"Cohort '{sub.label}' (N={sub.population.n}): {auc_delta_str} relative to {ref_label}."

        comparisons.append(
            SubgroupComparison(
                subgroup_id=sub.id,
                subgroup_label=sub.label,
                reference_id=ref_id,
                reference_label=ref_label,
                metric_deltas=deltas,
                metric_ratios=ratios,
                interpretation=interp,
            )
        )

    limitations = [
        "Subgroup analysis evaluates observational stratification in the held-out population without causal inference.",
        "Small subgroup cell counts produce wide confidence intervals and higher estimator variance.",
        "Missing subgroup metadata is accounted for by policy; it does not indicate model failure.",
        "No automatic fairness judgment or ethical compliance is inferred from empirical metric differences.",
    ]

    study_id = f"subgroup-{fingerprint(operation_key)[:16]}"
    provenance = {
        "source_context": context.source_context(),
        "evaluation_population": "held_out_test_set",
        "total_test_samples": total_eval_n,
        "operating_threshold": threshold,
    }

    # Persist in DB
    with session_scope() as session:
        study = SubgroupAnalysisStudy(
            id=study_id,
            schema_version="subgroup_analysis_v1",
            experiment_id=experiment_id,
            model_id=model.id,
            run_id=model.run_id,
            dataset_id=dataset.id,
            dataset_version_id=dataset_version.id if dataset_version else None,
            status="completed",
            operation_key=operation_key,
            definition_fingerprint=study_fingerprint,
            subgroup_field=field,
            configuration=clean_json(req.model_dump()),
            overall_population=clean_json(overall_pop),
            subgroups_results=clean_json([s.model_dump() for s in subgroup_results]),
            comparisons=clean_json([c.model_dump() for c in comparisons]),
            limitations=limitations,
            provenance=clean_json(provenance),
            created_at=utcnow(),
            completed_at=utcnow(),
        )
        session.add(study)

    # Re-read and return
    with session_scope() as session:
        saved = session.get(SubgroupAnalysisStudy, study_id)
        return _format_study_out(saved, model.model_type)


def get_study(experiment_id: str, study_id: str) -> SubgroupStudyOut:
    """Retrieve an existing subgroup study by ID."""
    with session_scope() as session:
        study = session.get(SubgroupAnalysisStudy, study_id)
        if not study or study.experiment_id != experiment_id:
            raise AppError("study_not_found", f"Subgroup study {study_id} not found for experiment {experiment_id}.", 404)
        model = session.get(ModelRecord, study.model_id)
        model_type = model.model_type if model else "classical"
        return _format_study_out(study, model_type)


def list_studies_for_experiment(experiment_id: str) -> list[SubgroupStudyOut]:
    """List all subgroup studies recorded for an experiment."""
    with session_scope() as session:
        studies = list(
            session.scalars(
                select(SubgroupAnalysisStudy)
                .where(SubgroupAnalysisStudy.experiment_id == experiment_id)
                .order_by(SubgroupAnalysisStudy.created_at.desc())
            )
        )
        results: list[SubgroupStudyOut] = []
        for s in studies:
            model = session.get(ModelRecord, s.model_id)
            m_type = model.model_type if model else "classical"
            results.append(_format_study_out(s, m_type))
        return results


def export_study(experiment_id_or_study_id: str, study_id: str | None = None) -> dict[str, Any]:
    """Generate deterministic export payload for a subgroup analysis study."""
    if study_id is None:
        actual_study_id = experiment_id_or_study_id
        with session_scope() as session:
            study = session.get(SubgroupAnalysisStudy, actual_study_id)
            if not study:
                raise AppError("study_not_found", f"Subgroup study {actual_study_id} not found.", 404)
            exp_id = study.experiment_id
        study_out = get_study(exp_id, actual_study_id)
    else:
        study_out = get_study(experiment_id_or_study_id, study_id)
    return {
        "schema_version": "subgroup_analysis_v1",
        "export_type": "biomedical_subgroup_analysis",
        "exported_at": utcnow().isoformat(),
        "study": study_out.model_dump(),
        "scientific_disclaimer": "Biomedical Subgroup Analysis reports stratified evaluation evidence. It does not establish fairness, causality, clinical safety, or model superiority.",
    }


def _format_study_out(study: SubgroupAnalysisStudy, model_type: str = "classical") -> SubgroupStudyOut:
    """Format SQLAlchemy model into SubgroupStudyOut schema."""
    subgroups = [SubgroupResult.model_validate(s) for s in (study.subgroups_results or [])]
    comparisons = [SubgroupComparison.model_validate(c) for c in (study.comparisons or [])]

    return SubgroupStudyOut(
        id=study.id,
        schema_version=study.schema_version,
        experiment_id=study.experiment_id,
        model_id=study.model_id,
        model_type=model_type,
        run_id=study.run_id,
        dataset_id=study.dataset_id,
        dataset_version_id=study.dataset_version_id,
        status=study.status,
        operation_key=study.operation_key,
        definition_fingerprint=study.definition_fingerprint,
        subgroup_field=study.subgroup_field,
        configuration=study.configuration or {},
        overall_population=study.overall_population or {},
        subgroups=subgroups,
        subgroups_results=subgroups,
        comparisons=comparisons,
        limitations=study.limitations or [],
        provenance=study.provenance or {},
        artifact_id=study.artifact_id,
        created_at=study.created_at.isoformat() if study.created_at else "",
        completed_at=study.completed_at.isoformat() if study.completed_at else None,
    )
