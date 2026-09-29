"""Deterministic, explainable target-column ranking for tabular datasets."""
from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from .quality import is_identifier

TARGET_NAMES = {
    "target", "label", "class", "outcome", "diagnosis", "disease", "result",
    "status", "response", "condition",
}
POSITIVE_LABELS = {
    "1", "true", "yes", "positive", "pos", "present", "disease", "diseased",
    "malignant", "affected", "ckd", "diabetic",
}
NEGATIVE_LABELS = {
    "0", "false", "no", "negative", "neg", "absent", "healthy", "benign",
    "unaffected", "not_ckd", "non_diabetic",
}


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _timestamp_like(name: str, series: pd.Series) -> bool:
    normalized = _normalized(name)
    if any(token in normalized.split("_") for token in ("date", "time", "timestamp", "datetime")):
        return True
    values = series.dropna()
    if len(values) < 10 or pd.api.types.is_numeric_dtype(series):
        return False
    sample = values.astype(str).head(100)
    if sample.str.contains(r"[-/:T]", regex=True).mean() < 0.8:
        return False
    parsed = pd.to_datetime(sample, errors="coerce", utc=True)
    return bool(parsed.notna().mean() >= 0.9)


def _class_metadata(series: pd.Series) -> tuple[list[str], dict[str, int]]:
    values = series.dropna().astype(str).map(str.strip)
    distribution = {str(k): int(v) for k, v in values.value_counts().items()}
    return sorted(distribution), distribution


def _target_type(series: pd.Series, unique: int) -> str:
    if unique == 2:
        return "binary_classification"
    if 3 <= unique <= 10:
        return "multiclass_classification"
    if pd.api.types.is_numeric_dtype(series):
        return "continuous"
    return "high_cardinality"


def rank_target_candidates(frame: pd.DataFrame) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    rows = max(1, len(frame))
    for position, column in enumerate(frame.columns):
        series = frame[column]
        name = _normalized(column)
        tokens = set(name.split("_"))
        nonmissing = series.dropna()
        unique = int(nonmissing.astype(str).nunique())
        unique_ratio = unique / max(1, len(nonmissing))
        missing_fraction = 1 - len(nonmissing) / rows
        reasons: list[str] = []
        penalties: list[str] = []
        score = 0.10

        if name in TARGET_NAMES:
            score += 0.48
            reasons.append("exact target-like column name")
        elif tokens.intersection(TARGET_NAMES):
            score += 0.34
            reasons.append("target-like token in column name")

        if unique == 2:
            score += 0.30
            reasons.append("exactly two observed classes")
        elif 3 <= unique <= 10:
            score += 0.15
            reasons.append("low-cardinality multiclass values")
        elif unique <= 1:
            score -= 0.65
            penalties.append("constant or empty column")

        categorical = not pd.api.types.is_numeric_dtype(series)
        if categorical and 2 <= unique <= 10:
            score += 0.07
            reasons.append("categorical low-cardinality values")

        labels, distribution = _class_metadata(series)
        normalized_labels = {_normalized(label) for label in labels}
        if unique == 2 and normalized_labels.intersection(POSITIVE_LABELS) and normalized_labels.intersection(NEGATIVE_LABELS):
            score += 0.08
            reasons.append("semantically opposed binary labels")
        if distribution and min(distribution.values()) / sum(distribution.values()) >= 0.1:
            score += 0.05
            reasons.append("both classes have meaningful support")

        if missing_fraction:
            score -= min(0.30, missing_fraction)
            penalties.append("contains missing candidate labels")
        identifier_like = is_identifier(str(column)) or (unique >= 20 and unique_ratio >= 0.95)
        timestamp_like = _timestamp_like(str(column), series)
        if identifier_like:
            score -= 0.75
            penalties.append("identifier-like or almost unique")
        if timestamp_like:
            score -= 0.65
            penalties.append("timestamp-like")
        if pd.api.types.is_numeric_dtype(series) and unique > 20 and unique_ratio > 0.20:
            score -= 0.42
            penalties.append("continuous numeric measurement")

        score = round(float(np.clip(score, 0.0, 1.0)), 3)
        kind = _target_type(series, unique)
        public_labels = labels if unique <= 20 and not identifier_like and not timestamp_like else []
        public_distribution = distribution if public_labels else {}
        candidates.append({
            "column": str(column),
            "score": score,
            "confidence": "high" if score >= 0.8 else "medium" if score >= 0.55 else "low",
            "target_type": kind,
            "class_labels": public_labels,
            "class_distribution": public_distribution,
            "unique_values": unique,
            "missing_fraction": round(missing_fraction, 4),
            "eligible_for_current_pipeline": kind == "binary_classification" and missing_fraction == 0,
            "reasons": reasons,
            "penalties": penalties,
            "position": position,
        })
    return sorted(candidates, key=lambda item: (-item["score"], item["position"]))


def infer_positive_label(labels: list[str]) -> tuple[str | None, float, str]:
    if len(labels) != 2:
        return None, 0.0, "Exactly two classes are required."
    normalized = {label: _normalized(label) for label in labels}
    positive = [label for label, value in normalized.items() if value in POSITIVE_LABELS]
    negative = [label for label, value in normalized.items() if value in NEGATIVE_LABELS]
    if len(positive) == 1 and len(negative) == 1:
        return positive[0], 0.95, "Semantic positive/negative label pair."
    return None, 0.0, "Binary labels are semantically ambiguous; choose the positive label."


def detect_target(frame: pd.DataFrame, explicit_target: str | None = None, explicit_positive: str | None = None) -> dict[str, Any]:
    candidates = rank_target_candidates(frame)
    selected = None
    method = "automatic"
    if explicit_target is not None:
        selected = next((item for item in candidates if item["column"] == explicit_target), None)
        if selected is None:
            from ..utils.errors import AppError
            raise AppError("target_missing", "The selected target column is absent.")
        method = "manual_override"
    elif candidates:
        top = candidates[0]
        runner_up = candidates[1]["score"] if len(candidates) > 1 else 0.0
        if top["score"] >= 0.68 and top["score"] - runner_up >= 0.12 and top["eligible_for_current_pipeline"]:
            selected = top

    labels = selected["class_labels"] if selected else []
    positive, positive_confidence, positive_reason = infer_positive_label(labels)
    if explicit_positive is not None:
        if explicit_positive not in labels:
            from ..utils.errors import AppError
            raise AppError("positive_label_unknown", "The selected positive label is not present in the target.")
        positive, positive_confidence, positive_reason = explicit_positive, 1.0, "Explicit user selection."

    return {
        "detected_target": selected["column"] if selected else None,
        "target_type": selected["target_type"] if selected else None,
        "confidence_score": selected["score"] if selected else 0.0,
        "confidence": selected["confidence"] if selected else "low",
        "selection_method": method if selected else "manual_selection_required",
        "class_labels": labels,
        "class_distribution": selected["class_distribution"] if selected else {},
        "positive_label": positive,
        "positive_label_confidence": positive_confidence,
        "positive_label_reason": positive_reason,
        "requires_manual_target": selected is None,
        "requires_positive_label": selected is not None and positive is None,
        "heuristic_notice": "Scores are deterministic heuristic rankings, not calibrated probabilities.",
        "candidates": candidates[:10],
    }