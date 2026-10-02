from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from ..api.schemas import Schema


class ManifestIdentity(Schema):
    manifest_schema_version: Literal["1.0.0"]
    manifest_id: str
    experiment_id: str
    run_id: str
    created_at: str
    immutable_at: str
    manifest_hash: str
    configuration_fingerprint: str
    parent_run_id: str | None
    parent_experiment_id: str | None


class DatasetProvenance(Schema):
    dataset_id: str
    name: str
    source: str
    source_reference: str | None
    source_version: str
    sha256: str
    hash_scope: str
    row_count: int
    feature_count: int
    target_column: str
    positive_class: str
    negative_class: str
    class_distribution: dict[str, int]
    input_filename: str
    storage_identity: str
    schema_fingerprint: str
    feature_names: list[str]


class SamplingProvenance(Schema):
    strategy: str
    requested_sample_count: int | None
    actual_sample_count: int
    sampling_seed: int
    selected_row_fingerprint: str
    class_balancing: str
    restrictions: list[str]
    dropped_duplicate_count: int
    excluded_by_sampling: int


class SplitProvenance(Schema):
    strategy: str
    test_size: float
    split_seed: int
    train_row_count: int
    test_row_count: int
    train_index_fingerprint: str
    test_index_fingerprint: str
    split_fingerprint: str
    stratification: str
    grouping: Literal["not_supported"]
    time_based: Literal["not_supported"]


class CrossValidationProvenance(Schema):
    strategy: Literal["StratifiedKFold"]
    folds: int
    shuffle: Literal[True]
    seed: int
    fold_structure_fingerprint: str
    training_only_fitting: Literal[True]
    fold_local_preprocessing: Literal[True]


class PreprocessingProvenance(Schema):
    missing_value_strategy: str
    numeric_imputation: str
    categorical_imputation: Literal["most_frequent"]
    scaling: str
    outlier_strategy: str
    clipping_quantiles: dict[str, float] | None
    duplicate_policy: str
    infinite_value_handling: str
    categorical_encoding: str
    angle_scaling: bool
    angle_range: list[float] | None


class FeatureEngineeringProvenance(Schema):
    log_transforms: list[str]
    ratio_transforms: list[dict[str, str]]
    source_features: list[str]
    resulting_schema_fingerprint: str


class FeatureSelectionProvenance(Schema):
    method: str
    requested_feature_count: int
    variance_threshold: float
    scoring_parameters: dict[str, Any]
    seed: int
    retained_feature_identifiers: list[str] | None
    retained_features_evidence: str


class DimensionalityReductionProvenance(Schema):
    enabled: bool
    method: Literal["PCA"] | None
    component_count: int | None
    solver: Literal["full"] | None
    whiten: bool
    fitted_input_dimensions: int | None
    explained_variance: list[float] | None
    output_dimensionality: int | None
    fitted_evidence: str
    angle_scaling: bool
    angle_range: list[float] | None


class QuantumProvenance(Schema):
    framework: Literal["Qiskit", "PennyLane"]
    classical_framework: Literal["PyTorch"] | None
    model_type: str
    backend: str
    execution_kind: str
    real_hardware: Literal[False]
    qubits: int
    feature_map: str
    ansatz: str | None
    circuit_layers: int | None
    shots: int | None
    noise_configuration: dict[str, Any]
    optimizer: str
    learning_rate: float | None
    epochs_or_iterations: int
    batch_size: int | None
    seed: int
    circuit_resource_evidence: str


class ModelConfigurationProvenance(Schema):
    model_identifier: str
    model_family: Literal["classical", "qiskit_quantum", "pennylane_hybrid"]
    estimator_type: str
    hyperparameters: dict[str, Any]
    training_parameters: dict[str, Any]
    class_weight: str | None
    calibration: dict[str, Any]
    deterministic_seed: int
    quantum: QuantumProvenance | None


class ThresholdProtocolProvenance(Schema):
    selection_method: str
    target_sensitivity: float | None
    configured_fixed_threshold: float
    calibration_status: str
    actual_decision_threshold: float | None
    actual_threshold_evidence: str
    selected_from_out_of_fold_data: bool
    untouched_holdout_not_used_for_selection: Literal[True]
    infeasible_policy: str


class EvaluationProtocolProvenance(Schema):
    evaluated_metrics: list[str]
    positive_class: str
    primary_metric: str | None
    secondary_metrics: list[str]
    held_out_evaluation: str
    cross_validation_evaluation: str
    confusion_matrix_convention: str
    timing_categories: list[str]
    evaluation_sample_count: int


class SoftwareEnvironmentProvenance(Schema):
    application_version: str
    packages: dict[str, str | None]


class RuntimeEnvironmentProvenance(Schema):
    operating_system: str
    platform: str
    machine_architecture: str
    python_architecture: str
    logical_cpu_count: int | None
    worker_mode: Literal["single_process_thread_pool"]
    worker_count: Literal[1]
    simulator_runtime: dict[str, Any]


class ExecutionAtLockProvenance(Schema):
    job_id: str
    state_at_lock: Literal["created"]
    run_created_at: str
    manifest_locked_at: str
    started_at: None
    completed_at: None
    volatile_execution_metadata_location: str


class ReproducibilityProvenance(Schema):
    status: Literal[
        "CONFIGURATIONALLY_REPRODUCIBLE",
        "PARTIALLY_REPRODUCIBLE",
        "NON_REPRODUCIBLE",
        "INCOMPLETE_PROVENANCE",
    ]
    bitwise_reproducible: Literal[False]
    evidence: list[str]
    limitations: list[str]


class RunManifest(Schema):
    identity: ManifestIdentity
    dataset: DatasetProvenance
    sampling: SamplingProvenance
    split: SplitProvenance
    cross_validation: CrossValidationProvenance
    preprocessing: PreprocessingProvenance
    feature_engineering: FeatureEngineeringProvenance
    feature_selection: FeatureSelectionProvenance
    dimensionality_reduction: DimensionalityReductionProvenance
    models: list[ModelConfigurationProvenance] = Field(min_length=1, max_length=7)
    threshold_protocol: ThresholdProtocolProvenance
    evaluation_protocol: EvaluationProtocolProvenance
    software_environment: SoftwareEnvironmentProvenance
    runtime_environment: RuntimeEnvironmentProvenance
    execution_at_lock: ExecutionAtLockProvenance
    reproducibility: ReproducibilityProvenance


class ManifestIntegrityResult(Schema):
    valid: bool
    run_id: str
    artifact_id: str | None
    manifest_hash: str | None
    configuration_fingerprint: str | None
    errors: list[str]
