from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..storage.entities import (
    Artifact,
    Dataset,
    DatasetVersion,
    Experiment,
    Job,
    ModelRecord,
    ResearchEvidencePackage,
    Run,
    ScientificAuditEvent,
)
from ..storage.repository import require


def _configuration_summary(config: dict[str, Any]) -> dict[str, Any]:
    pipeline = config.get("pipeline") if isinstance(config.get("pipeline"), dict) else {}
    return {
        "model_families": config.get("models"),
        "random_seed": config.get("seed"),
        "test_size": config.get("test_size"),
        "cv_folds": config.get("cv_folds"),
        "sample_budget": config.get("max_samples"),
        "preprocessing": {
            key: pipeline.get(key)
            for key in ("imputer", "scaler", "outlier_strategy")
            if pipeline.get(key) is not None
        },
        "feature_configuration": {
            "selected_features": config.get("features"),
            "selection": pipeline.get("selection"),
            "pca_components": pipeline.get("pca_components"),
        },
        "threshold_strategy": config.get("threshold_strategy"),
    }


def _status(
    *,
    dataset_hash: str | None,
    configuration_fingerprint: str | None,
    run: Run | None,
    models: list[ModelRecord],
    artifacts: list[Artifact],
    reports_available: bool,
) -> tuple[str, list[str]]:
    recorded = []
    if dataset_hash:
        recorded.append("dataset_hash")
    if configuration_fingerprint:
        recorded.append("configuration_fingerprint")
    if run:
        recorded.append("run")
    if models:
        recorded.append("model_registry")
    if artifacts:
        recorded.append("artifact_registry")
    if reports_available:
        recorded.append("report_access")
    if len(recorded) == 6:
        return "RECORDED", recorded
    if len(recorded) >= 2:
        return "PARTIAL", recorded
    return "INSUFFICIENT", recorded


def experiment_traceability(session: Session, experiment_id: str) -> dict[str, Any]:
    """Project recorded evidence without exposing storage paths or inventing links."""
    experiment = require(session, Experiment, experiment_id)
    dataset = session.get(Dataset, experiment.dataset_id)
    runs = list(session.scalars(
        select(Run)
        .where(Run.experiment_id == experiment_id)
        .order_by(Run.created_at.desc())
    ))
    run = runs[0] if runs else None
    jobs = list(session.scalars(
        select(Job)
        .where(Job.experiment_id == experiment_id)
        .order_by(Job.created_at.desc())
    ))
    job = next((item for item in jobs if run and item.run_id == run.id), jobs[0] if jobs else None)
    models = list(session.scalars(
        select(ModelRecord)
        .where(ModelRecord.experiment_id == experiment_id)
        .order_by(ModelRecord.created_at.asc())
    ))
    artifacts = list(session.scalars(
        select(Artifact)
        .where(Artifact.experiment_id == experiment_id)
        .order_by(Artifact.created_at.desc())
    ))

    configured_version_id = (run.dataset_version_id if run else None) or (
        experiment.config or {}
    ).get("dataset_version_id")
    dataset_version = session.get(DatasetVersion, configured_version_id) if configured_version_id else None
    if dataset_version and dataset_version.dataset_id != experiment.dataset_id:
        dataset_version = None

    audit_event_id = session.scalar(
        select(ScientificAuditEvent.id)
        .where(or_(
            (ScientificAuditEvent.object_type == "experiment")
            & (ScientificAuditEvent.object_id == experiment_id),
            (ScientificAuditEvent.parent_object_type == "experiment")
            & (ScientificAuditEvent.parent_object_id == experiment_id),
        ))
        .limit(1)
    )
    audit_recorded = audit_event_id is not None
    packages = list(session.scalars(
        select(ResearchEvidencePackage)
        .where(ResearchEvidencePackage.experiment_id == experiment_id)
        .order_by(ResearchEvidencePackage.created_at.desc())
    ))

    configuration_fingerprint = (
        run.configuration_fingerprint if run else None
    ) or (job.configuration_fingerprint if job else None)
    reports_available = bool(models)
    reproducibility_status, recorded_fields = _status(
        dataset_hash=dataset.sha256 if dataset else None,
        configuration_fingerprint=configuration_fingerprint,
        run=run,
        models=models,
        artifacts=artifacts,
        reports_available=reports_available,
    )
    provenance = dataset.provenance if dataset and isinstance(dataset.provenance, dict) else {}

    return {
        "dataset": {
            "id": dataset.id if dataset else experiment.dataset_id,
            "name": dataset.name if dataset else None,
            "domain": provenance.get("domain"),
            "source": provenance.get("source") or provenance.get("source_url"),
            "positive_class": provenance.get("positive_label"),
            "sha256": dataset.sha256 if dataset else None,
            "created_at": dataset.created_at if dataset else None,
            "version": {
                "id": dataset_version.id,
                "label": dataset_version.version_label,
                "content_sha256": dataset_version.content_sha256,
                "schema_fingerprint": dataset_version.schema_fingerprint,
                "created_at": dataset_version.created_at,
            } if dataset_version else None,
        },
        "experiment": {
            "id": experiment.id,
            "name": experiment.name,
            "status": experiment.status,
            "created_at": experiment.created_at,
            "parent_id": experiment.parent_id,
            "configuration_fingerprint": configuration_fingerprint,
            "configuration": _configuration_summary(experiment.config or {}),
        },
        "run": {
            "id": run.id,
            "status": run.status,
            "created_at": run.created_at,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "duration_seconds": (run.execution_metadata or {}).get("duration_seconds"),
            "reproducibility_status": run.reproducibility_status,
            "reproducibility_metadata": run.reproducibility_metadata or {},
            "job": {
                "id": job.id,
                "status": job.status,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
            } if job else None,
        } if run else None,
        "models": [{
            "id": model.id,
            "run_id": model.run_id,
            "model_family": model.model_type,
            "status": model.status,
            "artifact_hash": model.artifact_sha256,
            "artifact_ids": [artifact.id for artifact in artifacts if artifact.model_id == model.id],
        } for model in models],
        "artifacts": [{
            "id": artifact.id,
            "type": artifact.artifact_type,
            "name": artifact.name,
            "run_id": artifact.run_id,
            "model_id": artifact.model_id,
            "integrity_hash": artifact.integrity_hash or None,
            "hash_algorithm": artifact.hash_algorithm,
            "storage_status": "recorded" if artifact.storage_reference else "metadata_only",
            "immutable": artifact.immutable,
        } for artifact in artifacts],
        "evidence": {
            "html_report_available": reports_available,
            "json_report_available": reports_available,
            "package_count": len(packages),
            "latest_package_id": packages[0].id if packages else None,
        },
        "audit": {
            "events_recorded": audit_recorded,
            "description": "Integrity-linked audit records" if audit_recorded else "Audit events not recorded",
        },
        "reproducibility": {
            "status": reproducibility_status,
            "recorded_fields": recorded_fields,
            "label": {
                "RECORDED": "Reproducibility metadata recorded",
                "PARTIAL": "Partial reproducibility metadata",
                "INSUFFICIENT": "Insufficient metadata",
            }[reproducibility_status],
            "claim": "Recorded metadata supports traceability; it does not establish clinical validity or bitwise reproducibility.",
        },
    }