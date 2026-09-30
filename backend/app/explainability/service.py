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
        mixed_hybrid = record.model_type == "hybrid_pennylane_torch" and set(bundle["numeric"]) != set(bundle["features"])
        if not mixed_hybrid and set(bundle["numeric"]) != set(bundle["features"]):
            raise AppError("shap_numeric_only", "This bounded raw-feature SHAP implementation requires numeric-only inputs. Use permutation importance for mixed-type tables.")
        if mixed_hybrid:
            # Categories and all encoding statistics come only from the training partition.
            categories = {}
            numeric_fill = {}
            for feature in bundle["features"]:
                if feature in bundle["numeric"]:
                    numeric_fill[feature] = float(pd.to_numeric(background[feature], errors="coerce").median())
                else:
                    observed = background[feature].dropna().astype(str)
                    values_seen = sorted(observed.unique().tolist())
                    if not values_seen:
                        raise AppError("shap_category_support", "A categorical feature has no observed training values for SHAP reconstruction.")
                    categories[feature] = values_seen
            def encode(frame):
                encoded = np.zeros((len(frame), len(bundle["features"])), dtype=float)
                for index, feature in enumerate(bundle["features"]):
                    if feature in bundle["numeric"]:
                        encoded[:, index] = pd.to_numeric(frame[feature], errors="coerce").fillna(numeric_fill[feature]).to_numpy(float)
                    else:
                        mapping = {value: position for position, value in enumerate(categories[feature])}
                        fallback = 0
                        encoded[:, index] = frame[feature].map(lambda value: mapping.get(str(value), fallback) if pd.notna(value) else fallback).to_numpy(float)
                return encoded
            def decode(values):
                values = np.asarray(values, dtype=float)
                rebuilt = {}
                for index, feature in enumerate(bundle["features"]):
                    if feature in bundle["numeric"]:
                        rebuilt[feature] = values[:, index]
                    else:
                        choices = categories[feature]
                        positions = np.clip(np.rint(values[:, index]).astype(int), 0, len(choices) - 1)
                        rebuilt[feature] = [choices[position] for position in positions]
                return pd.DataFrame(rebuilt, columns=bundle["features"])
            reference = encode(background.iloc[:min(20, len(background))])
            explained = encode(X)
            def model_output(values):
                _, scores, _ = score_outputs(estimator, decode(values), config["probability_threshold"])
                return scores
            shap_input = explained
            extra_limitation = "Categorical variables are encoded only for the SHAP perturbation interface; contributions remain model influence, not causal effects."
        else:
            if X.isna().any().any() or background.isna().any().any():
                raise AppError("shap_missing_values", "Raw-feature SHAP requires complete numeric inputs in this implementation; use permutation importance with missing data.")
            reference = background.iloc[:min(20, len(background))].astype(float)
            def model_output(values):
                _, scores, _ = score_outputs(estimator, pd.DataFrame(values, columns=bundle["features"]), config["probability_threshold"])
                return scores
            shap_input = X.astype(float)
            extra_limitation = None
        explainer = shap.Explainer(model_output, reference, algorithm="permutation", feature_names=bundle["features"], seed=config["seed"])
        values = np.asarray(explainer(shap_input, max_evals=(2 * len(bundle["features"]) + 1) * request.repeats).values, dtype=float)
        influence = [{"feature": f, "magnitude": float(np.mean(np.abs(values[:, i]))), "signed_mean": float(np.mean(values[:, i]))} for i, f in enumerate(bundle["features"])]
        units = "Mean absolute approximate SHAP contribution to the final hybrid positive-class output." if mixed_hybrid else "Mean absolute approximate SHAP contribution to positive-class model probability or decision score."
    else:
        influence = feature_perturbation(estimator, X, background, bundle["numeric"], config["probability_threshold"], max_features=request.max_features)
        units = "Mean absolute change in positive-class model probability or decision score."
    influence.sort(key=lambda item: item["magnitude"], reverse=True)
    result = clean_json({"title": "Model Feature Influence" if request.method != "perturbation" else "Feature Perturbation / Sensitivity Analysis", "scope": "Post-hoc explanation of a frozen model on a bounded held-out subset; never a tuning score.", "sample_count": len(X), "baseline": baseline, "request": request.model_dump(mode="json"), "background_source": "training partition only", "input_feature_count": len(bundle["features"]), "evaluated_feature_count": len(influence), "method": request.method, "units": units, "influence": influence, "elapsed_seconds": perf_counter() - start, "limitations": [item for item in ["Influence does not establish biological or medical causation.", "Correlated features can redistribute importance; perturbations may be off-manifold.", "SHAP explains the frozen final hybrid output, not internal quantum causal mechanisms." if record.model_type == "hybrid_pennylane_torch" else "Quantum perturbation is model sensitivity, not a complete explanation of circuit internals.", "Repeated test-set analysis requires an untouched external validation set for subsequent model selection.", extra_limitation if request.method == "shap" else None] if item]})
    with session_scope() as session:
        explanation = ExplanationRecord(id=str(uuid4()), model_id=identity, method=request.method, result=result)
        session.add(explanation)
    return explanation
