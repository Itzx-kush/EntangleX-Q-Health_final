"""Generic control and observability API for durable background jobs."""
from uuid import UUID
from fastapi import APIRouter, Header, Query
from sqlalchemy import select
from ..database import session_scope
from ..jobs.manager import manager
from ..storage.entities import Job, JobCheckpoint, JobEvent
from ..storage.repository import require
from .schemas import JobCheckpointOut, JobOut, JobProgressOut
from .training import _job_payload
router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("", response_model=list[JobOut])
def list_jobs(status: str | None = None, job_type: str | None = None,
              limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    with session_scope() as session:
        query = select(Job)
        if status: query = query.where(Job.status == status)
        if job_type: query = query.where(Job.job_type == job_type)
        return [_job_payload(session, job) for job in session.scalars(query.order_by(Job.created_at.desc()).offset(offset).limit(limit))]

@router.get("/{identity}", response_model=JobOut)
def get_job(identity: UUID):
    with session_scope() as session: return _job_payload(session, require(session, Job, str(identity)))

@router.get("/{identity}/status", response_model=JobOut)
def get_job_status(identity: UUID): return get_job(identity)

@router.get("/{identity}/progress", response_model=JobProgressOut)
def get_job_progress(identity: UUID):
    with session_scope() as session:
        job = require(session, Job, str(identity)); determinate = job.total_units is not None and job.total_units > 0
        return {"job_id": job.id, "status": job.status, "determinate": determinate,
            "percentage": job.progress if determinate else None, "total_units": job.total_units,
            "completed_units": job.completed_units, "failed_units": job.failed_units,
            "skipped_units": job.skipped_units, "active_unit": job.active_unit, "current_phase": job.current_phase}

@router.get("/{identity}/checkpoints", response_model=list[JobCheckpointOut])
def get_job_checkpoints(identity: UUID):
    with session_scope() as session:
        require(session, Job, str(identity))
        return list(session.scalars(select(JobCheckpoint).where(JobCheckpoint.job_id == str(identity)).order_by(JobCheckpoint.sequence_number.desc())))

@router.get("/{identity}/history", response_model=list[dict])
def get_job_history(identity: UUID, limit: int = Query(100, ge=1, le=500)):
    with session_scope() as session:
        require(session, Job, str(identity))
        events = session.scalars(select(JobEvent).where(JobEvent.job_id == str(identity)).order_by(JobEvent.created_at.desc()).limit(limit))
        return [{"id": e.id, "event_type": e.event_type, "from_status": e.from_status, "to_status": e.to_status,
            "checkpoint_id": e.checkpoint_id, "details": e.details, "created_at": e.created_at.isoformat()} for e in events]

@router.post("/{identity}/pause", response_model=JobOut)
def pause_job(identity: UUID): manager.pause(str(identity)); return get_job(identity)
@router.post("/{identity}/resume", response_model=JobOut, status_code=202)
def resume_job(identity: UUID): manager.resume(str(identity)); return get_job(identity)
@router.post("/{identity}/cancel", response_model=JobOut)
def cancel_job(identity: UUID): manager.cancel(str(identity)); return get_job(identity)
@router.post("/{identity}/retry", response_model=JobOut, status_code=202)
def retry_job(identity: UUID, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    job, _experiment, _run = manager.retry(str(identity), idempotency_key=idempotency_key)
    with session_scope() as session: return _job_payload(session, require(session, Job, job.id))
