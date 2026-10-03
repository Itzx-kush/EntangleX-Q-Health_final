from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd
from sqlalchemy import select

from ..artifacts.service import register_file, register_metadata
from ..config import get_settings
from ..database import session_scope
from ..data.service import _read_csv_table
from ..dataset_versions.service import read_version_bytes, resolve_version
from ..storage.entities import (
    Artifact,
    Dataset,
    DatasetQualityScorecard,
    DatasetVersion,
    Experiment,
    ExperimentProtocolVersion,
    PipelineVersion,
)
from ..storage.files import safe_path, verify
from ..storage.repository import require
from ..utils.errors import AppError
from ..utils.serialization import clean_json, fingerprint, utcnow
from .schemas import (
    CheckSeverity,
    CheckStatus,
    DatasetQualityPreflightResponse,
    DatasetQualityRequest,
    DatasetQualityScorecardOut,
    FeatureProfile,
    QualityCheckResult,
    QualityDomainResult,
    SchemaSnapshot,
    ScorecardComparisonOut,
    ScorecardSummary,
)

logger = logging.getLogger("qhealth.data_quality")

SCORECARD_SCHEMA_VERSION = "dataset_quality_scorecard_v1"
ARTIFACT_TYPE = "dataset_quality_scorecard"

DEFAULT_THRESHOLDS = {
    "min_row_count": 30,
    "warn_row_count": 50,
    "max_missing_rate_overall": 0.20,
    "warn_missing_rate_overall": 0.05,
    "max_missing_rate_column": 0.50,
    "warn_missing_rate_column": 0.20,
    "max_duplicate_rate": 0.10,
    "warn_duplicate_rate": 0.01,
    "min_minority_class_rate": 0.02,
    "warn_minority_class_rate": 0.10,
    "max_feature_correlation": 0.9999,
    "near_constant_threshold": 0.99,
    "outlier_zscore_threshold": 5.0,
    "high_cardinality_threshold": 0.90,
}


def _load_raw_dataset_bytes(session, dataset: Dataset, version: DatasetVersion | None) -> tuple[bytes, str]:
    """Retrieve raw bytes and sha256 for a dataset or specific version."""
    if version is not None:
        content = read_version_bytes(version)
        return content, version.content_sha256

    path = safe_path("data/datasets", dataset.id, ".csv")
    verify(path, dataset.sha256)
    content = path.read_bytes()
    return content, dataset.sha256


def compute_assessment_fingerprint(
    dataset_id: str,
    dataset_version_id: str | None,
    content_sha256: str,
    configuration: dict[str, Any],
    context: dict[str, Any],
) -> str:
    basis = {
        "schema_version": SCORECARD_SCHEMA_VERSION,
        "dataset_id": str(dataset_id),
        "dataset_version_id": str(dataset_version_id) if dataset_version_id else None,
        "content_sha256": str(content_sha256),
        "configuration": clean_json(configuration),
        "context": clean_json(context),
    }
    return fingerprint(basis)


def _compute_column_stats(series: pd.Series) -> dict[str, Any]:
    """Compute aggregate statistical summaries without exposing individual rows."""
    if pd.api.types.is_numeric_dtype(series):
        valid = series.dropna()
        if len(valid) == 0:
            return {"count": 0, "numeric": True}
        return {
            "count": int(len(valid)),
            "numeric": True,
            "min": round(float(valid.min()), 4),
            "max": round(float(valid.max()), 4),
            "mean": round(float(valid.mean()), 4),
            "std": round(float(valid.std()), 4) if len(valid) > 1 else 0.0,
            "median": round(float(valid.median()), 4),
            "q25": round(float(valid.quantile(0.25)), 4),
            "q75": round(float(valid.quantile(0.75)), 4),
        }
    else:
        valid = series.dropna().astype(str)
        top_cats = valid.value_counts().head(5).to_dict()
        return {
            "count": int(len(valid)),
            "numeric": False,
            "top_categories": {str(k): int(v) for k, v in top_cats.items()},
        }


def _build_schema_snapshot(frame: pd.DataFrame, target_column: str | None) -> SchemaSnapshot:
    """Build column profiles and summary statistics."""
    columns_profile: list[FeatureProfile] = []
    total_rows = len(frame)

    for col in frame.columns:
        s = frame[col]
        null_cnt = int(s.isna().sum())
        null_pct = round(float(null_cnt / total_rows), 4) if total_rows > 0 else 0.0
        distinct_cnt = int(s.nunique(dropna=True))
        is_const = distinct_cnt <= 1

        stats = _compute_column_stats(s)

        dtype_str = "numeric" if pd.api.types.is_numeric_dtype(s) else "string"
        if pd.api.types.is_bool_dtype(s):
            dtype_str = "boolean"
        elif pd.api.types.is_datetime64_any_dtype(s):
            dtype_str = "datetime"

        columns_profile.append(
            FeatureProfile(
                name=str(col),
                data_type=dtype_str,
                null_count=null_cnt,
                null_percentage=null_pct,
                distinct_count=distinct_cnt,
                is_constant=is_const,
                sample_stats=stats,
            )
        )

    return SchemaSnapshot(
        total_rows=total_rows,
        total_features=len(frame.columns) - (1 if target_column and target_column in frame.columns else 0),
        target_column=target_column,
        columns=columns_profile,
    )


def _check_schema_integrity(frame: pd.DataFrame, target_name: str | None) -> QualityDomainResult:
    checks: list[QualityCheckResult] = []

    # 1. Column Naming
    cols = list(frame.columns)
    invalid_cols = [
        str(c) for c in cols
        if not str(c).strip() or len(str(c)) > 100 or any(ord(ch) < 32 for ch in str(c))
    ]
    duplicate_names = [c for c in set(cols) if cols.count(c) > 1]

    if duplicate_names:
        checks.append(
            QualityCheckResult(
                name="unique_column_names",
                domain="schema_integrity",
                status="FAIL",
                severity="CRITICAL",
                message=f"Duplicate column names detected: {duplicate_names}",
                details={"duplicate_columns": duplicate_names},
                recommendation="Rename conflicting columns to ensure unique identifiers.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="unique_column_names",
                domain="schema_integrity",
                status="PASS",
                severity="INFO",
                message="All column names are unique.",
                details={"column_count": len(cols)},
            )
        )

    if invalid_cols:
        checks.append(
            QualityCheckResult(
                name="valid_column_names",
                domain="schema_integrity",
                status="WARN",
                severity="MEDIUM",
                message=f"Detected {len(invalid_cols)} columns with whitespace or unprintable characters.",
                details={"invalid_columns": invalid_cols[:10]},
                recommendation="Standardize column names to trimmed, clean strings.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="valid_column_names",
                domain="schema_integrity",
                status="PASS",
                severity="INFO",
                message="All column names satisfy standard string format constraints.",
                details={},
            )
        )

    # 2. Target Column Presence
    if target_name and target_name in frame.columns:
        checks.append(
            QualityCheckResult(
                name="target_column_presence",
                domain="schema_integrity",
                status="PASS",
                severity="INFO",
                message=f"Target column '{target_name}' is present in dataset.",
                details={"target_column": target_name},
            )
        )
    elif target_name:
        checks.append(
            QualityCheckResult(
                name="target_column_presence",
                domain="schema_integrity",
                status="FAIL",
                severity="CRITICAL",
                message=f"Declared target column '{target_name}' was not found in dataset.",
                details={"declared_target": target_name, "available_columns": list(frame.columns[:10])},
                recommendation="Verify the target column name matches one of the dataset headers.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="target_column_presence",
                domain="schema_integrity",
                status="WARN",
                severity="HIGH",
                message="No target column was declared or identified in metadata.",
                details={},
                recommendation="Specify a target column before supervised model training.",
            )
        )

    # 3. Unnamed index columns
    unnamed = [str(c) for c in cols if str(c).lower().startswith("unnamed:") or str(c) == ""]
    if unnamed:
        checks.append(
            QualityCheckResult(
                name="unnamed_index_columns",
                domain="schema_integrity",
                status="WARN",
                severity="LOW",
                message=f"Detected {len(unnamed)} unnamed or index-like columns.",
                details={"unnamed_columns": unnamed},
                recommendation="Drop unintended index columns prior to pipeline processing.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="unnamed_index_columns",
                domain="schema_integrity",
                status="PASS",
                severity="INFO",
                message="No unnamed index artifact columns detected.",
                details={},
            )
        )

    return _summarize_domain("schema_integrity", "Schema & Structural Integrity", checks)


def _check_completeness(frame: pd.DataFrame, thresholds: dict[str, Any]) -> QualityDomainResult:
    checks: list[QualityCheckResult] = []
    total_rows = len(frame)
    min_rows = thresholds.get("min_row_count", DEFAULT_THRESHOLDS["min_row_count"])
    warn_rows = thresholds.get("warn_row_count", DEFAULT_THRESHOLDS["warn_row_count"])

    # 1. Sample Size Adequacy
    if total_rows < min_rows:
        checks.append(
            QualityCheckResult(
                name="sample_size_adequacy",
                domain="completeness",
                status="FAIL",
                severity="HIGH",
                message=f"Sample size ({total_rows}) is below minimum threshold of {min_rows}.",
                details={"row_count": total_rows, "minimum_threshold": min_rows},
                recommendation="Increase dataset volume to prevent overfitting and high-variance estimates.",
            )
        )
    elif total_rows < warn_rows:
        checks.append(
            QualityCheckResult(
                name="sample_size_adequacy",
                domain="completeness",
                status="WARN",
                severity="MEDIUM",
                message=f"Sample size ({total_rows}) is modest (recommended >= {warn_rows}).",
                details={"row_count": total_rows, "recommended_threshold": warn_rows},
                recommendation="Use cross-validation or regularization to mitigate small-sample risk.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="sample_size_adequacy",
                domain="completeness",
                status="PASS",
                severity="INFO",
                message=f"Sample size ({total_rows} rows) meets research requirements.",
                details={"row_count": total_rows},
            )
        )

    # 2. Overall Missingness
    total_cells = frame.size
    total_missing = int(frame.isna().sum().sum())
    overall_missing_rate = round(float(total_missing / total_cells), 4) if total_cells > 0 else 0.0

    max_missing = thresholds.get("max_missing_rate_overall", DEFAULT_THRESHOLDS["max_missing_rate_overall"])
    warn_missing = thresholds.get("warn_missing_rate_overall", DEFAULT_THRESHOLDS["warn_missing_rate_overall"])

    if overall_missing_rate > max_missing:
        checks.append(
            QualityCheckResult(
                name="overall_missingness",
                domain="completeness",
                status="FAIL",
                severity="HIGH",
                message=f"Overall missing cell rate ({overall_missing_rate:.1%}) exceeds maximum tolerance ({max_missing:.1%}).",
                details={"missing_cells": total_missing, "total_cells": total_cells, "missing_rate": overall_missing_rate},
                recommendation="Investigate data collection pipeline for systematic missingness.",
            )
        )
    elif overall_missing_rate > warn_missing:
        checks.append(
            QualityCheckResult(
                name="overall_missingness",
                domain="completeness",
                status="WARN",
                severity="MEDIUM",
                message=f"Overall missing cell rate ({overall_missing_rate:.1%}) exceeds warning threshold ({warn_missing:.1%}).",
                details={"missing_cells": total_missing, "total_cells": total_cells, "missing_rate": overall_missing_rate},
                recommendation="Ensure robust imputation strategy is documented in protocol.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="overall_missingness",
                domain="completeness",
                status="PASS",
                severity="INFO",
                message=f"Overall missing cell rate ({overall_missing_rate:.1%}) is within healthy limits.",
                details={"missing_rate": overall_missing_rate},
            )
        )

    # 3. Column-Level Missingness Spikes
    warn_col_missing = thresholds.get("warn_missing_rate_column", DEFAULT_THRESHOLDS["warn_missing_rate_column"])
    max_col_missing = thresholds.get("max_missing_rate_column", DEFAULT_THRESHOLDS["max_missing_rate_column"])

    col_missing_series = frame.isna().mean()
    high_missing_cols = [
        {"column": str(col), "missing_rate": round(float(val), 4)}
        for col, val in col_missing_series.items() if val > warn_col_missing
    ]

    severe_missing_cols = [c for c in high_missing_cols if c["missing_rate"] > max_col_missing]

    if severe_missing_cols:
        checks.append(
            QualityCheckResult(
                name="column_missingness_spikes",
                domain="completeness",
                status="WARN",
                severity="HIGH",
                message=f"{len(severe_missing_cols)} feature(s) have > {max_col_missing:.0%} missing data.",
                details={"severe_columns": severe_missing_cols, "total_affected": len(high_missing_cols)},
                recommendation="Consider dropping severely incomplete columns or verifying imputation validity.",
            )
        )
    elif high_missing_cols:
        checks.append(
            QualityCheckResult(
                name="column_missingness_spikes",
                domain="completeness",
                status="WARN",
                severity="MEDIUM",
                message=f"{len(high_missing_cols)} feature(s) exceed {warn_col_missing:.0%} missing values.",
                details={"affected_columns": high_missing_cols[:10]},
                recommendation="Review missing-data mechanism (MCAR vs MAR vs MNAR).",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="column_missingness_spikes",
                domain="completeness",
                status="PASS",
                severity="INFO",
                message="No columns exceed individual missingness thresholds.",
                details={},
            )
        )

    # 4. Completely Empty Rows or Columns
    empty_cols = [str(c) for c in frame.columns if frame[c].isna().all()]
    empty_rows_count = int(frame.isna().all(axis=1).sum())

    if empty_cols or empty_rows_count > 0:
        checks.append(
            QualityCheckResult(
                name="empty_rows_or_columns",
                domain="completeness",
                status="FAIL",
                severity="HIGH",
                message=f"Found {len(empty_cols)} completely empty column(s) and {empty_rows_count} completely empty row(s).",
                details={"empty_columns": empty_cols, "empty_rows_count": empty_rows_count},
                recommendation="Drop empty rows and columns prior to downstream experiment execution.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="empty_rows_or_columns",
                domain="completeness",
                status="PASS",
                severity="INFO",
                message="Zero completely empty rows or columns detected.",
                details={},
            )
        )

    return _summarize_domain("completeness", "Completeness & Missingness", checks)


def _check_duplicate_integrity(frame: pd.DataFrame, thresholds: dict[str, Any]) -> QualityDomainResult:
    checks: list[QualityCheckResult] = []
    total_rows = len(frame)

    # 1. Exact Duplicate Rows
    dup_rows = int(frame.duplicated().sum())
    dup_rate = round(float(dup_rows / total_rows), 4) if total_rows > 0 else 0.0

    max_dup = thresholds.get("max_duplicate_rate", DEFAULT_THRESHOLDS["max_duplicate_rate"])
    warn_dup = thresholds.get("warn_duplicate_rate", DEFAULT_THRESHOLDS["warn_duplicate_rate"])

    if dup_rate > max_dup:
        checks.append(
            QualityCheckResult(
                name="exact_duplicate_rows",
                domain="duplicate_integrity",
                status="FAIL",
                severity="HIGH",
                message=f"Exact duplicate row rate ({dup_rate:.1%}, {dup_rows} rows) exceeds maximum tolerance ({max_dup:.1%}).",
                details={"duplicate_row_count": dup_rows, "duplicate_rate": dup_rate},
                recommendation="Deduplicate records or verify if repeated measurements are clinically justified.",
            )
        )
    elif dup_rate > warn_dup:
        checks.append(
            QualityCheckResult(
                name="exact_duplicate_rows",
                domain="duplicate_integrity",
                status="WARN",
                severity="MEDIUM",
                message=f"Detected {dup_rows} exact duplicate rows ({dup_rate:.1%}).",
                details={"duplicate_row_count": dup_rows, "duplicate_rate": dup_rate},
                recommendation="Verify whether duplicate rows represent identical observations or distinct patient encounters.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="exact_duplicate_rows",
                domain="duplicate_integrity",
                status="PASS",
                severity="INFO",
                message=f"Duplicate row rate ({dup_rate:.1%}) is within acceptable parameters.",
                details={"duplicate_count": dup_rows},
            )
        )

    # 2. Identifier uniqueness check
    id_candidates = [
        col for col in frame.columns
        if any(term in str(col).lower() for term in ["patient_id", "subject_id", "encounter_id", "mrn", "id"])
        and not str(col).lower().startswith("unnamed")
    ]
    if id_candidates:
        primary_id_col = id_candidates[0]
        id_series = frame[primary_id_col].dropna()
        dup_ids = int(id_series.duplicated().sum())
        if dup_ids > 0:
            checks.append(
                QualityCheckResult(
                    name="identifier_uniqueness",
                    domain="duplicate_integrity",
                    status="WARN",
                    severity="MEDIUM",
                    message=f"Identifier column '{primary_id_col}' contains {dup_ids} repeated values.",
                    details={"identifier_column": str(primary_id_col), "duplicate_id_count": dup_ids},
                    recommendation="Ensure patient-level grouped validation is used to avoid cross-split data leakage.",
                )
            )
        else:
            checks.append(
                QualityCheckResult(
                    name="identifier_uniqueness",
                    domain="duplicate_integrity",
                    status="PASS",
                    severity="INFO",
                    message=f"Identifier column '{primary_id_col}' has unique values across all rows.",
                    details={"identifier_column": str(primary_id_col)},
                )
            )
    else:
        checks.append(
            QualityCheckResult(
                name="identifier_uniqueness",
                domain="duplicate_integrity",
                status="NOT_APPLICABLE",
                severity="INFO",
                message="No patient/subject identifier column detected.",
                details={},
            )
        )

    return _summarize_domain("duplicate_integrity", "Duplicate Integrity", checks)


def _check_target_integrity(
    frame: pd.DataFrame,
    target_name: str | None,
    declared_pos: str | None,
    declared_neg: str | None,
) -> QualityDomainResult:
    checks: list[QualityCheckResult] = []

    if not target_name or target_name not in frame.columns:
        checks.append(
            QualityCheckResult(
                name="target_integrity_evaluation",
                domain="target_integrity",
                status="UNVERIFIABLE",
                severity="CRITICAL",
                message="Target column not resolved in dataset.",
                details={},
                recommendation="Target must be resolved before target integrity can be assessed.",
            )
        )
        return _summarize_domain("target_integrity", "Target & Label Integrity", checks)

    target_series = frame[target_name]

    # 1. Target Missingness
    missing_target = int(target_series.isna().sum())
    if missing_target > 0:
        missing_rate = round(float(missing_target / len(frame)), 4)
        checks.append(
            QualityCheckResult(
                name="target_missingness",
                domain="target_integrity",
                status="FAIL",
                severity="CRITICAL",
                message=f"Target column contains {missing_target} missing values ({missing_rate:.1%}).",
                details={"missing_count": missing_target, "missing_rate": missing_rate},
                recommendation="Supervised learning requires ground truth. Drop rows with unobserved target values.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="target_missingness",
                domain="target_integrity",
                status="PASS",
                severity="INFO",
                message="Target column is 100% complete with 0 missing labels.",
                details={"missing_count": 0},
            )
        )

    # 2. Target Class Cardinality
    observed_classes = [str(c) for c in target_series.dropna().unique()]
    cardinality = len(observed_classes)

    if cardinality < 2:
        checks.append(
            QualityCheckResult(
                name="target_class_cardinality",
                domain="target_integrity",
                status="FAIL",
                severity="CRITICAL",
                message=f"Target has only {cardinality} class ({observed_classes}). Classification is mathematically impossible.",
                details={"cardinality": cardinality, "observed_classes": observed_classes},
                recommendation="Verify dataset filtering or inclusion criteria.",
            )
        )
    elif cardinality == 2:
        checks.append(
            QualityCheckResult(
                name="target_class_cardinality",
                domain="target_integrity",
                status="PASS",
                severity="INFO",
                message="Target has exactly 2 classes, suitable for binary classification.",
                details={"cardinality": 2, "observed_classes": observed_classes},
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="target_class_cardinality",
                domain="target_integrity",
                status="WARN",
                severity="LOW",
                message=f"Target has {cardinality} classes ({observed_classes[:5]}...). Ensure multiclass support.",
                details={"cardinality": cardinality, "observed_classes": observed_classes[:10]},
            )
        )

    # 3. Label Conformance
    if declared_pos is not None and declared_neg is not None:
        conforms = declared_pos in observed_classes and declared_neg in observed_classes
        if conforms:
            checks.append(
                QualityCheckResult(
                    name="label_conformance",
                    domain="target_integrity",
                    status="PASS",
                    severity="INFO",
                    message=f"Declared positive ('{declared_pos}') and negative ('{declared_neg}') labels match observed classes.",
                    details={"declared_positive": declared_pos, "declared_negative": declared_neg},
                )
            )
        else:
            checks.append(
                QualityCheckResult(
                    name="label_conformance",
                    domain="target_integrity",
                    status="FAIL",
                    severity="HIGH",
                    message=f"Declared labels ('{declared_pos}', '{declared_neg}') do not match observed classes ({observed_classes}).",
                    details={"declared": [declared_pos, declared_neg], "observed": observed_classes},
                    recommendation="Align metadata positive/negative labels with dataset values.",
                )
            )
    else:
        checks.append(
            QualityCheckResult(
                name="label_conformance",
                domain="target_integrity",
                status="NOT_APPLICABLE",
                severity="INFO",
                message="Positive/negative labels not explicitly declared in metadata.",
                details={"observed_classes": observed_classes},
            )
        )

    return _summarize_domain("target_integrity", "Target & Label Integrity", checks)


def _check_feature_health(frame: pd.DataFrame, target_name: str | None, thresholds: dict[str, Any]) -> QualityDomainResult:
    checks: list[QualityCheckResult] = []
    features = [c for c in frame.columns if c != target_name]
    near_const_thresh = thresholds.get("near_constant_threshold", DEFAULT_THRESHOLDS["near_constant_threshold"])
    high_card_thresh = thresholds.get("high_cardinality_threshold", DEFAULT_THRESHOLDS["high_cardinality_threshold"])
    total_rows = len(frame)

    constant_cols = []
    near_constant_cols = []
    non_finite_cols = []
    outlier_cols = []
    high_card_cols = []

    for col in features:
        s = frame[col]
        non_null = s.dropna()
        if len(non_null) == 0:
            continue

        distinct = non_null.nunique()
        if distinct <= 1:
            constant_cols.append(str(col))
        elif total_rows > 0:
            top_freq = non_null.value_counts().iloc[0] / len(non_null)
            if top_freq >= near_const_thresh:
                near_constant_cols.append({"column": str(col), "dominant_ratio": round(float(top_freq), 4)})

        if pd.api.types.is_numeric_dtype(s):
            # Non-finite check
            inf_cnt = int(np.isinf(non_null).sum())
            if inf_cnt > 0:
                non_finite_cols.append({"column": str(col), "infinite_count": inf_cnt})

            # Outlier diagnostics (z-score > 5)
            if len(non_null) > 10 and non_null.std() > 0:
                z = (non_null - non_null.mean()) / non_null.std()
                extreme_cnt = int((z.abs() > thresholds.get("outlier_zscore_threshold", 5.0)).sum())
                if extreme_cnt > 0:
                    outlier_cols.append({"column": str(col), "extreme_outliers_count": extreme_cnt})
        else:
            # High cardinality categorical
            if total_rows > 20 and (distinct / total_rows) > high_card_thresh:
                high_card_cols.append({"column": str(col), "unique_ratio": round(float(distinct / total_rows), 4)})

    # 1. Constant Features
    if constant_cols:
        checks.append(
            QualityCheckResult(
                name="constant_features",
                domain="feature_health",
                status="WARN",
                severity="HIGH",
                message=f"Detected {len(constant_cols)} zero-variance constant feature(s).",
                details={"constant_columns": constant_cols},
                recommendation="Remove constant features as they provide zero discriminative signal and risk collinearity.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="constant_features",
                domain="feature_health",
                status="PASS",
                severity="INFO",
                message="Zero constant features detected across input predictors.",
                details={},
            )
        )

    # 2. Near-constant Features
    if near_constant_cols:
        checks.append(
            QualityCheckResult(
                name="near_constant_features",
                domain="feature_health",
                status="WARN",
                severity="MEDIUM",
                message=f"Detected {len(near_constant_cols)} near-constant feature(s) (> {near_const_thresh:.0%} single value).",
                details={"near_constant_columns": near_constant_cols[:10]},
                recommendation="Evaluate whether near-constant features add value or should be pruned.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="near_constant_features",
                domain="feature_health",
                status="PASS",
                severity="INFO",
                message="No near-constant features detected.",
                details={},
            )
        )

    # 3. Non-finite values
    if non_finite_cols:
        checks.append(
            QualityCheckResult(
                name="non_finite_values",
                domain="feature_health",
                status="FAIL",
                severity="HIGH",
                message=f"Detected infinite values in {len(non_finite_cols)} numeric feature(s).",
                details={"affected_columns": non_finite_cols},
                recommendation="Replace infinite values with NaN or clamp to numerical bounds.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="non_finite_values",
                domain="feature_health",
                status="PASS",
                severity="INFO",
                message="No infinite or overflow values detected in numerical features.",
                details={},
            )
        )

    # 4. Outliers check (observational only)
    if outlier_cols:
        checks.append(
            QualityCheckResult(
                name="extreme_outliers",
                domain="feature_health",
                status="WARN",
                severity="LOW",
                message=f"Detected extreme outliers (|z| > 5) in {len(outlier_cols)} feature(s).",
                details={"outlier_columns": outlier_cols[:10]},
                recommendation="Confirm clinical plausibility of extreme laboratory/biomarker measurements.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="extreme_outliers",
                domain="feature_health",
                status="PASS",
                severity="INFO",
                message="No extreme mathematical outliers (|z| > 5) detected.",
                details={},
            )
        )

    # 5. High Cardinality Categoricals
    if high_card_cols:
        checks.append(
            QualityCheckResult(
                name="high_cardinality_categoricals",
                domain="feature_health",
                status="WARN",
                severity="MEDIUM",
                message=f"Detected {len(high_card_cols)} categorical feature(s) with > {high_card_thresh:.0%} distinct values.",
                details={"high_cardinality_columns": high_card_cols},
                recommendation="High cardinality features may be unmasked identifiers or text fields.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="high_cardinality_categoricals",
                domain="feature_health",
                status="PASS",
                severity="INFO",
                message="No excessively high cardinality categorical predictors detected.",
                details={},
            )
        )

    return _summarize_domain("feature_health", "Feature Health & Numerical Stability", checks)


def _check_class_balance(frame: pd.DataFrame, target_name: str | None, thresholds: dict[str, Any]) -> QualityDomainResult:
    checks: list[QualityCheckResult] = []

    if not target_name or target_name not in frame.columns:
        checks.append(
            QualityCheckResult(
                name="class_balance_check",
                domain="class_balance",
                status="UNVERIFIABLE",
                severity="MEDIUM",
                message="Target column not resolved; class balance cannot be evaluated.",
                details={},
            )
        )
        return _summarize_domain("class_balance", "Class Balance & Prevalence", checks)

    s = frame[target_name].dropna()
    total = len(s)
    if total == 0:
        checks.append(
            QualityCheckResult(
                name="class_balance_check",
                domain="class_balance",
                status="FAIL",
                severity="HIGH",
                message="Target column has 0 non-null values.",
                details={},
            )
        )
        return _summarize_domain("class_balance", "Class Balance & Prevalence", checks)

    counts = s.value_counts().to_dict()
    proportions = {str(k): round(float(v / total), 4) for k, v in counts.items()}

    minority_class = min(counts, key=counts.get)
    minority_frac = proportions[str(minority_class)]

    min_rate = thresholds.get("min_minority_class_rate", DEFAULT_THRESHOLDS["min_minority_class_rate"])
    warn_rate = thresholds.get("warn_minority_class_rate", DEFAULT_THRESHOLDS["warn_minority_class_rate"])

    if minority_frac < min_rate:
        checks.append(
            QualityCheckResult(
                name="class_prevalence",
                domain="class_balance",
                status="FAIL",
                severity="HIGH",
                message=f"Severe class imbalance: minority class '{minority_class}' represents only {minority_frac:.1%} of samples.",
                details={"class_counts": {str(k): int(v) for k, v in counts.items()}, "proportions": proportions},
                recommendation="Standard metrics like Accuracy are deceptive at this prevalence. Use balanced metrics and stratification.",
            )
        )
    elif minority_frac < warn_rate:
        checks.append(
            QualityCheckResult(
                name="class_prevalence",
                domain="class_balance",
                status="WARN",
                severity="MEDIUM",
                message=f"Moderate class imbalance: minority class '{minority_class}' is {minority_frac:.1%}.",
                details={"class_counts": {str(k): int(v) for k, v in counts.items()}, "proportions": proportions},
                recommendation="Consider precision-recall analysis, PR-AUC, and stratified cross-validation.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="class_prevalence",
                domain="class_balance",
                status="PASS",
                severity="INFO",
                message=f"Class distribution is adequately balanced (minority class '{minority_class}' is {minority_frac:.1%}).",
                details={"class_counts": {str(k): int(v) for k, v in counts.items()}, "proportions": proportions},
            )
        )

    return _summarize_domain("class_balance", "Class Balance & Prevalence", checks)


def _check_data_leakage(frame: pd.DataFrame, target_name: str | None, thresholds: dict[str, Any]) -> QualityDomainResult:
    checks: list[QualityCheckResult] = []
    features = [c for c in frame.columns if c != target_name]
    corr_thresh = thresholds.get("max_feature_correlation", DEFAULT_THRESHOLDS["max_feature_correlation"])

    # 1. Target Correlation Leakage
    leaking_features = []
    if target_name and target_name in frame.columns:
        target_s = frame[target_name]
        # Attempt to numeric encode target if binary
        if pd.api.types.is_numeric_dtype(target_s):
            y = target_s.astype(float)
        else:
            unique_vals = list(target_s.dropna().unique())
            if len(unique_vals) == 2:
                y = (target_s == unique_vals[0]).astype(float)
            else:
                y = None

        if y is not None:
            for feat in features:
                f_s = frame[feat]
                if pd.api.types.is_numeric_dtype(f_s):
                    valid_mask = f_s.notna() & y.notna()
                    if valid_mask.sum() > 10 and f_s[valid_mask].std() > 0 and y[valid_mask].std() > 0:
                        r = float(np.corrcoef(f_s[valid_mask], y[valid_mask])[0, 1])
                        if abs(r) >= corr_thresh:
                            leaking_features.append({"feature": str(feat), "correlation": round(r, 6)})

    if leaking_features:
        checks.append(
            QualityCheckResult(
                name="target_correlation_leakage",
                domain="data_leakage",
                status="FAIL",
                severity="CRITICAL",
                message=f"Detected {len(leaking_features)} feature(s) with near-perfect correlation (|r| >= {corr_thresh}) to target.",
                details={"leaking_features": leaking_features},
                recommendation="Feature is a direct target proxy or duplicate. Remove to prevent invalid predictive inflation.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="target_correlation_leakage",
                domain="data_leakage",
                status="PASS",
                severity="INFO",
                message="Zero artificial target-proxy features detected.",
                details={},
            )
        )

    # 2. Identifier in features
    id_terms = ["patient_id", "subject_id", "encounter_id", "mrn", "ssn"]
    id_in_feats = [str(c) for c in features if any(term == str(c).lower() or f"{term}_" in str(c).lower() for term in id_terms)]
    if id_in_feats:
        checks.append(
            QualityCheckResult(
                name="identifier_in_features",
                domain="data_leakage",
                status="WARN",
                severity="HIGH",
                message=f"Identifier column(s) {id_in_feats} included among predictor features.",
                details={"identifier_features": id_in_feats},
                recommendation="Exclude administrative patient identifiers from machine learning feature matrices.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="identifier_in_features",
                domain="data_leakage",
                status="PASS",
                severity="INFO",
                message="No patient identifier columns included among model features.",
                details={},
            )
        )

    # 3. Monotonic Row Index Leakage
    monotonic_features = []
    n = len(frame)
    if n > 20:
        expected_seq = np.arange(n)
        for feat in features:
            f_s = frame[feat]
            if pd.api.types.is_numeric_dtype(f_s):
                arr = f_s.values
                if np.array_equal(arr, expected_seq) or np.array_equal(arr, expected_seq + 1):
                    monotonic_features.append(str(feat))

    if monotonic_features:
        checks.append(
            QualityCheckResult(
                name="index_monotonic_leakage",
                domain="data_leakage",
                status="WARN",
                severity="HIGH",
                message=f"Feature(s) {monotonic_features} exactly mirror sequential row numbers.",
                details={"monotonic_features": monotonic_features},
                recommendation="Drop synthetic row sequence counters prior to model training.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="index_monotonic_leakage",
                domain="data_leakage",
                status="PASS",
                severity="INFO",
                message="No row-index sequential counter leakage detected.",
                details={},
            )
        )

    return _summarize_domain("data_leakage", "Data Leakage & Integrity Signals", checks)


def _check_sensitive_fields(frame: pd.DataFrame, provenance: dict[str, Any]) -> QualityDomainResult:
    checks: list[QualityCheckResult] = []
    cols = [str(c).lower() for c in frame.columns]

    pii_terms = ["ssn", "social_security", "medical_record_number", "mrn", "patient_name", "first_name", "last_name", "full_name", "phone", "email", "address", "dob", "date_of_birth"]
    flagged = [str(c) for c in frame.columns if str(c).lower() in pii_terms]

    if flagged:
        checks.append(
            QualityCheckResult(
                name="direct_identifiers_scan",
                domain="sensitive_fields",
                status="FAIL",
                severity="CRITICAL",
                message=f"Detected potentially direct HIPAA identifiers: {flagged}.",
                details={"flagged_columns": flagged},
                recommendation="Remove direct identifiers to maintain strict biomedical de-identification standards.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="direct_identifiers_scan",
                domain="sensitive_fields",
                status="PASS",
                severity="INFO",
                message="Zero direct identifier column names detected.",
                details={},
            )
        )

    deidentified_asserted = provenance.get("deidentified", provenance.get("deidentification_asserted_by_uploader", None))
    if deidentified_asserted is True:
        checks.append(
            QualityCheckResult(
                name="deidentification_status",
                domain="sensitive_fields",
                status="PASS",
                severity="INFO",
                message="Dataset provenance explicitly asserts certified de-identification.",
                details={"deidentified_asserted": True},
            )
        )
    elif deidentified_asserted is False:
        checks.append(
            QualityCheckResult(
                name="deidentification_status",
                domain="sensitive_fields",
                status="WARN",
                severity="MEDIUM",
                message="De-identification status is asserted as False or unverified.",
                details={"deidentified_asserted": False},
                recommendation="Verify institutional governance compliance before external distribution.",
            )
        )
    else:
        checks.append(
            QualityCheckResult(
                name="deidentification_status",
                domain="sensitive_fields",
                status="WARN",
                severity="LOW",
                message="De-identification assertion is missing from provenance metadata.",
                details={},
                recommendation="Record explicit de-identification metadata during dataset ingestion.",
            )
        )

    return _summarize_domain("sensitive_fields", "Sensitive Field & De-identification Diagnostics", checks)


def _check_context_compatibility(
    session,
    frame: pd.DataFrame,
    target_name: str | None,
    protocol_version_id: str | None,
    pipeline_version_id: str | None,
    subgroup_field: str | None,
    reference_dataset_version_id: str | None,
) -> tuple[QualityDomainResult, list[str]]:
    checks: list[QualityCheckResult] = []
    limitations: list[str] = []

    # 1. Protocol Compatibility
    if protocol_version_id:
        protocol = session.get(ExperimentProtocolVersion, protocol_version_id)
        if not protocol:
            checks.append(
                QualityCheckResult(
                    name="protocol_compatibility",
                    domain="context_compatibility",
                    status="UNVERIFIABLE",
                    severity="HIGH",
                    message=f"Protocol version '{protocol_version_id}' could not be loaded.",
                    details={"protocol_version_id": protocol_version_id},
                )
            )
            limitations.append(f"Protocol version {protocol_version_id} was not found; protocol checks unverifiable.")
        else:
            proto_def = protocol.canonical_definition or {}
            proto_target = proto_def.get("study", {}).get("target_column") or proto_def.get("dataset_policy", {}).get("target_column")
            if proto_target and target_name and proto_target != target_name:
                checks.append(
                    QualityCheckResult(
                        name="protocol_compatibility",
                        domain="context_compatibility",
                        status="FAIL",
                        severity="CRITICAL",
                        message=f"Target mismatch: Protocol requires '{proto_target}' but dataset specifies '{target_name}'.",
                        details={"protocol_target": proto_target, "dataset_target": target_name},
                        recommendation="Realign dataset target column with protocol specification.",
                    )
                )
            else:
                checks.append(
                    QualityCheckResult(
                        name="protocol_compatibility",
                        domain="context_compatibility",
                        status="PASS",
                        severity="INFO",
                        message=f"Dataset conforms to protocol specification ({protocol.version_label}).",
                        details={"protocol_version_id": protocol_version_id, "protocol_fingerprint": protocol.definition_fingerprint},
                    )
                )
    else:
        checks.append(
            QualityCheckResult(
                name="protocol_compatibility",
                domain="context_compatibility",
                status="NOT_APPLICABLE",
                severity="INFO",
                message="No protocol version specified; protocol compatibility check is not applicable.",
                details={},
            )
        )
        limitations.append("Experimental protocol version was not specified; protocol conformance was not checked.")

    # 2. Pipeline Compatibility
    if pipeline_version_id:
        pipeline = session.get(PipelineVersion, pipeline_version_id)
        if not pipeline:
            checks.append(
                QualityCheckResult(
                    name="pipeline_compatibility",
                    domain="context_compatibility",
                    status="UNVERIFIABLE",
                    severity="HIGH",
                    message=f"Pipeline version '{pipeline_version_id}' could not be loaded.",
                    details={"pipeline_version_id": pipeline_version_id},
                )
            )
            limitations.append(f"Pipeline version {pipeline_version_id} was not found; pipeline checks unverifiable.")
        else:
            checks.append(
                QualityCheckResult(
                    name="pipeline_compatibility",
                    domain="context_compatibility",
                    status="PASS",
                    severity="INFO",
                    message=f"Dataset compatible with pipeline stages ({pipeline.version_label}).",
                    details={"pipeline_version_id": pipeline_version_id, "pipeline_fingerprint": pipeline.definition_fingerprint},
                )
            )
    else:
        checks.append(
            QualityCheckResult(
                name="pipeline_compatibility",
                domain="context_compatibility",
                status="NOT_APPLICABLE",
                severity="INFO",
                message="No pipeline version specified; pipeline compatibility check is not applicable.",
                details={},
            )
        )
        limitations.append("Computational pipeline version was not specified; pipeline stage compatibility was not checked.")

    # 3. Subgroup Field Coverage
    if subgroup_field:
        if subgroup_field not in frame.columns:
            checks.append(
                QualityCheckResult(
                    name="subgroup_coverage",
                    domain="context_compatibility",
                    status="FAIL",
                    severity="CRITICAL",
                    message=f"Requested subgroup column '{subgroup_field}' is not in dataset.",
                    details={"subgroup_field": subgroup_field},
                    recommendation="Ensure the subgroup stratification column exists in the dataset schema.",
                )
            )
        else:
            grp_s = frame[subgroup_field].dropna()
            distinct_groups = grp_s.nunique()
            min_group_size = int(grp_s.value_counts().min()) if distinct_groups > 0 else 0

            if distinct_groups < 2:
                checks.append(
                    QualityCheckResult(
                        name="subgroup_coverage",
                        domain="context_compatibility",
                        status="WARN",
                        severity="HIGH",
                        message=f"Subgroup column '{subgroup_field}' has only {distinct_groups} distinct category.",
                        details={"distinct_groups": distinct_groups},
                    )
                )
            elif min_group_size < 5:
                checks.append(
                    QualityCheckResult(
                        name="subgroup_coverage",
                        domain="context_compatibility",
                        status="WARN",
                        severity="MEDIUM",
                        message=f"Smallest subgroup category in '{subgroup_field}' has only {min_group_size} samples.",
                        details={"min_group_size": min_group_size, "group_counts": grp_s.value_counts().to_dict()},
                        recommendation="Consider collapsing sparse subgroup categories.",
                    )
                )
            else:
                checks.append(
                    QualityCheckResult(
                        name="subgroup_coverage",
                        domain="context_compatibility",
                        status="PASS",
                        severity="INFO",
                        message=f"Subgroup field '{subgroup_field}' is well-represented across {distinct_groups} groups.",
                        details={"distinct_groups": distinct_groups, "min_group_size": min_group_size},
                    )
                )
    else:
        checks.append(
            QualityCheckResult(
                name="subgroup_coverage",
                domain="context_compatibility",
                status="NOT_APPLICABLE",
                severity="INFO",
                message="No subgroup field specified; stratified subgroup coverage check is not applicable.",
                details={},
            )
        )

    # 4. Reference Dataset Distribution Shift
    if reference_dataset_version_id:
        ref_ver = session.get(DatasetVersion, reference_dataset_version_id)
        if not ref_ver:
            checks.append(
                QualityCheckResult(
                    name="reference_distribution_shift",
                    domain="context_compatibility",
                    status="UNVERIFIABLE",
                    severity="MEDIUM",
                    message=f"Reference dataset version '{reference_dataset_version_id}' could not be resolved.",
                    details={"reference_dataset_version_id": reference_dataset_version_id},
                )
            )
            limitations.append("Reference dataset version was not found; distribution shift check unverifiable.")
        else:
            try:
                ref_bytes = read_version_bytes(ref_ver)
                ref_frame, _ = _read_csv_table(ref_bytes)
                # Compute overlap and mean shifts on numeric columns
                common_num = [
                    c for c in frame.columns
                    if c in ref_frame.columns and pd.api.types.is_numeric_dtype(frame[c]) and pd.api.types.is_numeric_dtype(ref_frame[c])
                ]
                shifts = {}
                for col in common_num:
                    s_curr = frame[col].dropna()
                    s_ref = ref_frame[col].dropna()
                    if len(s_curr) > 0 and len(s_ref) > 0 and s_ref.std() > 0:
                        std_diff = abs(s_curr.mean() - s_ref.mean()) / s_ref.std()
                        shifts[col] = round(float(std_diff), 4)

                max_shift = max(shifts.values()) if shifts else 0.0
                if max_shift > 1.0:
                    checks.append(
                        QualityCheckResult(
                            name="reference_distribution_shift",
                            domain="context_compatibility",
                            status="WARN",
                            severity="MEDIUM",
                            message=f"Substantial covariate distribution shift detected (max normalized delta: {max_shift:.2f} standard deviations).",
                            details={"shifts": shifts, "reference_version": ref_ver.version_label},
                        )
                    )
                else:
                    checks.append(
                        QualityCheckResult(
                            name="reference_distribution_shift",
                            domain="context_compatibility",
                            status="PASS",
                            severity="INFO",
                            message=f"Covariate distributions consistent with reference dataset version {ref_ver.version_label}.",
                            details={"reference_version": ref_ver.version_label, "features_compared": len(common_num)},
                        )
                    )
            except Exception as e:
                checks.append(
                    QualityCheckResult(
                        name="reference_distribution_shift",
                        domain="context_compatibility",
                        status="UNVERIFIABLE",
                        severity="LOW",
                        message=f"Failed to compute shift against reference version: {str(e)}",
                        details={"error": str(e)},
                    )
                )
    else:
        checks.append(
            QualityCheckResult(
                name="reference_distribution_shift",
                domain="context_compatibility",
                status="NOT_APPLICABLE",
                severity="INFO",
                message="No reference dataset version specified; distribution shift check is not applicable.",
                details={},
            )
        )
        limitations.append("No reference dataset version provided; longitudinal distribution shift was not evaluated.")

    return _summarize_domain("context_compatibility", "Context & Pipeline Compatibility", checks), limitations


def _summarize_domain(domain_key: str, display_name: str, checks: list[QualityCheckResult]) -> QualityDomainResult:
    total = len(checks)
    passed = sum(1 for c in checks if c.status == "PASS")
    warnings = sum(1 for c in checks if c.status == "WARN")
    failed = sum(1 for c in checks if c.status == "FAIL")
    na = sum(1 for c in checks if c.status == "NOT_APPLICABLE")
    unverifiable = sum(1 for c in checks if c.status == "UNVERIFIABLE")

    if failed > 0:
        status: CheckStatus = "FAIL"
    elif warnings > 0:
        status = "WARN"
    elif unverifiable > 0 and passed == 0:
        status = "UNVERIFIABLE"
    else:
        status = "PASS"

    summary_msg = f"{passed}/{total} passed"
    if failed:
        summary_msg += f", {failed} failed"
    if warnings:
        summary_msg += f", {warnings} warnings"
    if na:
        summary_msg += f", {na} N/A"

    return QualityDomainResult(
        domain=domain_key,
        display_name=display_name,
        status=status,
        total_checks=total,
        passed_checks=passed,
        warning_checks=warnings,
        failed_checks=failed,
        not_applicable_checks=na,
        unverifiable_checks=unverifiable,
        checks=checks,
        summary=summary_msg,
    )


def _compute_scorecard_summary(domains: dict[str, QualityDomainResult]) -> ScorecardSummary:
    total_checks = sum(d.total_checks for d in domains.values())
    passed = sum(d.passed_checks for d in domains.values())
    warnings = sum(d.warning_checks for d in domains.values())
    failed = sum(d.failed_checks for d in domains.values())
    na = sum(d.not_applicable_checks for d in domains.values())
    unverifiable = sum(d.unverifiable_checks for d in domains.values())

    critical_failures = 0
    high_failures = 0

    for d in domains.values():
        for c in d.checks:
            if c.status == "FAIL":
                if c.severity == "CRITICAL":
                    critical_failures += 1
                elif c.severity == "HIGH":
                    high_failures += 1

    if critical_failures > 0 or high_failures > 0:
        overall_status: CheckStatus = "FAIL"
    elif failed > 0 or warnings > 0:
        overall_status = "WARN"
    else:
        overall_status = "PASS"

    # Score calculation (100 base, deductions for failures and warnings)
    penalty = 0.0
    for d in domains.values():
        for c in d.checks:
            if c.status == "FAIL":
                if c.severity == "CRITICAL":
                    penalty += 30.0
                elif c.severity == "HIGH":
                    penalty += 15.0
                else:
                    penalty += 8.0
            elif c.status == "WARN":
                if c.severity in ("CRITICAL", "HIGH"):
                    penalty += 10.0
                elif c.severity == "MEDIUM":
                    penalty += 5.0
                else:
                    penalty += 2.0

    quality_score = max(0.0, min(100.0, round(100.0 - penalty, 2)))
    domain_scores = {k: d.status for k, d in domains.items()}

    return ScorecardSummary(
        overall_status=overall_status,
        total_checks=total_checks,
        passed=passed,
        warnings=warnings,
        failed=failed,
        not_applicable=na,
        unverifiable=unverifiable,
        critical_failures=critical_failures,
        high_failures=high_failures,
        quality_score=quality_score,
        domain_scores=domain_scores,
    )


def preflight_dataset_quality(
    session,
    dataset_id: str,
    request: DatasetQualityRequest,
) -> DatasetQualityPreflightResponse:
    dataset = require(session, Dataset, dataset_id)
    version = resolve_version(session, dataset, version_id=request.dataset_version_id)
    content, content_sha = _load_raw_dataset_bytes(session, dataset, version)

    context = {
        "experiment_id": request.experiment_id,
        "protocol_version_id": request.protocol_version_id,
        "pipeline_version_id": request.pipeline_version_id,
        "reference_dataset_version_id": request.reference_dataset_version_id,
        "subgroup_field": request.subgroup_field,
        "target_column": request.target_column,
        "positive_label": request.positive_label,
        "negative_label": request.negative_label,
    }
    expected_fp = compute_assessment_fingerprint(
        dataset.id,
        version.id if version else None,
        content_sha,
        request.thresholds,
        context,
    )

    domains_planned = [
        "schema_integrity",
        "completeness",
        "duplicate_integrity",
        "target_integrity",
        "feature_health",
        "class_balance",
        "data_leakage",
        "sensitive_fields",
        "context_compatibility",
    ]

    reasons = []
    ready = True
    if len(content) == 0:
        ready = False
        reasons.append("Dataset file is empty (0 bytes).")

    return DatasetQualityPreflightResponse(
        dataset_id=dataset.id,
        dataset_version_id=version.id if version else None,
        dataset_name=dataset.name,
        dataset_hash=content_sha,
        expected_fingerprint=expected_fp,
        checks_planned=22,
        domains_planned=domains_planned,
        context=context,
        ready_to_assess=ready,
        reasons=reasons,
    )


def assess_dataset_quality(
    session,
    dataset_id: str,
    request: DatasetQualityRequest,
) -> DatasetQualityScorecard:
    dataset = require(session, Dataset, dataset_id)
    version = resolve_version(session, dataset, version_id=request.dataset_version_id)
    content, content_sha = _load_raw_dataset_bytes(session, dataset, version)

    target_name = (
        request.target_column
        or (version.target if version else None)
        or dataset.provenance.get("target")
        or dataset.quality.get("target")
    )
    pos_label = (
        request.positive_label
        or (version.positive_label if version else None)
        or dataset.provenance.get("positive_label")
    )
    neg_label = (
        request.negative_label
        or (version.negative_label if version else None)
        or dataset.provenance.get("negative_label")
    )

    context = {
        "experiment_id": request.experiment_id,
        "protocol_version_id": request.protocol_version_id,
        "pipeline_version_id": request.pipeline_version_id,
        "reference_dataset_version_id": request.reference_dataset_version_id,
        "subgroup_field": request.subgroup_field,
        "target_column": request.target_column,
        "positive_label": request.positive_label,
        "negative_label": request.negative_label,
    }

    fp = compute_assessment_fingerprint(
        dataset.id,
        version.id if version else None,
        content_sha,
        request.thresholds,
        context,
    )
    op_key = request.operation_key or f"dataset-quality:{fp}"

    # Idempotent return if already computed
    existing = session.scalar(
        select(DatasetQualityScorecard).where(DatasetQualityScorecard.operation_key == op_key)
    )
    if existing is not None:
        return existing

    # Record start in scientific audit timeline
    from ..audit.service import record_event
    record_event(
        session,
        event_type="DATASET_QUALITY_ASSESSMENT_STARTED",
        event_category="DATASET",
        object_type="dataset",
        object_id=dataset.id,
        parent_object_type="dataset_version" if version else None,
        parent_object_id=version.id if version else None,
        source_component="data_quality_service",
        operation_key=f"start:{op_key}",
        metadata={"fingerprint": fp, "context": context},
    )

    frame, _ = _read_csv_table(content, target_hint=target_name)

    # Run check suites across all domains
    domain_schema = _check_schema_integrity(frame, target_name)
    domain_completeness = _check_completeness(frame, request.thresholds)
    domain_duplicates = _check_duplicate_integrity(frame, request.thresholds)
    domain_target = _check_target_integrity(frame, target_name, pos_label, neg_label)
    domain_features = _check_feature_health(frame, target_name, request.thresholds)
    domain_balance = _check_class_balance(frame, target_name, request.thresholds)
    domain_leakage = _check_data_leakage(frame, target_name, request.thresholds)
    domain_sensitive = _check_sensitive_fields(frame, dataset.provenance)
    domain_context, context_limitations = _check_context_compatibility(
        session,
        frame,
        target_name,
        request.protocol_version_id,
        request.pipeline_version_id,
        request.subgroup_field,
        request.reference_dataset_version_id,
    )

    domains = {
        "schema_integrity": domain_schema,
        "completeness": domain_completeness,
        "duplicate_integrity": domain_duplicates,
        "target_integrity": domain_target,
        "feature_health": domain_features,
        "class_balance": domain_balance,
        "data_leakage": domain_leakage,
        "sensitive_fields": domain_sensitive,
        "context_compatibility": domain_context,
    }

    summary = _compute_scorecard_summary(domains)
    schema_snapshot = _build_schema_snapshot(frame, target_name)

    limitations = [
        "Assessment reflects concrete checks against this dataset version and does not imply clinical safety or regulatory validity.",
        "Outlier and missingness checks are observational and do not perform automated or silent data repair.",
        *context_limitations,
    ]

    provenance_data = {
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "dataset_version_id": version.id if version else None,
        "version_number": version.version_number if version else None,
        "version_label": version.version_label if version else None,
        "content_sha256": content_sha,
        "assessed_at": utcnow().isoformat(),
        "evaluator_engine": "EntangleX Q-Health Advanced Data Quality Suite v1",
    }

    scorecard_id = str(uuid4())

    scorecard = DatasetQualityScorecard(
        id=scorecard_id,
        schema_version=SCORECARD_SCHEMA_VERSION,
        dataset_id=dataset.id,
        dataset_version_id=version.id if version else None,
        experiment_id=request.experiment_id,
        protocol_version_id=request.protocol_version_id,
        pipeline_version_id=request.pipeline_version_id,
        status=summary.overall_status,
        operation_key=op_key,
        assessment_fingerprint=fp,
        configuration=clean_json(request.thresholds),
        summary=summary.model_dump(mode="json"),
        domains={k: v.model_dump(mode="json") for k, v in domains.items()},
        schema_snapshot=schema_snapshot.model_dump(mode="json"),
        limitations=limitations,
        provenance=provenance_data,
        artifact_id=None,
        created_at=utcnow(),
        completed_at=utcnow(),
    )
    session.add(scorecard)
    session.flush()

    # Register artifact
    artifact_id = _register_scorecard_artifacts(session, scorecard)
    scorecard.artifact_id = artifact_id
    session.flush()

    # Record completion in audit timeline
    record_event(
        session,
        event_type="DATASET_QUALITY_ASSESSMENT_COMPLETED",
        event_category="DATASET",
        object_type="dataset_quality_scorecard",
        object_id=scorecard.id,
        parent_object_type="dataset",
        parent_object_id=dataset.id,
        source_component="data_quality_service",
        operation_key=f"completed:{op_key}",
        metadata={
            "status": scorecard.status,
            "quality_score": summary.quality_score,
            "fingerprint": fp,
            "artifact_id": artifact_id,
        },
    )

    return scorecard


def _register_scorecard_artifacts(session, scorecard: DatasetQualityScorecard) -> str:
    """Store scorecard JSON payload as an immutable research artifact."""
    payload = _to_scorecard_out(scorecard).model_dump(mode="json")
    artifact = register_metadata(
        session,
        experiment_id=scorecard.experiment_id,
        run_id=None,
        model_id=None,
        artifact_type=ARTIFACT_TYPE,
        name=f"Dataset Quality Scorecard {scorecard.id}",
        description=f"Structured quality scorecard for dataset {scorecard.dataset_id} (version {scorecard.dataset_version_id}).",
        payload=payload,
        operation_key=f"dataset-quality-artifact:{scorecard.id}",
    )
    return artifact.id


def get_scorecard(session, scorecard_id: str) -> DatasetQualityScorecard:
    return require(session, DatasetQualityScorecard, scorecard_id)


def list_scorecards(
    session,
    dataset_id: str,
    dataset_version_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[DatasetQualityScorecard]:
    stmt = select(DatasetQualityScorecard).where(DatasetQualityScorecard.dataset_id == dataset_id)
    if dataset_version_id:
        stmt = stmt.where(DatasetQualityScorecard.dataset_version_id == dataset_version_id)
    if status:
        stmt = stmt.where(DatasetQualityScorecard.status == status)
    stmt = stmt.order_by(DatasetQualityScorecard.created_at.desc(), DatasetQualityScorecard.id.desc()).offset(offset).limit(limit)
    return list(session.scalars(stmt))


def get_latest_scorecard(
    session,
    dataset_id: str,
    dataset_version_id: str | None = None,
) -> DatasetQualityScorecard | None:
    stmt = select(DatasetQualityScorecard).where(DatasetQualityScorecard.dataset_id == dataset_id)
    if dataset_version_id:
        stmt = stmt.where(DatasetQualityScorecard.dataset_version_id == dataset_version_id)
    stmt = stmt.order_by(DatasetQualityScorecard.created_at.desc(), DatasetQualityScorecard.id.desc()).limit(1)
    return session.scalar(stmt)


def compare_scorecards(
    session,
    base_scorecard_id: str,
    target_scorecard_id: str,
) -> ScorecardComparisonOut:
    base = get_scorecard(session, base_scorecard_id)
    target = get_scorecard(session, target_scorecard_id)

    base_summary = base.summary or {}
    target_summary = target.summary or {}

    status_delta = {
        "base_status": base.status,
        "target_status": target.status,
        "changed": base.status != target.status,
    }

    summary_delta = {
        "score_delta": round(float(target_summary.get("quality_score", 0.0) - base_summary.get("quality_score", 0.0)), 2),
        "passed_delta": int(target_summary.get("passed", 0) - base_summary.get("passed", 0)),
        "warnings_delta": int(target_summary.get("warnings", 0) - base_summary.get("warnings", 0)),
        "failed_delta": int(target_summary.get("failed", 0) - base_summary.get("failed", 0)),
    }

    # Compare check by check
    base_checks: dict[str, dict[str, Any]] = {}
    for d in (base.domains or {}).values():
        for c in d.get("checks", []):
            base_checks[f"{c['domain']}:{c['name']}"] = c

    target_checks: dict[str, dict[str, Any]] = {}
    for d in (target.domains or {}).values():
        for c in d.get("checks", []):
            target_checks[f"{c['domain']}:{c['name']}"] = c

    new_failures: list[QualityCheckResult] = []
    resolved_failures: list[QualityCheckResult] = []
    new_warnings: list[QualityCheckResult] = []
    resolved_warnings: list[QualityCheckResult] = []

    for k, tc in target_checks.items():
        bc = base_checks.get(k)
        if tc["status"] == "FAIL" and (bc is None or bc["status"] != "FAIL"):
            new_failures.append(QualityCheckResult.model_validate(tc))
        if tc["status"] == "WARN" and (bc is None or bc["status"] == "PASS"):
            new_warnings.append(QualityCheckResult.model_validate(tc))

    for k, bc in base_checks.items():
        tc = target_checks.get(k)
        if bc["status"] == "FAIL" and (tc is None or tc["status"] != "FAIL"):
            resolved_failures.append(QualityCheckResult.model_validate(bc))
        if bc["status"] == "WARN" and (tc is not None and tc["status"] == "PASS"):
            resolved_warnings.append(QualityCheckResult.model_validate(bc))

    # Metric changes
    metric_changes = []
    base_rows = base.schema_snapshot.get("total_rows", 0) if base.schema_snapshot else 0
    target_rows = target.schema_snapshot.get("total_rows", 0) if target.schema_snapshot else 0
    if base_rows != target_rows:
        metric_changes.append({"metric": "total_rows", "base": base_rows, "target": target_rows, "delta": target_rows - base_rows})

    return ScorecardComparisonOut(
        base_scorecard_id=base.id,
        target_scorecard_id=target.id,
        base_fingerprint=base.assessment_fingerprint,
        target_fingerprint=target.assessment_fingerprint,
        status_delta=status_delta,
        summary_delta=summary_delta,
        new_warnings=new_warnings,
        resolved_warnings=resolved_warnings,
        new_failures=new_failures,
        resolved_failures=resolved_failures,
        metric_changes=metric_changes,
    )


def export_scorecard_markdown(scorecard: DatasetQualityScorecard) -> str:
    out = _to_scorecard_out(scorecard)
    lines = [
        f"# EntangleX Q-Health Dataset Quality Scorecard",
        f"**Scorecard ID:** `{out.id}`  ",
        f"**Assessment Status:** `{out.status}`  ",
        f"**Quality Score:** `{out.summary.quality_score}/100`  ",
        f"**Assessment Fingerprint:** `{out.assessment_fingerprint}`  ",
        f"**Dataset ID:** `{out.dataset_id}`  ",
        f"**Dataset Version ID:** `{out.dataset_version_id or 'None'}`  ",
        f"**Evaluated At:** {out.created_at.isoformat()}  ",
        "",
        "## Domain Summaries",
        "| Domain | Status | Passed | Warnings | Failed | Summary |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for d_key, d in out.domains.items():
        lines.append(f"| {d.display_name} | `{d.status}` | {d.passed_checks} | {d.warning_checks} | {d.failed_checks} | {d.summary} |")

    lines.extend([
        "",
        "## Detailed Checks",
    ])
    for d_key, d in out.domains.items():
        lines.append(f"### {d.display_name}")
        for c in d.checks:
            lines.append(f"- **{c.name}** [`{c.status}` / Severity: `{c.severity}`]: {c.message}")
            if c.recommendation:
                lines.append(f"  *Recommendation:* {c.recommendation}")

    lines.extend([
        "",
        "## Limitations & Scientific Boundary",
    ])
    for lim in out.limitations:
        lines.append(f"- {lim}")

    return "\n".join(lines)


def _to_scorecard_out(sc: DatasetQualityScorecard) -> DatasetQualityScorecardOut:
    return DatasetQualityScorecardOut(
        id=sc.id,
        schema_version=sc.schema_version,
        dataset_id=sc.dataset_id,
        dataset_version_id=sc.dataset_version_id,
        experiment_id=sc.experiment_id,
        protocol_version_id=sc.protocol_version_id,
        pipeline_version_id=sc.pipeline_version_id,
        status=sc.status,
        operation_key=sc.operation_key,
        assessment_fingerprint=sc.assessment_fingerprint,
        configuration=sc.configuration or {},
        summary=ScorecardSummary.model_validate(sc.summary or {}),
        domains={k: QualityDomainResult.model_validate(v) for k, v in (sc.domains or {}).items()},
        schema_snapshot=SchemaSnapshot.model_validate(sc.schema_snapshot or {}),
        limitations=sc.limitations or [],
        provenance=sc.provenance or {},
        artifact_id=sc.artifact_id,
        created_at=sc.created_at,
        completed_at=sc.completed_at,
    )
