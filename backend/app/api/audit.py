from __future__ import annotations

import json
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Query, Response
from ..database import session_scope
from ..audit.schemas import AuditIntegrityOut, AuditTimelineOut, ScientificAuditEventOut
from ..audit.service import (
    export_audit_timeline,
    get_events,
    get_experiment_timeline,
    get_object_timeline,
    verify_audit_integrity,
)

router = APIRouter(tags=["scientific audit timeline"])


@router.get("/audit/events", response_model=list[ScientificAuditEventOut])
def list_audit_events(
    event_category: str | None = Query(None, description="Category filter (e.g. EXPERIMENT, JOB, PIPELINE, RUN, EVIDENCE)"),
    event_type: str | None = Query(None, description="Specific event type (e.g. EXPERIMENT_CREATED, JOB_STARTED)"),
    object_type: str | None = Query(None, description="Target object type"),
    object_id: str | None = Query(None, description="Target object identifier"),
    parent_object_id: str | None = Query(None, description="Parent object identifier"),
    source_component: str | None = Query(None, description="Source component name"),
    actor_type: str | None = Query(None, description="Actor type (SYSTEM, USER)"),
    start_time: datetime | None = Query(None, description="Lower bound occurred_at"),
    end_time: datetime | None = Query(None, description="Upper bound occurred_at"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    with session_scope() as session:
        return get_events(
            session,
            event_category=event_category,
            event_type=event_type,
            object_type=object_type,
            object_id=object_id,
            parent_object_id=parent_object_id,
            source_component=source_component,
            actor_type=actor_type,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )


@router.get("/audit/integrity", response_model=AuditIntegrityOut)
def check_audit_integrity(
    object_type: str | None = Query(None),
    object_id: str | None = Query(None),
):
    with session_scope() as session:
        return verify_audit_integrity(session, object_type=object_type, object_id=object_id)


@router.get("/experiments/{identity}/audit", response_model=AuditTimelineOut)
def get_experiment_audit_timeline(
    identity: UUID,
    event_category: str | None = Query(None),
    limit: int = Query(100, ge=1, le=300),
    offset: int = Query(0, ge=0),
):
    with session_scope() as session:
        return get_experiment_timeline(
            session,
            str(identity),
            event_category=event_category,
            limit=limit,
            offset=offset,
        )


@router.get("/experiments/{identity}/audit/export")
def export_experiment_audit(identity: UUID):
    with session_scope() as session:
        data = export_audit_timeline(session, "experiment", str(identity))
        content = json.dumps(data, indent=2, ensure_ascii=False)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="audit-timeline-{identity}.json"'},
        )


@router.get("/audit/{object_type}/{object_id}", response_model=AuditTimelineOut)
def get_object_audit_timeline(
    object_type: str,
    object_id: str,
    event_category: str | None = Query(None),
    limit: int = Query(100, ge=1, le=300),
    offset: int = Query(0, ge=0),
):
    with session_scope() as session:
        return get_object_timeline(
            session,
            object_type=object_type,
            object_id=object_id,
            event_category=event_category,
            limit=limit,
            offset=offset,
        )
