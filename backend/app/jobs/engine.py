"""Durable, lease-protected primitives for resumable background jobs."""
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import timedelta
import logging
from typing import Any
from uuid import uuid4
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..config import get_settings
from ..database import session_scope
from ..storage.entities import Artifact, Job, JobCheckpoint, JobEvent, JobExecutionUnit, ModelRecord
from ..storage.repository import require
from ..utils.errors import AppError
from ..utils.serialization import fingerprint, utcnow

logger = logging.getLogger("qhealth.jobs")
TERMINAL_STATUSES = {"succeeded", "partial", "failed", "cancelled"}
ACTIVE_STATUSES = {"queued", "running", "resuming", "checkpointing", "pause_requested", "cancel_requested"}
TRANSITIONS = {
    "created": {"queued", "cancelled"},
    "queued": {"running", "resuming", "cancel_requested", "failed", "recoverable"},
    "running": {"checkpointing", "pause_requested", "cancel_requested", "recoverable", "failed", "partial", "succeeded"},
    "checkpointing": {"running", "paused", "cancel_requested", "recoverable", "failed"},
    "pause_requested": {"checkpointing", "paused", "cancel_requested", "recoverable", "failed"},
    "paused": {"queued", "resuming", "cancel_requested", "cancelled"},
    "recoverable": {"queued", "resuming", "failed", "cancel_requested", "cancelled"},
    "resuming": {"running", "checkpointing", "cancel_requested", "recoverable", "failed"},
    "cancel_requested": {"checkpointing", "cancelled", "recoverable", "failed"},
    "interrupted": {"queued", "recoverable", "failed", "cancel_requested"},
    "failed": set(), "partial": set(), "succeeded": set(), "cancelled": set(),
}

class PauseRequested(Exception):
    pass

class JobHandler(ABC):
    job_type: str
    @abstractmethod
    def validate(self, job: Job) -> None: ...
    @abstractmethod
    def initialize(self, job: Job) -> dict[str, Any]: ...
    @abstractmethod
    def run(self, job: Job, checkpoint: JobCheckpoint | None) -> None: ...
    @abstractmethod
    def resume(self, job: Job, checkpoint: JobCheckpoint) -> None: ...
    @abstractmethod
    def finalize(self, job: Job) -> None: ...
    @abstractmethod
    def cancel(self, job: Job) -> None: ...
    @abstractmethod
    def recover(self, job: Job) -> None: ...

def _event(session: Session, job: Job, event_type: str, *, from_status=None, checkpoint_id=None, details=None):
    session.add(JobEvent(job_id=job.id, event_type=event_type, from_status=from_status,
        to_status=job.status, checkpoint_id=checkpoint_id, worker_id=job.worker_id,
        details=details or {}))

def transition_job(session: Session, job: Job, target: str, *, state=None, event_type="status_transition"):
    source = job.status
    if source == target:
        return job
    if target not in TRANSITIONS.get(source, set()):
        raise AppError("invalid_job_transition", f"Job cannot transition from {source} to {target}.", 409)
    job.status, job.updated_at = target, utcnow()
    if state is not None: job.state = state[:200]
    if target in {"running", "resuming"} and job.started_at is None: job.started_at = utcnow()
    if target in {"succeeded", "partial", "failed"}: job.completed_at = utcnow()
    if target == "cancelled":
        job.cancelled_at, job.failure_category = utcnow(), "cancelled"
    _event(session, job, event_type, from_status=source)
    return job

def acquire_lease(job_id: str, worker_id: str, *, resuming=False):
    now, lease_id = utcnow(), str(uuid4())
    expires = now + timedelta(seconds=get_settings().job_lease_seconds)
    allowed = {"queued", "recoverable", "paused", "interrupted"}
    with session_scope() as session:
        result = session.execute(update(Job).where(Job.id == job_id, Job.status.in_(allowed),
            or_(Job.lease_id.is_(None), Job.lease_expires_at.is_(None), Job.lease_expires_at <= now)).values(
            lease_id=lease_id, worker_id=worker_id, leased_at=now, lease_expires_at=expires,
            last_heartbeat_at=now, status="resuming" if resuming else "running", started_at=now, updated_at=now))
        if result.rowcount != 1:
            raise AppError("job_lease_conflict", "The job is already owned or cannot be executed.", 409)
        job = require(session, Job, job_id)
        if resuming: job.resume_count += 1
        else: job.attempt_count += 1
        _event(session, job, "lease_acquired")
        session.flush()
        return lease_id, job

def heartbeat(job_id: str, lease_id: str):
    now = utcnow()
    with session_scope() as session:
        result = session.execute(update(Job).where(Job.id == job_id, Job.lease_id == lease_id,
            Job.status.in_(ACTIVE_STATUSES)).values(last_heartbeat_at=now,
            lease_expires_at=now + timedelta(seconds=get_settings().job_lease_seconds), updated_at=now))
        if result.rowcount != 1: raise AppError("job_lease_lost", "The execution lease is no longer valid.", 409)
        return require(session, Job, job_id)

def release_lease(session: Session, job: Job, lease_id=None):
    if lease_id is not None and job.lease_id != lease_id:
        raise AppError("job_lease_lost", "The execution lease is no longer valid.", 409)
    job.worker_id = job.lease_id = job.leased_at = job.lease_expires_at = job.last_heartbeat_at = None

def _artifact_valid(session, ref):
    kind, identity, expected = ref.get("kind"), ref.get("id"), ref.get("fingerprint")
    if not isinstance(identity, str): return False
    if kind == "artifact":
        row = session.get(Artifact, identity)
        return bool(row and (expected is None or row.integrity_hash == expected))
    if kind == "model":
        row = session.get(ModelRecord, identity)
        return bool(row and row.status == "ready" and row.artifact_sha256 and (expected is None or row.artifact_sha256 == expected))
    return False

def validate_checkpoint(session, job, checkpoint):
    if checkpoint.job_id != job.id: return False, "job_identity_mismatch"
    if checkpoint.configuration_fingerprint != job.configuration_fingerprint: return False, "configuration_fingerprint_mismatch"
    if checkpoint.input_fingerprint != job.input_fingerprint: return False, "input_fingerprint_mismatch"
    state = checkpoint.checkpoint_state
    if not isinstance(state, dict) or state.get("job_type") != job.job_type: return False, "checkpoint_state_invalid"
    if checkpoint.state_fingerprint != fingerprint(state): return False, "checkpoint_corruption"
    if checkpoint.sequence_number < 1 or checkpoint.completed_units < 0: return False, "checkpoint_sequence_invalid"
    if job.total_units is not None and checkpoint.completed_units > job.total_units: return False, "checkpoint_progress_invalid"
    if not isinstance(checkpoint.artifact_references, list) or any(not isinstance(r, dict) or not _artifact_valid(session, r) for r in checkpoint.artifact_references):
        return False, "checkpoint_artifact_missing"
    completed = state.get("completed_logical_units", [])
    if not isinstance(completed, list) or len(completed) != len(set(completed)): return False, "completed_units_invalid"
    if checkpoint.completed_units != len(completed): return False, "completed_units_inconsistent"
    if completed:
        durable = set(session.scalars(select(JobExecutionUnit.logical_key).where(JobExecutionUnit.job_id == job.id,
            JobExecutionUnit.logical_key.in_(completed), JobExecutionUnit.status == "succeeded")))
        if durable != set(completed): return False, "completed_units_not_durable"
    return True, None

def create_checkpoint(job_id, lease_id, state, *, checkpoint_type="unit_completion", logical_unit=None,
                      completed_units, artifact_references=None):
    if checkpoint_type not in {"periodic", "unit_completion", "phase_completion", "manual"}:
        raise AppError("checkpoint_type_invalid", "Unsupported checkpoint type.", 422)
    with session_scope() as session:
        job = require(session, Job, job_id)
        if job.lease_id != lease_id: raise AppError("job_lease_lost", "The execution lease is no longer valid.", 409)
        if job.status not in {"running", "resuming", "pause_requested", "cancel_requested"}:
            raise AppError("checkpoint_not_allowed", "The job is not at a checkpointable state.", 409)
        sequence = (session.scalar(select(JobCheckpoint.sequence_number).where(JobCheckpoint.job_id == job.id)
                    .order_by(JobCheckpoint.sequence_number.desc()).limit(1)) or 0) + 1
        normalized = {**state, "job_type": job.job_type}
        cp = JobCheckpoint(job_id=job.id, sequence_number=sequence, checkpoint_type=checkpoint_type,
            status="pending", logical_unit=logical_unit, completed_units=completed_units,
            checkpoint_state=normalized, state_fingerprint=fingerprint(normalized),
            input_fingerprint=job.input_fingerprint, configuration_fingerprint=job.configuration_fingerprint,
            artifact_references=artifact_references or [])
        session.add(cp); session.flush()
        valid, reason = validate_checkpoint(session, job, cp)
        if not valid: raise AppError(reason or "checkpoint_invalid", "Checkpoint validation failed.", 409)
        cp.status, cp.validated_at = "valid", utcnow()
        job.current_checkpoint_id, job.completed_units, job.updated_at = cp.id, completed_units, utcnow()
        if job.total_units: job.progress = min(99, int(completed_units * 100 / job.total_units))
        _event(session, job, "checkpoint_validated", checkpoint_id=cp.id,
            details={"sequence_number": sequence, "checkpoint_type": checkpoint_type})
        return cp

def latest_valid_checkpoint(job_id):
    with session_scope() as session:
        job = require(session, Job, job_id)
        candidates = list(session.scalars(select(JobCheckpoint).where(JobCheckpoint.job_id == job.id,
            JobCheckpoint.status == "valid").order_by(JobCheckpoint.sequence_number.desc())))
        for cp in candidates:
            valid, reason = validate_checkpoint(session, job, cp)
            if valid: return cp
            cp.status, cp.invalidated_at = "invalid", utcnow()
            _event(session, job, "checkpoint_invalidated", checkpoint_id=cp.id, details={"reason": reason})
        return None

def begin_logical_unit(job_id, logical_key, *, phase=None, unit_index=None):
    with session_scope() as session:
        unit = session.scalar(select(JobExecutionUnit).where(JobExecutionUnit.job_id == job_id,
            JobExecutionUnit.logical_key == logical_key))
        if unit:
            if unit.status == "succeeded": return unit, True
            if unit.status == "running": raise AppError("logical_unit_conflict", "The logical unit is already executing.", 409)
            unit.status, unit.started_at, unit.completed_at = "running", utcnow(), None
            return unit, False
        unit = JobExecutionUnit(job_id=job_id, logical_key=logical_key, phase=phase, unit_index=unit_index)
        session.add(unit)
        try: session.flush()
        except IntegrityError as exc: raise AppError("logical_unit_conflict", "The logical unit is already executing.", 409) from exc
        return unit, False

def complete_logical_unit(job_id, logical_key, *, result_reference=None, result_fingerprint=None):
    with session_scope() as session:
        unit = session.scalar(select(JobExecutionUnit).where(JobExecutionUnit.job_id == job_id, JobExecutionUnit.logical_key == logical_key))
        if unit is None: raise AppError("logical_unit_not_claimed", "The logical unit was not claimed.", 409)
        if unit.status != "succeeded":
            unit.status, unit.result_reference, unit.result_fingerprint, unit.completed_at = "succeeded", result_reference, result_fingerprint, utcnow()
        return unit

def fail_logical_unit(job_id, logical_key):
    with session_scope() as session:
        unit = session.scalar(select(JobExecutionUnit).where(JobExecutionUnit.job_id == job_id, JobExecutionUnit.logical_key == logical_key))
        if unit is None: raise AppError("logical_unit_not_claimed", "The logical unit was not claimed.", 409)
        unit.status, unit.completed_at = "failed", utcnow()
        return unit

def recover_stale_jobs():
    now, recovered = utcnow(), []
    with session_scope() as session:
        jobs = list(session.scalars(select(Job).where(Job.status.in_(ACTIVE_STATUSES), Job.lease_id.is_not(None),
            Job.lease_expires_at.is_not(None), Job.lease_expires_at <= now)))
        for job in jobs:
            source = job.status
            job.status, job.failure_category, job.error_code = "recoverable", "worker_lost", "worker_lease_expired"
            job.error_message, job.state, job.updated_at = "Worker heartbeat expired; resume from a valid checkpoint.", "Worker lease expired; recovery is available.", now
            release_lease(session, job); _event(session, job, "worker_lost", from_status=source)
            for unit in session.scalars(select(JobExecutionUnit).where(JobExecutionUnit.job_id == job.id, JobExecutionUnit.status == "running")):
                unit.status, unit.completed_at = "failed", now
            recovered.append(job.id); logger.warning("worker_lost job_id=%s", job.id)
    return recovered

def request_pause(job_id):
    with session_scope() as session:
        job = require(session, Job, job_id)
        if job.status in {"paused", "pause_requested"}: return job
        if job.status not in {"running", "resuming", "checkpointing"}: raise AppError("pause_not_allowed", "Only an active job can be paused.", 409)
        return transition_job(session, job, "pause_requested", state="Pause requested; waiting for a safe checkpoint boundary.", event_type="pause_requested")

def request_cancel(job_id):
    with session_scope() as session:
        job = require(session, Job, job_id)
        if job.status in {"cancel_requested", "cancelled"} or job.status in TERMINAL_STATUSES: return job
        return transition_job(session, job, "cancel_requested", state="Cancellation requested; waiting for a safe execution boundary.", event_type="cancel_requested")

def check_control(job_id, lease_id, *, safe_boundary):
    heartbeat(job_id, lease_id)
    with session_scope() as session:
        job = require(session, Job, job_id)
        if job.lease_id != lease_id: raise AppError("job_lease_lost", "The execution lease is no longer valid.", 409)
        if safe_boundary and job.status == "pause_requested": return "pause"
        if safe_boundary and job.status == "cancel_requested": return "cancel"
        return "continue"

def mark_paused(job_id, lease_id):
    with session_scope() as session:
        job = require(session, Job, job_id)
        if job.lease_id != lease_id: raise AppError("job_lease_lost", "The execution lease is no longer valid.", 409)
        if job.current_checkpoint_id is None: raise AppError("checkpoint_required", "A valid checkpoint is required before pausing.", 409)
        if job.status == "pause_requested": transition_job(session, job, "paused", state="Paused at a validated checkpoint.")
        elif job.status != "paused": raise AppError("pause_not_allowed", "The job has no active pause request.", 409)
        release_lease(session, job, lease_id)
        return job
