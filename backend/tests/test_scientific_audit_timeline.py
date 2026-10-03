from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select

from app.database import session_scope
from app.storage.entities import Experiment, Job, Run, ScientificAuditEvent
from app.audit.service import (
    compute_event_fingerprint,
    export_audit_timeline,
    get_events,
    get_experiment_timeline,
    get_object_timeline,
    record_event,
    sanitize_audit_metadata,
    verify_audit_integrity,
)
from app.utils.errors import AppError
from app.utils.serialization import utcnow


def test_record_event_and_deterministic_fingerprint():
    exp_id = str(uuid4())
    with session_scope() as session:
        ev = record_event(
            session,
            event_type="EXPERIMENT_CREATED",
            event_category="EXPERIMENT",
            object_type="experiment",
            object_id=exp_id,
            source_component="experiment_service",
            metadata={"seed": 42, "models": ["ridge"]},
        )
        assert ev.id is not None
        assert ev.event_fingerprint is not None
        assert len(ev.event_fingerprint) == 64
        assert ev.event_type == "EXPERIMENT_CREATED"
        assert ev.event_category == "EXPERIMENT"

        # Recomputing fingerprint with identical data yields exact match
        fp = compute_event_fingerprint(
            schema_version=ev.schema_version,
            event_type=ev.event_type,
            event_category=ev.event_category,
            occurred_at=ev.occurred_at,
            actor_type=ev.actor_type,
            actor_reference=ev.actor_reference,
            source_component=ev.source_component,
            operation_key=ev.operation_key,
            object_type=ev.object_type,
            object_id=ev.object_id,
            parent_object_type=ev.parent_object_type,
            parent_object_id=ev.parent_object_id,
            before_fingerprint=ev.before_fingerprint,
            after_fingerprint=ev.after_fingerprint,
            previous_event_fingerprint=ev.previous_event_fingerprint,
            metadata=ev.metadata_payload,
        )
        assert fp == ev.event_fingerprint


def test_event_immutability():
    exp_id = str(uuid4())
    with session_scope() as session:
        ev = record_event(
            session,
            event_type="EXPERIMENT_CREATED",
            event_category="EXPERIMENT",
            object_type="experiment",
            object_id=exp_id,
            source_component="experiment_service",
        )
        ev_id = ev.id

    # Test update prevention
    with session_scope() as session:
        event = session.get(ScientificAuditEvent, ev_id)
        event.event_type = "TAMPERED_EVENT"
        with pytest.raises(AppError) as exc_info:
            session.flush()
        assert exc_info.value.code == "audit_event_immutable"
        session.rollback()

    # Test deletion prevention
    with session_scope() as session:
        event = session.get(ScientificAuditEvent, ev_id)
        session.delete(event)
        with pytest.raises(AppError) as exc_info:
            session.flush()
        assert exc_info.value.code == "audit_event_immutable"
        session.rollback()


def test_idempotency_via_operation_key():
    exp_id = str(uuid4())
    op_key = f"op-create-exp-{uuid4()}"
    with session_scope() as session:
        ev1 = record_event(
            session,
            event_type="EXPERIMENT_CREATED",
            event_category="EXPERIMENT",
            object_type="experiment",
            object_id=exp_id,
            source_component="experiment_service",
            operation_key=op_key,
            metadata={"attempt": 1},
        )
        ev2 = record_event(
            session,
            event_type="EXPERIMENT_CREATED",
            event_category="EXPERIMENT",
            object_type="experiment",
            object_id=exp_id,
            source_component="experiment_service",
            operation_key=op_key,
            metadata={"attempt": 2},
        )
        assert ev1.id == ev2.id
        assert ev1.event_fingerprint == ev2.event_fingerprint


def test_deterministic_ordering_and_pagination():
    obj_id = str(uuid4())
    base_time = utcnow()
    with session_scope() as session:
        for i in range(5):
            record_event(
                session,
                event_type="JOB_STARTED",
                event_category="JOB",
                object_type="job",
                object_id=obj_id,
                source_component="job_engine",
                occurred_at=base_time + timedelta(seconds=i * 10),
                metadata={"step": i},
            )

    with session_scope() as session:
        events = get_events(session, object_id=obj_id, limit=3, offset=0)
        assert len(events) == 3
        # Should be ordered descending (step 4, step 3, step 2)
        assert events[0].metadata["step"] == 4
        assert events[1].metadata["step"] == 3
        assert events[2].metadata["step"] == 2

        # Next page
        page_2 = get_events(session, object_id=obj_id, limit=3, offset=3)
        assert len(page_2) == 2
        assert page_2[0].metadata["step"] == 1
        assert page_2[1].metadata["step"] == 0


def test_filtering_by_category_type_and_time():
    obj_id = str(uuid4())
    t0 = utcnow()
    with session_scope() as session:
        record_event(
            session,
            event_type="RUN_CREATED",
            event_category="RUN",
            object_type="run",
            object_id=obj_id,
            source_component="run_service",
            occurred_at=t0,
        )
        record_event(
            session,
            event_type="JOB_STARTED",
            event_category="JOB",
            object_type="job",
            object_id=obj_id,
            source_component="job_engine",
            occurred_at=t0 + timedelta(seconds=5),
        )

    with session_scope() as session:
        run_events = get_events(session, object_id=obj_id, event_category="RUN")
        assert len(run_events) == 1
        assert run_events[0].event_type == "RUN_CREATED"

        job_events = get_events(session, object_id=obj_id, event_type="JOB_STARTED")
        assert len(job_events) == 1
        assert job_events[0].event_category == "JOB"


def test_event_chaining_and_integrity_check():
    exp_id = str(uuid4())
    t0 = utcnow()
    with session_scope() as session:
        e1 = record_event(
            session,
            event_type="EXPERIMENT_CREATED",
            event_category="EXPERIMENT",
            object_type="experiment",
            object_id=exp_id,
            source_component="experiment_service",
            occurred_at=t0,
        )
        assert e1.previous_event_fingerprint is None

        e2 = record_event(
            session,
            event_type="EXPERIMENT_STARTED",
            event_category="EXPERIMENT",
            object_type="experiment",
            object_id=exp_id,
            source_component="experiment_service",
            occurred_at=t0 + timedelta(seconds=1),
        )
        assert e2.previous_event_fingerprint == e1.event_fingerprint

        integrity = verify_audit_integrity(session, object_type="experiment", object_id=exp_id)
        assert integrity.valid is True
        assert len(integrity.issues) == 0


def test_privacy_metadata_sanitization():
    dirty = {
        "user_token": "secret_abc123",
        "api_key": "private_key_xyz",
        "nested": {"password_hash": "supersecret", "normal_metric": 0.95},
        "rows": [{"patient_id": 123}, {"patient_id": 124}],
        "huge_string": "x" * 5000,
    }
    clean = sanitize_audit_metadata(dirty)
    assert clean["user_token"] == "<redacted_credential>"
    assert clean["api_key"] == "<redacted_credential>"
    assert clean["nested"]["password_hash"] == "<redacted_credential>"
    assert clean["nested"]["normal_metric"] == 0.95
    assert "<omitted_raw_data_count_2>" in clean["rows"]
    assert len(clean["huge_string"]) <= 2020


def test_experiment_timeline_and_legacy_disclaimer(registered):
    exp_id = str(uuid4())
    with session_scope() as session:
        # Create a test experiment
        exp = Experiment(
            id=exp_id,
            dataset_id=registered.id,
            name="Audit Test Experiment",
            config={},
            summary={},
            status="completed",
        )
        session.add(exp)
        session.flush()

        # Get timeline before any events exist -> should provide truthful legacy disclaimer
        timeline_empty = get_experiment_timeline(session, exp_id)
        assert timeline_empty.total_events == 0
        assert timeline_empty.legacy_disclaimer is not None
        assert "Audit history is recorded from" in timeline_empty.legacy_disclaimer

        # Record events for experiment and a child job
        record_event(
            session,
            event_type="EXPERIMENT_CREATED",
            event_category="EXPERIMENT",
            object_type="experiment",
            object_id=exp_id,
            source_component="experiment_service",
        )
        record_event(
            session,
            event_type="JOB_STARTED",
            event_category="JOB",
            object_type="job",
            object_id=str(uuid4()),
            parent_object_type="experiment",
            parent_object_id=exp_id,
            source_component="job_manager",
        )

    with session_scope() as session:
        timeline = get_experiment_timeline(session, exp_id)
        assert timeline.total_events == 2
        assert "EXPERIMENT" in timeline.categories_present
        assert "JOB" in timeline.categories_present
        assert timeline.integrity_status == "VERIFIED"


def test_export_audit_timeline(registered):
    exp_id = str(uuid4())
    with session_scope() as session:
        exp = Experiment(
            id=exp_id,
            dataset_id=registered.id,
            name="Export Test Experiment",
            config={},
            summary={},
            status="completed",
        )
        session.add(exp)
        session.flush()
        record_event(
            session,
            event_type="EXPERIMENT_CREATED",
            event_category="EXPERIMENT",
            object_type="experiment",
            object_id=exp_id,
            source_component="experiment_service",
            metadata={"study": "biomedical"},
        )
        export = export_audit_timeline(session, "experiment", exp_id)
        assert export["export_schema_version"] == "scientific_audit_export_v1"
        assert export["object_type"] == "experiment"
        assert export["object_id"] == exp_id
        assert export["total_events"] == 1
        assert len(export["events"]) == 1
        assert "scientific_boundary" in export
        assert "software_versions" in export

