import numpy as np
import pandas as pd
import pytest

from app.explainability.hybrid_shap import HybridShapAdapter, local_contract
from app.utils.errors import AppError


class MixedProbabilityModel:
    classes_ = np.array([0, 1])
    def predict_proba(self, frame):
        age = pd.to_numeric(frame["age"]).to_numpy(float)
        gender = (frame["gender"].astype(str) == "Male").to_numpy(float)
        symptom = (frame["polyuria"].astype(str) == "Yes").to_numpy(float)
        logits = (age - 40) / 20 + 0.2 * gender + 0.8 * symptom
        positive = 1 / (1 + np.exp(-logits))
        return np.column_stack([1 - positive, positive])


def data():
    background = pd.DataFrame({
        "age": [25, 35, 45, 55, 65],
        "gender": ["Female", "Male", "Female", "Male", "Female"],
        "polyuria": ["No", "No", "Yes", "Yes", "No"],
    })
    case = pd.DataFrame({"age": [52], "gender": ["Male"], "polyuria": ["Yes"]})
    return background, case


def test_mixed_adapter_preserves_original_names_values_and_final_probability():
    background, case = data()
    adapter = HybridShapAdapter(MixedProbabilityModel(), background, list(case.columns), ["age"], 0.6, 17)
    result = adapter.explain(case)
    contract = local_contract(result, threshold=0.6, threshold_source="out_of_fold_validation", predicted_class="positive", positive_label="positive", negative_label="negative", risk_category="HIGH")
    assert [item["feature"] for item in contract["contributions"]] == sorted(case.columns, key=lambda name: next(item["absolute_contribution"] for item in contract["contributions"] if item["feature"] == name), reverse=True)
    assert {item["feature"] for item in contract["contributions"]} == {"age", "gender", "polyuria"}
    original = {item["feature"]: item["original_value"] for item in contract["contributions"]}
    assert original == {"age": 52, "gender": "Male", "polyuria": "Yes"}
    assert all(np.isfinite(item["contribution"]) for item in contract["contributions"])
    assert contract["prediction_context"]["probability_positive"] == pytest.approx(MixedProbabilityModel().predict_proba(case)[0, 1])
    assert contract["method"] == "shap"
    assert contract["output_semantics"] == "final positive-class probability"


def test_unseen_category_is_rejected_instead_of_silently_remapped():
    background, case = data(); case.loc[0, "gender"] = "Unknown"
    adapter = HybridShapAdapter(MixedProbabilityModel(), background, list(case.columns), ["age"], 0.6, 17)
    with pytest.raises(AppError) as error:
        adapter.explain(case)
    assert error.value.code == "shap_category_mismatch"


def test_missing_background_and_shap_failure_never_return_placeholder_values(monkeypatch):
    _, case = data()
    with pytest.raises(AppError) as missing:
        HybridShapAdapter(MixedProbabilityModel(), case.iloc[:0], list(case.columns), ["age"], 0.6, 17)
    assert missing.value.code == "shap_background_missing"

    background, case = data()
    adapter = HybridShapAdapter(MixedProbabilityModel(), background, list(case.columns), ["age"], 0.6, 17)
    import shap
    monkeypatch.setattr(shap, "Explainer", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("forced")))
    with pytest.raises(AppError) as failure:
        adapter.explain(case)
    assert failure.value.code == "shap_computation_failed"
