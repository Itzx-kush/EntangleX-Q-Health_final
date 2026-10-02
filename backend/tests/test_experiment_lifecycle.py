import threading
import time
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.database import session_scope
from app.storage.entities import Dataset, DatasetVersion, Experiment, Job


def create_experiment(registered, status: str, *, name: str | None = None, job_status: str | None = None):
    identity = str(uuid4())
    with session_scope() as session:
        experiment = Experiment(
            id=identity,
            name=name or f"Lifecycle {identity[:8]}",
            dataset_id=registered.id,
            status=status,
            config={"models": [], "seed": 42},
            summary={},
        )
        session.add(experiment)
        if job_status:
            session.add(Job(
                id=str(uuid4()),
                experiment_id=identity,
                status=job_status,
                progress=100 if job_status in {"succeeded", "failed", "cancelled"} else 10,
                state=job_status,
                errors=[],
            ))
    return identity


def poll_job(client, identity: str, timeout: float = 10):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = client.get(f"/api/training/jobs/{identity}").json()
        if value["status"] not in {"queued", "running", "cancel_requested"}:
            return value
        time.sleep(0.05)
    pytest.fail("Job did not reach a terminal state.")


def test_completed_experiment_is_archived_and_scientific_records_survive(client, registered):
    identity = create_experiment(registered, "succeeded", job_status="succeeded")
    count_before = client.get("/api/summary").json()["counts"]["experiments"]
    with session_scope() as session:
        dataset = session.get(Dataset, registered.id)
        version_id = dataset.current_version_id

    response = client.delete(f"/api/experiments/{identity}")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "archived"
    assert result["already_deleted"] is False
    assert result["preserved_records"]["jobs"] == 1

    assert identity not in {item["id"] for item in client.get("/api/experiments").json()}
    summary = client.get("/api/summary").json()
    assert summary["counts"]["experiments"] == count_before - 1
    assert identity not in {item["id"] for item in summary["recent_experiments"]}
    assert client.get(f"/api/experiments/{identity}").status_code == 410
    repeated = client.delete(f"/api/experiments/{identity}")
    assert repeated.status_code == 200
    assert repeated.json()["already_deleted"] is True

    with session_scope() as session:
        archived = session.get(Experiment, identity)
        assert archived is not None and archived.deleted_at is not None
        assert session.get(Dataset, registered.id) is not None
        assert session.get(DatasetVersion, version_id) is not None
        job = session.scalar(select(Job).where(Job.experiment_id == identity))
        assert job is not None and job.status == "succeeded"


@pytest.mark.parametrize("status", ["failed", "cancelled"])
def test_failed_and_cancelled_experiments_may_be_archived(client, registered, status):
    identity = create_experiment(registered, status, job_status=status)
    response = client.delete(f"/api/experiments/{identity}")
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


@pytest.mark.parametrize("status", ["queued", "running", "cancel_requested"])
def test_active_experiment_deletion_is_rejected_without_orphaning_job(client, registered, status):
    identity = create_experiment(registered, status, job_status=status)
    response = client.delete(f"/api/experiments/{identity}")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "experiment_active"
    with session_scope() as session:
        experiment = session.get(Experiment, identity)
        job = session.scalar(select(Job).where(Job.experiment_id == identity))
        assert experiment.deleted_at is None
        assert job is not None and job.status == status


def test_deleting_one_of_multiple_experiments_preserves_names_and_dataset(client, registered):
    first = create_experiment(registered, "succeeded", name="Shared Dataset · Training 01")
    middle = create_experiment(registered, "failed", name="Shared Dataset · Training 02")
    last = create_experiment(registered, "cancelled", name="Shared Dataset · Training 03")

    assert client.delete(f"/api/experiments/{middle}").status_code == 200
    records = {item["id"]: item for item in client.get("/api/experiments").json()}
    assert records[first]["name"] == "Shared Dataset · Training 01"
    assert middle not in records
    assert records[last]["name"] == "Shared Dataset · Training 03"
    assert client.get(f"/api/datasets/{registered.id}").status_code == 200


def test_cancel_then_delete_leaves_no_active_or_orphaned_job(client, config, registered, monkeypatch):
    import app.jobs.manager as jobs_module

    started = threading.Event()
    def cancellable_training(_kind, _config, _data, checkpoint):
        started.set()
        while True:
            checkpoint("lifecycle cancellation boundary")

    monkeypatch.setattr(jobs_module, "train_model", cancellable_training)
    created = client.post("/api/training/jobs", json=config.model_dump(mode="json")).json()
    assert started.wait(timeout=5)
    job_id = created["job"]["id"]
    experiment_id = created["experiment"]["id"]
    assert client.post(f"/api/training/jobs/{job_id}/cancel").status_code == 200
    assert poll_job(client, job_id)["status"] == "cancelled"

    deleted = client.delete(f"/api/experiments/{experiment_id}")
    assert deleted.status_code == 200, deleted.text
    with session_scope() as session:
        job = session.get(Job, job_id)
        assert job is not None and job.status == "cancelled"
        assert session.get(Experiment, experiment_id).deleted_at is not None
        assert session.get(Dataset, registered.id) is not None


def test_delete_handles_invalid_and_missing_experiment_ids(client):
    invalid = client.delete("/api/experiments/not-a-uuid")
    assert invalid.status_code == 422
    missing = client.delete(f"/api/experiments/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"