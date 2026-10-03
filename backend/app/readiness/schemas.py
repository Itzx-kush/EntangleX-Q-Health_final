from pydantic import BaseModel, Field
from typing import Literal, Any
from uuid import UUID
from datetime import datetime

class ConditionTaskMetadata(BaseModel):
    terminology_system: str | None = None
    terminology_code: str | None = None
    terminology_display: str | None = None
    case_definition: str | None = None
    population_description: str | None = None
    prediction_horizon: str | None = None
    label_source: str | None = None
    feature_domain: str | None = None

class ConditionTaskCreate(BaseModel):
    condition_name: str = Field(..., min_length=1, max_length=200)
    task_type: Literal["binary_classification"] = "binary_classification"
    target_column: str = Field(..., min_length=1, max_length=200)
    positive_label: str | None = None
    negative_label: str | None = None
    dataset_id: UUID
    dataset_version_id: UUID | None = None
    metadata_: ConditionTaskMetadata = Field(default_factory=ConditionTaskMetadata, alias="metadata")

class ConditionTaskUpdate(BaseModel):
    condition_name: str | None = None
    metadata_: ConditionTaskMetadata | None = Field(default=None, alias="metadata")

class ConditionTaskResponse(ConditionTaskCreate):
    id: UUID
    status: Literal["draft", "ready", "blocked", "ready_with_limitations", "incomplete_configuration"]
    readiness_status: Literal["READY", "READY_WITH_LIMITATIONS", "BLOCKED", "INCOMPLETE_CONFIGURATION"] | None = None
    readiness_report: dict[str, Any] | None = None
    readiness_updated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
        populate_by_name = True

class ModelCapabilityResponse(BaseModel):
    model_type: str
    binary_classification: Literal["supported", "unsupported"]
    grouped_validation: Literal["supported", "unsupported"]
    calibration: Literal["supported", "unsupported"]
    threshold_analysis: Literal["supported", "unsupported"]
    external_validation: Literal["supported", "unsupported"]
    limitations: list[str] = Field(default_factory=list)

class ReadinessResult(BaseModel):
    condition_task: dict[str, Any]
    dataset: dict[str, Any]
    task_type: str
    status: Literal["READY", "READY_WITH_LIMITATIONS", "BLOCKED", "INCOMPLETE_CONFIGURATION"]
    checks: dict[str, Any]
    blockers: list[str]
    warnings: list[str]
    limitations: list[str]
    supported_models: list[ModelCapabilityResponse]
    configuration_fingerprint: str
