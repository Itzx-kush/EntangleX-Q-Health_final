import re
import numpy as np
import pandas as pd
from ..utils.errors import AppError
from ..utils.serialization import clean_json

IDENTIFIER_NAMES = {"id", "name", "patient", "patient_id", "patient_name", "sample_id", "record_id", "mrn", "medical_record_number", "email", "phone", "address", "aadhaar", "ssn"}

def is_identifier(name: str) -> bool:
    normalized = re.sub(r"[ -]+", "_", name.strip().lower())
    return normalized in IDENTIFIER_NAMES or normalized.endswith(("_email", "_phone", "_mrn"))

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

def quality_report(frame: pd.DataFrame, target: str, positive_label: str, features: list[str] | None = None) -> dict:
    labels = validate_target(frame, target, positive_label, features)
    features = features if features is not None else [c for c in frame if c != target]
    X = frame[features]
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
    target_codes = (target_str == positive_label).astype(int)
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
                correlation = values.corr(target_codes)
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
    # Do not expose category values, which could contain identifiers.
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
        "invalid_numeric_values": "Numeric coercion is rejected at prediction. At CSV upload, mixed-type columns are reported as categorical for explicit review.",
        "schema_consistent": True,
    })
