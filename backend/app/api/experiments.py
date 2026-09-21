from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Query, Response
from sqlalchemy import select
from ..database import session_scope
from ..experiments.comparison import comparison
from ..experiments.reports import html_report, report_data
from ..jobs.manager import manager
from ..storage.entities import Experiment, ModelRecord, Job
from ..storage.repository import recent, require
from .schemas import ExperimentOut, ModelOut, JobOut, TrainingConfig, TrainingResponse, Schema

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
