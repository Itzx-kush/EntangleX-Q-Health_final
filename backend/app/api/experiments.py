from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Query, Response
from sqlalchemy import select
from ..database import session_scope
from ..demo_readiness import ARTIFACT_VERSION, READY_DEMO_DATASETS, validate_packaged_dataset
from ..experiments.comparison import comparison
from ..experiments.reports import html_report, report_data
from ..experiments.pdf_reports import pdf_report
from ..experiments.lifecycle import archive_experiment
from ..evidence_packages.service import (
    create_package,
    latest_package,
    package_payload,
    preflight_package,
    specific_package,
)
from ..evaluation.robustness import evaluate_robustness, list_robustness
from ..jobs.manager import manager
from ..lineage.service import lineage_preflight, lineage_snapshot
from ..storage.entities import Experiment, ModelRecord, Job
from ..storage.repository import require
from ..utils.errors import AppError
from .schemas import ExperimentDeletionOut, ExperimentOut, ModelOut, JobOut, RobustnessRecordOut, RobustnessRequest, TrainingConfig, TrainingResponse, Schema

class ExperimentDetailOut(Schema):
    experiment: ExperimentOut
    models: list[ModelOut]
    jobs: list[JobOut]

router = APIRouter(prefix="/experiments", tags=["experiments and reports"])

@router.get("", response_model=list[ExperimentOut])
def list_experiments(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    with session_scope() as session:
        return list(session.scalars(
            select(Experiment)
            .where(Experiment.deleted_at.is_(None))
            .order_by(Experiment.created_at.desc())
            .offset(offset)
            .limit(limit)
        ))

@router.delete("/{identity}", response_model=ExperimentDeletionOut)
def delete_experiment(identity: UUID):
    return archive_experiment(str(identity))

@router.get("/{identity}", response_model=ExperimentDetailOut)
def get_experiment(identity: UUID):
    with session_scope() as session:
        return {"experiment": require(session, Experiment, str(identity)),
            "models": list(session.scalars(select(ModelRecord).where(ModelRecord.experiment_id == str(identity)))),
            "jobs": list(session.scalars(select(Job).where(Job.experiment_id == str(identity))))}


@router.get("/{identity}/lineage", response_model=dict)
def get_experiment_lineage(
    identity: UUID,
    depth: str = Query("3", pattern=r"^(all|[1-9]|1[0-2])$"),
    direction: Literal["ancestors", "descendants", "both"] = "both",
    include_artifacts: bool = True,
    include_evidence: bool = True,
):
    with session_scope() as session:
        return lineage_snapshot(
            session,
            str(identity),
            depth=depth,
            direction=direction,
            include_artifacts=include_artifacts,
            include_evidence=include_evidence,
        )


@router.get("/{identity}/lineage/ancestors", response_model=dict)
def get_experiment_lineage_ancestors(
    identity: UUID,
    depth: str = Query("3", pattern=r"^(all|[1-9]|1[0-2])$"),
    include_artifacts: bool = True,
    include_evidence: bool = True,
):
    with session_scope() as session:
        return lineage_snapshot(
            session, str(identity), depth=depth, direction="ancestors",
            include_artifacts=include_artifacts, include_evidence=include_evidence,
        )


@router.get("/{identity}/lineage/descendants", response_model=dict)
def get_experiment_lineage_descendants(
    identity: UUID,
    depth: str = Query("3", pattern=r"^(all|[1-9]|1[0-2])$"),
    include_artifacts: bool = True,
    include_evidence: bool = True,
):
    with session_scope() as session:
        return lineage_snapshot(
            session, str(identity), depth=depth, direction="descendants",
            include_artifacts=include_artifacts, include_evidence=include_evidence,
        )


@router.get("/{identity}/lineage/preflight", response_model=dict)
def get_experiment_lineage_preflight(identity: UUID):
    with session_scope() as session:
        return lineage_preflight(session, str(identity))

@router.get("/{identity}/comparison", response_model=dict)
def compare_models(identity: UUID):
    return comparison(str(identity))

@router.get("/{identity}/verified-evidence", response_model=dict)
def verified_evidence(identity: UUID):
    """Read-only access to the already validated flagship package; never computes evidence."""
    requested = str(identity)
    for slug in READY_DEMO_DATASETS:
        checked = validate_packaged_dataset(slug)
        if checked["experiment"]["id"] == requested:
            return {
                "verified": True,
                "precomputed": True,
                "slug": slug,
                "artifact_version": ARTIFACT_VERSION,
                "manifest_sha256": checked["manifest_sha256"],
                "dataset": checked["dataset"],
                "experiment": checked["experiment"],
                "models": checked["models"],
                "evidence": checked["evidence"],
            }
    raise AppError("verified_evidence_not_found", "This experiment is not a packaged verified demonstration.", 404)


@router.post("/{identity}/evidence-package/preflight", response_model=dict)
def evidence_package_preflight(identity: UUID):
    """Validate package feasibility without creating records or artifacts."""
    with session_scope() as session:
        return preflight_package(session, str(identity))


@router.post("/{identity}/evidence-package", response_model=dict)
def generate_evidence_package(identity: UUID):
    """Create or return the immutable package for the current evidence state."""
    with session_scope() as session:
        package, created = create_package(session, str(identity))
        return {**package_payload(session, package), "created": created}


@router.get("/{identity}/evidence-package", response_model=dict)
def get_latest_evidence_package(identity: UUID):
    with session_scope() as session:
        return package_payload(session, latest_package(session, str(identity)))


@router.get("/{identity}/evidence-package/{package_id}", response_model=dict)
def get_evidence_package(identity: UUID, package_id: UUID):
    with session_scope() as session:
        return package_payload(session, specific_package(session, str(identity), str(package_id)))


@router.get("/{identity}/evidence-package/{package_id}/provenance", response_model=dict)
def get_evidence_package_provenance(identity: UUID, package_id: UUID):
    with session_scope() as session:
        package = specific_package(session, str(identity), str(package_id))
        payload = package_payload(session, package)
        return {
            "package_id": package.id,
            "package_fingerprint": package.package_fingerprint,
            "source_context": payload["source_context"],
            "provenance": package.provenance,
            "integrity": payload["integrity"],
            "artifact": payload["artifact"],
        }


@router.get("/{identity}/evidence-package/{package_id}/download")
def download_evidence_package(identity: UUID, package_id: UUID):
    import json
    with session_scope() as session:
        payload = package_payload(session, specific_package(session, str(identity), str(package_id)))
    return Response(
        json.dumps(payload, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="qhealth-evidence-package-{package_id}.json"',
            "Cache-Control": "no-store",
        },
    )

@router.post("/{identity}/robustness", response_model=dict)
def run_robustness(identity: UUID, request: RobustnessRequest):
    return evaluate_robustness(str(identity), request)

@router.get("/{identity}/robustness", response_model=list[RobustnessRecordOut])
def robustness_history(identity: UUID):
    return list_robustness(str(identity))

@router.post("/{identity}/rerun", response_model=TrainingResponse, status_code=202)
def rerun(identity: UUID):
    with session_scope() as session:
        original = require(session, Experiment, str(identity))
    job, experiment = manager.enqueue(TrainingConfig.model_validate(original.config), parent_id=str(identity))
    return {"job": job, "experiment": experiment}

@router.get("/{identity}/report")
def export_report(identity: UUID, format: Literal["html", "json", "pdf"] = "html"):
    import json
    from ..utils.serialization import clean_json
    if format == "json":
        content, media_type, suffix = json.dumps(clean_json(report_data(str(identity))), indent=2), "application/json", "json"
    elif format == "pdf":
        data = report_data(str(identity))
        try:
            content = pdf_report(data)
        except Exception as error:
            raise AppError("pdf_generation_failed", "The PDF report could not be generated from the persisted evidence.", 500) from error
        media_type, suffix = "application/pdf", "pdf"
    else:
        content, media_type, suffix = html_report(str(identity)), "text/html", "html"
    return Response(content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="qhealth-{identity}.{suffix}"', "Cache-Control": "no-store"})
