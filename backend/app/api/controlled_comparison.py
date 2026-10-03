from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from ..controlled_comparison.service import (
    create_protocol,
    latest_protocol,
    preflight_protocol,
    protocol_payload,
)
from ..database import session_scope
from ..storage.entities import ControlledComparisonProtocol, Experiment
from ..storage.repository import require
from ..utils.errors import AppError

router = APIRouter(prefix="/experiments/{identity}/controlled-comparison", tags=["controlled comparison protocol"])


class ControlledComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    classical_model_ids: list[UUID] | None = Field(default=None, min_length=1)
    quantum_model_ids: list[UUID] | None = Field(default=None, min_length=1)


def _ids(values):
    return [str(item) for item in values] if values else None


@router.post("/preflight", response_model=dict)
def controlled_comparison_preflight(identity: UUID, request: ControlledComparisonRequest):
    with session_scope() as session:
        return preflight_protocol(session, str(identity), _ids(request.classical_model_ids), _ids(request.quantum_model_ids))


@router.post("", response_model=dict, status_code=201)
def run_controlled_comparison(identity: UUID, request: ControlledComparisonRequest):
    with session_scope() as session:
        protocol = create_protocol(session, str(identity), _ids(request.classical_model_ids), _ids(request.quantum_model_ids))
        session.flush()
        return protocol_payload(protocol)


@router.get("", response_model=dict)
def get_latest_controlled_comparison(identity: UUID):
    with session_scope() as session:
        require(session, Experiment, str(identity))
        protocol = latest_protocol(session, str(identity))
        if protocol is None:
            raise AppError("controlled_comparison_not_available", "No persisted controlled comparison protocol is available for this experiment.", 404)
        return protocol_payload(protocol)


@router.get("/{protocol_id}", response_model=dict)
def get_controlled_comparison(identity: UUID, protocol_id: UUID):
    with session_scope() as session:
        protocol = require(session, ControlledComparisonProtocol, str(protocol_id))
        if protocol.experiment_id != str(identity):
            raise AppError("controlled_comparison_not_found", "The requested protocol is not associated with this experiment.", 404)
        return protocol_payload(protocol)


@router.get("/{protocol_id}/provenance", response_model=dict)
def get_controlled_comparison_provenance(identity: UUID, protocol_id: UUID):
    with session_scope() as session:
        protocol = require(session, ControlledComparisonProtocol, str(protocol_id))
        if protocol.experiment_id != str(identity):
            raise AppError("controlled_comparison_not_found", "The requested protocol is not associated with this experiment.", 404)
        return {
            "protocol_id": protocol.id,
            "experiment_id": protocol.experiment_id,
            "schema_version": protocol.schema_version,
            "status": protocol.status,
            "configuration_fingerprint": protocol.configuration_fingerprint,
            "protocol_fingerprint": protocol.protocol_fingerprint,
            "provenance": protocol.provenance,
            "artifact_id": protocol.artifact_id,
        }