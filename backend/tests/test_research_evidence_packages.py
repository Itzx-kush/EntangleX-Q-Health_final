from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.database import session_scope
from app.evidence_packages.service import (
    PACKAGE_SCHEMA_VERSION,
    create_package,
    package_payload,
    preflight_package,
)
from app.storage.entities import (
    Artifact,
    CalibrationStudy,
    Dataset,
    Experiment,
    ModelRecord,
    ResearchEvidencePackage,
    RobustnessRecord,
    Run,
    ThresholdAnalysisStudy,
)
from app.utils.serialization import utcnow


def _persist_experiment(registered, *, model_type="logistic_regression", with_run=True, with_metrics=True):
    experiment_id, run_id, model_id = str(uuid4()), str(uuid4()), str(uuid4())
    config = {
        "dataset_id": registered.id,
        "dataset_version_id": registered.current_version_id,
        "models": [model_type],
        "seed": 42,
        "sampling_unit": "independent_samples",
    }
    with session_scope() as session:
        session.add(Experiment(
            id=experiment_id,
            name=f"Evidence package fixture {experiment_id[:8]}",
            dataset_id=registered.id,
            status="completed",
            config=config,
            summary={"limitations": ["Synthetic test evidence only."]},
        ))
        session.flush()
        if with_run:
            session.add(Run(
                id=run_id,
                experiment_id=experiment_id,
                dataset_id=registered.id,
                dataset_version_id=registered.current_version_id,
                status="completed",
                operation_key=f"evidence-package-test:{run_id}",
                config=config,
                execution_metadata={},
                reproducibility_metadata={"dataset_hash": registered.sha256},
                result_summary={},
                configuration_fingerprint="c" * 64,
                reproducibility_status="complete",
            ))
            session.flush()
        session.add(ModelRecord(
            id=model_id,
            experiment_id=experiment_id,
            run_id=run_id if with_run else None,
            dataset_id=registered.id,
            model_type=model_type,
            status="ready",
            artifact_sha256="a" * 64,
            details={
                "supports_probability": True,
                "secret": "must-not-leak",
                "raw_patient_rows": [{"patient_id": "must-not-leak"}],
            },
            metrics={
                "test": {"accuracy": 0.8, "sample_count": 24}
            } if with_metrics else {},
        ))
    return experiment_id, model_id


@pytest.mark.parametrize("model_type,quantum_status", [
    ("logistic_regression", "not_applicable"),
    ("vqc", "not_available"),
    ("hybrid_pennylane_torch", "not_available"),
])
def test_preflight_inventory_is_evidence_derived_and_private(registered, model_type, quantum_status):
    experiment_id, model_id = _persist_experiment(registered, model_type=model_type)
    with session_scope() as session:
        result = preflight_package(session, experiment_id)
    assert result["feasible"] is True
    assert result["package_status"] == "PARTIAL"
    assert result["evidence_inventory"]["evaluation"]["status"] == "available"
    assert result["evidence_inventory"]["calibration"]["status"] == "not_available"
    assert result["evidence_inventory"]["threshold"]["status"] == "not_available"
    assert result["evidence_inventory"]["quantum_diagnostics"]["status"] == quantum_status
    assert result["manifest"]["models"][0]["model_id"] == model_id
    serialized = str(result["manifest"])
    assert "must-not-leak" not in serialized
    assert "patient_id" not in serialized


def test_creation_is_deterministic_idempotent_and_registered(registered):
    experiment_id, _ = _persist_experiment(registered)
    with session_scope() as session:
        first, created = create_package(session, experiment_id)
        first_payload = package_payload(session, first)
        assert created is True
    with session_scope() as session:
        second, created = create_package(session, experiment_id)
        package_count = session.scalar(select(func.count()).select_from(ResearchEvidencePackage).where(
            ResearchEvidencePackage.experiment_id == experiment_id
        ))
        artifact_count = session.scalar(select(func.count()).select_from(Artifact).where(
            Artifact.experiment_id == experiment_id,
            Artifact.artifact_type == "research_evidence_package",
        ))
    assert created is False
    assert second.id == first.id
    assert second.package_fingerprint == first.package_fingerprint
    assert package_count == 1
    assert artifact_count == 1
    assert first_payload["schema_version"] == PACKAGE_SCHEMA_VERSION
    assert first_payload["artifact"]["immutable"] is True
    assert first_payload["integrity"]["artifact_id"] == first_payload["artifact"]["id"]


def test_new_evidence_creates_new_immutable_snapshot(registered):
    experiment_id, model_id = _persist_experiment(registered)
    with session_scope() as session:
        first, _ = create_package(session, experiment_id)
        first_manifest = dict(first.manifest)
    with session_scope() as session:
        session.add(RobustnessRecord(
            id=str(uuid4()),
            experiment_id=experiment_id,
            model_id=model_id,
            perturbation_type="missingness",
            perturbation_level=0.1,
            random_seed=42,
            result={"aggregate_accuracy": 0.75},
        ))
    with session_scope() as session:
        second, created = create_package(session, experiment_id)
        stored_first = session.get(ResearchEvidencePackage, first.id)
        package_count = session.scalar(select(func.count()).select_from(ResearchEvidencePackage).where(
            ResearchEvidencePackage.experiment_id == experiment_id
        ))
    assert created is True
    assert second.id != first.id
    assert second.package_fingerprint != first.package_fingerprint
    assert second.evidence_inventory["robustness"]["status"] == "available"
    assert stored_first.manifest == first_manifest
    assert package_count == 2


def test_core_evidence_gap_is_incomplete(registered):
    experiment_id, _ = _persist_experiment(registered, with_run=False, with_metrics=False)
    with session_scope() as session:
        result = preflight_package(session, experiment_id)
    assert result["feasible"] is True
    assert result["package_status"] == "INCOMPLETE"
    assert {"persisted_evaluation", "run_provenance"}.issubset(result["core_missing_evidence"])


def test_identity_mismatch_blocks_package_creation(registered):
    experiment_id, model_id = _persist_experiment(registered)
    other_dataset_id = str(uuid4())
    with session_scope() as session:
        session.add(Dataset(
            id=other_dataset_id,
            name="Mismatched synthetic dataset",
            filename="mismatch.csv",
            sha256="f" * 64,
            provenance={},
            quality={},
        ))
        session.flush()
        session.get(ModelRecord, model_id).dataset_id = other_dataset_id
    with session_scope() as session:
        result = preflight_package(session, experiment_id)
        with pytest.raises(Exception) as blocked:
            create_package(session, experiment_id)
    assert result["package_status"] == "BLOCKED"
    assert any(item["code"] == "model_dataset_mismatch" for item in result["blockers"])
    assert getattr(blocked.value, "code", None) == "package_blocked"


def test_persisted_calibration_and_threshold_are_referenced(registered):
    experiment_id, model_id = _persist_experiment(registered)
    calibration_id, threshold_id = str(uuid4()), str(uuid4())
    with session_scope() as session:
        session.add(CalibrationStudy(
            id=calibration_id,
            model_id=model_id,
            dataset_id=registered.id,
            dataset_version_id=registered.current_version_id,
            status="completed",
            operation_key=f"package-calibration:{calibration_id}",
            configuration={},
            created_at=utcnow(),
        ))
        session.add(ThresholdAnalysisStudy(
            id=threshold_id,
            model_id=model_id,
            dataset_id=registered.id,
            dataset_version_id=registered.current_version_id,
            status="completed",
            operation_key=f"package-threshold:{threshold_id}",
            configuration={},
            created_at=utcnow(),
        ))
    with session_scope() as session:
        result = preflight_package(session, experiment_id)
    assert result["evidence_inventory"]["calibration"]["referenced_ids"] == [calibration_id]
    assert result["evidence_inventory"]["calibration"]["status"] == "available"
    assert result["evidence_inventory"]["threshold"]["referenced_ids"] == [threshold_id]
    assert result["evidence_inventory"]["threshold"]["status"] == "available"


def test_verified_demo_preserves_manifest_without_fabricating_run(registered, monkeypatch):
    experiment_id, model_id = _persist_experiment(registered, with_run=False)
    with session_scope() as session:
        model = session.get(ModelRecord, model_id)
        model.details = {
            "experiment_kind": "precomputed_verified_demo",
            "dataset_provenance": {"library_slug": "fixture"},
        }
    monkeypatch.setattr("app.evidence_packages.service.READY_DEMO_DATASETS", {"fixture": {}})
    monkeypatch.setattr(
        "app.evidence_packages.service.validate_packaged_dataset",
        lambda _slug: {
            "experiment": {"id": experiment_id},
            "dataset": {"id": registered.id, "sha256": registered.sha256},
            "models": [{"id": model_id, "artifact_sha256": "a" * 64}],
            "evidence": {},
            "manifest_sha256": "b" * 64,
        },
    )
    with session_scope() as session:
        before = session.scalar(select(func.count()).select_from(Run))
        package, _ = create_package(session, experiment_id)
        payload = package_payload(session, package)
        after = session.scalar(select(func.count()).select_from(Run))
    assert before == after
    assert payload["source_context"]["type"] == "verified_demo_experiment"
    assert payload["source_context"]["precomputed"] is True
    assert payload["source_context"]["manifest_sha256"] == "b" * 64
    assert payload["provenance"]["run_ids"] == []


def test_api_create_latest_specific_provenance_download_and_not_found(client, registered):
    experiment_id, _ = _persist_experiment(registered)
    missing = client.get(f"/api/experiments/{experiment_id}/evidence-package")
    assert missing.status_code == 404
    preflight = client.post(f"/api/experiments/{experiment_id}/evidence-package/preflight")
    assert preflight.status_code == 200
    created = client.post(f"/api/experiments/{experiment_id}/evidence-package")
    assert created.status_code == 200
    body = created.json()
    package_id = body["package_id"]
    assert body["created"] is True
    assert client.get(f"/api/experiments/{experiment_id}/evidence-package").status_code == 200
    assert client.get(f"/api/experiments/{experiment_id}/evidence-package/{package_id}").status_code == 200
    provenance = client.get(f"/api/experiments/{experiment_id}/evidence-package/{package_id}/provenance")
    assert provenance.status_code == 200
    assert provenance.json()["artifact"]["immutable"] is True
    download = client.get(f"/api/experiments/{experiment_id}/evidence-package/{package_id}/download")
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/json")