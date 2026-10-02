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
    features: list[str] | None = Field(default=None, max_length=200)
    models: list[Literal["logistic_regression", "svm", "random_forest", "vqc", "qsvc", "qnn", "hybrid_pennylane_torch"]] = Field(default_factory=lambda: ["logistic_regression", "svm", "random_forest"], min_length=1, max_length=7)
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
    @model_validator(mode="after")
    def coherent(self):
        if len(self.models) != len(set(self.models)):
            raise ValueError("Choose each model only once.")
        if self.features is not None and (not self.features or len(set(self.features)) != len(self.features)):
            raise ValueError("Features must be a nonempty unique list.")
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

class ExperimentOut(Schema):
    id: str
    dataset_id: str
    parent_id: str | None
    status: str
    config: dict[str, Any]
    summary: dict[str, Any]
    created_at: datetime

class ModelOut(Schema):
    id: str
    experiment_id: str
    run_id: str | None = None
    dataset_id: str
    model_type: str
    status: str
    details: dict[str, Any]
    metrics: dict[str, Any]
    created_at: datetime

class JobOut(Schema):
    id: str
    experiment_id: str
    run_id: str | None = None
    status: str
    progress: int
    state: str
    errors: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

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
