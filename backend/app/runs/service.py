from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from ..database import session_scope
from ..storage.entities import Experiment, Run
from ..storage.repository import require
from ..utils.errors import AppError
from ..utils.serialization import utcnow


TERMINAL = {"completed", "failed", "cancelled"}
TRANSITIONS = {
    "created": {"queued", "failed", "cancelled"},
    "queued": {"running", "failed", "cancelled"},
    "running": {"completed", "failed", "cancelled"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}


def create_run(
    session,
    *,
    experiment: Experiment,
    config: dict,
    operation_key: str,
    execution_metadata: dict,
    reproducibility_metadata: dict,
    dataset_version_id: str | None = None,
) -> Run:
    existing = session.scalar(select(Run).where(Run.operation_key == operation_key))
    if existing is not None:
        if existing.experiment_id != experiment.id or existing.config != config:
            raise AppError("idempotency_conflict", "The operation key is already associated with another run.", 409)
        return existing
    run = Run(
        id=str(uuid4()),
        experiment_id=experiment.id,
        dataset_id=experiment.dataset_id,
        dataset_version_id=dataset_version_id,
        pipeline_version_id=experiment.pipeline_version_id,
        protocol_version_id=experiment.protocol_version_id,
        protocol_fingerprint=experiment.protocol_fingerprint,
        status="created",
        operation_key=operation_key,
        config=config,
        execution_metadata=execution_metadata,
        reproducibility_metadata=reproducibility_metadata,
    )
    session.add(run)
    session.flush()
    return run


def transition(
    session,
    run: Run,
    status: str,
    *,
    result_summary: dict | None = None,
    failure: dict | None = None,
) -> Run:
    if status == run.status:
        return run
    if status not in TRANSITIONS.get(run.status, set()):
        raise AppError("run_transition_invalid", f"Run cannot transition from {run.status} to {status}.", 409)
    now = utcnow()
    run.status = status
    if status == "running" and run.started_at is None:
        run.started_at = now
    elif status == "completed":
        run.completed_at = now
        elapsed = None
        if run.started_at is not None:
            comparable_now = now.replace(tzinfo=None) if run.started_at.tzinfo is None else now
            elapsed = (comparable_now - run.started_at).total_seconds()
        run.result_summary = {
            **(result_summary or {}),
            "elapsed_execution_seconds": elapsed,
        }
    elif status == "failed":
        run.failed_at = now
        run.failure = failure or {"code": "execution_failed", "message": "Scientific execution failed."}
    elif status == "cancelled":
        run.cancelled_at = now
        run.failure = failure or {"code": "cancelled", "message": "Scientific execution was cancelled."}
    return run


def list_runs(*, experiment_id: str | None = None, status: str | None = None, limit: int = 100, offset: int = 0):
    with session_scope() as session:
        query = select(Run)
        if experiment_id:
            require(session, Experiment, experiment_id)
            query = query.where(Run.experiment_id == experiment_id)
        if status:
            if status not in TRANSITIONS:
                raise AppError("run_status_invalid", "Unknown run status.")
            query = query.where(Run.status == status)
        return list(session.scalars(query.order_by(Run.created_at.desc()).limit(limit).offset(offset)))


def fail_run(run_id: str, *, code: str, message: str) -> None:
    with session_scope() as session:
        run = require(session, Run, run_id)
        if run.status not in TERMINAL:
            transition(session, run, "failed", failure={"code": code, "message": message})