from uuid import UUID

from fastapi import APIRouter, Header, Query
from sqlalchemy import select

from ..database import session_scope
from ..jobs.manager import manager
from ..runs.service import list_runs
from ..storage.entities import Artifact, Experiment, Job, ModelRecord, Run
from ..storage.repository import require
from .schemas import ArtifactOut, JobOut, ModelOut, RunOut, RunTrainingResponse, Schema


class RunDetailOut(Schema):
    run: RunOut
    job: JobOut | None
    models: list[ModelOut]
    artifacts: list[ArtifactOut]


router = APIRouter(tags=["research runs and artifacts"])


@router.get("/runs", response_model=list[RunOut])
def get_runs(
    experiment_id: UUID | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return list_runs(
        experiment_id=str(experiment_id) if experiment_id else None,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/experiments/{identity}/runs", response_model=list[RunOut])
def experiment_runs(identity: UUID, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    return list_runs(experiment_id=str(identity), limit=limit, offset=offset)


@router.post("/experiments/{identity}/runs", response_model=RunTrainingResponse, status_code=202)
def execute_experiment(identity: UUID, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    with session_scope() as session:
        experiment = require(session, Experiment, str(identity))
    job, experiment, run = manager.enqueue_existing(experiment.id, idempotency_key=idempotency_key)
    return {"job": job, "experiment": experiment, "run": run}


@router.get("/runs/{identity}", response_model=RunDetailOut)
def get_run(identity: UUID):
    with session_scope() as session:
        run = require(session, Run, str(identity))
        return {
            "run": run,
            "job": session.scalar(select(Job).where(Job.run_id == run.id)),
            "models": list(session.scalars(select(ModelRecord).where(ModelRecord.run_id == run.id))),
            "artifacts": list(session.scalars(
                select(Artifact).where(Artifact.run_id == run.id).order_by(Artifact.created_at.desc())
            )),
        }


@router.get("/runs/{identity}/artifacts", response_model=list[ArtifactOut])
def run_artifacts(identity: UUID):
    with session_scope() as session:
        require(session, Run, str(identity))
        return list(session.scalars(
            select(Artifact).where(Artifact.run_id == str(identity)).order_by(Artifact.created_at.desc())
        ))


@router.get("/experiments/{identity}/artifacts", response_model=list[ArtifactOut])
def experiment_artifacts(identity: UUID):
    with session_scope() as session:
        require(session, Experiment, str(identity))
        return list(session.scalars(
            select(Artifact).where(Artifact.experiment_id == str(identity)).order_by(Artifact.created_at.desc())
        ))


@router.get("/artifacts/{identity}", response_model=ArtifactOut)
def get_artifact(identity: UUID):
    with session_scope() as session:
        return require(session, Artifact, str(identity))