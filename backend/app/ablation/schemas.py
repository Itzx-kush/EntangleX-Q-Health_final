from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel as Schema, ConfigDict, Field

class AblationComponentConfig(Schema):
    model_config = ConfigDict(extra="forbid")
    component: Literal["preprocessing.scaler","preprocessing.imputer","preprocessing.outlier_strategy","preprocessing.pca","preprocessing.feature_selection","features.subset","model.family","calibration.policy","threshold.policy"]
    operator: Literal["REMOVE","DISABLE","REPLACE_WITH_BASELINE","SUBSTITUTE"]
    ablation_value: Any = None

class AblationStudyRequest(Schema):
    model_config = ConfigDict(extra="forbid")
    base_experiment_id: UUID
    ablation_configs: list[AblationComponentConfig] = Field(min_length=1,max_length=50)
    max_total_runs: int = Field(default=10,ge=1,le=50)

class AblationPreflightResponse(Schema):
    model_config = ConfigDict(extra="ignore",from_attributes=True)
    feasible: bool
    base_experiment_info: dict[str,Any]
    baseline_configuration: dict[str,Any]
    ablation_configurations: list[dict[str,Any]]
    configuration_diff: dict[str,Any]
    changed_components: list[str]
    held_constant: list[str]
    blockers: list[str]
    warnings: list[str]
    limitations: list[str]
    estimated_run_count: int

class AblationStudyOut(Schema):
    model_config = ConfigDict(extra="ignore",from_attributes=True)
    id: str
    base_experiment_id: str
    base_run_id: str | None = None
    ablation_experiment_id: str | None = None
    dataset_id: str
    dataset_version_id: str | None = None
    condition_task_id: str | None = None
    status: str
    operation_key: str
    baseline_configuration: dict[str,Any]
    ablation_configuration: dict[str,Any]
    changed_components: str | list[str]
    held_constant: list[str]
    configuration_diff: dict[str,Any]
    configuration_fingerprint: str
    comparison_results: dict[str,Any]
    limitations: list[str]
    warnings: list[str]
    artifact_id: str | None = None
    failure: dict[str,Any] | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime
