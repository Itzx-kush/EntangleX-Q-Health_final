from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ALLOWED_METRICS = {
    "accuracy", "balanced_accuracy", "sensitivity", "specificity",
    "precision", "recall", "f1", "roc_auc", "pr_auc", "brier_score",
    "log_loss", "mcc",
}

ALLOWED_TASK_TYPES = {
    "binary_classification", "multiclass_classification", "regression",
}

ALLOWED_REQUIREMENTS = {"REQUIRED", "OPTIONAL", "DISABLED"}

ALLOWED_THRESHOLD_STRATEGIES = {
    "f1_optimal", "youden_j", "fixed", "target_sensitivity",
    "cost_sensitive", "precision_constrained",
}

ALLOWED_CALIBRATION_METHODS = {
    "isotonic", "sigmoid", "platt", "temperature_scaling",
}

ALLOWED_SPLIT_STRATEGIES = {
    "stratified_kfold", "train_test_split", "group_kfold",
    "repeated_stratified_kfold", "time_series_split",
}


def _validate_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        raise ValueError("Protocol configuration nesting is too deep.")
    if isinstance(value, dict):
        if len(value) > 200:
            raise ValueError("Protocol configuration contains too many fields.")
        result = {}
        for key, item in value.items():
            normalized = str(key).strip()
            if not normalized or len(normalized) > 120:
                raise ValueError("Protocol configuration keys must be concise.")
            if any(token in normalized.lower() for token in ("password", "secret", "token", "credential", "api_key")):
                raise ValueError("Protocol definitions cannot contain credentials or secrets.")
            result[normalized] = _validate_safe(item, depth=depth + 1)
        return result
    if isinstance(value, list):
        if len(value) > 500:
            raise ValueError("Protocol configuration lists are too large.")
        return [_validate_safe(item, depth=depth + 1) for item in value]
    if isinstance(value, str):
        if len(value) > 1000:
            raise ValueError("Protocol configuration strings are too large.")
        return value.strip()
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise ValueError("Protocol configuration contains an unsupported value.")


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True, allow_inf_nan=False)


class StudyMetadataSpec(Schema):
    study_purpose: str = Field(default="Biomedical risk prediction study", max_length=500)
    task_type: str = Field(default="binary_classification", max_length=64)
    task_description: str = Field(default="", max_length=1000)
    experiment_scope: str = Field(default="research_benchmark", max_length=120)

    @field_validator("study_purpose", "task_description", "experiment_scope")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip() if value else value

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in ALLOWED_TASK_TYPES:
            raise ValueError(f"Unsupported task type: '{value}'. Must be one of {sorted(ALLOWED_TASK_TYPES)}")
        return cleaned



class DatasetPolicySpec(Schema):
    dataset_id: UUID | None = None
    dataset_version_id: UUID | None = None
    required_dataset_version: bool = Field(default=False)
    target_column: str | None = Field(default=None, max_length=120)
    positive_label: str | None = Field(default=None, max_length=120)
    negative_label: str | None = Field(default=None, max_length=120)
    included_populations: list[str] = Field(default_factory=list, max_length=50)
    excluded_populations: list[str] = Field(default_factory=list, max_length=50)


class SplitPolicySpec(Schema):
    strategy: str = Field(default="stratified_kfold", max_length=64)
    test_size: float = Field(default=0.2, ge=0.01, le=0.9)
    cv_folds: int = Field(default=5, ge=2, le=30)
    stratify: bool = Field(default=True)
    group_column: str | None = Field(default=None, max_length=120)
    split_seed: int = Field(default=42, ge=0)


class RandomnessPolicySpec(Schema):
    primary_seed: int = Field(default=42, ge=0)
    seed_list: list[int] = Field(default_factory=lambda: [42, 101, 202, 303, 404], max_length=50)
    multi_seed_count: int = Field(default=5, ge=1, le=50)
    determinism_required: bool = Field(default=True)


class ModelPolicySpec(Schema):
    allowed_model_types: list[str] = Field(default_factory=lambda: [
        "logistic_regression", "random_forest", "svm", "vqc", "qnn", "hybrid_pennylane_torch"
    ], max_length=50)
    model_families: list[str] = Field(default_factory=lambda: ["classical", "quantum", "hybrid"], max_length=10)


class PipelinePolicySpec(Schema):
    pipeline_version_id: UUID | None = None
    pipeline_fingerprint: str | None = Field(default=None, max_length=64)
    requirement: Literal["REQUIRED", "OPTIONAL", "DISABLED"] = Field(default="OPTIONAL")


class EvaluationPolicySpec(Schema):
    primary_metric: str = Field(default="roc_auc", max_length=64)
    secondary_metrics: list[str] = Field(default_factory=lambda: [
        "accuracy", "balanced_accuracy", "f1", "sensitivity", "specificity", "pr_auc", "brier_score"
    ], max_length=30)
    confidence_intervals: bool = Field(default=False)
    statistical_reporting: bool = Field(default=True)

    @field_validator("primary_metric")
    @classmethod
    def validate_primary_metric(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in ALLOWED_METRICS:
            raise ValueError(f"Unsupported primary metric: '{value}'. Must be one of {sorted(ALLOWED_METRICS)}")
        return cleaned

    @field_validator("secondary_metrics")
    @classmethod
    def validate_secondary_metrics(cls, value: list[str]) -> list[str]:
        cleaned_list = []
        for m in value:
            cleaned = m.strip().lower()
            if cleaned not in ALLOWED_METRICS:
                raise ValueError(f"Unsupported secondary metric: '{m}'. Must be one of {sorted(ALLOWED_METRICS)}")
            cleaned_list.append(cleaned)
        return cleaned_list



class ThresholdPolicySpec(Schema):
    requirement: Literal["REQUIRED", "OPTIONAL", "DISABLED"] = Field(default="REQUIRED")
    strategy: str = Field(default="f1_optimal", max_length=64)
    target_sensitivity: float | None = Field(default=None, ge=0.0, le=1.0)
    fixed_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    lock_threshold: bool = Field(default=True)


class CalibrationPolicySpec(Schema):
    requirement: Literal["REQUIRED", "OPTIONAL", "DISABLED"] = Field(default="REQUIRED")
    method: str = Field(default="isotonic", max_length=64)
    calibration_split: str = Field(default="cv", max_length=64)
    calibration_metrics: list[str] = Field(default_factory=lambda: ["brier_score"], max_length=10)


class MultiSeedExtensionSpec(Schema):
    requirement: Literal["REQUIRED", "OPTIONAL", "DISABLED"] = Field(default="OPTIONAL")
    min_seed_count: int = Field(default=5, ge=1, le=50)


class ExternalValidationExtensionSpec(Schema):
    requirement: Literal["REQUIRED", "OPTIONAL", "DISABLED"] = Field(default="OPTIONAL")
    external_dataset_id: UUID | None = None


class DistributionShiftExtensionSpec(Schema):
    requirement: Literal["REQUIRED", "OPTIONAL", "DISABLED"] = Field(default="OPTIONAL")
    significance_alpha: float | None = Field(default=0.05, ge=0.0001, le=0.5)


class GroupValidationExtensionSpec(Schema):
    requirement: Literal["REQUIRED", "OPTIONAL", "DISABLED"] = Field(default="OPTIONAL")
    required_group_column: str | None = Field(default=None, max_length=120)


class RobustnessExtensionSpec(Schema):
    requirement: Literal["REQUIRED", "OPTIONAL", "DISABLED"] = Field(default="OPTIONAL")
    perturbation_types: list[str] = Field(default_factory=lambda: ["missingness", "gaussian_noise"], max_length=10)


class AblationExtensionSpec(Schema):
    requirement: Literal["REQUIRED", "OPTIONAL", "DISABLED"] = Field(default="OPTIONAL")
    target_components: list[str] = Field(default_factory=list, max_length=20)


class ValidationExtensionsSpec(Schema):
    multi_seed: MultiSeedExtensionSpec = Field(default_factory=MultiSeedExtensionSpec)
    external_validation: ExternalValidationExtensionSpec = Field(default_factory=ExternalValidationExtensionSpec)
    distribution_shift: DistributionShiftExtensionSpec = Field(default_factory=DistributionShiftExtensionSpec)
    group_validation: GroupValidationExtensionSpec = Field(default_factory=GroupValidationExtensionSpec)
    robustness: RobustnessExtensionSpec = Field(default_factory=RobustnessExtensionSpec)
    ablation: AblationExtensionSpec = Field(default_factory=AblationExtensionSpec)


class QuantumControlsSpec(Schema):
    requirement: Literal["REQUIRED", "OPTIONAL", "DISABLED"] = Field(default="OPTIONAL")
    controlled_comparison_protocol_id: UUID | None = None
    dataset_parity: bool = Field(default=True)
    sample_parity: bool = Field(default=True)
    test_population_parity: bool = Field(default=True)
    preprocessing_parity: bool = Field(default=True)
    seed_policy_parity: bool = Field(default=True)
    provider_provenance: bool = Field(default=True)


class ProtocolDefinitionSpec(Schema):
    schema_version: str = Field(default="protocol_definition_v1", max_length=48)
    study_metadata: StudyMetadataSpec = Field(default_factory=StudyMetadataSpec)
    dataset_policy: DatasetPolicySpec = Field(default_factory=DatasetPolicySpec)
    split_policy: SplitPolicySpec = Field(default_factory=SplitPolicySpec)
    randomness_policy: RandomnessPolicySpec = Field(default_factory=RandomnessPolicySpec)
    model_policy: ModelPolicySpec = Field(default_factory=ModelPolicySpec)
    pipeline_policy: PipelinePolicySpec = Field(default_factory=PipelinePolicySpec)
    evaluation_policy: EvaluationPolicySpec = Field(default_factory=EvaluationPolicySpec)
    threshold_policy: ThresholdPolicySpec = Field(default_factory=ThresholdPolicySpec)
    calibration_policy: CalibrationPolicySpec = Field(default_factory=CalibrationPolicySpec)
    validation_extensions: ValidationExtensionsSpec = Field(default_factory=ValidationExtensionsSpec)
    quantum_controls: QuantumControlsSpec = Field(default_factory=QuantumControlsSpec)
    constraints: dict[str, Any] = Field(default_factory=dict)

    @field_validator("constraints")
    @classmethod
    def safe_constraints(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_safe(value)


class ProtocolCreateRequest(Schema):
    protocol_name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    template_id: UUID | None = None
    parent_protocol_version_id: UUID | None = None
    source_context: str | None = Field(default=None, max_length=48)
    definition: ProtocolDefinitionSpec

    @field_validator("protocol_name", "description", "source_context")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class TemplateInstantiateRequest(Schema):
    protocol_name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    parameters: dict[str, Any] = Field(default_factory=dict)
    source_context: str | None = Field(default="template_instantiation", max_length=48)

    @field_validator("protocol_name", "description", "source_context")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value

    @field_validator("parameters")
    @classmethod
    def safe_parameters(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_safe(value)


class ProtocolAttachRequest(Schema):
    protocol_version_id: UUID

