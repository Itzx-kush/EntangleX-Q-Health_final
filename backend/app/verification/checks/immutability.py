"""Immutability verification for append-only scientific records.

Published pipeline and protocol versions, lineage relationships, audit events and
immutable artifacts must reject silent modification.  Each check creates,
finalizes and then attempts a mutation on an isolated synthetic record.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from ..fixtures import create_pipeline, create_protocol, persist_chain, register_fixture_dataset
from ..isolation import initialize_database, session
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check
from ._support import expect_app_error


@check(
    check_id="pipeline_version_immutability",
    name="Pipeline version immutability",
    category=CheckCategory.PIPELINE_INTEGRITY,
    description="A published pipeline version and its stages reject mutation attempts.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=120.0,
)
def pipeline_version_immutability() -> CheckResult:
    from app.storage.entities import PipelineStage, PipelineVersion

    initialize_database()
    registered = register_fixture_dataset()
    with session() as scope:
        version = create_pipeline(scope, registered.id, registered.current_version_id)
        version_id = version.id
        fingerprint_before = version.definition_fingerprint
        stage_id = scope.scalar(
            select(PipelineStage.id).where(PipelineStage.pipeline_version_id == version_id).limit(1)
        )

    with expect_app_error("pipeline_version_immutable"):
        with session() as scope:
            scope.get(PipelineVersion, version_id).definition_fingerprint = "0" * 64

    with expect_app_error("pipeline_version_immutable"):
        with session() as scope:
            scope.get(PipelineStage, stage_id).stage_name = "Mutated stage"

    with session() as scope:
        stored = scope.get(PipelineVersion, version_id)
        fingerprint_after = stored.definition_fingerprint
        status = stored.status

    if fingerprint_after != fingerprint_before:
        return CheckResult(
            check_id="pipeline_version_immutability",
            category=CheckCategory.PIPELINE_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="Published Pipeline Version pv fingerprint changed after an attempted mutation.",
            evidence={"before": fingerprint_before, "after": fingerprint_after},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="immutable published definition",
            observed=f"fingerprint changed from {fingerprint_before} to {fingerprint_after}",
        )
    return CheckResult(
        check_id="pipeline_version_immutability",
        category=CheckCategory.PIPELINE_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Published pipeline versions and their stages reject mutation and keep their fingerprint.",
        evidence={
            "pipeline_version_id": version_id,
            "status": status,
            "definition_fingerprint": fingerprint_after,
            "rejected_mutations": ["definition_fingerprint", "stage_name"],
        },
    )


@check(
    check_id="protocol_version_immutability",
    name="Protocol version immutability",
    category=CheckCategory.PROTOCOL_INTEGRITY,
    description="A published protocol version rejects mutation attempts and keeps its definition fingerprint.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=120.0,
)
def protocol_version_immutability() -> CheckResult:
    from app.storage.entities import ExperimentProtocolVersion

    initialize_database()
    registered = register_fixture_dataset()
    with session() as scope:
        version = create_protocol(scope, registered.id)
        version_id = version.id
        fingerprint_before = version.definition_fingerprint

    with expect_app_error("protocol_version_immutable"):
        with session() as scope:
            scope.get(ExperimentProtocolVersion, version_id).definition_fingerprint = "0" * 64

    with expect_app_error("protocol_version_immutable"):
        with session() as scope:
            scope.get(ExperimentProtocolVersion, version_id).version_label = "v999"

    with session() as scope:
        stored = scope.get(ExperimentProtocolVersion, version_id)
        fingerprint_after = stored.definition_fingerprint
        status = stored.status

    if fingerprint_after != fingerprint_before:
        return CheckResult(
            check_id="protocol_version_immutability",
            category=CheckCategory.PROTOCOL_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="Published Protocol Version was mutated.",
            evidence={"before": fingerprint_before, "after": fingerprint_after},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="immutable definition",
            observed=f"fingerprint changed from {fingerprint_before} to {fingerprint_after}",
        )
    return CheckResult(
        check_id="protocol_version_immutability",
        category=CheckCategory.PROTOCOL_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Published protocol versions reject mutation and keep their definition fingerprint.",
        evidence={
            "protocol_version_id": version_id,
            "status": status,
            "definition_fingerprint": fingerprint_after,
            "rejected_mutations": ["definition_fingerprint", "version_label"],
        },
    )


@check(
    check_id="audit_event_immutability",
    name="Audit event immutability",
    category=CheckCategory.AUDIT_INTEGRITY,
    description="Scientific audit events reject both update and delete attempts.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=120.0,
)
def audit_event_immutability() -> CheckResult:
    from app.audit.service import record_event
    from app.storage.entities import ScientificAuditEvent

    initialize_database()
    object_id = str(uuid4())
    with session() as scope:
        event = record_event(
            scope,
            event_type="EXPERIMENT_CREATED",
            event_category="EXPERIMENT",
            object_type="experiment",
            object_id=object_id,
            source_component="scientific_ci_immutability",
            operation_key=f"scientific-ci:immutability:{object_id}",
            metadata={"stage": "fixture"},
        )
        event_id = event.id
        fingerprint = event.event_fingerprint

    with expect_app_error("audit_event_immutable"):
        with session() as scope:
            scope.get(ScientificAuditEvent, event_id).metadata_payload = {"mutated": True}

    with expect_app_error("audit_event_immutable"):
        with session() as scope:
            scope.delete(scope.get(ScientificAuditEvent, event_id))

    with session() as scope:
        stored = scope.get(ScientificAuditEvent, event_id)

    if stored is None or stored.event_fingerprint != fingerprint:
        return CheckResult(
            check_id="audit_event_immutability",
            category=CheckCategory.AUDIT_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="A scientific audit event was modified or deleted after it was recorded.",
            evidence={"event_id": event_id, "fingerprint": fingerprint},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="append-only immutable audit event",
            observed="audit event changed or disappeared",
        )
    return CheckResult(
        check_id="audit_event_immutability",
        category=CheckCategory.AUDIT_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Scientific audit events reject update and delete attempts.",
        evidence={"event_id": event_id, "event_fingerprint": fingerprint, "rejected_mutations": ["update", "delete"]},
    )


@check(
    check_id="lineage_relationship_immutability",
    name="Lineage relationship immutability",
    category=CheckCategory.LINEAGE_INTEGRITY,
    description="Re-recording an identical lineage relationship is idempotent, while rewriting it is rejected.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=120.0,
)
def lineage_relationship_immutability() -> CheckResult:
    from app.lineage.service import record_edge
    from app.storage.entities import LineageEdge

    initialize_database()
    experiment_id, model_id = str(uuid4()), str(uuid4())
    with session() as scope:
        first = record_edge(
            scope,
            source_type="experiment",
            source_id=experiment_id,
            target_type="model_record",
            target_id=model_id,
            relationship_type="produced_model",
            metadata={"synthetic": True},
        )
        edge_id = first.id
    with session() as scope:
        same = record_edge(
            scope,
            source_type="experiment",
            source_id=experiment_id,
            target_type="model_record",
            target_id=model_id,
            relationship_type="produced_model",
            metadata={"synthetic": True},
        )
        assert same.id == edge_id, "identical lineage relationships must be idempotent"

    with expect_app_error("immutable_lineage_conflict"):
        with session() as scope:
            record_edge(
                scope,
                source_type="experiment",
                source_id=experiment_id,
                target_type="model_record",
                target_id=model_id,
                relationship_type="produced_model",
                metadata={"synthetic": True, "rewritten": True},
            )

    with session() as scope:
        count = scope.query(LineageEdge).filter(LineageEdge.id == edge_id).count()
    if count != 1:
        return CheckResult(
            check_id="lineage_relationship_immutability",
            category=CheckCategory.LINEAGE_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="Lineage relationship history was duplicated or rewritten.",
            evidence={"edge_id": edge_id, "row_count": count},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="exactly one immutable relationship row",
            observed=f"{count} row(s)",
        )
    return CheckResult(
        check_id="lineage_relationship_immutability",
        category=CheckCategory.LINEAGE_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Identical lineage relationships are idempotent and rewritten relationships are rejected.",
        evidence={"edge_id": edge_id, "row_count": count},
    )


@check(
    check_id="artifact_immutability",
    name="Artifact immutability",
    category=CheckCategory.ARTIFACT_INTEGRITY,
    description="An immutable artifact operation key cannot silently produce different content.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=120.0,
)
def artifact_immutability() -> CheckResult:
    from app.artifacts.service import register_metadata

    initialize_database()
    chain = persist_chain()
    operation_key = f"scientific-ci:artifact:{uuid4()}"
    payload = {"kind": "synthetic", "values": [1, 2, 3]}
    with session() as scope:
        artifact = register_metadata(
            scope,
            experiment_id=chain.experiment_id,
            run_id=chain.run_id,
            model_id=chain.model_id,
            artifact_type="scientific_ci_fixture",
            name="Synthetic artifact",
            description="Synthetic Scientific CI artifact.",
            payload=payload,
            operation_key=operation_key,
        )
        artifact_id, integrity_hash, immutable = artifact.id, artifact.integrity_hash, artifact.immutable

    with expect_app_error("artifact_conflict"):
        with session() as scope:
            register_metadata(
                scope,
                experiment_id=chain.experiment_id,
                artifact_type="scientific_ci_fixture",
                name="Synthetic artifact",
                description="Synthetic Scientific CI artifact.",
                payload={"kind": "synthetic", "values": [3, 2, 1]},
                operation_key=operation_key,
            )

    from app.utils.serialization import fingerprint

    if integrity_hash != fingerprint(payload) or not immutable:
        return CheckResult(
            check_id="artifact_immutability",
            category=CheckCategory.ARTIFACT_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="Artifact metadata is not content-addressed or not marked immutable.",
            evidence={"artifact_id": artifact_id, "integrity_hash": integrity_hash, "immutable": immutable},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="integrity_hash == fingerprint(payload) and immutable == True",
            observed=f"integrity_hash={integrity_hash} immutable={immutable}",
        )
    return CheckResult(
        check_id="artifact_immutability",
        category=CheckCategory.ARTIFACT_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Immutable artifacts are content-addressed and reject conflicting rewrites.",
        evidence={"artifact_id": artifact_id, "integrity_hash": integrity_hash, "immutable": immutable},
    )
