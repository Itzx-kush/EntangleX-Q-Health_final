from time import perf_counter
from uuid import uuid4
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from ..api.schemas import ExplanationRequest
from ..database import session_scope
from ..evaluation.metrics import auc_scorer, score_outputs
from ..models.prediction import background_for, feature_perturbation, get_bundle
from ..storage.entities import ExplanationRecord
from ..utils.errors import AppError
from ..utils.serialization import clean_json

def explain(identity: str, request: ExplanationRequest):
    record, bundle = get_bundle(identity)
    if record.model_type in {"vqc", "qsvc", "qnn"} and request.method != "perturbation":
        raise AppError("quantum_explanation_method", "Quantum models use feature perturbation / sensitivity analysis.")
    background, frame = background_for(bundle)
    config = bundle["config"]
    estimator = bundle["estimator"]
    all_test = frame.iloc[bundle["test_indices"]]
    # A deterministic post-hoc subset is disclosed; no explanation-driven refit occurs.
    test = all_test.iloc[:request.max_samples]
    X = test[bundle["features"]]
    target = record.details["dataset_provenance"]["target"]
    y = (test[target].astype(str) == bundle["positive_label"]).astype(int).to_numpy()
    start = perf_counter()
    _, baseline_scores, baseline_probabilities = score_outputs(estimator, X, config["probability_threshold"])
    baseline = {"mean": float(np.mean(baseline_scores)), "units": "positive-class model probability" if baseline_probabilities is not None else "decision score", "sample_count": len(X)}
    if request.method == "permutation":
        if len(np.unique(y)) < 2:
            raise AppError("explanation_class_support", "The bounded explanation subset contains only one class; increase max_samples or use perturbation.")
        result = permutation_importance(estimator, X, y, scoring=auc_scorer, n_repeats=request.repeats, random_state=config["seed"], n_jobs=1)
        influence = [{"feature": f, "magnitude": float(mean), "std": float(std)} for f, mean, std in zip(bundle["features"], result.importances_mean, result.importances_std)]
        units = "Decrease in ROC-AUC under permutation; negative values are retained."
    elif request.method == "shap":
        try:
            import shap
        except ImportError as exc:
            raise AppError("shap_unavailable", "Install requirements-explainability.txt before requesting SHAP.", 503) from exc
        if set(bundle["numeric"]) != set(bundle["features"]):
            raise AppError("shap_numeric_only", "This bounded raw-feature SHAP implementation requires numeric-only inputs. Use permutation importance for mixed-type tables.")
        if X.isna().any().any() or background.isna().any().any():
            raise AppError("shap_missing_values", "Raw-feature SHAP requires complete numeric inputs in this implementation; use permutation importance with missing data.")
        reference = background.iloc[:min(20, len(background))].astype(float)
        def model_output(values):
            _, scores, _ = score_outputs(estimator, pd.DataFrame(values, columns=bundle["features"]), config["probability_threshold"])
            return scores
        explainer = shap.Explainer(model_output, reference, algorithm="permutation", feature_names=bundle["features"], seed=config["seed"])
        values = np.asarray(explainer(X.astype(float), max_evals=(2 * len(bundle["features"]) + 1) * request.repeats).values, dtype=float)
        influence = [{"feature": f, "magnitude": float(np.mean(np.abs(values[:, i]))), "signed_mean": float(np.mean(values[:, i]))} for i, f in enumerate(bundle["features"])]
        units = "Mean absolute approximate SHAP contribution to positive-class model probability or decision score."
    else:
        influence = feature_perturbation(estimator, X, background, bundle["numeric"], config["probability_threshold"], max_features=request.max_features)
        units = "Mean absolute change in positive-class model probability or decision score."
    influence.sort(key=lambda item: item["magnitude"], reverse=True)
    result = clean_json({"title": "Model Feature Influence" if request.method != "perturbation" else "Feature Perturbation / Sensitivity Analysis", "scope": "Post-hoc explanation of a frozen model on a bounded held-out subset; never a tuning score.", "sample_count": len(X), "baseline": baseline, "request": request.model_dump(mode="json"), "background_source": "training partition only", "input_feature_count": len(bundle["features"]), "evaluated_feature_count": len(influence), "method": request.method, "units": units, "influence": influence, "elapsed_seconds": perf_counter() - start, "limitations": ["Influence does not establish biological or medical causation.", "Correlated features can redistribute importance; perturbations may be off-manifold.", "Quantum perturbation is model sensitivity, not a complete explanation of circuit internals.", "Repeated test-set analysis requires an untouched external validation set for subsequent model selection."]})
    with session_scope() as session:
        explanation = ExplanationRecord(id=str(uuid4()), model_id=identity, method=request.method, result=result)
        session.add(explanation)
    return explanation
