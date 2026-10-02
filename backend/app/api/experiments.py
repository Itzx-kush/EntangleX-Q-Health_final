from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Query, Response
from sqlalchemy import select
from ..database import session_scope
from ..demo_readiness import ARTIFACT_VERSION, READY_DEMO_DATASETS, validate_packaged_dataset
from ..experiments.comparison import comparison
from ..experiments.reports import html_report, report_data
from ..evaluation.robustness import evaluate_robustness, list_robustness
from ..jobs.manager import manager
from ..storage.entities import Experiment, ModelRecord, Job
from ..storage.repository import recent, require
from ..utils.errors import AppError
from .schemas import ExperimentOut, ModelOut, JobOut, RobustnessRecordOut, RobustnessRequest, TrainingConfig, TrainingResponse, Schema

class ExperimentDetailOut(Schema):
    experiment: ExperimentOut
    models: list[ModelOut]
    jobs: list[JobOut]

router = APIRouter(prefix="/experiments", tags=["experiments and reports"])

@router.get("", response_model=list[ExperimentOut])
def list_experiments(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    with session_scope() as session:
        return recent(session, Experiment, limit, offset)

@router.get("/{identity}", response_model=ExperimentDetailOut)
def get_experiment(identity: UUID):
    with session_scope() as session:
        return {"experiment": require(session, Experiment, str(identity)),
            "models": list(session.scalars(select(ModelRecord).where(ModelRecord.experiment_id == str(identity)))),
            "jobs": list(session.scalars(select(Job).where(Job.experiment_id == str(identity))))}

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
def export_report(identity: UUID, format: Literal["html", "json"] = "html"):
    import json
    if format == "json":
        content, media_type, suffix = json.dumps(report_data(str(identity)), indent=2), "application/json", "json"
    else:
        content, media_type, suffix = html_report(str(identity)), "text/html", "html"
    return Response(content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="qhealth-{identity}.{suffix}"', "Cache-Control": "no-store"})
