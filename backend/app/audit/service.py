from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ..storage.entities import Experiment, Job, Run, ScientificAuditEvent
from ..utils.errors import AppError
from ..utils.serialization import clean_json, fingerprint, software_versions, utcnow
from .schemas import (
    CORE_EVENT_TYPES,
    EVENT_CATEGORIES,
    EVENT_SCHEMA_VERSION,
    AuditIntegrityIssue,
    AuditIntegrityOut,
    AuditTimelineOut,
    ScientificAuditEventOut,
)

SECRET_KEY_SUBSTRINGS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "credential",
    "authorization",
    "cookie",
    "bearer",
)


def sanitize_audit_metadata(data: Any, depth: int = 0) -> Any:
    """Recursively cleans metadata to eliminate secrets, credentials, and giant raw data dumps."""
    if depth > 8:
        return "<nested_limit_reached>"
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            k_lower = str(key).lower()
            if any(s in k_lower for s in SECRET_KEY_SUBSTRINGS):
                sanitized[key] = "<redacted_credential>"
            elif k_lower in ("data", "rows", "records", "csv_content") and isinstance(value, (list, str)):
                sanitized[key] = f"<omitted_raw_data_count_{len(value)}>"
            else:
                sanitized[key] = sanitize_audit_metadata(value, depth + 1)
        return sanitized
    if isinstance(data, (list, tuple)):
        if len(data) > 100:
            return [sanitize_audit_metadata(item, depth + 1) for item in data[:100]] + [f"<truncated_{len(data)-100}_more>"]
        return [sanitize_audit_metadata(item, depth + 1) for item in data]
    if isinstance(data, str) and len(data) > 2000:
        return data[:2000] + "…<truncated>"
    return data


def compute_event_fingerprint(
    *,
    schema_version: str,
    event_type: str,
    event_category: str,
    occurred_at: datetime,
    actor_type: str,
    actor_reference: str | None,
    source_component: str,
    operation_key: str | None,
    object_type: str,
    object_id: str,
    parent_object_type: str | None,
    parent_object_id: str | None,
    before_fingerprint: str | None,
    after_fingerprint: str | None,
    previous_event_fingerprint: str | None,
    metadata: dict[str, Any],
) -> str:
    """Computes a deterministic SHA-256 fingerprint from canonical audit event fields."""
    if isinstance(occurred_at, datetime):
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        occurred_str = occurred_at.astimezone(timezone.utc).isoformat()
    else:
        occurred_str = str(occurred_at)

    canonical = {
        "schema_version": schema_version,
        "event_type": event_type,
        "event_category": event_category,
        "occurred_at": occurred_str,
        "actor_type": actor_type,
        "actor_reference": actor_reference,
        "source_component": source_component,
        "operation_key": operation_key,
        "object_type": object_type,
        "object_id": object_id,
        "parent_object_type": parent_object_type,
        "parent_object_id": parent_object_id,
        "before_fingerprint": before_fingerprint,
        "after_fingerprint": after_fingerprint,
        "previous_event_fingerprint": previous_event_fingerprint,
        "metadata": metadata,
    }
    return fingerprint(clean_json(canonical))


def record_event(
    session: Session,
    *,
    event_type: str,
    event_category: str,
    object_type: str,
    object_id: str,
    source_component: str,
    actor_type: str = "SYSTEM",
    actor_reference: str | None = None,
    operation_key: str | None = None,
    parent_object_type: str | None = None,
    parent_object_id: str | None = None,
    before_fingerprint: str | None = None,
    after_fingerprint: str | None = None,
    metadata: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> ScientificAuditEvent:
    """Append-only recording of a scientific audit event with idempotency and event chaining."""
    # 1. Idempotency check: if an operation_key + event_type already exists, return it
    if operation_key is not None:
        existing = session.scalar(
            select(ScientificAuditEvent).where(
                ScientificAuditEvent.operation_key == operation_key,
                ScientificAuditEvent.event_type == event_type,
            )
        )
        if existing is not None:
            return existing

    occurred = occurred_at or utcnow()
    if occurred.tzinfo is None:
        occurred = occurred.replace(tzinfo=timezone.utc)
    recorded = utcnow()

    # 2. Event chaining: find the most recent event related to this object or parent
    prev_query = select(ScientificAuditEvent).where(
        or_(
            and_(ScientificAuditEvent.object_type == object_type, ScientificAuditEvent.object_id == object_id),
            and_(ScientificAuditEvent.parent_object_id == object_id),
            and_(ScientificAuditEvent.object_id == parent_object_id) if parent_object_id else False,
            and_(ScientificAuditEvent.parent_object_id == parent_object_id) if parent_object_id else False,
        )
    ).order_by(ScientificAuditEvent.occurred_at.desc(), ScientificAuditEvent.id.desc()).limit(1)

    previous = session.scalar(prev_query)
    previous_event_fingerprint = previous.event_fingerprint if previous else None

    # 3. Sanitize metadata (zero secrets, credentials, or raw rows)
    safe_metadata = sanitize_audit_metadata(metadata or {})

    # 4. Deterministic event fingerprint
    ev_fingerprint = compute_event_fingerprint(
        schema_version=EVENT_SCHEMA_VERSION,
        event_type=event_type,
        event_category=event_category,
        occurred_at=occurred,
        actor_type=actor_type,
        actor_reference=actor_reference,
        source_component=source_component,
        operation_key=operation_key,
        object_type=object_type,
        object_id=object_id,
        parent_object_type=parent_object_type,
        parent_object_id=parent_object_id,
        before_fingerprint=before_fingerprint,
        after_fingerprint=after_fingerprint,
        previous_event_fingerprint=previous_event_fingerprint,
        metadata=safe_metadata,
    )

    event = ScientificAuditEvent(
        id=str(uuid4()),
        schema_version=EVENT_SCHEMA_VERSION,
        event_type=event_type,
        event_category=event_category,
        occurred_at=occurred,
        recorded_at=recorded,
        actor_type=actor_type,
        actor_reference=actor_reference,
        source_component=source_component,
        operation_key=operation_key,
        object_type=object_type,
        object_id=object_id,
        parent_object_type=parent_object_type,
        parent_object_id=parent_object_id,
        before_fingerprint=before_fingerprint,
        after_fingerprint=after_fingerprint,
        previous_event_fingerprint=previous_event_fingerprint,
        event_fingerprint=ev_fingerprint,
        metadata_payload=safe_metadata,
    )
    session.add(event)
    session.flush()
    return event


def _to_event_out(event: ScientificAuditEvent) -> ScientificAuditEventOut:
    return ScientificAuditEventOut(
        id=event.id,
        schema_version=event.schema_version,
        event_type=event.event_type,
        event_category=event.event_category,
        occurred_at=event.occurred_at,
        recorded_at=event.recorded_at,
        actor_type=event.actor_type,
        actor_reference=event.actor_reference,
        source_component=event.source_component,
        operation_key=event.operation_key,
        object_type=event.object_type,
        object_id=event.object_id,
        parent_object_type=event.parent_object_type,
        parent_object_id=event.parent_object_id,
        before_fingerprint=event.before_fingerprint,
        after_fingerprint=event.after_fingerprint,
        previous_event_fingerprint=event.previous_event_fingerprint,
        event_fingerprint=event.event_fingerprint,
        metadata=event.metadata_payload or {},
    )


def get_events(
    session: Session,
    *,
    event_category: str | None = None,
    event_type: str | None = None,
    object_type: str | None = None,
    object_id: str | None = None,
    parent_object_id: str | None = None,
    source_component: str | None = None,
    actor_type: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ScientificAuditEventOut]:
    """Retrieve filtered, bounded, deterministically-ordered scientific audit events."""
    limit = min(max(1, limit), 200)
    offset = max(0, offset)

    stmt = select(ScientificAuditEvent)
    if event_category:
        stmt = stmt.where(ScientificAuditEvent.event_category == event_category)
    if event_type:
        stmt = stmt.where(ScientificAuditEvent.event_type == event_type)
    if object_type:
        stmt = stmt.where(ScientificAuditEvent.object_type == object_type)
    if object_id:
        stmt = stmt.where(ScientificAuditEvent.object_id == object_id)
    if parent_object_id:
        stmt = stmt.where(ScientificAuditEvent.parent_object_id == parent_object_id)
    if source_component:
        stmt = stmt.where(ScientificAuditEvent.source_component == source_component)
    if actor_type:
        stmt = stmt.where(ScientificAuditEvent.actor_type == actor_type)
    if start_time:
        stmt = stmt.where(ScientificAuditEvent.occurred_at >= start_time)
    if end_time:
        stmt = stmt.where(ScientificAuditEvent.occurred_at <= end_time)

    # Deterministic ordering: occurred_at DESC, id DESC
    stmt = stmt.order_by(ScientificAuditEvent.occurred_at.desc(), ScientificAuditEvent.id.desc()).offset(offset).limit(limit)
    rows = list(session.scalars(stmt))
    return [_to_event_out(r) for r in rows]


def get_object_timeline(
    session: Session,
    object_type: str,
    object_id: str,
    *,
    include_children: bool = True,
    event_category: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> AuditTimelineOut:
    """Retrieve full chronological audit timeline for an object and optionally its children."""
    limit = min(max(1, limit), 300)
    offset = max(0, offset)

    conditions = [
        and_(ScientificAuditEvent.object_type == object_type, ScientificAuditEvent.object_id == object_id)
    ]
    if include_children:
        conditions.append(
            and_(ScientificAuditEvent.parent_object_type == object_type, ScientificAuditEvent.parent_object_id == object_id)
        )

    stmt = select(ScientificAuditEvent).where(or_(*conditions))
    if event_category:
        stmt = stmt.where(ScientificAuditEvent.event_category == event_category)

    stmt = stmt.order_by(ScientificAuditEvent.occurred_at.desc(), ScientificAuditEvent.id.desc())
    all_events = list(session.scalars(stmt))
    total_count = len(all_events)
    page_events = all_events[offset : offset + limit]

    categories_present = sorted(list({e.event_category for e in all_events}))
    out_events = [_to_event_out(e) for e in page_events]

    # Quick integrity check
    integrity = verify_audit_integrity(session, object_type=object_type, object_id=object_id)
    integrity_status = "VERIFIED" if integrity.valid else "INTEGRITY_WARNING"

    return AuditTimelineOut(
        object_type=object_type,
        object_id=object_id,
        total_events=total_count,
        events=out_events,
        categories_present=categories_present,
        integrity_status=integrity_status,
        legacy_disclaimer=None if total_count > 0 else f"No audit events recorded for {object_type} {object_id}.",
    )


def get_experiment_timeline(
    session: Session,
    experiment_id: str,
    *,
    event_category: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> AuditTimelineOut:
    """Retrieve experiment-centric audit timeline covering runs, jobs, checkpoints, models, and packages."""
    limit = min(max(1, limit), 300)
    offset = max(0, offset)

    experiment = session.get(Experiment, experiment_id)
    if experiment is None:
        raise AppError("experiment_not_found", f"Experiment {experiment_id} not found.", 404)

    # Gathers related run IDs and job IDs
    run_ids = list(session.scalars(select(Run.id).where(Run.experiment_id == experiment_id)))
    job_ids = list(session.scalars(select(Job.id).where(Job.experiment_id == experiment_id)))

    conditions = [
        and_(ScientificAuditEvent.object_type == "experiment", ScientificAuditEvent.object_id == experiment_id),
        ScientificAuditEvent.parent_object_id == experiment_id,
    ]
    if run_ids:
        conditions.append(ScientificAuditEvent.object_id.in_(run_ids))
    if job_ids:
        conditions.append(ScientificAuditEvent.object_id.in_(job_ids))

    stmt = select(ScientificAuditEvent).where(or_(*conditions))
    if event_category:
        stmt = stmt.where(ScientificAuditEvent.event_category == event_category)

    stmt = stmt.order_by(ScientificAuditEvent.occurred_at.desc(), ScientificAuditEvent.id.desc())
    all_events = list(session.scalars(stmt))
    total_count = len(all_events)
    page_events = all_events[offset : offset + limit]

    categories_present = sorted(list({e.event_category for e in all_events}))
    out_events = [_to_event_out(e) for e in page_events]

    integrity = verify_audit_integrity(session, object_type="experiment", object_id=experiment_id)
    integrity_status = "VERIFIED" if integrity.valid else "INTEGRITY_WARNING"

    legacy_disclaimer = None
    if total_count == 0:
        legacy_disclaimer = (
            "Audit history is recorded from platform upgrade (2026-10-03). "
            "Earlier platform activity for this historical experiment was not captured. "
            "Existing scientific configuration, models, and evidence packages remain authoritative."
        )

    return AuditTimelineOut(
        object_type="experiment",
        object_id=experiment_id,
        total_events=total_count,
        events=out_events,
        categories_present=categories_present,
        integrity_status=integrity_status,
        legacy_disclaimer=legacy_disclaimer,
    )


def verify_audit_integrity(
    session: Session,
    *,
    object_type: str | None = None,
    object_id: str | None = None,
) -> AuditIntegrityOut:
    """Scans audit events for fingerprint consistency, schema conformity, and chain link continuity."""
    stmt = select(ScientificAuditEvent)
    if object_type and object_id:
        stmt = stmt.where(
            or_(
                and_(ScientificAuditEvent.object_type == object_type, ScientificAuditEvent.object_id == object_id),
                and_(ScientificAuditEvent.parent_object_id == object_id),
            )
        )
    stmt = stmt.order_by(ScientificAuditEvent.occurred_at.asc(), ScientificAuditEvent.id.asc())
    events = list(session.scalars(stmt))

    issues: list[AuditIntegrityIssue] = []
    seen_ops: set[tuple[str, str]] = set()

    for event in events:
        # 1. Recompute and verify fingerprint
        expected_fp = compute_event_fingerprint(
            schema_version=event.schema_version,
            event_type=event.event_type,
            event_category=event.event_category,
            occurred_at=event.occurred_at,
            actor_type=event.actor_type,
            actor_reference=event.actor_reference,
            source_component=event.source_component,
            operation_key=event.operation_key,
            object_type=event.object_type,
            object_id=event.object_id,
            parent_object_type=event.parent_object_type,
            parent_object_id=event.parent_object_id,
            before_fingerprint=event.before_fingerprint,
            after_fingerprint=event.after_fingerprint,
            previous_event_fingerprint=event.previous_event_fingerprint,
            metadata=event.metadata_payload or {},
        )
        if event.event_fingerprint != expected_fp:
            issues.append(
                AuditIntegrityIssue(
                    event_id=event.id,
                    issue_type="FINGERPRINT_MISMATCH",
                    message=f"Event {event.id} fingerprint mismatch. Persisted: {event.event_fingerprint[:16]}…, Expected: {expected_fp[:16]}…",
                    details={"persisted": event.event_fingerprint, "expected": expected_fp},
                )
            )

        # 2. Check controlled taxonomy
        if event.event_category not in EVENT_CATEGORIES:
            issues.append(
                AuditIntegrityIssue(
                    event_id=event.id,
                    issue_type="UNKNOWN_CATEGORY",
                    message=f"Event {event.id} uses unsupported category '{event.event_category}'.",
                    details={"event_category": event.event_category},
                )
            )

        # 3. Check duplicate operation keys
        if event.operation_key:
            op_key_pair = (event.operation_key, event.event_type)
            if op_key_pair in seen_ops:
                issues.append(
                    AuditIntegrityIssue(
                        event_id=event.id,
                        issue_type="DUPLICATE_OPERATION_KEY",
                        message=f"Duplicate operation key '{event.operation_key}' with event type '{event.event_type}'.",
                        details={"operation_key": event.operation_key, "event_type": event.event_type},
                    )
                )
            seen_ops.add(op_key_pair)

    interpretation = (
        f"Audit integrity verified across {len(events)} event(s)."
        if not issues
        else f"Integrity scan detected {len(issues)} structured issue(s) across {len(events)} event(s)."
    )

    return AuditIntegrityOut(
        valid=len(issues) == 0,
        total_events=len(events),
        issues=issues,
        interpretation=interpretation,
    )


def export_audit_timeline(session: Session, object_type: str, object_id: str) -> dict[str, Any]:
    """Generates a clean, deterministic, machine-readable JSON export of an object's audit timeline."""
    if object_type == "experiment":
        timeline = get_experiment_timeline(session, object_id, limit=300)
    else:
        timeline = get_object_timeline(session, object_type, object_id, limit=300)

    integrity = verify_audit_integrity(session, object_type=object_type, object_id=object_id)

    export_payload = {
        "export_schema_version": "scientific_audit_export_v1",
        "exported_at": utcnow().isoformat(),
        "object_type": object_type,
        "object_id": object_id,
        "total_events": timeline.total_events,
        "integrity_status": timeline.integrity_status,
        "integrity_details": {
            "valid": integrity.valid,
            "issues": [i.model_dump() for i in integrity.issues],
        },
        "software_versions": software_versions(),
        "events": [e.model_dump(mode="json") for e in timeline.events],
        "scientific_boundary": timeline.scientific_boundary,
    }
    return export_payload
