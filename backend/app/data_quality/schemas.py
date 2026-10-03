from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


CheckStatus = Literal["PASS", "WARN", "FAIL", "NOT_APPLICABLE", "UNVERIFIABLE"]
CheckSeverity = Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


class QualityCheckResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    domain: str
    status: CheckStatus
    severity: CheckSeverity
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    recommendation: str | None = None


class QualityDomainResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    domain: str
    display_name: str
    status: CheckStatus
    total_checks: int
    passed_checks: int
    warning_checks: int
    failed_checks: int
    not_applicable_checks: int
    unverifiable_checks: int
    checks: list[QualityCheckResult] = Field(default_factory=list)
    summary: str


class ScorecardSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    overall_status: CheckStatus
    total_checks: int
    passed: int
    warnings: int
    failed: int
    not_applicable: int
    unverifiable: int
    critical_failures: int = 0
    high_failures: int = 0
    quality_score: float = 100.0
    domain_scores: dict[str, str] = Field(default_factory=dict)


class FeatureProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    data_type: str
    null_count: int
    null_percentage: float
    distinct_count: int
    is_constant: bool = False
    sample_stats: dict[str, Any] = Field(default_factory=dict)


class SchemaSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_rows: int
    total_features: int
    target_column: str | None = None
    columns: list[FeatureProfile] = Field(default_factory=list)


class DatasetQualityRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    dataset_version_id: str | None = None
    experiment_id: str | None = None
    protocol_version_id: str | None = None
    pipeline_version_id: str | None = None
    reference_dataset_version_id: str | None = None
    subgroup_field: str | None = None
    target_column: str | None = None
    positive_label: str | None = None
    negative_label: str | None = None
    thresholds: dict[str, Any] = Field(default_factory=dict)
    operation_key: str | None = None


class DatasetQualityPreflightResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    dataset_id: str
    dataset_version_id: str | None
    dataset_name: str
    dataset_hash: str
    expected_fingerprint: str
    checks_planned: int
    domains_planned: list[str]
    context: dict[str, Any]
    ready_to_assess: bool
    reasons: list[str] = Field(default_factory=list)


class DatasetQualityScorecardOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    schema_version: str = "dataset_quality_scorecard_v1"
    dataset_id: str
    dataset_version_id: str | None = None
    experiment_id: str | None = None
    protocol_version_id: str | None = None
    pipeline_version_id: str | None = None
    status: CheckStatus
    operation_key: str
    assessment_fingerprint: str
    configuration: dict[str, Any] = Field(default_factory=dict)
    summary: ScorecardSummary
    domains: dict[str, QualityDomainResult] = Field(default_factory=dict)
    schema_snapshot: SchemaSnapshot
    limitations: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    artifact_id: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ScorecardComparisonOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    base_scorecard_id: str
    target_scorecard_id: str
    base_fingerprint: str
    target_fingerprint: str
    status_delta: dict[str, Any]
    summary_delta: dict[str, int | float]
    domain_deltas: dict[str, Any] = Field(default_factory=dict)
    new_warnings: list[QualityCheckResult] = Field(default_factory=list)
    resolved_warnings: list[QualityCheckResult] = Field(default_factory=list)
    new_failures: list[QualityCheckResult] = Field(default_factory=list)
    resolved_failures: list[QualityCheckResult] = Field(default_factory=list)
    metric_changes: list[dict[str, Any]] = Field(default_factory=list)
