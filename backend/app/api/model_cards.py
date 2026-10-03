from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from ..database import session_scope
from ..model_cards.service import card_summary, get_or_create_card
from ..storage.entities import Artifact, ModelRecord
from ..storage.repository import require

router = APIRouter(tags=["model cards"])


@router.get("/models/{identity}/card", response_model=dict)
def model_card(identity: UUID):
    with session_scope() as session:
        card, artifact = get_or_create_card(session, str(identity))
        session.flush()
        result = {**card, "artifact": {"artifact_id": artifact.id, "integrity_hash": artifact.integrity_hash, "immutable": artifact.immutable}}
        return result


@router.get("/models/{identity}/card/summary", response_model=dict)
def model_card_summary(identity: UUID):
    with session_scope() as session:
        card, artifact = get_or_create_card(session, str(identity))
        session.flush()
        return card_summary(card, artifact)


@router.get("/models/{identity}/card/evidence", response_model=dict)
def model_card_evidence(identity: UUID):
    with session_scope() as session:
        card, artifact = get_or_create_card(session, str(identity))
        session.flush()
        return {
            "model_id": str(identity),
            "card_id": card["card_id"],
            "artifact_id": artifact.id,
            "source_fingerprint": card["provenance"]["source_fingerprint"],
            "sources": card["provenance"]["evidence_sources"],
            "availability": card_summary(card, artifact)["evidence_availability"],
            "evidence_gaps": card["evidence_gaps"],
        }


@router.get("/model-cards", response_model=dict)
def list_model_cards(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    with session_scope() as session:
        total = session.scalar(select(func.count()).select_from(Artifact).where(Artifact.artifact_type == "model_card")) or 0
        records = list(session.scalars(
            select(Artifact)
            .where(Artifact.artifact_type == "model_card")
            .order_by(Artifact.created_at.desc())
            .offset(offset)
            .limit(limit)
        ))
        return {
            "items": [{
                "artifact_id": item.id,
                "model_id": item.model_id,
                "experiment_id": item.experiment_id,
                "run_id": item.run_id,
                "schema_version": item.details.get("schema_version", "unknown"),
                "card_id": item.details.get("card_id", "unknown"),
                "card_status": item.details.get("card_status", "UNAVAILABLE"),
                "integrity_hash": item.integrity_hash,
                "created_at": item.created_at,
            } for item in records],
            "pagination": {"limit": limit, "offset": offset, "total": total},
        }