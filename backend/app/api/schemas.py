from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True, allow_inf_nan=False)

class RatioConfig(Schema):
    name: str = Field(min_length=1, max_length=100)
    numerator: str
    denominator: str

class PipelineConfig(Schema):
    imputer: Literal["median", "mean", "most_frequent"] = "median"
    scaler: Literal["standard", "minmax", "robust", "none"] = "standard"
    outlier_strategy: Literal["none", "clip_quantiles"] = "none"
    lower_quantile: float = Field(default=0.01, ge=0, lt=0.5)
    upper_quantile: float = Field(default=0.99, gt=0.5, le=1)
    log_features: list[str] = Field(default_factory=list, max_length=100)
    ratios: list[RatioConfig] = Field(default_factory=list, max_length=20)
    selection: Literal["none", "anova", "mutual_info", "variance"] = "anova"
    k_features: int = Field(default=12, ge=1, le=400)
    variance_threshold: float = Field(default=0.0, ge=0, le=10)
    pca_components: int | None = Field(default=4, ge=1, le=100)
    pca_whiten: bool = False
    angle_scaling: bool = True

class QuantumConfig(Schema):
    provider_id: Literal["qiskit_local"] = "qiskit_local"
    execution_mode: Literal["local_simulator"] = "local_simulator"
    backend: Literal["statevector", "aer"] = "statevector"
    qubits: int = Field(default=4, ge=2, le=8)
    feature_map_reps: int = Field(default=1, ge=1, le=3)
    ansatz_reps: int = Field(default=1, ge=1, le=3)
    entanglement: Literal["linear", "full"] = "linear"
    optimizer: Literal["COBYLA", "SPSA"] = "COBYLA"
    maxiter: int = Field(default=30, ge=5, le=300)
    shots: int = Field(default=1024, ge=128, le=16384)
    noise_probability: float = Field(default=0.0, ge=0, le=0.1)
    @model_validator(mode="after")
    def noise_backend(self):
        if self.noise_probability and self.backend != "aer":
            raise ValueError("Noise simulation requires the Aer backend.")
        return self

class HybridModelConfig(Schema):
    model_type: Literal["hybrid_pennylane_torch"] = "hybrid_pennylane_torch"
    provider_id: Literal["pennylane_local"] = "pennylane_local"
    execution_mode: Literal["local_simulator"] = "local_simulator"
    qubits: int = Field(default=4, ge=2, le=8)
    feature_map: Literal["angle"] = "angle"
    quantum_layers: int = Field(default=2, ge=1, le=6)
    classical_hidden_dimensions: list[int] = Field(default_factory=lambda: [16, 8], min_length=1, max_length=3)
    classical_activation: Literal["relu", "tanh"] = "relu"
    optimizer: Literal["adam", "sgd"] = "adam"
    learning_rate: float = Field(default=0.001, ge=0.00001, le=0.1)
    epochs: int = Field(default=50, ge=1, le=500)
    batch_size: int = Field(default=16, ge=1, le=256)
    deterministic_seed: int = Field(default=42, ge=0, le=2147483647)
    sample_cap: int = Field(default=160, ge=30, le=2000)
    backend: Literal["default.qubit"] = "default.qubit"
    @field_validator("classical_hidden_dimensions")
    @classmethod
    def bounded_hidden_dimensions(cls, value):
        if any(dimension < 2 or dimension > 128 for dimension in value):
            raise ValueError("Hybrid hidden dimensions must be between 2 and 128.")
        return value

class ModelParameters(Schema):
    logistic_c: float = Field(default=1, gt=0, le=10000)
    svm_c: float = Field(default=1, gt=0, le=10000)
    svm_kernel: Literal["rbf", "linear"] = "rbf"
    forest_trees: int = Field(default=100, ge=10, le=500)
    forest_max_depth: int | None = Field(default=None, ge=1, le=100)
    class_weight: Literal["balanced"] | None = None

class TrainingConfig(Schema):
    dataset_id: UUID
    dataset_version_id: UUID | None = None
    pipeline_version_id: UUID | None = None
    condition_task_id: UUID | None = None
    features: list[str] | None = Field(default=None, max_length=200)
    models: list[Literal["logistic_regression", "svm", "random_forest", "vqc", "qsvc", "qnn", "hybrid_pennylane_torch"]] = Field(
        default_factory=lambda: ["logistic_regression", "svm", "random_forest"], min_length=1, max_length=7
    )
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    quantum: QuantumConfig = Field(default_factory=QuantumConfig)
    hybrid: HybridModelConfig = Field(default_factory=HybridModelConfig)
    parameters: ModelParameters = Field(default_factory=ModelParameters)
    seed: int = Field(default=42, ge=0, le=2147483647)
    test_size: float = Field(default=0.2, ge=0.1, le=0.4)
    cv_folds: int = Field(default=3, ge=2, le=10)
    max_samples: int | None = Field(default=160, ge=30, le=100000)
    duplicate_policy: Literal["reject", "drop_exact"] = "reject"
    probability_threshold: float = Field(default=0.5, gt=0, lt=1)
    threshold_strategy: Literal["fixed", "target_sensitivity"] = "fixed"
    target_sensitivity: float = Field(default=0.95, gt=0, le=1)
    calibration: Literal["none", "sigmoid", "isotonic"] = "none"
    calibration_folds: int = Field(default=3, ge=2, le=5)
    sampling_unit: Literal["independent_samples", "grouped_samples"] = "independent_samples"
    group_column: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def coherent(self):
        if len(self.models) != len(set(self.models)):
            raise ValueError("Choose each model only once.")
        if self.features is not None and (not self.features or len(set(self.features)) != len(self.features)):
            raise ValueError("Features must be a nonempty unique list.")
        if self.sampling_unit == "grouped_samples" and not self.group_column:
            raise ValueError("group_column is required when sampling_unit is 'grouped_samples'.")
        qiskit_models = {"vqc", "qsvc", "qnn"}
        qiskit_selected = bool(qiskit_models.intersection(self.models))
        hybrid_selected = "hybrid_pennylane_torch" in self.models
        if qiskit_selected:
            if self.pipeline.pca_components != self.quantum.qubits or not self.pipeline.angle_scaling:
                raise ValueError("Qiskit comparisons require PCA components equal to QuantumConfig qubits and shared angle scaling.")
        if hybrid_selected:
            if self.pipeline.pca_components != self.hybrid.qubits or not self.pipeline.angle_scaling:
                raise ValueError("PennyLane hybrid comparisons require PCA components equal to HybridModelConfig qubits and shared angle scaling.")
            if self.max_samples is None or self.max_samples > self.hybrid.sample_cap:
                raise ValueError("The shared experiment max_samples must not exceed the hybrid sample_cap.")
        if qiskit_selected and hybrid_selected and self.quantum.qubits != self.hybrid.qubits:
            raise ValueError("Qiskit and PennyLane hybrid qubits must agree for a shared comparison representation.")
        if qiskit_selected or hybrid_selected:
            if self.calibration != "none":
                raise ValueError("Calibration is currently implemented for classical-only experiments. Quantum-family calibration is not enabled.")
            if self.parameters.class_weight is not None:
                raise ValueError("Quantum-family classifiers do not implement class weights; use none for a fair shared experiment.")
        return self

class DatasetUploadMetadata(Schema):
    name: str = Field(min_length=1, max_length=160)
    domain: str = Field(default="biomedical", max_length=80)
    source: str = Field(default="User-provided", max_length=200)
    source_url: str | None = Field(default=None, max_length=500)
    version: str = Field(default="unspecified", max_length=80)
    target: str = Field(min_length=1, max_length=100)
    positive_label: str = Field(min_length=1, max_length=64)
    deidentified: Literal[True]
    sampling_unit: Literal["independent_samples"] = "independent_samples"
    @field_validator("name", "domain", "source", "version", "target", "positive_label")
    @classmethod
    def clean_text(cls, value):
        value = value.strip()
        if not value or any(ord(c) < 32 for c in value):
            raise ValueError("Text must be nonempty and contain no control characters.")
        return value
    @field_validator("source_url")
    @classmethod
    def source_http(cls, value):
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("Source reference must be an HTTP(S) URL; it is recorded, never fetched.")
        return value

class TargetCandidateOut(Schema):
    column: str
    score: float
    confidence: Literal["low", "medium", "high"]
    target_type: str
    class_labels: list[str]
    class_distribution: dict[str, int]
    unique_values: int
    missing_fraction: float
    eligible_for_current_pipeline: bool
    reasons: list[str]
    penalties: list[str]
    position: int

class DatasetInspectionOut(Schema):
    filename: str
    sha256: str
    row_count: int
    column_count: int
    columns: list[str]
    column_schema: list[dict[str, Any]] = Field(validation_alias="schema", serialization_alias="schema")
    detected_target: str | None
    target_type: str | None
    confidence_score: float
    confidence: Literal["low", "medium", "high"]
    selection_method: str
    class_labels: list[str]
    class_distribution: dict[str, int]
    positive_label: str | None
    positive_label_confidence: float
    positive_label_reason: str
    requires_manual_target: bool
    requires_positive_label: bool
    heuristic_notice: str
    candidates: list[TargetCandidateOut]

class DemoReadinessOut(Schema):
    status: Literal["ready", "requires_processing"]
    instant_demo_available: bool
    artifact_version: str | None
    experiment_id: str | None
    model_ids: list[str]
    verified_dataset_hash: str | None
    verified_artifact_manifest_hash: str | None
    unavailable_reason: str | None = None

class DatasetLibraryItem(Schema):
    slug: str
    name: str
    domain: str
    description: str
    source: str
    source_url: str
    version: str
    license: str
    license_url: str
    attribution: str
    target: str
    target_type: Literal["binary_classification"]
    positive_label: str
    negative_label: str
    row_count: int
    feature_count: int
    class_labels: list[str]
    sha256: str
    normalization: list[str]
    recommended_duplicate_policy: Literal["reject", "drop_exact"]
    origin: Literal["built_in"]
    dataset_status: Literal["available"]
    demo_readiness: DemoReadinessOut

class BuiltInRegistrationRequest(Schema):
    target: str | None = Field(default=None, max_length=100)
    positive_label: str | None = Field(default=None, max_length=64)

class ValidateRequest(Schema):
    features: list[str] | None = None

class DatasetOut(Schema):
    id: str
    name: str
    sha256: str
    provenance: dict[str, Any]
    quality: dict[str, Any]
    created_at: datetime
    current_version_id: str | None = None

class DatasetVersionOut(Schema):
    id: str
    dataset_id: str
    version_number: int
    version_label: str
    content_sha256: str
    schema_fingerprint: str
    row_count: int
    feature_count: int
    target: str
    positive_label: str
    negative_label: str
    target_type: str
    class_distribution: dict[str, int]
    source_metadata: dict[str, Any]
    status: str
    immutable: bool
    created_at: datetime

class DatasetVersionIntegrityOut(Schema):
    valid: bool
    dataset_id: str
    dataset_version_id: str
    expected_sha256: str
    actual_sha256: str | None
    errors: list[str]

class DatasetCardOut(Schema):
    identity: dict[str, Any]
    data: dict[str, Any]
    quality: dict[str, Any]
    provenance: dict[str, Any]
    limitations: list[str]
    usage: dict[str, Any]

class DatasetVersionComparisonOut(Schema):
    classification: Literal["IDENTICAL_CONTENT", "SAME_SCHEMA_DIFFERENT_DATA", "SCHEMA_CHANGED"]
    left: dict[str, Any]
    right: dict[str, Any]
    differences: dict[str, Any]

class ExperimentOut(Schema):
    id: str
    name: str | None = None
    dataset_id: str
    parent_id: str | None
    pipeline_version_id: str | None = None
    status: str
    config: dict[str, Any]
    summary: dict[str, Any]
    created_at: datetime

class ExperimentDeletionOut(Schema):
    id: str
    status: Literal["archived"]
    deleted_at: datetime
    already_deleted: bool
    preserved_records: dict[str, int]

class ModelOut(Schema):
    id: str
    experiment_id: str
    run_id: str | None = None
    dataset_id: str
    model_type: str
    status: str
    progress: int | None = None
    details: dict[str, Any]
    metrics: dict[str, Any]
    created_at: datetime

class JobOut(Schema):
    id: str
    experiment_id: str
    run_id: str | None = None
    job_type: str = "training"
    status: str
    priority: int = 0
    progress: int | None = None
    total_units: int | None = None
    completed_units: int = 0
    failed_units: int = 0
    skipped_units: int = 0
    active_unit: str | None = None
    current_phase: str | None = None
    state: str
    errors: list[dict[str, Any]]
    attempt_count: int = 0
    resume_count: int = 0
    current_checkpoint_id: str | None = None
    configuration_fingerprint: str | None = None
    input_fingerprint: str | None = None
    failure_category: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    requested_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    experiment_name: str | None = None
    models: list[ModelOut] = Field(default_factory=list)

class JobCheckpointOut(Schema):
    id: str
    job_id: str
    sequence_number: int
    checkpoint_type: str
    status: str
    logical_unit: str | None = None
    completed_units: int
    checkpoint_state: dict[str, Any]
    state_fingerprint: str
    artifact_references: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    validated_at: datetime | None = None
    invalidated_at: datetime | None = None

class JobProgressOut(Schema):
    job_id: str
    status: str
    determinate: bool
    percentage: int | None = None
    total_units: int | None = None
    completed_units: int
    failed_units: int
    skipped_units: int
    active_unit: str | None = None
    current_phase: str | None = None

class TrainingResponse(Schema):
    job: JobOut
    experiment: ExperimentOut

class PredictionRequest(Schema):
    samples: list[dict[str, str | float | int | bool | None]] = Field(min_length=1, max_length=32)
    risk_thresholds: tuple[float, float] = (0.33, 0.66)
    include_influence: bool = False
    @model_validator(mode="after")
    def validate_thresholds(self):
        low, high = self.risk_thresholds
        if not 0 < low < high < 1:
            raise ValueError("Research thresholds must satisfy 0 < low < high < 1.")
        if self.include_influence and len(self.samples) != 1:
            raise ValueError("Local feature influence requires exactly one sample.")
        return self

class PredictionItem(Schema):
    sample: str
    predicted_class: str
    probability_positive: float | None
    decision_score: float | None
    research_risk_category: str | None

class HybridShapContributionOut(Schema):
    feature: str
    original_value: str | float | int | bool | None
    contribution: float
    signed_mean: float
    magnitude: float
    absolute_contribution: float
    direction: Literal["toward_positive", "toward_negative", "neutral"]
    interpretation: str

class HybridPredictionContextOut(Schema):
    probability_positive: float
    operating_threshold: float
    threshold_source: str
    predicted_class: str
    positive_label: str
    negative_label: str
    research_risk_category: str | None
    base_value: float

class HybridLocalExplanationOut(Schema):
    method: Literal["shap"]
    method_display: Literal["SHAP — Final Hybrid Output"]
    scope: Literal["local_case"]
    model_type: Literal["hybrid_pennylane_torch"]
    model_display_name: Literal["PennyLane + PyTorch Hybrid"]
    output_semantics: Literal["final positive-class probability"]
    prediction_context: HybridPredictionContextOut
    contributions: list[HybridShapContributionOut]
    background_source: Literal["training partition only"]
    background_sample_count: int
    explained_case_count: Literal[1]
    limitations: list[str]

class PredictionOut(Schema):
    model_id: str
    model_type: str
    positive_label: str
    negative_label: str
    probability_status: str
    decision_rule: str
    operating_threshold: float
    threshold_source: str = "legacy_fixed_configuration"
    risk_thresholds: tuple[float, float]
    predictions: list[PredictionItem]
    influence: list[dict[str, Any]] | None
    explanation: HybridLocalExplanationOut | None = None
    limitations: list[str]
    disclaimer: str

class RobustnessScenario(Schema):
    perturbation_type: Literal["missingness", "gaussian_noise", "outliers", "categorical"]
    level: float = Field(gt=0, le=10)
    @model_validator(mode="after")
    def supported_level(self):
        limits = {
            "missingness": (0, 0.25),
            "gaussian_noise": (0, 0.5),
            "outliers": (1, 10),
            "categorical": (0, 0.25),
        }
        low, high = limits[self.perturbation_type]
        if not low < self.level <= high:
            raise ValueError("Perturbation level is outside the supported bounded range.")
        return self

class RobustnessRequest(Schema):
    model_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=6)
    scenarios: list[RobustnessScenario] = Field(
        default_factory=lambda: [
            RobustnessScenario(perturbation_type="missingness", level=0.05),
            RobustnessScenario(perturbation_type="missingness", level=0.10),
            RobustnessScenario(perturbation_type="gaussian_noise", level=0.05),
            RobustnessScenario(perturbation_type="gaussian_noise", level=0.10),
            RobustnessScenario(perturbation_type="outliers", level=3.0),
            RobustnessScenario(perturbation_type="categorical", level=0.05),
        ],
        min_length=1,
        max_length=8,
    )
    random_seed: int = Field(default=42, ge=0, le=2147483647)
    max_samples: int = Field(default=32, ge=8, le=64)
    @model_validator(mode="after")
    def bounded_budget(self):
        model_count = len(self.model_ids) if self.model_ids else 3
        if model_count * len(self.scenarios) > 24:
            raise ValueError("A robustness request may contain at most 24 model-scenario conditions.")
        if self.model_ids and len(self.model_ids) != len(set(self.model_ids)):
            raise ValueError("Choose each robustness model only once.")
        scenario_keys = [(item.perturbation_type, item.level) for item in self.scenarios]
        if len(scenario_keys) != len(set(scenario_keys)):
            raise ValueError("Choose each perturbation type and level only once.")
        return self

class RobustnessRecordOut(Schema):
    id: str
    experiment_id: str
    model_id: str
    perturbation_type: str
    perturbation_level: float
    random_seed: int
    result: dict[str, Any]
    created_at: datetime

class ExplanationRequest(Schema):
    method: Literal["permutation", "shap", "perturbation"] = "permutation"
    max_samples: int = Field(default=8, ge=2, le=32)
    repeats: int = Field(default=3, ge=1, le=10)
    max_features: int = Field(default=30, ge=1, le=60)

class ExplanationOut(Schema):
    id: str
    model_id: str
    run_id: str | None = None
    method: str
    result: dict[str, Any]
    created_at: datetime


class RunOut(Schema):
    id: str
    experiment_id: str
    dataset_id: str
    dataset_version_id: str | None = None
    pipeline_version_id: str | None = None
    status: Literal["created", "queued", "running", "completed", "failed", "cancelled"]
    config: dict[str, Any]
    execution_metadata: dict[str, Any]
    reproducibility_metadata: dict[str, Any]
    result_summary: dict[str, Any]
    failure: dict[str, Any] | None
    manifest_artifact_id: str | None = None
    configuration_fingerprint: str | None = None
    reproducibility_status: str | None = None
    manifest_locked_at: datetime | None = None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    cancelled_at: datetime | None


class ArtifactOut(Schema):
    id: str
    experiment_id: str
    run_id: str | None
    model_id: str | None
    artifact_type: str
    name: str
    description: str
    storage_reference: str | None
    integrity_hash: str
    hash_algorithm: Literal["sha256"]
    size_bytes: int | None
    content_type: str | None
    details: dict[str, Any]
    immutable: bool
    created_at: datetime


class RunTrainingResponse(Schema):
    job: JobOut
    experiment: ExperimentOut
    run: RunOut

class PreviewOut(Schema):
    train_count: int
    test_count: int
    input_features: list[str]
    selected_features: list[str]
    output_features: list[str]
    selection_scores: list[dict[str, Any]]
    pca_explained_variance: list[float]
    pca_loadings: list[list[float]]
    split_hash: str
    stages: list[str]
    warnings: list[str]

class CircuitRequest(Schema):
    quantum: QuantumConfig = Field(default_factory=QuantumConfig)
    model_type: Literal["vqc", "qsvc", "qnn"] = "vqc"
    seed: int = Field(default=42, ge=0)

class CircuitOut(Schema):
    model_type: str
    execution_kind: str
    backend: str
    qubits: int
    logical_depth: int | None
    gate_counts: dict[str, int]
    parameter_count: int
    text: str
    gates: list[dict[str, Any]]
    limitation: str


class ProviderPreflightRequest(Schema):
    provider_id: str = Field(default="qiskit_local", min_length=1, max_length=80)
    backend_id: str = Field(default="statevector", min_length=1, max_length=120)
    requested_capabilities: list[str] = Field(default_factory=list, max_length=20)
    configuration: dict[str, Any] = Field(default_factory=dict)

class ResourceAdvisorRequest(Schema):
    model_type: Literal["vqc", "qsvc", "qnn"]
    quantum: QuantumConfig = Field(default_factory=QuantumConfig)
    feature_dimension: int = Field(ge=2, le=100)
    sample_count: int = Field(ge=30, le=100000)
    dataset_id: UUID | None = None
    experiment_id: UUID | None = None
    @model_validator(mode="after")
    def quantum_representation(self):
        if self.feature_dimension != self.quantum.qubits:
            raise ValueError("Quantum feature dimension must equal the configured qubit count.")
        return self


class ModelCapabilityOut(Schema):
    model_id: str
    display_name: str
    category: str
    implementation_status: Literal["AVAILABLE", "NOT_YET_IMPLEMENTED", "UNAVAILABLE"]
    executable: bool
    quantum_framework: str | None = None
    classical_framework: str | None = None
    execution: str | None = None
    hardware_execution: str | None = None
    probability_output: str | None = None
    explainability: str | None = None
    supported_prediction: str | None = None
    supported_comparison: str | None = None
    supported_thresholding: str | None = None
    supported_robustness: str | None = None
    training: str | None = None

class FrameworkCapabilityOut(Schema):
    package_installed: bool
    package_importable: bool
    model_implemented: bool
    model_executable: bool
    simulator_available: bool
    real_hardware_available: bool
    runtime_verified: bool = False

class ShowcaseContextOut(Schema):
    id: str
    display_name: str
    label: str
    featured_dataset_slug: str
    disease_domain: str
    target: str
    positive_class: str
    dataset_hash: str
    research_only_disclaimer: str
    recommended_models: list[str]

class FlagshipPresetOut(Schema):
    id: str
    display_name: str
    dataset_slug: str
    models: list[str]
    auto_start_training: Literal[False]
    threshold_strategy: Literal["target_sensitivity"]
    configuration: dict[str, Any]
    scientific_status: str
    evidence_requirements: list[str]

class FlagshipArchitectureOut(Schema):
    model_id: Literal["hybrid_pennylane_torch"]
    status: Literal["IMPLEMENTED", "UNAVAILABLE"]
    stages: list[str]

class AlignmentContractOut(Schema):
    contract_version: str
    models: list[ModelCapabilityOut]
    frameworks: dict[str, FrameworkCapabilityOut]
    showcase: ShowcaseContextOut
    flagship_experiment_preset: FlagshipPresetOut
    flagship_architecture: FlagshipArchitectureOut


class ChatMessage(Schema):
    role: Literal["user", "model"]
    content: str = Field(min_length=1, max_length=2000)

class ChatRequest(Schema):
    message: str = Field(min_length=1, max_length=2000)
    conversation: list[ChatMessage] = Field(default_factory=list, max_length=10)

class ChatResponse(Schema):
    reply: str


class MultiSeedStudyRequest(Schema):
    base_experiment_id: UUID | None = None
    config: TrainingConfig | None = None
    seeds: list[int] = Field(min_length=2, max_length=20)

    @field_validator("seeds")
    @classmethod
    def validate_seeds(cls, v: list[int]) -> list[int]:
        if len(v) != len(set(v)):
            raise ValueError("Requested seeds must not contain duplicates.")
        for s in v:
            if not (0 <= s <= 2147483647):
                raise ValueError("Each seed must be an integer between 0 and 2147483647.")
        return v

    @model_validator(mode="after")
    def validate_experiment_or_config(self):
        if self.base_experiment_id is None and self.config is None:
            raise ValueError("Either base_experiment_id or config must be provided.")
        return self


class Interval95Out(Schema):
    lower: float | None = None
    upper: float | None = None
    method: str = "bootstrap_percentile"
    interpretation: str = "descriptive seed-variability interval; not population-level clinical or statistical significance"
    bootstrap_samples: int | None = None
    bootstrap_seed: int | None = None
    limitations: list[str] = Field(default_factory=list)


class MetricAggregateOut(Schema):
    metric_name: str
    n: int
    valid_count: int
    missing_count: int
    missing_seeds: list[int] = Field(default_factory=list)
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    min: float | None = None
    max: float | None = None
    interval_95: Interval95Out | None = None


class ModelAggregateOut(Schema):
    model_type: str
    metrics: dict[str, MetricAggregateOut]
    evaluated_seeds: list[int]
    successful_seeds: list[int]
    failed_seeds: list[int]


class PairedSeedObservationOut(Schema):
    seed: int
    value_a: float | None = None
    value_b: float | None = None
    delta: float | None = None


class PairedMetricComparisonOut(Schema):
    metric_name: str
    model_a: str
    model_b: str
    available: bool = True
    reason: str | None = None
    valid_pairs_count: int = 0
    mean_delta: float | None = None
    median_delta: float | None = None
    std_delta: float | None = None
    min_delta: float | None = None
    max_delta: float | None = None
    interval_95: Interval95Out | None = None
    observations: list[PairedSeedObservationOut] = Field(default_factory=list)


class StudyRunOut(Schema):
    id: str
    study_id: str
    run_id: str | None = None
    job_id: str | None = None
    seed: int
    seed_order: int
    status: str
    failure: dict[str, Any] | None = None
    created_at: datetime
    completed_at: datetime | None = None


class MultiSeedStudySummaryOut(Schema):
    study_id: str
    protocol_version: str
    base_experiment_id: str
    dataset_id: str
    dataset_version_id: str | None = None
    configuration_fingerprint: str
    requested_seeds: list[int]
    completed_seeds: list[int]
    failed_seeds: list[int]
    cancelled_seeds: list[int]
    models: list[str]
    aggregates: dict[str, ModelAggregateOut]
    paired_differences: list[PairedMetricComparisonOut]
    artifact_id: str | None = None
    bootstrap_protocol: dict[str, Any] = Field(default_factory=dict)
    software: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str]


class MultiSeedStudyOut(Schema):
    id: str
    base_experiment_id: str
    dataset_id: str
    dataset_version_id: str | None = None
    status: str
    operation_key: str
    protocol_version: str
    requested_seeds: list[int]
    completed_seeds: list[int] = Field(default_factory=list)
    failed_seeds: list[int] = Field(default_factory=list)
    cancelled_seeds: list[int] = Field(default_factory=list)
    model_identities: list[str]
    locked_config: dict[str, Any]
    configuration_fingerprint: str
    study_artifact_id: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    limitations: list[str]


class MultiSeedStudyDetailOut(Schema):
    study: MultiSeedStudyOut
    runs: list[StudyRunOut]
    summary: MultiSeedStudySummaryOut | None = None
    reproducibility: dict[str, Any] = Field(default_factory=dict)
    failure: dict[str, Any] | None = None


class MultiSeedStudyResponse(Schema):
    study: MultiSeedStudyOut
    runs: list[StudyRunOut]


class ExternalValidationRequest(Schema):
    model_config = ConfigDict(extra="forbid")

    model_id: UUID
    external_dataset_id: UUID
    external_dataset_version_id: UUID | None = None
    condition_task_id: UUID | None = None
    label_mapping: dict[str, str] | None = None
    notes: str | None = None


class FeatureCompatibilityOut(Schema):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    compatible: bool
    required_features: list[str]
    present_features: list[str]
    missing_features: list[str]
    extra_features: list[str]
    type_mismatches: list[dict[str, Any]] = Field(default_factory=list)


class LabelCompatibilityOut(Schema):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    compatible: bool
    model_positive_label: str
    model_negative_label: str
    external_target: str
    external_positive_label: str | None = None
    external_negative_label: str | None = None
    observed_classes: list[str]
    mapping_strategy: str
    mapped_positive_value: str | None = None
    mapped_negative_value: str | None = None
    reasons: list[str] = Field(default_factory=list)


class ThresholdLockOut(Schema):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    threshold_used: float
    threshold_source: str
    threshold_units: str
    external_threshold_tuning: bool = False


class IndependenceAssessmentOut(Schema):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    content_hash_distinct: bool
    dataset_identity_distinct: bool
    version_distinct: bool
    declared_source: str | None = None
    independence_status: str


class ValidationPreflightOut(Schema):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    ready: bool
    model_id: str
    model_type: str
    training_dataset: dict[str, Any]
    external_dataset: dict[str, Any]
    feature_compatibility: FeatureCompatibilityOut
    label_compatibility: LabelCompatibilityOut
    threshold_lock: ThresholdLockOut
    artifact_integrity: dict[str, Any]
    independence: IndependenceAssessmentOut
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)


class MetricComparisonItemOut(Schema):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    metric: str
    internal_value: float | None = None
    external_value: float | None = None
    delta: float | None = None
    relative_change: float | None = None
    interpretation: str = "Observed external-to-internal difference."


class ExternalValidationOut(Schema):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: str
    model_id: str
    model_type: str
    run_id: str | None = None
    experiment_id: str
    training_dataset_id: str
    training_dataset_version_id: str | None = None
    external_dataset_id: str
    external_dataset_version_id: str | None = None
    study_id: str | None = None
    study_seed: int | None = None
    status: str
    operation_key: str
    compatibility: dict[str, Any]
    label_mapping: dict[str, Any]
    threshold_metadata: dict[str, Any]
    metrics: dict[str, Any]
    internal_metrics: dict[str, Any]
    comparison: dict[str, Any]
    generalization_gap: dict[str, float | None]
    provenance: dict[str, Any]
    artifact_id: str | None = None
    limitations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    failure: dict[str, Any] | None = None
    created_at: datetime
    completed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Master Prompt 3: Distribution Shift Analysis Schemas
# ---------------------------------------------------------------------------

class DistributionShiftConfig(Schema):
    missingness_delta_threshold: float = Field(default=0.05, ge=0.001, le=0.50)
    numeric_distance_threshold: float = Field(default=0.15, ge=0.01, le=1.0)
    categorical_distance_threshold: float = Field(default=0.15, ge=0.01, le=1.0)
    statistical_significance_threshold: float = Field(default=0.05, ge=0.0001, le=0.20)
    multiple_testing_correction: Literal["benjamini_hochberg"] = "benjamini_hochberg"
    numeric_test: Literal["kolmogorov_smirnov"] = "kolmogorov_smirnov"
    categorical_test: Literal["total_variation_distance"] = "total_variation_distance"


class DistributionShiftRequest(Schema):
    reference_dataset_id: UUID
    comparison_dataset_id: UUID
    reference_dataset_version_id: UUID | None = None
    condition_task_id: UUID | None = None
    comparison_dataset_version_id: UUID | None = None
    model_id: UUID | None = None
    external_validation_id: UUID | None = None
    config: DistributionShiftConfig | None = None


class SchemaShiftOut(Schema):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    reference_columns: list[str] = Field(default_factory=list)
    comparison_columns: list[str] = Field(default_factory=list)
    shared_columns: list[str] = Field(default_factory=list)
    missing_in_comparison: list[str] = Field(default_factory=list)
    extra_in_comparison: list[str] = Field(default_factory=list)
    type_mismatches: list[dict[str, str]] = Field(default_factory=list)
    reference_feature_count: int
    comparison_feature_count: int


class TargetShiftOut(Schema):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    target_evaluated: bool
    target_column: str | None = None
    reference_classes: list[str] = Field(default_factory=list)
    comparison_classes: list[str] = Field(default_factory=list)
    compatible: bool = False
    reference_counts: dict[str, int] = Field(default_factory=dict)
    comparison_counts: dict[str, int] = Field(default_factory=dict)
    reference_positive_prevalence: float | None = None
    comparison_positive_prevalence: float | None = None
    prevalence_delta: float | None = None
    interpretation: str | None = None


class MissingnessShiftDetailOut(Schema):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    reference_missing_count: int
    reference_missing_fraction: float
    comparison_missing_count: int
    comparison_missing_fraction: float
    delta: float
    flagged: bool


class NumericShiftDetailOut(Schema):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    reference_count: int
    comparison_count: int
    reference_mean: float | None = None
    comparison_mean: float | None = None
    mean_difference: float | None = None
    reference_std: float | None = None
    comparison_std: float | None = None
    std_difference: float | None = None
    reference_median: float | None = None
    comparison_median: float | None = None
    median_difference: float | None = None
    reference_min: float | None = None
    reference_max: float | None = None
    comparison_min: float | None = None
    comparison_max: float | None = None
    standardized_mean_difference: float | None = None
    effect_size_label: str | None = None
    test_method: str = "kolmogorov_smirnov"
    statistic: float | None = None
    raw_p_value: float | None = None
    distance_metric: str = "wasserstein_distance"
    distance_value: float | None = None
    warnings: list[str] = Field(default_factory=list)


class CategoricalShiftDetailOut(Schema):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    reference_count: int
    comparison_count: int
    category_count: int
    reference_proportions: dict[str, float] = Field(default_factory=dict)
    comparison_proportions: dict[str, float] = Field(default_factory=dict)
    proportion_deltas: dict[str, float] = Field(default_factory=dict)
    distance_metric: str = "total_variation_distance"
    distance_value: float | None = None
    test_method: str = "chi_square_contingency"
    statistic: float | None = None
    raw_p_value: float | None = None
    sparse_categories: bool = False
    warnings: list[str] = Field(default_factory=list)


class FeatureShiftRecordOut(Schema):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    feature: str
    feature_type: str
    is_model_input: bool = False
    missingness: MissingnessShiftDetailOut
    numeric: NumericShiftDetailOut | None = None
    categorical: CategoricalShiftDetailOut | None = None
    raw_p_value: float | None = None
    adjusted_p_value: float | None = None
    p_value_interpretation: str | None = None
    flagged: bool = False
    flag_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ShiftSummaryOut(Schema):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    total_features_reference: int
    total_features_comparison: int
    shared_features_count: int
    model_features_count: int = 0
    model_features_missing_count: int = 0
    shifted_features_count: int
    missingness_shifted_count: int
    numeric_features_tested_count: int
    numeric_features_shifted_count: int
    categorical_features_tested_count: int
    categorical_features_shifted_count: int
    target_shift_detected: bool = False
    target_prevalence_delta: float | None = None
    schema_mismatch_count: int
    type_mismatch_count: int
    multiple_testing_correction: str
    tested_hypotheses_count: int


class DistributionShiftPreflightOut(Schema):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    ready: bool
    reference_dataset: dict[str, Any]
    comparison_dataset: dict[str, Any]
    model: dict[str, Any] | None = None
    external_validation: dict[str, Any] | None = None
    schema_preview: SchemaShiftOut
    target_preview: TargetShiftOut
    model_features: list[str] | None = None
    missing_model_features: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)


class DistributionShiftOut(Schema):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: str
    reference_dataset_id: str
    reference_dataset_version_id: str | None = None
    reference_content_sha256: str
    comparison_dataset_id: str
    comparison_dataset_version_id: str | None = None
    comparison_content_sha256: str
    model_id: str | None = None
    external_validation_id: str | None = None
    parent_study_id: str | None = None
    model_seed: int | None = None
    status: str
    operation_key: str
    policy_version: str
    configuration: dict[str, Any]
    schema_analysis: SchemaShiftOut
    target_analysis: TargetShiftOut
    missingness_analysis: dict[str, Any]
    feature_shifts: list[FeatureShiftRecordOut]
    summary: ShiftSummaryOut
    flagged_features: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    provenance: dict[str, Any]
    artifact_id: str | None = None
    failure: dict[str, Any] | None = None
    execution_time_seconds: float = 0.0
    created_at: datetime
    completed_at: datetime | None = None
