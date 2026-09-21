import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss, confusion_matrix, roc_auc_score, roc_curve
from ..utils.serialization import clean_json

METRIC_NAMES = ["accuracy", "precision", "recall", "sensitivity", "specificity", "f1", "roc_auc"]

def divide(a, b):
    return float(a / b) if b else None

def score_outputs(estimator, X, threshold=0.5) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    if hasattr(estimator, "predict_proba"):
        probabilities = np.asarray(estimator.predict_proba(X), dtype=float)
        classes = np.asarray(estimator.classes_)
        positive_index = int(np.flatnonzero(classes == 1)[0])
        p = probabilities[:, positive_index]
        if not np.isfinite(p).all() or np.any(p < -1e-8) or np.any(p > 1 + 1e-8):
            raise ValueError("The classifier returned invalid probabilities.")
        p = np.clip(p, 0, 1)
        return (p >= threshold).astype(int), p, p
    if hasattr(estimator, "decision_function"):
        score = np.asarray(estimator.decision_function(X), dtype=float).reshape(-1)
        if not np.isfinite(score).all():
            raise ValueError("The classifier returned invalid decision scores.")
        return (score >= 0).astype(int), score, None
    raise ValueError("A decision score or probability is required to calculate ROC-AUC.")

def classification_metrics(y_true, predicted, scores) -> dict:
    y_true, predicted, scores = np.asarray(y_true), np.asarray(predicted), np.asarray(scores)
    tn, fp, fn, tp = [int(x) for x in confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()]
    sensitivity = divide(tp, tp + fn)
    result = {
        "accuracy": divide(tp + tn, len(y_true)), "precision": divide(tp, tp + fp),
        "recall": sensitivity, "sensitivity": sensitivity, "specificity": divide(tn, tn + fp),
        "f1": divide(2 * tp, 2 * tp + fp + fn), "roc_auc": None,
        "true_positive": tp, "true_negative": tn, "false_positive": fp, "false_negative": fn,
        "confusion_matrix": [[tn, fp], [fn, tp]], "matrix_axis_order": ["negative", "positive"],
        "matrix_rows": "observed", "matrix_columns": "predicted", "sample_count": len(y_true), "roc_curve": None,
    }
    if len(np.unique(y_true)) == 2:
        fpr, tpr, thresholds = roc_curve(y_true, scores)
        result.update({"roc_auc": float(roc_auc_score(y_true, scores)), "roc_curve": {"fpr": fpr.tolist(), "tpr": tpr.tolist(), "thresholds": thresholds.tolist()}})
    result["undefined_metrics"] = [name for name in METRIC_NAMES if result[name] is None]
    return clean_json(result)

def summarize_cv(fold_metrics: list[dict]) -> dict:
    result = {}
    for name in METRIC_NAMES:
        values = [fold[name] for fold in fold_metrics if fold.get(name) is not None]
        result[name] = {"mean": float(np.mean(values)) if values else None, "std": float(np.std(values, ddof=1)) if len(values) > 1 else None, "valid_folds": len(values)}
    return {"folds": fold_metrics, "summary": result, "std_definition": "sample standard deviation across folds; not a confidence interval"}

def probability_diagnostics(y_true, probabilities, method: str) -> dict:
    if probabilities is None:
        return {"method": "not_available", "brier_score": None, "reliability_curve": None, "clinical_calibration": False}
    observed, predicted = calibration_curve(y_true, probabilities, n_bins=10, strategy="uniform")
    return {"method": method, "brier_score": float(brier_score_loss(y_true, probabilities)), "reliability_curve": {"mean_probability": predicted.tolist(), "observed_positive_fraction": observed.tolist()}, "clinical_calibration": False, "interpretation": "Held-out benchmark probability diagnostics; not externally or clinically validated calibration."}

def auc_scorer(estimator, X, y):
    _, scores, _ = score_outputs(estimator, X)
    return float(roc_auc_score(y, scores))
