import numpy as np
import pandas as pd
import pytest

from app.data.target_detection import detect_target, rank_target_candidates
from app.utils.errors import AppError


def test_obvious_binary_target_and_positive_label_are_detected():
    frame = pd.DataFrame({
        "patient_id": range(40),
        "age": np.linspace(20, 70, 40),
        "diagnosis": ["benign", "malignant"] * 20,
    })
    result = detect_target(frame)
    assert result["detected_target"] == "diagnosis"
    assert result["target_type"] == "binary_classification"
    assert result["positive_label"] == "malignant"
    assert result["confidence"] == "high"
    assert result["heuristic_notice"].startswith("Scores are deterministic heuristic")


def test_id_timestamp_and_continuous_features_are_penalized():
    frame = pd.DataFrame({
        "record_id": range(30),
        "recorded_at": pd.date_range("2025-01-01", periods=30).astype(str),
        "continuous_measurement": np.linspace(0.1, 9.0, 30),
        "outcome": ["yes", "no"] * 15,
    })
    ranked = {row["column"]: row for row in rank_target_candidates(frame)}
    assert ranked["record_id"]["score"] < ranked["outcome"]["score"]
    assert "identifier-like or almost unique" in ranked["record_id"]["penalties"]
    assert "timestamp-like" in ranked["recorded_at"]["penalties"]
    assert "continuous numeric measurement" in ranked["continuous_measurement"]["penalties"]
    assert detect_target(frame)["detected_target"] == "outcome"


def test_ambiguous_and_low_confidence_targets_require_manual_selection():
    frame = pd.DataFrame({
        "group_a": ["x", "y"] * 20,
        "group_b": ["m", "n"] * 20,
        "measurement": np.arange(40),
    })
    result = detect_target(frame)
    assert result["detected_target"] is None
    assert result["requires_manual_target"] is True
    assert result["selection_method"] == "manual_selection_required"


def test_multiclass_and_missing_targets_are_not_silently_selected():
    multiclass = pd.DataFrame({"feature": range(30), "class": ["a", "b", "c"] * 10})
    result = detect_target(multiclass)
    assert result["detected_target"] is None
    assert result["candidates"][0]["target_type"] == "multiclass_classification"
    assert result["candidates"][0]["eligible_for_current_pipeline"] is False

    missing = pd.DataFrame({"feature": range(20), "label": ["yes", "no"] * 9 + [None, None]})
    result = detect_target(missing)
    assert result["detected_target"] is None
    assert result["candidates"][0]["missing_fraction"] > 0


def test_manual_target_and_positive_label_override_are_validated():
    frame = pd.DataFrame({
        "diagnosis": ["benign", "malignant"] * 10,
        "review_result": ["keep", "remove"] * 10,
        "value": range(20),
    })
    result = detect_target(frame, "review_result", "remove")
    assert result["detected_target"] == "review_result"
    assert result["positive_label"] == "remove"
    assert result["selection_method"] == "manual_override"
    with pytest.raises(AppError, match="absent"):
        detect_target(frame, "not_a_column")
    with pytest.raises(AppError, match="positive"):
        detect_target(frame, "review_result", "unknown")