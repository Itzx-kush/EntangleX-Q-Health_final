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


def test_create_job_success(client, config, registered):
    payload = config.model_dump(mode="json")
    response = client.post("/api/training/jobs", json=payload)
    assert response.status_code == 202, response.text
    data = response.json()
    assert "job" in data and "experiment" in data
    assert data["job"]["experiment_id"] == data["experiment"]["id"]
    assert data["job"]["status"] in ("queued", "running", "succeeded")
    assert data["experiment"]["dataset_id"] == str(registered.id)


def test_create_job_dataset_not_found(client, config):
    from uuid import uuid4
    payload = config.model_dump(mode="json")
    payload["dataset_id"] = str(uuid4())
    response = client.post("/api/training/jobs", json=payload)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_create_job_validation_errors(client, config):
    # Missing dataset_id
    payload = config.model_dump(mode="json")
    del payload["dataset_id"]
    response = client.post("/api/training/jobs", json=payload)
    assert response.status_code == 422

    # Invalid dataset_id format
    payload = config.model_dump(mode="json")
    payload["dataset_id"] = "not-a-uuid"
    response = client.post("/api/training/jobs", json=payload)
    assert response.status_code == 422

    # Empty models list
    payload = config.model_dump(mode="json")
    payload["models"] = []
    response = client.post("/api/training/jobs", json=payload)
    assert response.status_code == 422

    # Duplicate models in list
    payload = config.model_dump(mode="json")
    payload["models"] = ["logistic_regression", "logistic_regression"]
    response = client.post("/api/training/jobs", json=payload)
    assert response.status_code == 422

    # Mismatched quantum configuration (vqc without matching pca_components and qubits)
    payload = config.model_dump(mode="json")
    payload["models"] = ["vqc"]
    payload["pipeline"]["pca_components"] = 2
    payload["quantum"]["qubits"] = 4
    response = client.post("/api/training/jobs", json=payload)
    assert response.status_code == 422


def test_create_job_worker_unavailable(client, config, monkeypatch):
    from app.jobs.manager import manager
    monkeypatch.setattr(manager, "executor", None)
    payload = config.model_dump(mode="json")
    response = client.post("/api/training/jobs", json=payload)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "worker_unavailable"


def test_create_job_queue_full(client, config, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "max_queued_jobs", 0)
    payload = config.model_dump(mode="json")
    response = client.post("/api/training/jobs", json=payload)
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "queue_full"


def test_create_job_mock_enqueue(client, config, registered):
    from unittest.mock import patch
    from app.jobs.manager import manager
    from app.storage.entities import Experiment, Job
    from app.utils.serialization import utcnow
    from uuid import uuid4

    now = utcnow()
    mock_job = Job(id=str(uuid4()), experiment_id=str(uuid4()), status="queued", progress=0, state="Queued", errors=[], created_at=now, updated_at=now)
    mock_exp = Experiment(id=mock_job.experiment_id, dataset_id=str(registered.id), parent_id=None, status="created", config={}, summary={}, created_at=now)

    with patch.object(manager, "enqueue", return_value=(mock_job, mock_exp)) as mock_enqueue:
        payload = config.model_dump(mode="json")
        response = client.post("/api/training/jobs", json=payload)
        assert response.status_code == 202
        assert mock_enqueue.called
        called_config = mock_enqueue.call_args[0][0]
        assert str(called_config.dataset_id) == str(registered.id)
        data = response.json()
        assert data["job"]["id"] == mock_job.id
        assert data["experiment"]["id"] == mock_exp.id
