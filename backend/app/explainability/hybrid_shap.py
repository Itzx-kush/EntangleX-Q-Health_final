"""Bounded SHAP adapter for the complete mixed-input hybrid prediction pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd

from ..evaluation.metrics import score_outputs
from ..utils.errors import AppError

MAX_BACKGROUND_ROWS = 20
MAX_EXPLAINED_ROWS = 32
MODEL_DISPLAY_NAME = "PennyLane + PyTorch Hybrid"
OUTPUT_SEMANTICS = "final positive-class probability"
LIMITATIONS = [
    "SHAP describes how input features influenced this model's final prediction; it does not establish biological or clinical causation.",
    "SHAP does not expose a complete causal interpretation of the quantum circuit.",
    "Categorical encoding is used only by the bounded SHAP perturbation interface and has no biological meaning.",
]


@dataclass
class HybridShapResult:
    values: np.ndarray
    base_values: np.ndarray
    probabilities: np.ndarray
    original_values: list[dict[str, Any]]
    background_count: int


class HybridShapAdapter:
    """Encode mixed raw inputs, then reconstruct valid raw frames for prediction."""

    def __init__(self, estimator, background: pd.DataFrame, features: list[str], numeric: list[str], threshold: float, seed: int):
        if background.empty:
            raise AppError("shap_background_missing", "Hybrid SHAP requires nonempty training-partition background data.", 409)
        self.estimator = estimator
        self.features = list(features)
        self.numeric = set(numeric)
        self.threshold = float(threshold)
        self.seed = int(seed)
        self.background = background.loc[:, self.features].iloc[:MAX_BACKGROUND_ROWS].copy()
        self.categories: dict[str, list[str]] = {}
        self.numeric_fill: dict[str, float] = {}
        for feature in self.features:
            if feature in self.numeric:
                values = pd.to_numeric(background[feature], errors="coerce")
                median = float(values.median())
                if not np.isfinite(median):
                    raise AppError("shap_numeric_background", "A numeric feature has no finite training value for SHAP reconstruction.", 409)
                self.numeric_fill[feature] = median
            else:
                observed = sorted(background[feature].dropna().astype(str).unique().tolist())
                if not observed:
                    raise AppError("shap_category_support", "A categorical feature has no observed training value for SHAP reconstruction.", 409)
                self.categories[feature] = observed

    def encode(self, frame: pd.DataFrame, *, strict_categories: bool) -> np.ndarray:
        if list(frame.columns) != self.features:
            raise AppError("shap_feature_schema", "Hybrid SHAP requires the exact fitted original feature order.")
        encoded = np.zeros((len(frame), len(self.features)), dtype=float)
        for index, feature in enumerate(self.features):
            if feature in self.numeric:
                values = pd.to_numeric(frame[feature], errors="coerce").fillna(self.numeric_fill[feature]).to_numpy(float)
                if not np.isfinite(values).all():
                    raise AppError("shap_numeric_input", "A numeric SHAP input is invalid or non-finite.")
                encoded[:, index] = values
            else:
                mapping = {value: position for position, value in enumerate(self.categories[feature])}
                positions = []
                for value in frame[feature]:
                    if pd.isna(value):
                        positions.append(0)
                        continue
                    key = str(value)
                    if strict_categories and key not in mapping:
                        raise AppError("shap_category_mismatch", f"Feature '{feature}' contains a category not observed in the training partition.")
                    positions.append(mapping.get(key, 0))
                encoded[:, index] = positions
        return encoded

    def decode(self, values) -> pd.DataFrame:
        array = np.asarray(values, dtype=float)
        if array.ndim != 2 or array.shape[1] != len(self.features):
            raise AppError("shap_encoded_shape", "The bounded SHAP adapter received an invalid encoded feature shape.")
        rebuilt: dict[str, Any] = {}
        for index, feature in enumerate(self.features):
            if feature in self.numeric:
                rebuilt[feature] = array[:, index]
            else:
                choices = self.categories[feature]
                positions = np.clip(np.rint(array[:, index]).astype(int), 0, len(choices) - 1)
                rebuilt[feature] = [choices[position] for position in positions]
        return pd.DataFrame(rebuilt, columns=self.features)

    def model_output(self, values) -> np.ndarray:
        _, scores, probabilities = score_outputs(self.estimator, self.decode(values), self.threshold)
        if probabilities is None:
            raise AppError("shap_probability_unavailable", "Hybrid SHAP requires the fitted model's positive-class probability output.", 409)
        return np.asarray(scores, dtype=float)

    def explain(self, frame: pd.DataFrame, *, repeats: int = 1) -> HybridShapResult:
        if frame.empty or len(frame) > MAX_EXPLAINED_ROWS:
            raise AppError("shap_sample_bound", f"Hybrid SHAP supports between 1 and {MAX_EXPLAINED_ROWS} cases per request.")
        try:
            import shap
        except ImportError as exc:
            raise AppError("shap_unavailable", "Install requirements-explainability.txt before requesting SHAP.", 503) from exc
        explained = self.encode(frame.loc[:, self.features], strict_categories=True)
        reference = self.encode(self.background, strict_categories=False)
        try:
            explainer = shap.Explainer(self.model_output, reference, algorithm="permutation", feature_names=self.features, seed=self.seed)
            result = explainer(explained, max_evals=(2 * len(self.features) + 1) * max(1, int(repeats)))
            values = np.asarray(result.values, dtype=float)
            base_values = np.asarray(result.base_values, dtype=float).reshape(-1)
            probabilities = self.model_output(explained)
        except AppError:
            raise
        except Exception as exc:
            raise AppError("shap_computation_failed", "Hybrid SHAP could not evaluate the frozen final prediction safely.", 422) from exc
        if values.shape != explained.shape or not np.isfinite(values).all() or not np.isfinite(base_values).all():
            raise AppError("shap_invalid_output", "Hybrid SHAP returned an invalid contribution array.", 422)
        originals = []
        for _, row in frame.loc[:, self.features].iterrows():
            originals.append({feature: None if pd.isna(row[feature]) else row[feature].item() if hasattr(row[feature], "item") else row[feature] for feature in self.features})
        return HybridShapResult(values, base_values, probabilities, originals, len(reference))


def direction(value: float) -> str:
    if value > 1e-12:
        return "toward_positive"
    if value < -1e-12:
        return "toward_negative"
    return "neutral"


def interpretation(value: float) -> str:
    label = direction(value)
    return {
        "toward_positive": "Increased the model's final positive-class probability.",
        "toward_negative": "Decreased the model's final positive-class probability.",
        "neutral": "Had negligible contribution to the model's final positive-class probability.",
    }[label]


def local_contract(result: HybridShapResult, *, threshold: float, threshold_source: str, predicted_class: str, positive_label: str, negative_label: str, risk_category: str | None) -> dict:
    contributions = []
    for feature, value in zip(result.original_values[0], result.values[0]):
        contribution = float(value)
        contributions.append({
            "feature": feature,
            "original_value": result.original_values[0][feature],
            "contribution": contribution,
            "signed_mean": contribution,
            "magnitude": abs(contribution),
            "absolute_contribution": abs(contribution),
            "direction": direction(contribution),
            "interpretation": interpretation(contribution),
        })
    contributions.sort(key=lambda item: item["absolute_contribution"], reverse=True)
    return {
        "method": "shap",
        "method_display": "SHAP — Final Hybrid Output",
        "scope": "local_case",
        "model_type": "hybrid_pennylane_torch",
        "model_display_name": MODEL_DISPLAY_NAME,
        "output_semantics": OUTPUT_SEMANTICS,
        "prediction_context": {
            "probability_positive": float(result.probabilities[0]),
            "operating_threshold": float(threshold),
            "threshold_source": threshold_source,
            "predicted_class": predicted_class,
            "positive_label": positive_label,
            "negative_label": negative_label,
            "research_risk_category": risk_category,
            "base_value": float(result.base_values[0]),
        },
        "contributions": contributions,
        "background_source": "training partition only",
        "background_sample_count": result.background_count,
        "explained_case_count": 1,
        "limitations": LIMITATIONS,
    }
