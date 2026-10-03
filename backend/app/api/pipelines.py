from uuid import UUID

from fastapi import APIRouter, Query
from ..database import session_scope
from ..pipelines.schemas import PipelineCreateRequest
from ..pipelines.service import (
    create_pipeline_version,
    diff_pipeline_versions,
    list_pipeline_versions,
    pipeline_payload,
    preflight_definition,
    publish_pipeline_version,
)
from ..storage.entities import Experiment, PipelineVersion
from ..storage.repository import require

router = APIRouter(tags=["pipeline version registry"])


@router.get("/pipelines", response_model=list[dict])
def get_pipelines(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    with session_scope() as session:
        return list_pipeline_versions(session, limit=limit, offset=offset)


@router.post("/pipelines/preflight", response_model=dict)
def pipeline_preflight(request: PipelineCreateRequest):
    with session_scope() as session:
        return {
            "pipeline_name": request.pipeline_name,
            **preflight_definition(session, request.definition),
        }


@router.post("/pipelines", response_model=dict, status_code=201)
def create_pipeline(request: PipelineCreateRequest):
    with session_scope() as session:
        version, created = create_pipeline_version(session, request)
        return {**pipeline_payload(session, version), "created": created}


@router.get("/pipelines/{identity}", response_model=dict)
def get_pipeline(identity: UUID):
    with session_scope() as session:
        return pipeline_payload(session, require(session, PipelineVersion, str(identity)))


@router.get("/pipelines/{identity}/preflight", response_model=dict)
def existing_pipeline_preflight(identity: UUID):
    with session_scope() as session:
        version = require(session, PipelineVersion, str(identity))
        return {
            "pipeline_version_id": version.id,
            **preflight_definition(session, version.canonical_definition),
        }


@router.post("/pipelines/{identity}/publish", response_model=dict)
def publish_pipeline(identity: UUID):
    with session_scope() as session:
        version = publish_pipeline_version(session, str(identity))
        return pipeline_payload(session, version)


@router.get("/pipelines/{identity}/diff/{other_identity}", response_model=dict)
def pipeline_diff(identity: UUID, other_identity: UUID):
    with session_scope() as session:
        return diff_pipeline_versions(session, str(identity), str(other_identity))


@router.get("/experiments/{identity}/pipeline", response_model=dict)
def experiment_pipeline(identity: UUID):
    with session_scope() as session:
        experiment = require(session, Experiment, str(identity))
        if not experiment.pipeline_version_id:
            return {
                "experiment_id": experiment.id,
                "status": "LEGACY_UNRESOLVED",
                "pipeline_version": None,
                "reason": "This experiment predates Pipeline Version capture or has no deterministic mapping.",
            }
        version = require(session, PipelineVersion, experiment.pipeline_version_id)
        return {
            "experiment_id": experiment.id,
            "status": "AVAILABLE",
            "pipeline_version": pipeline_payload(session, version),
        }