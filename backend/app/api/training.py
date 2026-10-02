from uuid import UUID
from fastapi import APIRouter, Header, Query
from sqlalchemy import select
from ..database import session_scope
from ..jobs.manager import manager
from ..storage.entities import Experiment, Job, ModelRecord
from ..storage.repository import recent, require
from .schemas import JobOut, TrainingConfig, TrainingResponse

router = APIRouter(prefix="/training/jobs", tags=["training jobs"])

def _job_payload(session, job: Job) -> dict:
    payload = JobOut.model_validate(job).model_dump()
    experiment = require(session, Experiment, job.experiment_id)
    payload["experiment_name"] = experiment.name
    payload["models"] = list(session.scalars(
        select(ModelRecord)
        .where(ModelRecord.run_id == job.run_id)
        .order_by(ModelRecord.created_at, ModelRecord.id)
    ))
    return payload

@router.post("", response_model=TrainingResponse, status_code=202)
def create_job(config: TrainingConfig, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    # Preserve the historical manager call shape when no optional idempotency
    # header is supplied; several integrations replace this boundary in tests.
    job, experiment = manager.enqueue(config) if idempotency_key is None else manager.enqueue(config, idempotency_key=idempotency_key)
    return {"job": job, "experiment": experiment}

@router.get("", response_model=list[JobOut])
def list_jobs(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    with session_scope() as session:
        return [_job_payload(session, job) for job in recent(session, Job, limit, offset)]

@router.get("/{identity}", response_model=JobOut)
def get_job(identity: UUID):
    with session_scope() as session:
        return _job_payload(session, require(session, Job, str(identity)))

@router.post("/{identity}/cancel", response_model=JobOut)
def cancel_job(identity: UUID):
    manager.cancel(str(identity))
    with session_scope() as session:
        return _job_payload(session, require(session, Job, str(identity)))
