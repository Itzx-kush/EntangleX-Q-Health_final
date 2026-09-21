import numpy as np
import pytest
from app.evaluation.metrics import classification_metrics, probability_diagnostics, score_outputs, summarize_cv
from app.models.prediction import prediction_frame
from app.api.schemas import PredictionRequest
from app.utils.errors import AppError

def test_confusion_sensitivity_specificity():
    # Hand-checkable artificial labels are unit-test inputs, not demo measurements.
    measured = classification_metrics([0, 0, 0, 1, 1, 1], [0, 0, 1, 0, 1, 1], [.1, .2, .8, .4, .7, .9])
    assert measured["confusion_matrix"] == [[2, 1], [1, 2]]
    assert measured["false_negative"] == 1 and measured["false_positive"] == 1
    assert measured["sensitivity"] == pytest.approx(2 / 3)
    assert measured["specificity"] == pytest.approx(2 / 3)
    assert measured["recall"] == measured["sensitivity"]
    assert measured["roc_curve"] is not None

def test_undefined_values_are_not_faked():
    measured = classification_metrics([0, 0], [0, 0], [.1, .2])
    assert measured["sensitivity"] is None
    assert measured["precision"] is None
    assert measured["roc_auc"] is None

def test_cross_validation_reports_sample_standard_deviation():
    m1 = classification_metrics([0, 1], [0, 1], [.1, .9])
    m2 = classification_metrics([0, 1], [0, 0], [.1, .2])
    summary = summarize_cv([m1, m2])["summary"]
    assert summary["sensitivity"]["mean"] == .5
    assert summary["sensitivity"]["std"] == pytest.approx(np.std([1., 0.], ddof=1))

def test_probability_class_order_and_threshold():
    class TestEstimator:
        classes_ = np.array([1, 0])
        def predict_proba(self, X):
            return np.array([[.7, .3]])
    prediction, _, p = score_outputs(TestEstimator(), [[0]], threshold=.8)
    assert p[0] == .7
    assert prediction[0] == 0

def test_margin_not_misrepresented_as_probability():
    class TestEstimator:
        def decision_function(self, X):
            return np.array([2.0, -1.0])
    predicted, score, p = score_outputs(TestEstimator(), [[0], [1]])
    assert p is None
    assert predicted.tolist() == [1, 0]
    assert probability_diagnostics([1, 0], p, "none")["clinical_calibration"] is False

def test_prediction_rejects_unknown_or_target_fields():
    with pytest.raises(AppError, match="exactly"):
        prediction_frame([{"x": 1, "diagnosis": "positive"}], ["x"], ["x"])
    with pytest.raises(AppError, match="numeric"):
        prediction_frame([{"x": "not-a-number"}], ["x"], ["x"])

def test_missing_prediction_input_is_explicitly_imputed():
    frame = prediction_frame([{"x": None}], ["x"], ["x"])
    assert frame["x"].isna().all()

@pytest.mark.parametrize("thresholds", [(0, .66), (.8, .2), (.4, 1)])
def test_research_thresholds_validated(thresholds):
    with pytest.raises(ValueError):
        PredictionRequest(samples=[{"x": 1}], risk_thresholds=thresholds)
