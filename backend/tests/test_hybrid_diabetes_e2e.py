import time
import numpy as np
import pytest
from sqlalchemy import select

from app.database import session_scope
from app.storage.entities import ModelRecord
from app.storage.files import load_model


def poll(client, job_id, timeout=180):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/api/training/jobs/{job_id}").json()
        if job["status"] not in {"queued", "running", "cancel_requested"}:
            return job
        time.sleep(0.1)
    pytest.fail("Bounded diabetes hybrid job timed out.")


@pytest.mark.integration
def test_real_diabetes_hybrid_training_prediction_persistence_shap_and_comparison(client):
    registered = client.post("/api/datasets/library/early-stage-diabetes", json={})
    assert registered.status_code == 201, registered.text
    dataset = registered.json()
    payload = {
        "dataset_id": dataset["id"],
        "models": ["random_forest", "hybrid_pennylane_torch"],
        "pipeline": {"pca_components": 2, "k_features": 6, "angle_scaling": True},
        "quantum": {"qubits": 4},
        "hybrid": {
            "qubits": 2, "quantum_layers": 1, "classical_hidden_dimensions": [4],
            "epochs": 5, "batch_size": 8, "learning_rate": 0.02,
            "sample_cap": 40, "deterministic_seed": 23,
        },
        "seed": 23, "cv_folds": 2, "test_size": 0.25, "max_samples": 40,
        "duplicate_policy": "drop_exact", "threshold_strategy": "target_sensitivity",
        "target_sensitivity": 0.8,
    }
    created = client.post("/api/training/jobs", json=payload)
    assert created.status_code == 202, created.text
    job = poll(client, created.json()["job"]["id"])
    assert job["status"] == "succeeded", job["errors"]
    experiment_id = created.json()["experiment"]["id"]
    detail = client.get(f"/api/experiments/{experiment_id}").json()
    hybrid = next(model for model in detail["models"] if model["model_type"] == "hybrid_pennylane_torch")
    assert hybrid["status"] == "ready"
    assert hybrid["details"]["quantum"]["framework"] == "PennyLane"
    assert hybrid["details"]["quantum"]["classical_framework"] == "PyTorch"
    assert hybrid["details"]["quantum"]["quantum_parameters_changed"] is True
    assert hybrid["metrics"]["operating_point"]["threshold_source"] == "out_of_fold_validation"
    assert hybrid["metrics"]["timing"]["final_training_seconds"] >= 0

    sample_response = client.get(f"/api/models/{hybrid['id']}/demo-sample")
    assert sample_response.status_code == 200
    sample = sample_response.json()["features"]
    prediction = client.post(f"/api/models/{hybrid['id']}/predict", json={"samples": [sample], "include_influence": True})
    assert prediction.status_code == 200, prediction.text
    output = prediction.json()
    probability = output["predictions"][0]["probability_positive"]
    assert probability is not None and 0 <= probability <= 1
    assert output["threshold_source"] == "out_of_fold_validation"
    assert output["operating_threshold"] == hybrid["metrics"]["operating_point"]["selected_threshold"]
    local = output["explanation"]
    assert local["method"] == "shap"
    assert local["method_display"] == "SHAP — Final Hybrid Output"
    assert local["scope"] == "local_case"
    assert local["prediction_context"]["probability_positive"] == probability
    assert local["prediction_context"]["operating_threshold"] == output["operating_threshold"]
    assert len(local["contributions"]) == 16
    assert all(np.isfinite(item["contribution"]) for item in local["contributions"])
    assert {item["direction"] for item in local["contributions"]} <= {"toward_positive", "toward_negative", "neutral"}
    assert {item["feature"] for item in local["contributions"]} == set(sample)
    assert all(item["original_value"] == sample[item["feature"]] for item in local["contributions"])

    with session_scope() as session:
        record = session.scalar(select(ModelRecord).where(ModelRecord.id == hybrid["id"]))
        artifact_hash = record.artifact_sha256
    first = load_model(hybrid["id"], artifact_hash)
    second = load_model(hybrid["id"], artifact_hash)
    frame = first["estimator"].named_steps["preprocessor"]
    raw = __import__("pandas").DataFrame([sample])
    assert np.allclose(first["estimator"].predict_proba(raw), second["estimator"].predict_proba(raw), atol=1e-10)

    explanation = client.post(f"/api/models/{hybrid['id']}/explain", json={"method": "shap", "max_samples": 2, "repeats": 1, "max_features": 16})
    assert explanation.status_code == 201, explanation.text
    result = explanation.json()["result"]
    assert result["method"] == "shap"
    assert result["method_display"] == "SHAP — Final Hybrid Output"
    assert result["explanation_level"] == "global_dataset"
    assert result["output_semantics"] == "final positive-class probability"
    assert result["explained_case_count"] == 2
    assert len(result["influence"]) == 16
    assert all(np.isfinite(item["magnitude"]) for item in result["influence"])
    assert any("does not establish" in item.lower() for item in result["limitations"])

    wrong_method = client.post(f"/api/models/{hybrid['id']}/explain", json={"method": "permutation", "max_samples": 2})
    assert wrong_method.status_code == 422
    assert wrong_method.json()["error"]["code"] == "hybrid_explanation_method"

    missing = dict(sample); missing.pop(next(iter(missing)))
    missing_response = client.post(f"/api/models/{hybrid['id']}/predict", json={"samples": [missing], "include_influence": True})
    assert missing_response.status_code == 422
    assert missing_response.json()["error"]["code"] == "prediction_schema"

    schema = client.get(f"/api/models/{hybrid['id']}/input-schema").json()
    categorical = next(field["name"] for field in schema["features"] if field["type"] == "string")
    unknown = dict(sample); unknown[categorical] = "__not_observed__"
    unknown_response = client.post(f"/api/models/{hybrid['id']}/predict", json={"samples": [unknown], "include_influence": True})
    assert unknown_response.status_code == 422
    assert unknown_response.json()["error"]["code"] == "shap_category_mismatch"

    comparison = client.get(f"/api/experiments/{experiment_id}/comparison")
    assert comparison.status_code == 200
    pair = comparison.json()["pairs"][0]
    assert pair["quantum_type"] == "hybrid_pennylane_torch"
    assert pair["fairness"]["controlled_comparison"] is True
    assert pair["fairness"]["status"] == "CONTROLLED COMPARISON"
    assert all(pair["fairness"][field] for field in [
        "dataset_match", "dataset_hash_match", "sample_pool_match", "split_match", "split_hash_match",
        "preprocessing_match", "feature_representation_match", "pca_dimension_match", "sample_budget_match",
        "cv_fold_match", "seed_match", "threshold_strategy_match", "holdout_match",
    ])
    assert pair["benchmark_type"] == "fair_controlled_diabetes_benchmark"
    assert pair["holdout_results"]["evaluation_population"] == "Untouched holdout evaluation"
    assert pair["operating_points"]["protocol"].startswith("OOF validation threshold")
    assert pair["quantum_resources"]["backend"] == "default.qubit"
    assert pair["quantum_resources"]["real_hardware"] is False
    assert pair["quantum_resources"]["shots"] is None
    assert "winner" not in pair["conclusion"].lower()

    classical = next(model for model in detail["models"] if model["model_type"] == "random_forest")
    robustness = client.post(f"/api/experiments/{experiment_id}/robustness", json={
        "model_ids": [classical["id"], hybrid["id"]],
        "scenarios": [{"perturbation_type": "missingness", "level": 0.05}],
        "random_seed": 23, "max_samples": 8,
    })
    assert robustness.status_code == 200, robustness.text
    assert len(robustness.json()["results"]) == 2
    assert all(item["status"] == "evaluated" for item in robustness.json()["results"])

    report = client.get(f"/api/experiments/{experiment_id}/report?format=json")
    assert report.status_code == 200
    report_hybrid = next(model for model in report.json()["models"] if model["model_type"] == "hybrid_pennylane_torch")
    assert report_hybrid["display_name"] == "PennyLane + PyTorch Hybrid"
    assert report_hybrid["details"]["quantum"]["real_hardware"] is False
    report_pair = report.json()["comparison"]["controlled_benchmarks"][0]
    assert report_pair["fairness"]["controlled_comparison"] is True
    reloaded = client.get(f"/api/experiments/{experiment_id}/comparison").json()
    assert reloaded["controlled_benchmarks"][0]["metric_deltas"] == pair["metric_deltas"]
    assert reloaded["controlled_benchmarks"][0]["fairness"]["comparison_fingerprint"] == pair["fairness"]["comparison_fingerprint"]
