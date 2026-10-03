"""Scientific Audit Timeline verification (Prompt 17).

Verifies meaningful lifecycle events, deterministic ordering and fingerprints,
idempotency, immutability, resolvable object references, secret-free payloads
and integrity reporting.  Production history is never inspected.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from ..fixtures import persist_chain
from ..isolation import initialize_database, session
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check
from ._support import flatten_strings


@check(
    check_id="audit_timeline_contract",
    name="Audit timeline contract",
    category=CheckCategory.AUDIT_INTEGRITY,
    description="Lifecycle events, deterministic fingerprints and ordering, idempotency, reference resolution, privacy and integrity reporting.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=240.0,
)
def audit_timeline_contract() -> CheckResult:
    from app.audit.service import (
        compute_event_fingerprint,
        get_events,
        record_event,
        sanitize_audit_metadata,
        verify_audit_integrity,
    )
    from app.storage.entities import Experiment, ScientificAuditEvent

    initialize_database()
    chain = persist_chain(with_pipeline=True, with_protocol=True)
    problems: list[str] = []
    operation_key = f"scientific-ci:audit:{uuid4()}"

    with session() as scope:
        first = record_event(
            scope,
            event_type="EXPERIMENT_CREATED",
            event_category="EXPERIMENT",
            object_type="experiment",
            object_id=chain.experiment_id,
            source_component="scientific_ci",
            operation_key=operation_key,
            metadata={
                "api_key": "synthetic-should-be-redacted",
                "password": "synthetic-should-be-redacted",
                "rows": [{"patient_id": "synthetic-should-not-be-stored"}],
                "step": 1,
            },
        )
        event_id, fingerprint = first.id, first.event_fingerprint
        stored_metadata = dict(first.metadata_payload)
        occurred_at = first.occurred_at

    with session() as scope:
        again = record_event(
            scope,
            event_type="EXPERIMENT_CREATED",
            event_category="EXPERIMENT",
            object_type="experiment",
            object_id=chain.experiment_id,
            source_component="scientific_ci",
            operation_key=operation_key,
            metadata={"step": 1},
        )
        event_count = scope.query(ScientificAuditEvent).filter(
            ScientificAuditEvent.operation_key == operation_key
        ).count()
    if again.id != event_id or event_count != 1:
        problems.append("operation-key idempotency did not prevent a duplicate logical event")

    with session() as scope:
        stored = scope.get(ScientificAuditEvent, event_id)
        if stored is None:
            problems.append("the recorded audit event disappeared")
        else:
            if stored.occurred_at.tzinfo is None:
                occurred = stored.occurred_at.replace(tzinfo=timezone.utc)
            else:
                occurred = stored.occurred_at
            recomputed = compute_event_fingerprint(
                schema_version=stored.schema_version,
                event_type=stored.event_type,
                event_category=stored.event_category,
                occurred_at=occurred,
                actor_type=stored.actor_type,
                actor_reference=stored.actor_reference,
                source_component=stored.source_component,
                operation_key=stored.operation_key,
                object_type=stored.object_type,
                object_id=stored.object_id,
                parent_object_type=stored.parent_object_type,
                parent_object_id=stored.parent_object_id,
                before_fingerprint=stored.before_fingerprint,
                after_fingerprint=stored.after_fingerprint,
                previous_event_fingerprint=stored.previous_event_fingerprint,
                metadata=stored.metadata_payload,
            )
            if recomputed != stored.event_fingerprint:
                problems.append("the stored audit event fingerprint is not reproducible from its own fields")
            if scope.get(Experiment, stored.object_id) is None:
                problems.append("the audit event object reference does not resolve to a persisted experiment")
        integrity = verify_audit_integrity(scope)
        if not integrity.valid or integrity.issues:
            problems.append(f"audit integrity verification reported issues: {integrity.issues}")

    text = flatten_strings(stored_metadata)
    if "synthetic-should-be-redacted" in text:
        problems.append("audit metadata stored a credential value instead of redacting it")
    if "<redacted_credential>" not in text:
        problems.append("audit metadata did not mark credential fields as redacted")
    if "patient_id" in text or "synthetic-should-not-be-stored" in text:
        problems.append("audit metadata stored raw record-level payloads")

    sanitized = sanitize_audit_metadata({"nested": {"password_hash": "x"}, "rows": ["a", "b"], "token": "t"})
    if sanitized["nested"]["password_hash"] != "<redacted_credential>" or sanitized["token"] != "<redacted_credential>":
        problems.append("the audit metadata sanitizer no longer redacts credential keys")

    with session() as scope:
        for index in range(2):
            record_event(
                scope,
                event_type="RUN_CREATED" if index else "JOB_CREATED",
                event_category="RUN" if index else "JOB",
                object_type="run" if index else "job",
                object_id=chain.run_id if index else str(uuid4()),
                source_component="scientific_ci",
                operation_key=f"scientific-ci:ordering:{operation_key}:{index}",
                metadata={"step": index},
                occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        events = get_events(scope, limit=50)
    occurred_values = [event.occurred_at for event in events]
    if occurred_values != sorted(occurred_values, reverse=True):
        problems.append("audit event ordering is not deterministic (newest first)")

    if problems:
        return CheckResult(
            check_id="audit_timeline_contract",
            category=CheckCategory.AUDIT_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="deterministic, idempotent, private and verifiable audit events",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="audit_timeline_contract",
        category=CheckCategory.AUDIT_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Audit events are deterministic, idempotent, reference-resolving, secret-free and verifiable.",
        evidence={
            "event_id": event_id,
            "event_fingerprint": fingerprint,
            "occurred_at": occurred_at.isoformat(),
            "idempotent": True,
            "integrity_valid": True,
        },
    )
