from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

EVENT_SCHEMA_VERSION = "scientific_audit_event_v1"

EVENT_CATEGORIES = {
    "EXPERIMENT",
    "DATASET",
    "PIPELINE",
    "PROTOCOL",
    "RUN",
    "JOB",
    "MODEL",
    "EVIDENCE",
    "ARTIFACT",
    "CONFIGURATION",
    "SYSTEM",
}

AuditEventCategory = Literal[
    "EXPERIMENT",
    "DATASET",
    "PIPELINE",
    "PROTOCOL",
    "RUN",
    "JOB",
    "MODEL",
    "EVIDENCE",
    "ARTIFACT",
    "CONFIGURATION",
    "SYSTEM",
]

CORE_EVENT_TYPES = {
    # Experiment
    "EXPERIMENT_CREATED",
    "EXPERIMENT_UPDATED",
    "EXPERIMENT_STARTED",
    "EXPERIMENT_COMPLETED",
    "EXPERIMENT_FAILED",
    "EXPERIMENT_CANCELLED",
    "EXPERIMENT_RERUN_REQUESTED",
    "EXPERIMENT_RERUN_COMPLETED",
    # Dataset
    "DATASET_CREATED",
    "DATASET_VERSION_CREATED",
    "DATASET_VERSION_REGISTERED",
    "DATASET_VALIDATED",
    # Pipeline
    "PIPELINE_CREATED",
    "PIPELINE_VERSION_CREATED",
    "PIPELINE_VERSION_PUBLISHED",
    "PIPELINE_VERSION_DEPRECATED",
    # Protocol
    "PROTOCOL_CREATED",
    "PROTOCOL_VERSION_CREATED",
    "PROTOCOL_VERSION_PUBLISHED",
    "PROTOCOL_VERSION_DEPRECATED",
    "PROTOCOL_APPLIED",
    # Run
    "RUN_CREATED",
    "RUN_STARTED",
    "RUN_COMPLETED",
    "RUN_FAILED",
    "RUN_CANCELLED",
    # Job
    "JOB_CREATED",
    "JOB_STARTED",
    "JOB_PAUSED",
    "JOB_RESUMED",
    "JOB_COMPLETED",
    "JOB_FAILED",
    "JOB_CANCELLED",
    "CHECKPOINT_CREATED",
    # Model
    "MODEL_REGISTERED",
    "MODEL_VERSION_REGISTERED",
    "MODEL_EVALUATED",
    # Evidence
    "EVIDENCE_STUDY_CREATED",
    "EVIDENCE_STUDY_COMPLETED",
    "EVIDENCE_STUDY_FAILED",
    "EVIDENCE_PACKAGE_CREATED",
    "EVIDENCE_PACKAGE_READY",
    "EVIDENCE_PACKAGE_PARTIAL",
    # Artifact
    "ARTIFACT_REGISTERED",
    "ARTIFACT_VERIFIED",
    # System
    "SYSTEM_EVENT",
}


class ScientificAuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    schema_version: str = EVENT_SCHEMA_VERSION
    event_type: str
    event_category: str
    occurred_at: datetime
    recorded_at: datetime
    actor_type: str = "SYSTEM"
    actor_reference: str | None = None
    source_component: str
    operation_key: str | None = None
    object_type: str
    object_id: str
    parent_object_type: str | None = None
    parent_object_id: str | None = None
    before_fingerprint: str | None = None
    after_fingerprint: str | None = None
    previous_event_fingerprint: str | None = None
    event_fingerprint: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditIntegrityIssue(BaseModel):
    event_id: str | None = None
    issue_type: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class AuditIntegrityOut(BaseModel):
    valid: bool
    total_events: int
    issues: list[AuditIntegrityIssue]
    interpretation: str


class AuditTimelineOut(BaseModel):
    object_type: str
    object_id: str
    total_events: int
    events: list[ScientificAuditEventOut]
    categories_present: list[str]
    integrity_status: Literal["VERIFIED", "INTEGRITY_WARNING", "NOT_VERIFIED"]
    legacy_disclaimer: str | None = None
    scientific_boundary: str = (
        "The Scientific Audit Timeline records platform events and persisted state transitions. "
        "It does not establish scientific validity, causal relationships, model quality, or performance."
    )
