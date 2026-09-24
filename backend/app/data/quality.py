from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from ..utils.errors import AppError
from ..utils.serialization import clean_json

IDENTIFIER_NAMES = {"id", "name", "patient", "patient_id", "patient_name", "sample_id", "record_id", "mrn", "medical_record_number", "email", "phone", "address", "aadhaar", "ssn"}
TARGET_NAME_HINTS = {
    "target", "label", "class", "outcome", "diagnosis", "condition", "disease", "status",
    "response", "result", "readmitted", "readmitted_30d", "heart_disease", "diabetes",
}


def is_identifier(name: str) -> bool:
    normalized = re.sub(r"[ -]+", "_", name.strip().lower())
    return normalized in IDENTIFIER_NAMES or normalized.endswith(("_email", "_phone", "_mrn"))


def _column_groups(frame: pd.DataFrame) -> dict[str, list[str]]:
    numeric = list(frame.select_dtypes(include=np.number).columns)
    boolean = [c for c in frame.columns if pd.api.types.is_bool_dtype(frame[c])]
    datetime_like: list[str] = []
    unsupported: list[str] = []
    categorical: list[str] = []
    for col in frame.columns:
        series = frame[col]
        if col in numeric or col in boolean:
            continue
        if pd.api.types.is_datetime64_any_dtype(series):
            datetime_like.append(col)
            continue
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series) or pd.api.types.is_categorical_dtype(series):
            sample = series.dropna().head(32)
            if any(isinstance(value, (list, dict, set, tuple, bytes, bytearray, complex)) for value in sample):
                unsupported.append(col)
            elif _looks_datetime_like(series):
                datetime_like.append(col)
            else:
                categorical.append(col)
            continue
        if pd.api.types.is_timedelta64_dtype(series) or pd.api.types.is_complex_dtype(series):
            unsupported.append(col)
        else:
            categorical.append(col)
    return {"numeric": numeric, "categorical": categorical, "boolean": boolean, "datetime_like": datetime_like, "unsupported": unsupported}


def _looks_datetime_like(series: pd.Series) -> bool:
    values = series.dropna()
    if values.empty or pd.api.types.is_numeric_dtype(values):
        return False
    sample = values.astype(str).head(100)
    parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    return len(sample) >= 8 and float(parsed.notna().mean()) >= 0.95


def _safe_nunique(series: pd.Series) -> int:
    try:
        return int(series.nunique(dropna=True))
    except TypeError:
        return int(series.map(repr).nunique(dropna=True))


def _safe_distribution(series: pd.Series) -> dict[str, int]:
    values = series.astype("string").fillna("<missing>")
    return {str(k): int(v) for k, v in values.value_counts(dropna=False).head(20).items()}


def _target_candidates(frame: pd.DataFrame, groups: dict[str, list[str]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for column in frame.columns:
        if is_identifier(str(column)):
            continue
        series = frame[column]
        distinct = _safe_nunique(series)
        if distinct < 1 or distinct > 10:
            continue
        if groups["datetime_like"] and column in groups["datetime_like"]:
            continue
        if column in groups["unsupported"]:
            continue
        if distinct == 1:
            reasons = ["low-cardinality column"]
        else:
            reasons = ["low-cardinality column"]
        normalized = re.sub(r"[^a-z0-9]+", "_", str(column).lower()).strip("_")
        score = 0.45
        if normalized in TARGET_NAME_HINTS or any(token in normalized.split("_") for token in TARGET_NAME_HINTS):
            score += 0.4
            reasons.insert(0, "target-like column name")
        if distinct == 2:
            score += 0.15
            reasons.append("binary observed classes")
        candidates.append({
            "column": str(column),
            "confidence": round(min(score, 0.99), 2),
            "reasons": reasons,
            "class_count": distinct,
            "class_distribution": _safe_distribution(series),
        })
    return sorted(candidates, key=lambda item: (-item["confidence"], item["column"]))


def validate_target(frame: pd.DataFrame, target: str, positive_label: str, features: list[str] | None = None) -> list[str]:
    if target not in frame:
        raise AppError("target_missing", "The target column is absent.")
    if frame[target].isna().any() or (frame[target].astype(str).str.strip() == "").any():
        raise AppError("target_missing_values", "Target values must not be missing.")
    labels = sorted(frame[target].astype(str).unique().tolist())
    if len(labels) != 2:
        raise AppError("binary_target_required", "This MVP requires exactly two observed target classes.")
    if any(len(label) > 64 or any(ord(c) < 32 for c in label) for label in labels):
        raise AppError("target_invalid", "Target labels are invalid.")
    if positive_label not in labels:
        raise AppError("positive_label_unknown", "The configured positive label is not present in the target.")
    if features is not None:
        if target in features:
            raise AppError("target_leakage", "The target must never be included as an input feature.")
        if not features or len(set(features)) != len(features) or any(f not in frame for f in features):
            raise AppError("feature_schema", "Choose a nonempty, unique list of existing input features.")
    return labels


def inspection_report(frame: pd.DataFrame, target: str | None = None, positive_label: str | None = None) -> dict:
    groups = _column_groups(frame)
    feature_names = [str(c) for c in frame.columns if c != target]
    numeric = [c for c in groups["numeric"] if c != target]
    categorical = [c for c in groups["categorical"] if c != target]
    boolean = [c for c in groups["boolean"] if c != target]
    datetime_like = [c for c in groups["datetime_like"] if c != target]
    unsupported = [c for c in groups["unsupported"] if c != target]
    features = frame[feature_names] if feature_names else frame.iloc[:, 0:0]
    missing = {str(c): int(frame[c].isna().sum()) for c in frame.columns}
    infinity = {str(c): int(np.isinf(frame[c].to_numpy(dtype=float)).sum()) for c in numeric if pd.api.types.is_numeric_dtype(frame[c])}
    constants = [str(c) for c in feature_names if _safe_nunique(frame[c]) <= 1]
    low_variance = [str(c) for c in numeric if float(frame[c].replace([np.inf, -np.inf], np.nan).var()) < 1e-8]
    high_cardinality = [str(c) for c in categorical if _safe_nunique(frame[c]) > 32]
    identifier_features = [str(c) for c in feature_names if is_identifier(str(c))]
    empty_columns = [str(c) for c in frame.columns if frame[c].isna().all()]
    duplicate_rows = int(frame.duplicated().sum())
    duplicate_feature_rows = int(features.duplicated().sum()) if feature_names else duplicate_rows
    target_candidates = _target_candidates(frame, groups)
    selected_target = None
    target_classes: list[str] = []
    class_distribution: dict[str, int] = {}
    if target and target in frame:
        target_values = frame[target].astype("string")
        target_classes = sorted(target_values.dropna().unique().tolist())
        class_distribution = _safe_distribution(frame[target])
        selected_target = target
    report = {
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "column_names": [str(c) for c in frame.columns],
        "numeric_columns": numeric,
        "categorical_columns": categorical,
        "boolean_columns": boolean,
        "datetime_like_columns": datetime_like,
        "unsupported_columns": unsupported,
        "missing_values": missing,
        "infinite_values": infinity,
        "duplicate_rows": duplicate_rows,
        "duplicate_feature_rows": duplicate_feature_rows,
        "constant_features": constants,
        "low_variance_features": low_variance,
        "high_cardinality_categorical_features": high_cardinality,
        "identifier_like_columns": identifier_features,
        "empty_columns": empty_columns,
        "possible_target_columns": [item["column"] for item in target_candidates],
        "target_candidates": target_candidates,
        "target": selected_target,
        "target_classes": target_classes,
        "class_distribution": class_distribution,
        "schema_consistent": True,
        "suspicious_target_proxy_columns": [],
        "transformations_applied": [],
    }
    if target and target in frame and positive_label is not None:
        report["compatibility"] = compatibility_report(frame, target, positive_label)
    else:
        report["compatibility"] = compatibility_report(frame, None, None)
    return clean_json(report)


def compatibility_report(frame: pd.DataFrame, target: str | None, positive_label: str | None) -> dict:
    groups = _column_groups(frame)
    checks: list[dict[str, str]] = []
    blockers: list[str] = []
    warnings: list[str] = []
    def add(code: str, status: str, message: str) -> None:
        checks.append({"code": code, "status": status, "message": message})
        (blockers if status == "BLOCKED" else warnings if status == "WARNING" else []).append(message)

    add("file_format", "PASS", "Tabular file format was parsed by a supported reader.")
    add("schema", "PASS", "Rows and columns form a consistent table.")
    if target is None:
        add("target_selection", "BLOCKED", "Select a target column before registration. Q-Health currently supports binary classification in this research workflow.")
    elif target not in frame:
        add("target_present", "BLOCKED", "The selected target column is not present in the parsed table.")
    else:
        add("target_present", "PASS", "Selected target column is present.")
        values = frame[target]
        if values.isna().any() or (values.astype(str).str.strip() == "").any():
            add("target_missing_values", "BLOCKED", "Target values are missing; fill or correct them at the source before registration.")
        labels = sorted(values.astype(str).dropna().unique().tolist())
        if len(labels) != 2:
            add("binary_target", "BLOCKED", "Q-Health currently supports binary classification in this research workflow; the selected target does not contain exactly two observed classes.")
        else:
            add("binary_target", "PASS", "Target contains exactly two observed classes.")
            if positive_label not in labels:
                add("positive_label", "BLOCKED", "The selected positive class is not present in the target.")
            else:
                add("positive_label", "PASS", "Selected positive class is present; the other observed class is retained as negative.")
    features = [c for c in frame.columns if c != target]
    if not features:
        add("features", "BLOCKED", "At least one input feature is required.")
    else:
        add("features", "PASS", "Input features were detected.")
    if groups["numeric"]:
        add("numeric_features", "PASS", f"{len([c for c in groups['numeric'] if c != target])} numeric feature(s) detected.")
    else:
        add("numeric_features", "WARNING", "No numeric features were detected; training will rely on categorical encoding only.")
    if groups["categorical"] or groups["boolean"]:
        add("categorical_features", "PASS", "Categorical and boolean features can use the existing encoding path.")
    else:
        add("categorical_features", "PASS", "No categorical features detected.")
    missing_features = sum(int(frame[c].isna().sum()) for c in features)
    add("missing_features", "PASS", "Missing feature values can be handled by the existing training imputer." if missing_features else "No missing feature values detected.")
    if any(count for count in {c: int(np.isinf(frame[c].to_numpy(dtype=float)).sum()) for c in groups["numeric"]}.values()):
        add("infinite_values", "BLOCKED", "Infinite numeric values must be corrected at the source before training.")
    else:
        add("infinite_values", "PASS", "No infinite numeric values detected.")
    if groups["datetime_like"]:
        add("datetime_columns", "BLOCKED", "Datetime-like columns are not automatically converted; remove or explicitly represent them before registration.")
    if groups["unsupported"]:
        add("unsupported_types", "BLOCKED", "Unsupported complex column types were detected; upload scalar tabular values only.")
    if any(is_identifier(str(c)) for c in features):
        add("identifier_columns", "WARNING", "Identifier-like columns were detected. Review and exclude them before training.")
    else:
        add("identifier_columns", "PASS", "No obvious identifier-like columns detected.")
    if any(_safe_nunique(frame[c]) > 32 for c in groups["categorical"]):
        add("high_cardinality", "WARNING", "High-cardinality categorical columns require review before encoding.")
    if len(frame) < 1000:
        add("sample_size", "WARNING", "This is a small research benchmark; compatibility does not establish clinical validity or generalization.")
    status = "BLOCKED" if blockers else "WARNING" if warnings else "READY"
    return clean_json({"status": status, "checks": checks, "blockers": blockers, "warnings": warnings})


def quality_report(frame: pd.DataFrame, target: str, positive_label: str, features: list[str] | None = None) -> dict:
    labels = validate_target(frame, target, positive_label, features)
    features = features if features is not None else [c for c in frame if c != target]
    X = frame[features]
    groups = _column_groups(X)
    numeric = list(X.select_dtypes(include=np.number).columns)
    categorical = [c for c in features if c not in numeric]
    target_str = frame[target].astype(str)
    counts = target_str.value_counts().to_dict()
    minority_fraction = min(counts.values()) / len(frame)
    warnings: list[str] = []
    blockers: list[str] = []
    infinity = {c: int(np.isinf(X[c].to_numpy(dtype=float)).sum()) for c in numeric}
    constants = [c for c in X if X[c].nunique(dropna=True) <= 1]
    low_variance = [c for c in numeric if float(X[c].replace([np.inf, -np.inf], np.nan).var()) < 1e-8]
    suspect_identifiers = [c for c in features if is_identifier(c)]
    high_cardinality = [c for c in categorical if X[c].nunique(dropna=True) > 32]
    suspicious = []
    for c in features:
        nonmissing = X[c].notna()
        if nonmissing.sum() < 4:
            continue
        if X[c].astype(str).equals(target_str):
            suspicious.append(c)
        elif c in numeric:
            values = X[c].replace([np.inf, -np.inf], np.nan)
            if values.nunique(dropna=True) > 1:
                correlation = values.corr((target_str == positive_label).astype(int))
                if pd.notna(correlation) and abs(correlation) > 0.9999:
                    suspicious.append(c)
    finite = X[numeric].replace([np.inf, -np.inf], np.nan)
    correlations = []
    if len(numeric) > 1:
        corr = finite.corr().abs()
        for i, a in enumerate(numeric):
            for b in numeric[i + 1:]:
                if pd.notna(corr.loc[a, b]) and corr.loc[a, b] >= 0.95:
                    correlations.append({"feature_a": a, "feature_b": b, "absolute_correlation": float(corr.loc[a, b])})
    distributions = []
    for name in numeric:
        values = finite[name].dropna().to_numpy(dtype=float)
        entry = {"feature": name, "type": "numeric", "valid_count": len(values)}
        if len(values):
            counts_hist, edges = np.histogram(values, bins=min(10, max(1, len(np.unique(values)))))
            entry.update({"min": float(values.min()), "max": float(values.max()), "mean": float(values.mean()), "std": float(values.std()), "histogram": {"counts": counts_hist.tolist(), "edges": edges.tolist()}})
        distributions.append(entry)
    for name in categorical:
        distributions.append({"feature": name, "type": "categorical", "distinct_count": int(X[name].nunique(dropna=True))})
    duplicates = int(frame.duplicated().sum())
    feature_duplicates = int(X.duplicated().sum())
    row_hashes = pd.util.hash_pandas_object(X, index=False)
    conflicting = int(pd.DataFrame({"hash": row_hashes, "target": target_str}).groupby("hash")["target"].nunique().gt(1).sum())
    if minority_fraction < 0.2:
        warnings.append("Class imbalance: the minority class represents less than 20% of samples.")
    if len(frame) < 1000:
        warnings.append("Small benchmark: performance cannot establish clinical effectiveness or population generalization.")
    if duplicates:
        warnings.append("Exact duplicates exist. Reject them or explicitly drop duplicates before splitting.")
    if constants:
        warnings.append("Constant/all-missing features exist. Review or remove them before training.")
    if high_cardinality:
        warnings.append("High-cardinality categorical features require review; encoding caps retained categories at 32 per feature.")
    if suspect_identifiers:
        blockers.append("Potential identifier columns must be excluded from model inputs.")
    if suspicious:
        blockers.append("Near-perfect target proxy features require source review and exclusion before training.")
    if conflicting:
        blockers.append("Identical feature records with conflicting targets are not allowed.")
    if any(infinity.values()):
        blockers.append("Infinite numeric values must be corrected at the source before training.")
    if groups["datetime_like"]:
        blockers.append("Datetime-like columns are unsupported until explicitly represented.")
    if groups["unsupported"]:
        blockers.append("Unsupported complex column types were detected.")
    if feature_duplicates > duplicates:
        warnings.append("Duplicated selected features may cause leakage. Training checks and rejects residual duplicated feature vectors.")
    return clean_json({
        "scope": "Aggregate source-data quality; not a fitted model or clinical assessment.",
        "row_count": len(frame), "feature_count": len(features), "target": target,
        "target_classes": labels, "positive_label": positive_label, "class_distribution": counts,
        "minority_fraction": minority_fraction, "class_imbalance": minority_fraction < 0.2,
        "numeric_features": numeric, "categorical_features": categorical,
        "missing_values": {c: int(X[c].isna().sum()) for c in features},
        "duplicate_rows": duplicates, "duplicate_feature_rows": feature_duplicates,
        "conflicting_feature_groups": conflicting, "infinite_values": infinity,
        "constant_features": constants, "low_variance_features": low_variance,
        "highly_correlated_pairs": correlations[:300], "correlation_pairs_truncated": len(correlations) > 300,
        "suspiciously_predictive_features": suspicious, "identifier_features": suspect_identifiers,
        "high_cardinality_features": high_cardinality, "distributions": distributions,
        "warnings": warnings, "blockers": blockers, "eligible_after_review": not blockers,
        "invalid_numeric_values": "Numeric coercion is rejected at prediction. Mixed-type columns are reported as categorical for explicit review.",
        "schema_consistent": True,
    })
