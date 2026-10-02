import copy
import time
from uuid import uuid4

import pytest

from app.api.schemas import TrainingConfig
from app.config import get_settings
from app.data.splitting import prepare_data
from app.database import session_scope
from app.manifests.service import (
    _manifest_hash,
    configuration_fingerprint,
    create_locked_manifest,
    get_manifest,
    validate_manifest_consistency,
    verify_manifest_integrity,
)
from app.runs.service import create_run, transition
from app.storage.entities import Artifact, Experiment, Run
from app.utils.errors import AppError
from app.utils.serialization import canonical_json_bytes


def poll(client, job_id, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = client.get(f"/api/training/jobs/{job_id}").json()
        if value["status"] not in {"queued", "running", "cancel_requested"}:
            return value
        time.sleep(0.05)
    pytest.fail("Manifest-backed training job did not finish.")


def create_manifest_fixture(config, registered):
    data = prepare_data(config)
    experiment = Experiment(
        id=str(uuid4()), dataset_id=registered.id, status="queued",
        config=config.model_dump(mode="json"), summary={},
    )
    with session_scope() as session:
        session.add(experiment)
        session.flush()
        run = create_run(
            session, experiment=experiment, config=experiment.config,
            operation_key=f"manifest-test:{uuid4()}",
            execution_metadata={"executor": "test"},
            reproducibility_metadata={"dataset_hash": registered.sha256},
        )
        artifact = create_locked_manifest(
            session, run=run, experiment=experiment, data=data,
            config=config, job_id=str(uuid4()),
        )
        return run.id, artifact.id


def test_manifest_has_required_sections_and_is_locked_before_execution(config, registered):
    run_id, artifact_id = create_manifest_fixture(config, registered)
    run, artifact, manifest = get_manifest(run_id)
    expected = {
        "identity", "dataset", "sampling", "split", "cross_validation",
        "preprocessing", "feature_engineering", "feature_selection",
        "dimensionality_reduction", "models", "threshold_protocol",
        "evaluation_protocol", "software_environment", "runtime_environment",
        "execution_at_lock", "reproducibility",
    }
    assert set(manifest) == expected
    assert run.manifest_artifact_id == artifact_id == artifact.id
    assert run.manifest_locked_at is not None
    assert artifact.artifact_type == "experiment_manifest"
    assert artifact.immutable is True and artifact.storage_reference is None
    assert manifest["dataset"]["sha256"] == registered.sha256
    assert manifest["dataset"]["feature_names"] == registered.provenance["features"]
    assert "rows" not in manifest["dataset"]
    assert manifest["execution_at_lock"]["started_at"] is None
    assert manifest["reproducibility"]["status"] == "CONFIGURATIONALLY_REPRODUCIBLE"
    assert manifest["reproducibility"]["bitwise_reproducible"] is False


def test_canonical_manifest_hash_is_order_independent(config, registered):
    run_id, _ = create_manifest_fixture(config, registered)
    _, _, manifest = get_manifest(run_id)
    reordered = {key: manifest[key] for key in reversed(list(manifest))}
    reordered["identity"] = {
        key: reordered["identity"][key] for key in reversed(list(reordered["identity"]))
    }
    assert canonical_json_bytes(manifest) == canonical_json_bytes(reordered)
    assert _manifest_hash(manifest) == _manifest_hash(reordered)
    assert _manifest_hash(manifest) == manifest["identity"]["manifest_hash"]


def test_configuration_fingerprint_ignores_identity_time_and_runtime_but_changes_science(config, registered):
    run_id, _ = create_manifest_fixture(config, registered)
    _, _, manifest = get_manifest(run_id)
    baseline = configuration_fingerprint(manifest)
    volatile = copy.deepcopy(manifest)
    volatile["identity"]["created_at"] = "2099-01-01T00:00:00+00:00"
    volatile["identity"]["manifest_id"] = str(uuid4())
    volatile["runtime_environment"]["logical_cpu_count"] = 999
    volatile["execution_at_lock"]["manifest_locked_at"] = "2099-01-01T00:00:00+00:00"
    assert configuration_fingerprint(volatile) == baseline

    changed = copy.deepcopy(manifest)
    changed["preprocessing"]["scaling"] = "robust"
    assert configuration_fingerprint(changed) != baseline
    changed_dataset = copy.deepcopy(manifest)
    changed_dataset["dataset"]["sha256"] = "0" * 64
    assert configuration_fingerprint(changed_dataset) != baseline


def test_manifest_creation_is_idempotent_and_cannot_relock_after_run_starts(config, registered):
    run_id, artifact_id = create_manifest_fixture(config, registered)
    data = prepare_data(config)
    with session_scope() as session:
        run = session.get(Run, run_id)
        experiment = session.get(Experiment, run.experiment_id)
        same = create_locked_manifest(
            session, run=run, experiment=experiment, data=data,
            config=config, job_id=str(uuid4()),
        )
        assert same.id == artifact_id
        unmanifested = create_run(
            session, experiment=experiment, config=experiment.config,
            operation_key=f"late-manifest:{uuid4()}",
            execution_metadata={}, reproducibility_metadata={},
        )
        transition(session, unmanifested, "queued")
        with pytest.raises(AppError, match="before scientific execution"):
            create_locked_manifest(
                session, run=unmanifested, experiment=experiment, data=data,
                config=config, job_id=str(uuid4()),
            )


def test_valid_manifest_passes_and_tampering_is_detected_without_repair(config, registered):
    run_id, artifact_id = create_manifest_fixture(config, registered)
    valid = verify_manifest_integrity(run_id)
    assert valid.valid is True and valid.errors == []
    with session_scope() as session:
        artifact = session.get(Artifact, artifact_id)
        tampered = copy.deepcopy(artifact.details)
        tampered["preprocessing"]["scaling"] = "tampered"
        artifact.details = tampered
    invalid = verify_manifest_integrity(run_id)
    assert invalid.valid is False
    assert "manifest_hash_mismatch" in invalid.errors
    assert "configuration_fingerprint_mismatch" in invalid.errors
    with session_scope() as session:
        assert session.get(Artifact, artifact_id).details["preprocessing"]["scaling"] == "tampered"


def test_focused_consistency_validation_rejects_identity_dataset_and_quantum_mismatches(config, registered):
    run_id, artifact_id = create_manifest_fixture(config, registered)
    with session_scope() as session:
        run = session.get(Run, run_id)
        artifact = session.get(Artifact, artifact_id)
        original = copy.deepcopy(artifact.details)
    wrong_run = copy.deepcopy(original)
    wrong_run["identity"]["run_id"] = str(uuid4())
    assert "run_id_mismatch" in validate_manifest_consistency(run, artifact, wrong_run)
    wrong_experiment = copy.deepcopy(original)
    wrong_experiment["identity"]["experiment_id"] = str(uuid4())
    assert "experiment_id_mismatch" in validate_manifest_consistency(run, artifact, wrong_experiment)
    wrong_dataset = copy.deepcopy(original)
    wrong_dataset["dataset"]["sha256"] = "f" * 64
    assert "dataset_hash_mismatch" in validate_manifest_consistency(run, artifact, wrong_dataset)

    quantum_config = TrainingConfig.model_validate({
        **config.model_dump(mode="json"),
        "models": ["qnn"],
        "pipeline": {**config.pipeline.model_dump(mode="json"), "pca_components": 4},
        "quantum": {**config.quantum.model_dump(mode="json"), "qubits": 4},
        "max_samples": 60,
    })
    q_run_id, q_artifact_id = create_manifest_fixture(quantum_config, registered)
    with session_scope() as session:
        q_run = session.get(Run, q_run_id)
        q_artifact = session.get(Artifact, q_artifact_id)
        wrong_quantum = copy.deepcopy(q_artifact.details)
    wrong_quantum["models"][0]["quantum"] = None
    assert "quantum_configuration_mismatch" in validate_manifest_consistency(q_run, q_artifact, wrong_quantum)


def test_training_api_creates_retrievable_manifest_provenance_and_integrity(client, config):
    created = client.post("/api/training/jobs", json=config.model_dump(mode="json"))
    assert created.status_code == 202, created.text
    job = poll(client, created.json()["job"]["id"])
    assert job["status"] == "succeeded"
    run_id = job["run_id"]

    manifest_response = client.get(f"/api/runs/{run_id}/manifest")
    assert manifest_response.status_code == 200
    body = manifest_response.json()
    assert body["manifest"]["identity"]["run_id"] == run_id
    assert body["integrity"]["valid"] is True

    provenance = client.get(f"/api/runs/{run_id}/provenance").json()
    assert provenance["dataset_id"] == body["manifest"]["dataset"]["dataset_id"]
    assert provenance["manifest_artifact_id"] == body["artifact_id"]
    assert {"experiment_manifest", "model", "evaluation_result"} <= {
        item["artifact_type"] for item in provenance["artifacts"]
    }
    reproducibility = client.get(f"/api/runs/{run_id}/reproducibility").json()
    assert reproducibility["status"] == "CONFIGURATIONALLY_REPRODUCIBLE"
    assert reproducibility["bitwise_reproducible"] is False
    assert reproducibility["integrity"]["valid"] is True
    assert client.get(f"/api/runs/{run_id}/manifest/integrity").json()["valid"] is True


def test_legacy_run_remains_readable_with_incomplete_provenance(client, registered, config):
    experiment = Experiment(
        id=str(uuid4()), dataset_id=registered.id, status="succeeded",
        config=config.model_dump(mode="json"), summary={"legacy": True},
    )
    with session_scope() as session:
        session.add(experiment)
        session.flush()
        run = Run(
            id=str(uuid4()), experiment_id=experiment.id, dataset_id=registered.id,
            status="completed", operation_key=f"legacy:{uuid4()}", config=experiment.config,
            execution_metadata={}, reproducibility_metadata={}, result_summary={},
        )
        session.add(run)
        session.flush()
        run_id = run.id
    assert client.get(f"/api/runs/{run_id}").status_code == 200
    assert client.get(f"/api/runs/{run_id}/manifest").status_code == 404
    status = client.get(f"/api/runs/{run_id}/reproducibility").json()
    assert status["status"] == "INCOMPLETE_PROVENANCE"
    assert status["manifest_available"] is False
    assert status["integrity"]["errors"] == ["manifest_unavailable"]
    graph = client.get(f"/api/runs/{run_id}/provenance").json()
    assert graph["legacy_limitations"]


def test_manifest_endpoints_follow_existing_bearer_security(client, config, monkeypatch):
    import secrets
    token = secrets.token_urlsafe(32)
    monkeypatch.setattr(get_settings(), "api_token", token)
    run_id = str(uuid4())
    assert client.get(f"/api/runs/{run_id}/manifest").status_code == 401
    authorized = client.get(
        f"/api/runs/{run_id}/manifest",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert authorized.status_code == 404


def test_manifest_api_rejects_malformed_ids(client):
    for suffix in ["manifest", "manifest/integrity", "provenance", "reproducibility"]:
        assert client.get(f"/api/runs/not-a-uuid/{suffix}").status_code == 422