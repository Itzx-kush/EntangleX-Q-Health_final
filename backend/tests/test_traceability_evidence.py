from uuid import uuid4

from app.artifacts.service import register_metadata
from app.audit.service import record_event
from app.database import session_scope
from app.runs.service import create_run, transition
from app.storage.entities import Dataset, Experiment, Job, ModelRecord
from app.utils.serialization import utcnow


def _experiment(registered, config, *, parent_id=None, config_overrides=None):
    payload = config.model_dump(mode="json")
    payload.update(config_overrides or {})
    return Experiment(
        id=str(uuid4()),
        dataset_id=registered.id,
        parent_id=parent_id,
        status="succeeded",
        config=payload,
        summary={},
        created_at=utcnow(),
    )


def test_complete_traceability_chain_reuses_recorded_evidence(client, registered, config):
    experiment = _experiment(registered, config, config_overrides={"dataset_version_id": registered.current_version_id})
    with session_scope() as session:
        session.add(experiment)
        session.flush()
        run = create_run(
            session,
            experiment=experiment,
            config=experiment.config,
            operation_key=f"trace-run:{uuid4()}",
            execution_metadata={"duration_seconds": 12.5},
            reproducibility_metadata={"dataset_hash": registered.sha256, "software": {"python": "recorded"}},
        )
        run.configuration_fingerprint = "a" * 64
        run.reproducibility_status = "CONFIGURATION_RECORDED"
        transition(session, run, "queued")
        transition(session, run, "running")
        transition(session, run, "completed")
        job = Job(
            id=str(uuid4()), experiment_id=experiment.id, run_id=run.id,
            status="succeeded", progress=100, state="Completed", errors=[],
            configuration_fingerprint="a" * 64, created_at=utcnow(), updated_at=utcnow(),
        )
        model = ModelRecord(
            id=str(uuid4()), experiment_id=experiment.id, run_id=run.id,
            dataset_id=registered.id, model_type="logistic_regression",
            status="ready", artifact_sha256="b" * 64, details={}, metrics={},
            created_at=utcnow(),
        )
        session.add_all([job, model])
        session.flush()
        artifact = register_metadata(
            session,
            experiment_id=experiment.id,
            run_id=run.id,
            model_id=model.id,
            artifact_type="model",
            name="Recorded model artifact",
            description="Synthetic test metadata.",
            payload={"model_id": model.id},
            operation_key=f"trace-artifact:{uuid4()}",
        )
        record_event(
            session,
            event_type="EXPERIMENT_COMPLETED",
            event_category="EXPERIMENT",
            object_type="experiment",
            object_id=experiment.id,
            source_component="test",
        )
        experiment_id, artifact_id = experiment.id, artifact.id

    response = client.get(f"/api/experiments/{experiment_id}")
    assert response.status_code == 200
    trace = response.json()["traceability"]
    assert trace["dataset"]["sha256"] == registered.sha256
    assert trace["dataset"]["version"]["id"] == registered.current_version_id
    assert trace["experiment"]["configuration_fingerprint"] == "a" * 64
    assert trace["run"]["duration_seconds"] == 12.5
    assert trace["run"]["job"]["status"] == "succeeded"
    assert trace["models"][0]["artifact_hash"] == "b" * 64
    assert trace["artifacts"][0]["id"] == artifact_id
    assert trace["audit"]["events_recorded"] is True
    assert trace["reproducibility"]["status"] == "RECORDED"


def test_partial_legacy_traceability_is_truthful(client, registered, config):
    parent = _experiment(registered, config)
    child = _experiment(
        registered,
        config,
        parent_id=parent.id,
        config_overrides={"dataset_version_id": None},
    )
    with session_scope() as session:
        session.add_all([parent, child])
        child_id, parent_id = child.id, parent.id

    trace = client.get(f"/api/experiments/{child_id}").json()["traceability"]
    assert trace["experiment"]["parent_id"] == parent_id
    assert trace["dataset"]["version"] is None
    assert trace["experiment"]["configuration_fingerprint"] is None
    assert trace["run"] is None
    assert trace["models"] == []
    assert trace["artifacts"] == []
    assert trace["evidence"]["html_report_available"] is False
    assert trace["audit"]["events_recorded"] is False
    assert trace["reproducibility"]["status"] == "INSUFFICIENT"


def test_missing_hashes_are_not_fabricated(client, registered, config):
    experiment = _experiment(registered, config)
    with session_scope() as session:
        dataset = session.get(Dataset, registered.id)
        original_hash = dataset.sha256
        dataset.sha256 = ""
        session.add(experiment)
        session.flush()
        model = ModelRecord(
            id=str(uuid4()), experiment_id=experiment.id, run_id=None,
            dataset_id=registered.id, model_type="logistic_regression",
            status="ready", artifact_sha256=None, details={}, metrics={},
            created_at=utcnow(),
        )
        session.add(model)
        experiment_id = experiment.id

    try:
        trace = client.get(f"/api/experiments/{experiment_id}").json()["traceability"]
        assert trace["dataset"]["sha256"] in ("", None)
        assert trace["models"][0]["artifact_hash"] is None
        assert "dataset_hash" not in trace["reproducibility"]["recorded_fields"]
    finally:
        with session_scope() as session:
            session.get(Dataset, registered.id).sha256 = original_hash


def test_traceability_never_exposes_storage_paths(client, registered, config):
    experiment = _experiment(registered, config)
    with session_scope() as session:
        session.add(experiment)
        session.flush()
        register_metadata(
            session,
            experiment_id=experiment.id,
            run_id=None,
            model_id=None,
            artifact_type="experiment_evidence",
            name="Metadata evidence",
            description="No public storage path.",
            payload={"safe": True},
            operation_key=f"trace-security:{uuid4()}",
        )
        experiment_id = experiment.id

    body = client.get(f"/api/experiments/{experiment_id}").json()["traceability"]
    assert body["artifacts"][0]["storage_status"] == "metadata_only"
    assert "storage_reference" not in body["artifacts"][0]
    assert "filename" not in body["dataset"]