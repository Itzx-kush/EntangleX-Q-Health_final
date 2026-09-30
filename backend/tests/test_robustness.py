import time

import numpy as np
import pandas as pd
import pytest

from app.api.schemas import RobustnessRequest, RobustnessScenario
from app.evaluation.robustness import _changes, perturb_frame


def scenario(kind, level):
    return RobustnessScenario(perturbation_type=kind, level=level)


def test_perturbations_are_deterministic_and_levels_are_measured():
    frame = pd.DataFrame({"numeric": np.arange(20, dtype=float), "category": ["a", "b"] * 10})
    background = frame.copy()
    for kind, level in [("missingness", .1), ("gaussian_noise", .05), ("outliers", 3), ("categorical", .1)]:
        first = perturb_frame(frame, background, ["numeric"], scenario(kind, level), 17)
        second = perturb_frame(frame, background, ["numeric"], scenario(kind, level), 17)
        assert first["status"] == second["status"] == "evaluated"
        pd.testing.assert_frame_equal(first["frame"], second["frame"])
        assert first["metadata"] == second["metadata"]
        assert first["metadata"]["changed_cells"] > 0
    missing = perturb_frame(frame, background, ["numeric"], scenario("missingness", .1), 17)
    assert missing["metadata"]["realized_fraction"] == pytest.approx(.1)
    categorical = perturb_frame(frame, background, ["numeric"], scenario("categorical", .1), 17)
    changed = categorical["frame"]["category"] != frame["category"]
    assert changed.sum() == categorical["metadata"]["changed_cells"]
    noisy = perturb_frame(frame, background, ["numeric"], scenario("gaussian_noise", .05), 17)
    assert not noisy["frame"]["numeric"].equals(frame["numeric"])
    outliers = perturb_frame(frame, background, ["numeric"], scenario("outliers", 3), 17)
    assert outliers["metadata"]["injected_standard_deviations"] == 3


def test_non_applicable_and_undefined_metric_states_are_explicit():
    numeric_only = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    categorical = perturb_frame(numeric_only, numeric_only, ["x"], scenario("categorical", .1), 1)
    assert categorical["status"] == "not_applicable"
    assert "categorical feature" in categorical["reason"]
    constant = pd.DataFrame({"x": [1.0, 1.0, 1.0]})
    noise = perturb_frame(constant, constant, ["x"], scenario("gaussian_noise", .1), 1)
    assert noise["status"] == "not_applicable"
    baseline = {"accuracy": 0.0, "sensitivity": None}
    delta, relative, undefined = _changes(baseline, {"accuracy": .2, "sensitivity": None})
    assert delta["accuracy"] == .2
    assert relative["accuracy"] is None
    assert "relative_accuracy" in undefined
    assert delta["sensitivity"] is None
    assert "sensitivity" in undefined


def _poll(client, job_id):
    end = time.monotonic() + 90
    while time.monotonic() < end:
        result = client.get(f"/api/training/jobs/{job_id}").json()
        if result["status"] not in {"queued", "running", "cancel_requested"}:
            return result
        time.sleep(.1)
    pytest.fail("Training timed out.")


@pytest.mark.integration
def test_robustness_endpoint_uses_frozen_models_locked_threshold_and_bounded_holdout(client, config, monkeypatch):
    payload = config.model_dump(mode="json")
    payload["models"] = ["logistic_regression", "random_forest"]
    created = client.post("/api/training/jobs", json=payload)
    assert created.status_code == 202
    assert _poll(client, created.json()["job"]["id"])["status"] == "succeeded"
    experiment_id = created.json()["experiment"]["id"]
    detail = client.get(f"/api/experiments/{experiment_id}").json()
    ready = [model for model in detail["models"] if model["status"] == "ready"]
    assert len(ready) == 2

    def forbid_fit(*_args, **_kwargs):
        raise AssertionError("Robustness evaluation must not refit a model.")

    monkeypatch.setattr("sklearn.pipeline.Pipeline.fit", forbid_fit)
    response = client.post(f"/api/experiments/{experiment_id}/robustness", json={
        "model_ids": [model["id"] for model in ready],
        "scenarios": [
            {"perturbation_type": "missingness", "level": .05},
            {"perturbation_type": "categorical", "level": .05},
        ],
        "random_seed": 73,
        "max_samples": 64,
    })
    assert response.status_code == 200, response.text
    output = response.json()
    assert output["condition_count"] == 4
    assert output["sample_count"] <= 64
    missing = [item for item in output["results"] if item["perturbation_type"] == "missingness"]
    assert len({item["reproducibility_metadata"]["perturbation_fingerprint"] for item in missing}) == 1
    by_id = {model["id"]: model for model in ready}
    for item in output["results"]:
        source = by_id[item["model_id"]]
        point = source["metrics"]["operating_point"]
        assert item["threshold_used"] == point["selected_threshold"]
        assert item["threshold_source"] == point["threshold_source"]
        assert item["baseline_metrics"]["accuracy"] == source["metrics"]["test"]["accuracy"]
        if item["perturbation_type"] == "categorical":
            assert item["status"] == "not_applicable"
            assert item["perturbed_metrics"] is None
        else:
            assert item["status"] == "evaluated"
            assert item["degradation_delta"]["accuracy"] == pytest.approx(
                item["perturbed_metrics"]["accuracy"] - item["baseline_metrics"]["accuracy"]
            )

    history = client.get(f"/api/experiments/{experiment_id}/robustness")
    assert history.status_code == 200
    assert len(history.json()) == 4
    comparison = client.get(f"/api/experiments/{experiment_id}/comparison").json()
    assert comparison["pairs"] == []
    report = client.get(f"/api/experiments/{experiment_id}/report?format=html")
    assert report.status_code == 200
    assert "Robustness and degradation evidence" in report.text


def test_robustness_request_budget_is_bounded():
    with pytest.raises(ValueError):
        RobustnessRequest(
            model_ids=[f"00000000-0000-0000-0000-00000000000{i}" for i in range(5)],
            scenarios=[scenario("missingness", value) for value in (.01, .02, .03, .04, .05)],
        )