import time
from uuid import uuid4

import pytest
from sqlalchemy import inspect, select

from app.artifacts.service import register_metadata
from app.database import engine, session_scope
from app.migrations import MIGRATION_ID, apply_migrations
from app.runs.service import create_run, transition
from app.storage.entities import Artifact, Experiment, Job, ModelRecord, Run
from app.storage.files import digest, safe_path
from app.utils.errors import AppError
from app.utils.serialization import utcnow


def poll(client, job_id, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/training/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] not in {"queued", "running", "cancel_requested"}:
            return job
        time.sleep(0.05)
    pytest.fail("Run-backed training job did not finish.")


def test_run_lifecycle_parent_integrity_and_terminal_states(registered, config):
    experiment = Experiment(
        id=str(uuid4()), dataset_id=registered.id, status="queued",
        config=config.model_dump(mode="json"), summary={},
    )
    with session_scope() as session:
        session.add(experiment)
        session.flush()
        first = create_run(
            session, experiment=experiment, config=experiment.config,
            operation_key=f"test-run:{uuid4()}",
            execution_metadata={"executor": "test"},
            reproducibility_metadata={"dataset_hash": registered.sha256},
        )
        second = create_run(
            session, experiment=experiment, config=experiment.config,
            operation_key=f"test-run:{uuid4()}",
            execution_metadata={"executor": "test"},
            reproducibility_metadata={"dataset_hash": registered.sha256},
        )
        assert first.experiment_id == second.experiment_id == experiment.id
        transition(session, first, "queued")
        transition(session, first, "running")
        transition(session, first, "completed", result_summary={"models_persisted": 1})
        transition(session, second, "cancelled")
        assert first.completed_at is not None and second.cancelled_at is not None
        with pytest.raises(AppError):
            transition(session, first, "running")

    with session_scope() as session:
        assert len(list(session.scalars(select(Run).where(Run.experiment_id == experiment.id)))) == 2


def test_failed_run_is_retained_with_safe_failure_metadata(registered, config):
    experiment = Experiment(
        id=str(uuid4()), dataset_id=registered.id, status="failed",
        config=config.model_dump(mode="json"), summary={},
    )
    with session_scope() as session:
        session.add(experiment)
        session.flush()
        run = create_run(
            session, experiment=experiment, config=experiment.config,
            operation_key=f"failed-run:{uuid4()}",
            execution_metadata={}, reproducibility_metadata={},
        )
        transition(session, run, "failed", failure={"code": "training_failed", "message": "Safe failure metadata only."})
        run_id = run.id
    with session_scope() as session:
        stored = session.get(Run, run_id)
        assert stored.status == "failed"
        assert stored.failed_at is not None
        assert stored.failure == {"code": "training_failed", "message": "Safe failure metadata only."}


def test_training_creates_run_job_model_and_integrity_registered_artifacts(client, config):
    response = client.post("/api/training/jobs", json=config.model_dump(mode="json"))
    assert response.status_code == 202, response.text
    created = response.json()
    job = poll(client, created["job"]["id"])
    assert job["status"] == "succeeded", job["errors"]
    assert job["run_id"]

    runs = client.get(f"/api/experiments/{created['experiment']['id']}/runs")
    assert runs.status_code == 200
    assert len(runs.json()) == 1
    run = runs.json()[0]
    assert run["status"] == "completed"
    assert run["result_summary"]["models_persisted"] == 1

    detail = client.get(f"/api/runs/{run['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["job"]["id"] == job["id"]
    model = body["models"][0]
    assert model["run_id"] == run["id"]
    artifact_types = {item["artifact_type"] for item in body["artifacts"]}
    assert {"model", "evaluation_result"} <= artifact_types

    model_artifact = next(item for item in body["artifacts"] if item["artifact_type"] == "model")
    assert model_artifact["storage_reference"] == f"models/{model['id']}.dill"
    assert not model_artifact["storage_reference"].startswith(("http://", "https://", "/"))
    assert model_artifact["integrity_hash"] == digest(safe_path("models", model["id"], ".dill"))

    legacy = client.get(f"/api/models/{model['id']}")
    assert legacy.status_code == 200
    assert legacy.json()["id"] == model["id"]

    report = client.get(f"/api/experiments/{created['experiment']['id']}/report?format=html")
    assert report.status_code == 200
    artifacts = client.get(f"/api/runs/{run['id']}/artifacts").json()
    assert "report" in {item["artifact_type"] for item in artifacts}


def test_existing_experiment_can_execute_multiple_runs_and_retry_is_idempotent(client, config):
    first = client.post(
        "/api/training/jobs",
        json=config.model_dump(mode="json"),
        headers={"Idempotency-Key": f"initial-{uuid4()}"},
    )
    assert first.status_code == 202
    poll(client, first.json()["job"]["id"])
    experiment_id = first.json()["experiment"]["id"]

    key = f"repeat-{uuid4()}"
    second = client.post(f"/api/experiments/{experiment_id}/runs", headers={"Idempotency-Key": key})
    assert second.status_code == 202, second.text
    poll(client, second.json()["job"]["id"])
    retry = client.post(f"/api/experiments/{experiment_id}/runs", headers={"Idempotency-Key": key})
    assert retry.status_code == 202
    assert retry.json()["run"]["id"] == second.json()["run"]["id"]
    assert retry.json()["job"]["id"] == second.json()["job"]["id"]

    runs = client.get(f"/api/experiments/{experiment_id}/runs").json()
    assert len(runs) == 2
    assert {item["experiment_id"] for item in runs} == {experiment_id}


def test_artifact_duplicate_prevention_and_metadata_retrieval(client, registered, config):
    experiment = Experiment(
        id=str(uuid4()), dataset_id=registered.id, status="succeeded",
        config=config.model_dump(mode="json"), summary={},
    )
    operation_key = f"metadata:{uuid4()}"
    with session_scope() as session:
        session.add(experiment)
        session.flush()
        run = create_run(
            session, experiment=experiment, config=experiment.config,
            operation_key=f"run:{uuid4()}", execution_metadata={}, reproducibility_metadata={},
        )
        transition(session, run, "queued")
        transition(session, run, "running")
        transition(session, run, "completed")
        first = register_metadata(
            session, experiment_id=experiment.id, run_id=run.id, model_id=None,
            artifact_type="experiment_manifest", name="Test manifest", description="Test metadata.",
            payload={"dataset_hash": registered.sha256}, operation_key=operation_key,
        )
        duplicate = register_metadata(
            session, experiment_id=experiment.id, run_id=run.id, model_id=None,
            artifact_type="experiment_manifest", name="Test manifest", description="Test metadata.",
            payload={"dataset_hash": registered.sha256}, operation_key=operation_key,
        )
        assert duplicate.id == first.id
        artifact_id = first.id
        with pytest.raises(AppError):
            register_metadata(
                session, experiment_id=experiment.id, run_id=run.id, model_id=None,
                artifact_type="experiment_manifest", name="Changed", description="Changed.",
                payload={"dataset_hash": "different"}, operation_key=operation_key,
            )

    response = client.get(f"/api/artifacts/{artifact_id}")
    assert response.status_code == 200
    assert response.json()["integrity_hash"]
    assert response.json()["hash_algorithm"] == "sha256"
    assert response.json()["storage_reference"] is None


def test_legacy_records_remain_readable_without_fabricated_run(client, registered):
    experiment_id, job_id, model_id = str(uuid4()), str(uuid4()), str(uuid4())
    with session_scope() as session:
        session.add(Experiment(
            id=experiment_id, dataset_id=registered.id, parent_id=None, status="succeeded",
            config={}, summary={"legacy": True}, created_at=utcnow(),
        ))
        session.add(Job(
            id=job_id, experiment_id=experiment_id, run_id=None, status="succeeded",
            progress=100, state="Legacy completed job", errors=[],
            created_at=utcnow(), updated_at=utcnow(),
        ))
        session.add(ModelRecord(
            id=model_id, experiment_id=experiment_id, run_id=None, dataset_id=registered.id,
            model_type="logistic_regression", status="failed", details={"legacy": True},
            metrics={}, created_at=utcnow(),
        ))
    detail = client.get(f"/api/experiments/{experiment_id}")
    assert detail.status_code == 200
    assert detail.json()["jobs"][0]["run_id"] is None
    assert detail.json()["models"][0]["run_id"] is None
    assert client.get(f"/api/experiments/{experiment_id}/runs").json() == []


def test_migration_is_additive_idempotent_and_indexed():
    apply_migrations()
    apply_migrations()
    schema = inspect(engine)
    assert {"runs", "artifacts", "schema_migrations"} <= set(schema.get_table_names())
    assert "run_id" in {column["name"] for column in schema.get_columns("jobs")}
    assert "run_id" in {column["name"] for column in schema.get_columns("models")}
    with engine.connect() as connection:
        count = connection.exec_driver_sql(
            "SELECT COUNT(*) FROM schema_migrations WHERE id = ?", (MIGRATION_ID,)
        ).scalar_one()
    assert count == 1


def test_run_and_artifact_api_reject_malformed_or_missing_ids(client):
    assert client.get("/api/runs/not-a-uuid").status_code == 422
    assert client.get("/api/artifacts/not-a-uuid").status_code == 422
    assert client.get(f"/api/runs/{uuid4()}").status_code == 404
    assert client.get(f"/api/artifacts/{uuid4()}").status_code == 404