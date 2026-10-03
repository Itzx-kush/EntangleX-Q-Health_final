from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from ..database import session_scope
from ..protocols.compliance import evaluate_experiment_compliance
from ..protocols.schemas import ProtocolAttachRequest, ProtocolCreateRequest, TemplateInstantiateRequest
from ..protocols.service import (
    attach_protocol_to_experiment,
    create_protocol_version,
    diff_protocol_versions,
    get_protocol_template,
    instantiate_protocol_template,
    list_protocol_templates,
    list_protocol_versions,
    preflight_definition,
    protocol_payload,
    publish_protocol_version,
)
from ..storage.entities import Experiment, ExperimentProtocolVersion
from ..storage.repository import require

router = APIRouter(tags=["experiment protocols & reusable research templates"])


@router.get("/protocols", response_model=list[dict])
def get_protocols(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    with session_scope() as session:
        return list_protocol_versions(session, limit=limit, offset=offset)


@router.post("/protocols/preflight", response_model=dict)
def protocol_preflight(request: ProtocolCreateRequest):
    with session_scope() as session:
        return {
            "protocol_name": request.protocol_name,
            **preflight_definition(session, request.definition),
        }


@router.post("/protocols", response_model=dict, status_code=201)
def create_protocol(request: ProtocolCreateRequest):
    with session_scope() as session:
        version, created = create_protocol_version(session, request)
        return {**protocol_payload(session, version), "created": created}


@router.get("/protocols/{identity}", response_model=dict)
def get_protocol(identity: UUID):
    with session_scope() as session:
        return protocol_payload(session, require(session, ExperimentProtocolVersion, str(identity)))


@router.get("/protocols/{identity}/preflight", response_model=dict)
def existing_protocol_preflight(identity: UUID):
    with session_scope() as session:
        version = require(session, ExperimentProtocolVersion, str(identity))
        return {
            "protocol_version_id": version.id,
            **preflight_definition(session, version.canonical_definition),
        }


@router.post("/protocols/{identity}/publish", response_model=dict)
def publish_protocol(identity: UUID):
    with session_scope() as session:
        version = publish_protocol_version(session, str(identity))
        return protocol_payload(session, version)


@router.get("/protocols/{identity}/diff/{other_identity}", response_model=dict)
def protocol_diff(identity: UUID, other_identity: UUID):
    with session_scope() as session:
        return diff_protocol_versions(session, str(identity), str(other_identity))


@router.get("/protocol-templates", response_model=list[dict])
def get_protocol_templates():
    with session_scope() as session:
        return list_protocol_templates(session)


@router.get("/protocol-templates/{identity}", response_model=dict)
def get_single_protocol_template(identity: UUID):
    with session_scope() as session:
        return get_protocol_template(session, str(identity))


@router.post("/protocol-templates/{identity}/instantiate", response_model=dict, status_code=201)
def instantiate_template(identity: UUID, request: TemplateInstantiateRequest):
    with session_scope() as session:
        version, created = instantiate_protocol_template(session, str(identity), request)
        return {**protocol_payload(session, version), "created": created}


@router.get("/experiments/{identity}/protocol", response_model=dict)
def experiment_protocol(identity: UUID):
    with session_scope() as session:
        experiment = require(session, Experiment, str(identity))
        if not experiment.protocol_version_id:
            return {
                "experiment_id": experiment.id,
                "status": "LEGACY_UNSPECIFIED",
                "protocol_version": None,
                "reason": "This experiment predates experimental protocol capture or was executed without a declared protocol.",
            }
        version = require(session, ExperimentProtocolVersion, experiment.protocol_version_id)
        return {
            "experiment_id": experiment.id,
            "status": "AVAILABLE",
            "protocol_version": protocol_payload(session, version),
        }


@router.post("/experiments/{identity}/protocol/attach", response_model=dict)
def attach_protocol(identity: UUID, request: ProtocolAttachRequest):
    with session_scope() as session:
        version = attach_protocol_to_experiment(session, str(identity), str(request.protocol_version_id))
        return {
            "experiment_id": str(identity),
            "protocol_version_id": version.id,
            "protocol_fingerprint": version.definition_fingerprint,
            "status": "ATTACHED",
            "protocol_version": protocol_payload(session, version),
        }


@router.get("/experiments/{identity}/protocol/compliance", response_model=dict)
def experiment_protocol_compliance(identity: UUID):
    with session_scope() as session:
        return evaluate_experiment_compliance(session, str(identity))

