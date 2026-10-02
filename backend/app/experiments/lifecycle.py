from __future__ import annotations

from sqlalchemy import func, select

from ..database import session_scope
from ..storage.entities import Artifact, Experiment, Job, ModelRecord, Run
from ..utils.errors import AppError
from ..utils.serialization import utcnow


ACTIVE_JOB_STATUSES = {"queued", "running", "cancel_requested"}
ACTIVE_RUN_STATUSES = {"created", "queued", "running"}
ACTIVE_EXPERIMENT_STATUSES = {"queued", "running", "cancel_requested"}
DELETABLE_EXPERIMENT_STATUSES = {
    "completed",
    "succeeded",
    "partial",
    "failed",
    "cancelled",
    "interrupted",
}


def archive_experiment(identity: str) -> dict:
    """Hide a terminal experiment while retaining immutable scientific evidence."""
    with session_scope() as session:
        experiment = session.get(Experiment, identity)
        if experiment is None:
            raise AppError("not_found", "The requested experiment does not exist.", 404)

        preserved = {
            "jobs": session.scalar(
                select(func.count()).select_from(Job).where(Job.experiment_id == identity)
            ) or 0,
            "models": session.scalar(
                select(func.count()).select_from(ModelRecord).where(ModelRecord.experiment_id == identity)
            ) or 0,
            "runs": session.scalar(
                select(func.count()).select_from(Run).where(Run.experiment_id == identity)
            ) or 0,
            "artifacts": session.scalar(
                select(func.count()).select_from(Artifact).where(Artifact.experiment_id == identity)
            ) or 0,
        }
        if experiment.deleted_at is not None:
            return {
                "id": experiment.id,
                "status": "archived",
                "deleted_at": experiment.deleted_at,
                "already_deleted": True,
                "preserved_records": preserved,
            }

        active_job = session.scalar(select(Job.id).where(
            Job.experiment_id == identity,
            Job.status.in_(ACTIVE_JOB_STATUSES),
        ).limit(1))
        active_run = session.scalar(select(Run.id).where(
            Run.experiment_id == identity,
            Run.status.in_(ACTIVE_RUN_STATUSES),
        ).limit(1))
        if (
            experiment.status in ACTIVE_EXPERIMENT_STATUSES
            or active_job is not None
            or active_run is not None
        ):
            raise AppError(
                "experiment_active",
                "Cancel this experiment and wait for a terminal state before deleting it.",
                409,
            )
        if experiment.status not in DELETABLE_EXPERIMENT_STATUSES:
            raise AppError(
                "experiment_not_terminal",
                f"Experiment status '{experiment.status}' is not eligible for deletion.",
                409,
            )

        experiment.deleted_at = utcnow()
        session.flush()
        return {
            "id": experiment.id,
            "status": "archived",
            "deleted_at": experiment.deleted_at,
            "already_deleted": False,
            "preserved_records": preserved,
        }