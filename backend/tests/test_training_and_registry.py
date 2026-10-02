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
    assert metrics["operating_point"]["threshold_source"] == "configured_fixed_threshold"
    assert metrics["operating_point"]["selected_threshold"] == (config.probability_threshold if kind != "svm" else 0.0)
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
    assert model["metrics"]["operating_point"]["threshold_source"] == "configured_fixed_threshold"
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
    rerun_detail = client.get(f"/api/experiments/{rerun['experiment']['id']}").json()
    rerun_model = next(m for m in rerun_detail["models"] if m["status"] == "ready")
    assert rerun_model["metrics"]["operating_point"]["selected_threshold"] == model["metrics"]["operating_point"]["selected_threshold"]


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


def test_experiment_names_increment_and_child_executions_are_persisted(client, config, registered):
    from sqlalchemy import func, select
    from app.database import session_scope
    from app.storage.entities import Experiment

    with session_scope() as session:
        starting_count = session.scalar(
            select(func.count()).select_from(Experiment).where(Experiment.dataset_id == registered.id)
        ) or 0

    payload = config.model_copy(update={
        "models": ["logistic_regression", "svm", "random_forest"],
    }).model_dump(mode="json")
    response = client.post("/api/training/jobs", json=payload)
    assert response.status_code == 202, response.text
    created = response.json()
    assert created["experiment"]["name"] == f"{registered.name} · Training {starting_count + 1:02d}"

    detail = client.get(f"/api/training/jobs/{created['job']['id']}").json()
    assert detail["experiment_name"] == created["experiment"]["name"]
    assert {model["model_type"] for model in detail["models"]} == set(payload["models"])
    assert {model["status"] for model in detail["models"]} <= {"queued", "running", "ready", "failed"}

    finished = poll_job(client, created["job"]["id"])
    assert finished["status"] == "succeeded"
    assert finished["progress"] == 100
    assert all(model["status"] == "ready" and model["progress"] == 100 for model in finished["models"])

    subsequent = []
    for offset in (2, 3):
        response = client.post("/api/training/jobs", json=config.model_dump(mode="json"))
        assert response.status_code == 202, response.text
        value = response.json()
        assert value["experiment"]["name"] == f"{registered.name} · Training {starting_count + offset:02d}"
        subsequent.append(value["job"]["id"])
    for job_id in subsequent:
        client.post(f"/api/training/jobs/{job_id}/cancel")
        assert poll_job(client, job_id)["status"] in {"cancelled", "succeeded"}


def test_one_model_failure_does_not_hide_other_executions(client, config, monkeypatch):
    import app.jobs.manager as jobs_module

    original = jobs_module.train_model
    def fail_svm(kind, training_config, data, checkpoint):
        if kind == "svm":
            raise RuntimeError("synthetic test failure")
        return original(kind, training_config, data, checkpoint)

    monkeypatch.setattr(jobs_module, "train_model", fail_svm)
    payload = config.model_copy(update={
        "models": ["logistic_regression", "svm"],
    }).model_dump(mode="json")
    created = client.post("/api/training/jobs", json=payload).json()
    finished = poll_job(client, created["job"]["id"])
    assert finished["status"] == "partial"
    states = {model["model_type"]: model["status"] for model in finished["models"]}
    assert states == {"logistic_regression": "ready", "svm": "failed"}
    assert finished["progress"] == 100


def test_running_cancellation_reaches_backend_terminal_state(client, config, monkeypatch):
    import threading
    import app.jobs.manager as jobs_module

    started = threading.Event()
    def cancellable_training(_kind, _training_config, _data, checkpoint):
        started.set()
        while True:
            checkpoint("test safe cancellation boundary")

    monkeypatch.setattr(jobs_module, "train_model", cancellable_training)
    created = client.post("/api/training/jobs", json=config.model_dump(mode="json")).json()
    assert started.wait(timeout=5)

    queued = client.post("/api/training/jobs", json=config.model_dump(mode="json")).json()
    queued_cancel = client.post(f"/api/training/jobs/{queued['job']['id']}/cancel")
    assert queued_cancel.status_code == 200
    assert queued_cancel.json()["status"] == "cancelled"
    assert all(model["status"] == "cancelled" for model in queued_cancel.json()["models"])

    cancelled = client.post(f"/api/training/jobs/{created['job']['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] in {"cancel_requested", "cancelled"}
    finished = poll_job(client, created["job"]["id"])
    assert finished["status"] == "cancelled"
    assert all(model["status"] == "cancelled" for model in finished["models"])
