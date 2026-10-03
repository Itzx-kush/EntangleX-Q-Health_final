from pydantic import BaseModel, Field
from typing import Literal
from uuid import UUID

class ThresholdAnalysisRequest(BaseModel):
    model_id: UUID
    dataset_id: UUID
    dataset_version_id: UUID | None = None
    probability_source: Literal["uncalibrated", "calibrated"] = Field(default="uncalibrated")
    sampling_unit: Literal["independent_samples", "grouped_samples"] = Field(default="independent_samples")
    group_column: str | None = Field(default=None, max_length=200)
    split_seed: int = Field(default=42)
    selection_protocol: Literal["dedicated_split"] = Field(default="dedicated_split")
    selection_size: float = Field(default=0.2, gt=0.0, lt=1.0)
    
    threshold_min: float = Field(default=0.0, ge=0.0, le=1.0)
    threshold_max: float = Field(default=1.0, ge=0.0, le=1.0)
    threshold_step: float = Field(default=0.01, gt=0.0, le=0.5)

    selection_method: Literal[
        "fixed_user_threshold",
        "youden_j",
        "f1_maximization",
        "balanced_accuracy_maximization",
        "target_sensitivity",
        "target_specificity",
        "target_precision",
        "target_npv"
    ] = Field(default="youden_j")
    
    fixed_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    target_value: float | None = Field(default=None, ge=0.0, le=1.0)
    tie_breaking_policy: Literal["lowest_threshold", "highest_threshold", "closest_to_0.5"] = Field(default="closest_to_0.5")
    false_positive_cost: float | None = Field(default=None, ge=0.0)
    false_negative_cost: float | None = Field(default=None, ge=0.0)

class ThresholdPreflightResponse(BaseModel):
    feasible: bool
    limitations: list[str]
    method_support: dict[str, bool]
    configuration_fingerprint: str
    source_context_type: str | None = None
