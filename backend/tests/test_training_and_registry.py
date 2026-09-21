import time
import pytest
from app.api.schemas import ExplanationRequest, PredictionRequest
from app.data.splitting import prepare_data
from app.models.training import train_model
from app.models.prediction import predict
from app.storage.files import save_model, load_model

@pytest.mark.parametrize("kind", ["logistic_regression", "svm", "random_forest"])
def test_classical_training_outputs_are_computed(kind, config):
    data = prepare_data(config)
    bundle, metrics, details = train_model(kind, config, data, lambda _: None)
    assert metrics["test"]["sample_count"] == len(data.test)
    assert metrics["training"]["sample_count"] == len(data.train)
    assert len(metrics["validation"]["folds"]) == config.cv_folds
    assert details["split"]["split_hash"] == data.split_hash
    assert metrics["timing"]["final_training_seconds"] >= 0
    from uuid import uuid4
    identity = str(uuid4())
    digest = save_model(identity, bundle)
    assert load_model(identity, digest)["features"] == bundle["features"]

def poll_job(client, identity, timeout=90):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        response = client.get(f"/api/training/jobs/{identity}")
        assert response.status_code == 200
        value = response.json()
        if value["status"] not in ("queued", "running", "cancel_requested"):
            return value
        time.sleep(.1)
    pytest.fail("Training job did not finish within the test timeout.")

@pytest.mark.integration
def test_http_experiment_prediction_report_and_rerun(client, config, registered):
    request = config.model_dump(mode="json")
    response = client.post("/api/training/jobs", json=request)
    assert response.status_code == 202, response.text
    created = response.json()
    job = poll_job(client, created["job"]["id"])
    assert job["status"] == "succeeded", job["errors"]
    identity = created["experiment"]["id"]
    result = client.get(f"/api/experiments/{identity}").json()
    model = next(m for m in result["models"] if m["status"] == "ready")
    comparison = client.get(f"/api/experiments/{identity}/comparison").json()
    assert comparison["experiment_id"] == identity
    assert model["details"]["dataset_provenance"]["dataset_hash"] == registered.sha256
    schema = client.get(f"/api/models/{model['id']}/input-schema").json()
    from app.data.service import load_frame
    _, frame = load_frame(registered.id)
    sample = {name: None if value != value else value for name, value in frame[registered.provenance["features"]].iloc[0].to_dict().items()}
    prediction = client.post(f"/api/models/{model['id']}/predict", json={"samples": [sample]})
    assert prediction.status_code == 200, prediction.text
    assert prediction.json()["predictions"][0]["predicted_class"] in ("positive", "negative")
    assert "Research Prototype" in prediction.json()["disclaimer"]
    assert client.get(f"/api/models/{model['id']}/demo-sample").status_code == 403
    report = client.get(f"/api/experiments/{identity}/report?format=html")
    assert report.status_code == 200 and "Research Prototype" in report.text
    assert "clinical validation" in report.text
    assert client.delete(f"/api/datasets/{registered.id}").status_code == 409
    rerun = client.post(f"/api/experiments/{identity}/rerun").json()
    assert rerun["experiment"]["id"] != identity
    assert rerun["experiment"]["parent_id"] == identity
    assert poll_job(client, rerun["job"]["id"])["status"] == "succeeded"
