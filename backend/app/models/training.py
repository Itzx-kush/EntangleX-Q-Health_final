from time import perf_counter
from typing import Callable
import warnings
import numpy as np
from sklearn.exceptions import ConvergenceWarning
from ..api.schemas import TrainingConfig
from ..data.splitting import PreparedData
from ..evaluation.calibration import base_pipeline
from ..evaluation.metrics import classification_metrics, probability_diagnostics, score_outputs, summarize_cv
from ..evaluation.thresholds import predictions_at_threshold, select_operating_point
from ..feature_engineering.pipeline import describe_preprocessor
from ..utils.serialization import clean_json, fingerprint, software_versions
from .factory import build_estimator

def train_model(kind: str, config: TrainingConfig, data: PreparedData, checkpoint: Callable[[str], None]) -> tuple[dict, dict, dict]:
    X_train, y_train = data.X.iloc[data.train], data.y[data.train]
    X_test, y_test = data.X.iloc[data.test], data.y[data.test]
    fold_outputs, fold_times, training_warnings = [], [], []
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
        prediction, score, probabilities = score_outputs(estimator, X_train.iloc[validation_rows], config.probability_threshold)
        fold_times.append(perf_counter() - start)
        fold_outputs.append({
            "labels": y_train[validation_rows],
            "scores": score,
            "probabilities": probabilities,
        })
    cv_seconds = perf_counter() - cv_start
    oof_labels = np.concatenate([fold["labels"] for fold in fold_outputs])
    oof_scores = np.concatenate([fold["scores"] for fold in fold_outputs])
    probability_based = all(fold["probabilities"] is not None for fold in fold_outputs)
    threshold_units = "positive_class_probability" if probability_based else "decision_score"
    fixed_threshold = config.probability_threshold if probability_based else 0.0
    operating = select_operating_point(
        oof_labels,
        oof_scores,
        strategy=config.threshold_strategy,
        fixed_threshold=fixed_threshold,
        target_sensitivity=config.target_sensitivity,
        threshold_units=threshold_units,
        cv_fold_count=len(data.cv),
    )
    # A feasible optimized point is locked before final fitting.  A theoretically
    # infeasible validation result keeps the legacy fixed rule for model
    # usability, while the operating-point record remains explicitly infeasible.
    locked_threshold = operating["selected_threshold"]
    evaluation_threshold = fixed_threshold if locked_threshold is None else locked_threshold
    prediction_threshold_source = (
        operating["threshold_source"]
        if operating["threshold_feasible"]
        else "configured_fixed_fallback_after_infeasible_validation"
    )
    fold_metrics = [
        classification_metrics(
            fold["labels"],
            predictions_at_threshold(fold["scores"], evaluation_threshold),
            fold["scores"],
        )
        for fold in fold_outputs
    ]
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
    _, scores, probabilities = score_outputs(final, X_test, config.probability_threshold)
    predicted = predictions_at_threshold(scores, evaluation_threshold)
    inference_seconds = perf_counter() - start
    _, train_scores, _ = score_outputs(final, X_train, config.probability_threshold)
    train_prediction = predictions_at_threshold(train_scores, evaluation_threshold)
    fitted_pipeline = base_pipeline(final)
    classifier = fitted_pipeline.named_steps["classifier"]
    quantum = getattr(classifier, "quantum_metadata_", None)
    test_metrics = classification_metrics(y_test, predicted, scores)
    operating["holdout_metrics"] = {
        key: test_metrics.get(key)
        for key in ["sensitivity", "specificity", "precision", "recall", "f1", "accuracy", "roc_auc"]
    } if operating["threshold_feasible"] else None
    operating["evaluation_fallback_threshold"] = evaluation_threshold if not operating["threshold_feasible"] else None
    metrics = {
        "training": classification_metrics(y_train, train_prediction, train_scores),
        "validation": summarize_cv(fold_metrics),
        "test": test_metrics,
        "calibration": probability_diagnostics(y_test, probabilities, config.calibration),
        "timing": {"final_training_seconds": training_seconds, "cv_total_seconds": cv_seconds, "cv_fold_seconds": fold_times, "test_inference_seconds": inference_seconds, "test_inference_seconds_per_sample": inference_seconds / len(X_test)},
        "operating_point": operating,
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
    split_metadata = data.split_metadata()
    preprocessing = describe_preprocessor(fitted_pipeline.named_steps["preprocessor"])
    representation = {
        "raw_input_features": list(data.features),
        "selected_feature_count": len(preprocessing["selected_features"]),
        "feature_selection": {
            "method": config.pipeline.selection,
            "k_features": config.pipeline.k_features,
            "variance_threshold": config.pipeline.variance_threshold,
        },
        "pca_components": config.pipeline.pca_components,
        "angle_scaling": config.pipeline.angle_scaling,
        "final_representation_dimension": len(preprocessing["output_features"]),
        "hybrid_qubits": config.hybrid.qubits,
        "hybrid_quantum_layers": config.hybrid.quantum_layers,
        "pipeline": config.pipeline.model_dump(mode="json"),
    }
    comparison_conditions = {
        "dataset_id": data.dataset.id,
        "dataset_hash": data.dataset.sha256,
        "target": data.dataset.provenance["target"],
        "positive_label": data.dataset.provenance["positive_label"],
        "negative_label": data.dataset.provenance["negative_label"],
        "source_row_count": len(data.frame),
        "evaluated_row_count": split_metadata["evaluated_sample_count"],
        "sample_pool_hash": split_metadata["sample_pool_hash"],
        "sampled_row_indices": split_metadata["sampled_row_indices"],
        "train_indices": split_metadata["train_indices"],
        "test_indices": split_metadata["test_indices"],
        "split_hash": data.split_hash,
        "seed": config.seed,
        "test_size": config.test_size,
        "cv_folds": config.cv_folds,
        "duplicate_policy": config.duplicate_policy,
        "max_samples": config.max_samples,
        "representation": representation,
        "threshold_strategy": config.threshold_strategy,
        "target_sensitivity": config.target_sensitivity,
    }
    comparison_conditions["comparison_fingerprint"] = fingerprint(comparison_conditions)
    details = {
        "task": "binary_classification", "positive_label": data.dataset.provenance["positive_label"],
        "negative_label": data.dataset.provenance["negative_label"], "input_features": data.features,
        "numeric_features": data.numeric, "dataset_provenance": data.dataset.provenance,
        "split": split_metadata, "configuration": config.model_dump(mode="json"),
        "comparison_conditions": comparison_conditions, "common_representation": representation,
        "preprocessing": preprocessing,
        "software": software_versions(), "quantum": quantum,
        "optimization_objective": getattr(classifier, "loss_curve_", []),
        "probability_status": "uncalibrated model probability" if config.calibration == "none" else f"internally {config.calibration}-calibrated benchmark probability; not clinical risk",
        "supports_probability": probabilities is not None,
        "operating_point": operating,
        "warnings": training_warnings, "limitations": limitations,
    }
    bundle = {"estimator": final, "features": data.features, "numeric": data.numeric,
              "dataset_id": data.dataset.id, "dataset_hash": data.dataset.sha256,
              "train_indices": data.train.tolist(), "test_indices": data.test.tolist(),
              "config": config.model_dump(mode="json"), "positive_label": details["positive_label"], "negative_label": details["negative_label"],
              "operating_threshold": evaluation_threshold, "threshold_units": threshold_units,
              "threshold_source": prediction_threshold_source, "threshold_feasible": operating["threshold_feasible"]}
    return bundle, clean_json(metrics), clean_json(details)
