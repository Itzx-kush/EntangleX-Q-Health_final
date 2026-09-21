from time import perf_counter
from typing import Callable
import warnings
from sklearn.exceptions import ConvergenceWarning
from ..api.schemas import TrainingConfig
from ..data.splitting import PreparedData
from ..evaluation.calibration import base_pipeline
from ..evaluation.metrics import classification_metrics, probability_diagnostics, score_outputs, summarize_cv
from ..feature_engineering.pipeline import describe_preprocessor
from ..utils.serialization import clean_json, software_versions
from .factory import build_estimator

def train_model(kind: str, config: TrainingConfig, data: PreparedData, checkpoint: Callable[[str], None]) -> tuple[dict, dict, dict]:
    X_train, y_train = data.X.iloc[data.train], data.y[data.train]
    X_test, y_test = data.X.iloc[data.test], data.y[data.test]
    fold_metrics, fold_times, training_warnings = [], [], []
    cv_start = perf_counter()
    for number, (training_rows, validation_rows) in enumerate(data.cv, start=1):
        checkpoint(f"{kind}: cross-validation fold {number}/{len(data.cv)}")
        estimator = build_estimator(kind, config, data.features, data.numeric)
        start = perf_counter()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            estimator.fit(X_train.iloc[training_rows], y_train[training_rows])
        if any(issubclass(w.category, ConvergenceWarning) for w in caught):
            training_warnings.append(f"Convergence warning in fold {number}; inspect optimization settings without tuning on the test set.")
        prediction, score, _ = score_outputs(estimator, X_train.iloc[validation_rows], config.probability_threshold)
        fold_times.append(perf_counter() - start)
        fold_metrics.append(classification_metrics(y_train[validation_rows], prediction, score))
    cv_seconds = perf_counter() - cv_start
    checkpoint(f"{kind}: final training fit")
    final = build_estimator(kind, config, data.features, data.numeric)
    start = perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        final.fit(X_train, y_train)
    training_seconds = perf_counter() - start
    if any(issubclass(w.category, ConvergenceWarning) for w in caught):
        training_warnings.append("Final fit raised a convergence warning.")
    checkpoint(f"{kind}: held-out evaluation")
    start = perf_counter()
    predicted, scores, probabilities = score_outputs(final, X_test, config.probability_threshold)
    inference_seconds = perf_counter() - start
    train_prediction, train_scores, _ = score_outputs(final, X_train, config.probability_threshold)
    fitted_pipeline = base_pipeline(final)
    classifier = fitted_pipeline.named_steps["classifier"]
    quantum = getattr(classifier, "quantum_metadata_", None)
    metrics = {
        "training": classification_metrics(y_train, train_prediction, train_scores),
        "validation": summarize_cv(fold_metrics),
        "test": classification_metrics(y_test, predicted, scores),
        "calibration": probability_diagnostics(y_test, probabilities, config.calibration),
        "timing": {"final_training_seconds": training_seconds, "cv_total_seconds": cv_seconds, "cv_fold_seconds": fold_times, "test_inference_seconds": inference_seconds, "test_inference_seconds_per_sample": inference_seconds / len(X_test)},
    }
    limitations = data.quality["warnings"] + [
        "Benchmark results are not clinical validation, patient prognosis, or treatment advice.",
        "Only independent, identically distributed binary-classification samples are supported; grouped, longitudinal and temporal validation require another design.",
        "Repeated inspection of this holdout across reruns can overfit research decisions. Use an external dataset for final confirmation.",
        "A single seed and fold standard deviation do not establish statistical significance or quantum advantage.",
    ]
    if data.excluded_by_sampling:
        limitations.append("A disclosed stratified subset was selected before splitting; all compared models use exactly that subset.")
    if config.calibration == "isotonic":
        limitations.append("Isotonic calibration can overfit small calibration samples; examine independent calibration evidence.")
    details = {
        "task": "binary_classification", "positive_label": data.dataset.provenance["positive_label"],
        "negative_label": data.dataset.provenance["negative_label"], "input_features": data.features,
        "numeric_features": data.numeric, "dataset_provenance": data.dataset.provenance,
        "split": data.split_metadata(), "configuration": config.model_dump(mode="json"),
        "preprocessing": describe_preprocessor(fitted_pipeline.named_steps["preprocessor"]),
        "software": software_versions(), "quantum": quantum,
        "optimization_objective": getattr(classifier, "loss_curve_", []),
        "probability_status": "uncalibrated model probability" if config.calibration == "none" else f"internally {config.calibration}-calibrated benchmark probability; not clinical risk",
        "supports_probability": probabilities is not None,
        "warnings": training_warnings, "limitations": limitations,
    }
    bundle = {"estimator": final, "features": data.features, "numeric": data.numeric,
              "dataset_id": data.dataset.id, "dataset_hash": data.dataset.sha256,
              "train_indices": data.train.tolist(), "test_indices": data.test.tolist(),
              "config": config.model_dump(mode="json"), "positive_label": details["positive_label"], "negative_label": details["negative_label"]}
    return bundle, clean_json(metrics), clean_json(details)
