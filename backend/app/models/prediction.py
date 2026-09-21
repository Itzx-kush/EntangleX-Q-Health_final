import numpy as np
import pandas as pd
from ..api.schemas import PredictionRequest
from ..config import DISCLAIMER
from ..data.service import load_frame
from ..database import session_scope
from ..evaluation.metrics import score_outputs
from ..storage.entities import ModelRecord
from ..storage.files import load_model
from ..storage.repository import require
from ..utils.errors import AppError

def get_bundle(identity: str):
    with session_scope() as session:
        record = require(session, ModelRecord, identity)
    if record.status != "ready" or not record.artifact_sha256:
        raise AppError("model_not_ready", "This model has no completed training artifact.", 409)
    return record, load_model(identity, record.artifact_sha256)

def prediction_frame(samples, features, numeric):
    expected = set(features)
    if any(set(sample) != expected for sample in samples):
        raise AppError("prediction_schema", "Each sample must contain exactly the model input feature names, without the target or unknown fields.")
    frame = pd.DataFrame(samples, columns=features)
    for col in features:
        if col in numeric:
            try:
                frame[col] = pd.to_numeric(frame[col], errors="raise").astype(float)
            except (ValueError, TypeError) as exc:
                raise AppError("invalid_numeric", "A numeric input contains an unsupported value.") from exc
            if np.isinf(frame[col].to_numpy()).any():
                raise AppError("invalid_numeric", "Infinite numeric inputs are not supported.")
        else:
            frame[col] = frame[col].map(lambda v: str(v) if v is not None and pd.notna(v) else np.nan).astype(object)
            if frame[col].dropna().str.len().gt(200).any():
                raise AppError("category_limit", "Categorical inputs must be at most 200 characters.")
    return frame

def background_for(bundle):
    dataset, frame = load_frame(bundle["dataset_id"])
    if dataset.sha256 != bundle["dataset_hash"]:
        raise AppError("dataset_mismatch", "The model and source dataset hashes do not match.", 409)
    return frame[bundle["features"]].iloc[bundle["train_indices"]], frame

def feature_perturbation(estimator, X: pd.DataFrame, background: pd.DataFrame, numeric: list[str], threshold: float, max_features=30):
    """Local or aggregate finite-difference sensitivity in ORIGINAL feature units."""
    _, baseline, probabilities = score_outputs(estimator, X, threshold)
    influences = []
    for feature in list(X.columns)[:max_features]:
        plus, minus = X.copy(), X.copy()
        if feature in numeric:
            sigma = float(pd.to_numeric(background[feature], errors="coerce").std())
            if not np.isfinite(sigma) or sigma == 0:
                influences.append({"feature": feature, "magnitude": 0.0, "delta_plus": 0.0, "delta_minus": 0.0, "perturbation": "No perturbation: zero or unavailable training standard deviation."})
                continue
            amount = 0.25 * sigma
            plus[feature] = plus[feature] + amount
            minus[feature] = minus[feature] - amount
            # Respect the fitted log domain, without turning an invalid input into a diagnosis.
            if (background[feature].dropna() >= 0).all():
                minus[feature] = minus[feature].clip(lower=0)
            note = "Plus/minus 0.25 training standard deviations; lower perturbation bounded at zero for nonnegative training features."
        else:
            categories = background[feature].dropna().value_counts().index.tolist()
            if len(categories) < 2:
                influences.append({"feature": feature, "magnitude": 0.0, "delta_plus": 0.0, "delta_minus": 0.0, "perturbation": "No observed alternative category."})
                continue
            plus[feature] = plus[feature].map(lambda value: categories[0] if value != categories[0] else categories[1])
            minus = plus.copy()
            note = "Alternate observed training category; categories are not disclosed in explanations."
        _, score_plus, _ = score_outputs(estimator, plus, threshold)
        _, score_minus, _ = score_outputs(estimator, minus, threshold)
        influences.append({"feature": feature, "magnitude": float(np.mean((np.abs(score_plus - baseline) + np.abs(score_minus - baseline)) / 2)), "delta_plus": float(np.mean(score_plus - baseline)), "delta_minus": float(np.mean(score_minus - baseline)), "perturbation": note})
    return sorted(influences, key=lambda row: row["magnitude"], reverse=True)

def predict(identity: str, request: PredictionRequest):
    record, bundle = get_bundle(identity)
    frame = prediction_frame(request.samples, bundle["features"], bundle["numeric"])
    threshold = bundle["config"]["probability_threshold"]
    try:
        predicted, scores, probabilities = score_outputs(bundle["estimator"], frame, threshold)
    except ValueError as exc:
        raise AppError("prediction_domain", "Input values are outside the configured model transformation domain.") from exc
    low, high = request.risk_thresholds
    results = []
    for index, label in enumerate(predicted):
        p = float(probabilities[index]) if probabilities is not None else None
        category = None if p is None else "LOW" if p < low else "MEDIUM" if p < high else "HIGH"
        results.append({"sample": f"Sample #{index + 1}", "predicted_class": bundle["positive_label"] if label else bundle["negative_label"], "probability_positive": p, "decision_score": float(scores[index]) if probabilities is None else None, "research_risk_category": category})
    influence = None
    if request.include_influence:
        background, _ = background_for(bundle)
        try:
            influence = feature_perturbation(bundle["estimator"], frame, background, bundle["numeric"], threshold, max_features=min(60, len(bundle["features"])))
        except ValueError as exc:
            raise AppError("perturbation_domain", "A perturbation is outside the feature engineering domain. Disable local influence for this sample.") from exc
    return {"model_id": identity, "model_type": record.model_type, "positive_label": bundle["positive_label"], "negative_label": bundle["negative_label"],
        "probability_status": record.details["probability_status"] if probabilities is not None else "Decision score only; no model probability or risk category is available.",
        "decision_rule": f"Positive model probability >= {threshold}" if probabilities is not None else "Decision score >= 0", "risk_thresholds": request.risk_thresholds,
        "predictions": results, "influence": influence, "limitations": ["Research predictions are not diagnoses or medical advice.", "Risk thresholds are demonstration/research thresholds, not clinically validated cutoffs.", "Feature influence is model sensitivity, not medical causation or complete quantum-circuit interpretation.", "Inputs and predictions are not persisted by this endpoint."], "disclaimer": DISCLAIMER}
