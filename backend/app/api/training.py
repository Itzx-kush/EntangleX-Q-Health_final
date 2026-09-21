from uuid import UUID
from fastapi import APIRouter, Query
from ..database import session_scope
from ..jobs.manager import manager
from ..storage.entities import Job
from ..storage.repository import recent, require
from .schemas import JobOut, TrainingConfig, TrainingResponse

router = APIRouter(prefix="/training/jobs", tags=["training jobs"])

@router.post("", response_model=TrainingResponse, status_code=202)
def create_job(config: TrainingConfig):
    job, experiment = manager.enqueue(config)
    return {"job": job, "experiment": experiment}

@router.get("", response_model=list[JobOut])
def list_jobs(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    with session_scope() as session:
        return recent(session, Job, limit, offset)

@router.get("/{identity}", response_model=JobOut)
def get_job(identity: UUID):
    with session_scope() as session:
        return require(session, Job, str(identity))

@router.post("/{identity}/cancel", response_model=JobOut)
def cancel_job(identity: UUID):
    return manager.cancel(str(identity))
