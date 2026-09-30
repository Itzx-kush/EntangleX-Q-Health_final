"""Deterministic research operating-point selection from validation scores.

This module is deliberately independent of estimators and data splits.  Callers
must provide out-of-fold validation labels and scores; held-out test values must
never be passed here.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score

from .metrics import classification_metrics
from ..utils.serialization import clean_json


def predictions_at_threshold(scores, threshold: float) -> np.ndarray:
    values = np.asarray(scores, dtype=float).reshape(-1)
    if not np.isfinite(values).all():
        raise ValueError("Threshold scores must be finite.")
    return (values >= float(threshold)).astype(int)


def operating_point(y_true, scores, threshold: float) -> dict:
    labels = np.asarray(y_true, dtype=int).reshape(-1)
    values = np.asarray(scores, dtype=float).reshape(-1)
    if len(labels) != len(values) or not len(labels):
        raise ValueError("Threshold labels and scores must be nonempty and aligned.")
    metrics = classification_metrics(labels, predictions_at_threshold(values, threshold), values)
    return {
        "threshold": float(threshold),
        "sensitivity": metrics["sensitivity"],
        "specificity": metrics["specificity"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "accuracy": metrics["accuracy"],
        "roc_auc": metrics["roc_auc"],
        "true_positive": metrics["true_positive"],
        "true_negative": metrics["true_negative"],
        "false_positive": metrics["false_positive"],
        "false_negative": metrics["false_negative"],
    }


def threshold_curve(y_true, scores, fixed_threshold: float | None = None) -> list[dict]:
    labels = np.asarray(y_true, dtype=int).reshape(-1)
    values = np.asarray(scores, dtype=float).reshape(-1)
    if len(labels) != len(values) or not len(labels):
        raise ValueError("Threshold labels and scores must be nonempty and aligned.")
    if not np.isfinite(values).all():
        raise ValueError("Threshold scores must be finite.")
    candidates = set(float(value) for value in np.unique(values))
    if fixed_threshold is not None:
        candidates.add(float(fixed_threshold))
    return [operating_point(labels, values, value) for value in sorted(candidates, reverse=True)]


def select_operating_point(
    y_true,
    scores,
    *,
    strategy: str,
    fixed_threshold: float,
    target_sensitivity: float | None,
    threshold_units: str,
    cv_fold_count: int,
) -> dict:
    """Build an OOF curve and select one threshold without holdout information.

    Sensitivity-first ties are resolved by specificity, sensitivity, F1, then
    the higher threshold.  The final rule is deterministic and conservative.
    """

    labels = np.asarray(y_true, dtype=int).reshape(-1)
    values = np.asarray(scores, dtype=float).reshape(-1)
    curve = threshold_curve(labels, values, fixed_threshold)
    common = {
        "selection_strategy": strategy,
        "target_sensitivity": target_sensitivity if strategy == "target_sensitivity" else None,
        "target_specificity": None,
        "threshold_units": threshold_units,
        "number_of_oof_samples": int(len(labels)),
        "cv_fold_count": int(cv_fold_count),
        "curve": curve,
        "holdout_metrics": None,
        "clinical_cutoff": False,
        "interpretation": "Research operating point; not a clinically validated screening cutoff.",
    }
    if strategy == "fixed":
        selected = operating_point(labels, values, fixed_threshold)
        return clean_json({
            **common,
            "selected_threshold": float(fixed_threshold),
            "threshold_feasible": True,
            "threshold_source": "configured_fixed_threshold",
            "validation_metrics": selected,
        })
    if strategy != "target_sensitivity":
        raise ValueError("Unsupported threshold selection strategy.")
    if target_sensitivity is None or not 0 < target_sensitivity <= 1:
        raise ValueError("Target sensitivity must satisfy 0 < target <= 1.")
    # A missing class makes sensitivity/specificity evidence undefined.  Do not
    # silently choose a threshold from such validation data.
    if len(np.unique(labels)) != 2:
        return clean_json({
            **common,
            "selected_threshold": None,
            "threshold_feasible": False,
            "threshold_source": "out_of_fold_validation",
            "validation_metrics": None,
            "infeasible_reason": "Target sensitivity is not achievable because the out-of-fold validation evidence does not contain both classes.",
        })
    feasible = [
        row for row in curve
        if row["sensitivity"] is not None and row["sensitivity"] >= target_sensitivity
        and row["specificity"] is not None
    ]
    if not feasible:
        return clean_json({
            **common,
            "selected_threshold": None,
            "threshold_feasible": False,
            "threshold_source": "out_of_fold_validation",
            "validation_metrics": None,
            "infeasible_reason": "Target sensitivity is not achievable on the validation folds under the current model configuration.",
        })
    selected = max(
        feasible,
        key=lambda row: (
            row["specificity"],
            row["sensitivity"],
            row["f1"] if row["f1"] is not None else float("-inf"),
            row["threshold"],
        ),
    )
    # ROC-AUC is threshold-independent, but retain it on the selected evidence
    # object so reports do not need to reconstruct it.
    selected["roc_auc"] = float(roc_auc_score(labels, values))
    return clean_json({
        **common,
        "selected_threshold": selected["threshold"],
        "threshold_feasible": True,
        "threshold_source": "out_of_fold_validation",
        "validation_metrics": selected,
        "infeasible_reason": None,
    })