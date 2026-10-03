"""Pydantic schemas and types for Biomedical Subgroup Analysis & Stratified Evaluation."""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

SubgroupOperator = Literal[
    "equals",
    "between",
    "in",
    "greater_than",
    "less_than",
    "greater_than_or_equal",
    "less_than_or_equal",
    "is_null",
]

MissingValuePolicy = Literal[
    "exclude",
    "separate_unknown_group",
    "error",
]

SubgroupStatus = Literal[
    "VALID",
    "TOO_SMALL",
    "EMPTY",
    "UNAVAILABLE",
    "UNVERIFIABLE",
]

MetricStatus = Literal[
    "AVAILABLE",
    "UNDEFINED",
    "INSUFFICIENT_DATA",
    "WITHHELD",
    "NOT_APPLICABLE",
    "UNVERIFIABLE",
]


class SubgroupRule(BaseModel):
    id: str = Field(description="Unique identifier slug for this subgroup")
    label: str = Field(description="Human-readable label for this subgroup")
    field: str = Field(description="Dataset column name")
    operator: SubgroupOperator = Field(default="equals")
    value: Any | None = None
    lower: float | None = None
    upper: float | None = None
    values: list[Any] | None = None


class SubgroupAnalysisRequest(BaseModel):
    model_id: str | None = None
    dataset_id: str | None = None
    dataset_version_id: str | None = None
    subgroup_field: str = Field(description="The dataset field/attribute to stratify by")
    subgroup_rules: list[SubgroupRule] | None = Field(
        default=None,
        description="Explicit subgroup cohorts. If omitted, derived from dataset field schema.",
    )
    minimum_n: int = Field(
        default=20,
        ge=1,
        description="Configurable minimum subgroup sample size for privacy and statistical stability",
    )
    missing_value_policy: MissingValuePolicy = Field(
        default="exclude",
        description="Policy for handling null or unrecorded subgroup values",
    )
    reference_subgroup_id: str | None = Field(
        default=None,
        description="Optional subgroup ID to use as baseline reference in addition to overall population",
    )
    confidence_level: float = Field(
        default=0.95,
        ge=0.5,
        le=0.999,
        description="Confidence interval coverage level",
    )


class SubgroupMetricValue(BaseModel):
    value: float | None = None
    status: MetricStatus = "AVAILABLE"
    reason: str | None = None
    ci_lower: float | None = None
    ci_upper: float | None = None
    ci_level: float | None = None
    ci_method: str | None = None


class SubgroupPopulationAccounting(BaseModel):
    n: int
    positive_n: int
    negative_n: int
    prevalence: float | None = None
    excluded_missing_n: int = 0


class SubgroupResult(BaseModel):
    id: str
    label: str
    rule: dict[str, Any]
    status: SubgroupStatus
    status_reason: str | None = None
    population: SubgroupPopulationAccounting
    metrics: dict[str, SubgroupMetricValue]


class SubgroupComparison(BaseModel):
    subgroup_id: str
    subgroup_label: str
    reference_id: str
    reference_label: str
    metric_deltas: dict[str, float | None]
    metric_ratios: dict[str, float | None]
    interpretation: str


class SubgroupStudyOut(BaseModel):
    id: str
    schema_version: str = "subgroup_analysis_v1"
    experiment_id: str
    model_id: str
    model_type: str
    run_id: str | None = None
    dataset_id: str
    dataset_version_id: str | None = None
    status: str
    operation_key: str
    definition_fingerprint: str
    subgroup_field: str
    configuration: dict[str, Any]
    overall_population: dict[str, Any]
    subgroups: list[SubgroupResult]
    subgroups_results: list[SubgroupResult] | None = None
    comparisons: list[SubgroupComparison]
    limitations: list[str]
    provenance: dict[str, Any]
    artifact_id: str | None = None
    created_at: str
    completed_at: str | None = None


class SubgroupPreflightResponse(BaseModel):
    feasible: bool
    subgroup_field: str
    field_data_type: str
    unique_values_count: int
    missing_values_count: int
    suggested_rules: list[SubgroupRule]
    eligible_samples: int
    blockers: list[str]
    warnings: list[str]
    limitations: list[str]
    configuration_fingerprint: str
