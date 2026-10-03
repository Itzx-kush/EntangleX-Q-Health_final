from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


STAGE_TYPES = {
    "data_validation", "preprocessing", "feature_engineering",
    "representation", "quantum_encoding", "model", "evaluation",
}


def _validate_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        raise ValueError("Pipeline configuration nesting is too deep.")
    if isinstance(value, dict):
        if len(value) > 200:
            raise ValueError("Pipeline configuration contains too many fields.")
        result = {}
        for key, item in value.items():
            normalized = str(key).strip()
            if not normalized or len(normalized) > 120:
                raise ValueError("Pipeline configuration keys must be concise.")
            if any(token in normalized.lower() for token in ("password", "secret", "token", "credential", "api_key")):
                raise ValueError("Pipeline definitions cannot contain credentials or secrets.")
            result[normalized] = _validate_safe(item, depth=depth + 1)
        return result
    if isinstance(value, list):
        if len(value) > 500:
            raise ValueError("Pipeline configuration lists are too large.")
        return [_validate_safe(item, depth=depth + 1) for item in value]
    if isinstance(value, str):
        if len(value) > 1000:
            raise ValueError("Pipeline configuration strings are too large.")
        return value.strip()
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise ValueError("Pipeline configuration contains an unsupported value.")


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True, allow_inf_nan=False)


class PipelineStageSpec(Schema):
    stage_order: int = Field(ge=1, le=50)
    stage_type: Literal[
        "data_validation", "preprocessing", "feature_engineering",
        "representation", "quantum_encoding", "model", "evaluation",
    ]
    stage_name: str = Field(min_length=1, max_length=120)
    configuration: dict[str, Any] = Field(default_factory=dict)
    component_version: str | None = Field(default=None, max_length=64)

    @field_validator("stage_name", "component_version")
    @classmethod
    def normalize_text(cls, value):
        return value.strip() if value else value

    @field_validator("configuration")
    @classmethod
    def safe_configuration(cls, value):
        return _validate_safe(value)


class PipelineDefinitionSpec(Schema):
    dataset_id: UUID | None = None
    dataset_version_id: UUID | None = None
    controlled_comparison_protocol_id: UUID | None = None
    stages: list[PipelineStageSpec] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def ordered_stages(self):
        orders = [stage.stage_order for stage in self.stages]
        if len(orders) != len(set(orders)):
            raise ValueError("Pipeline stage positions must be unique.")
        if sorted(orders) != list(range(1, len(orders) + 1)):
            raise ValueError("Pipeline stage positions must be contiguous and start at 1.")
        return self


class PipelineCreateRequest(Schema):
    pipeline_name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    parent_pipeline_version_id: UUID | None = None
    source_context: str | None = Field(default=None, max_length=48)
    definition: PipelineDefinitionSpec

    @field_validator("pipeline_name", "description", "source_context")
    @classmethod
    def normalize_text(cls, value):
        return value.strip() if value else value