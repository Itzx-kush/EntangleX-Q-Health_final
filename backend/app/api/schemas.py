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
    models: list[Literal["logistic_regression", "svm", "random_forest", "vqc", "qsvc", "qnn"]] = Field(default_factory=lambda: ["logistic_regression", "svm", "random_forest"], min_length=1, max_length=6)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    quantum: QuantumConfig = Field(default_factory=QuantumConfig)
    parameters: ModelParameters = Field(default_factory=ModelParameters)
    seed: int = Field(default=42, ge=0, le=2147483647)
    test_size: float = Field(default=0.2, ge=0.1, le=0.4)
    cv_folds: int = Field(default=3, ge=2, le=10)
    max_samples: int | None = Field(default=160, ge=30, le=100000)
    duplicate_policy: Literal["reject", "drop_exact"] = "reject"
    probability_threshold: float = Field(default=0.5, gt=0, lt=1)
    calibration: Literal["none", "sigmoid", "isotonic"] = "none"
    calibration_folds: int = Field(default=3, ge=2, le=5)
    @model_validator(mode="after")
    def coherent(self):
        if len(self.models) != len(set(self.models)):
            raise ValueError("Choose each model only once.")
        if self.features is not None and (not self.features or len(set(self.features)) != len(self.features)):
            raise ValueError("Features must be a nonempty unique list.")
        quantum_models = {"vqc", "qsvc", "qnn"}
        if quantum_models.intersection(self.models):
            if self.pipeline.pca_components != self.quantum.qubits or not self.pipeline.angle_scaling:
                raise ValueError("Quantum comparisons require shared PCA components equal to qubits and shared angle scaling.")
            if self.calibration != "none":
                raise ValueError("Calibration is currently implemented for classical-only experiments. Quantum calibration is not enabled.")
            if self.parameters.class_weight is not None:
                raise ValueError("Quantum classifiers do not implement class weights; use none for a fair shared experiment.")
        return self

class DatasetUploadMetadata(Schema):
    name: str = Field(min_length=1, max_length=160)
    domain: str = Field(default="biomedical", max_length=80)
    source: str = Field(default="User-provided", max_length=200)
    source_url: str | None = Field(default=None, max_length=500)
    version: str = Field(default="unspecified", max_length=80)
    target: str = Field(min_length=1, max_length=100)
    positive_label: str = Field(min_length=1, max_length=64)
    negative_label: str | None = Field(default=None, max_length=64)
    deidentified: Literal[True]
    sampling_unit: Literal["independent_samples"] = "independent_samples"
    metadata_confirmed: bool = False
    metadata_sources: dict[str, str] = Field(default_factory=dict, max_length=32)
    metadata_suggestions: dict[str, Any] = Field(default_factory=dict)
    metadata_warnings: list[str] = Field(default_factory=list, max_length=20)
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

class ValidateRequest(Schema):
    features: list[str] | None = None

class DatasetOut(Schema):
    id: str
    name: str
    sha256: str
    provenance: dict[str, Any]
    quality: dict[str, Any]
    created_at: datetime


class DatasetLibraryItem(Schema):
    slug: str
    name: str
    domain: str
    description: str
    source: str
    source_url: str
    version: str
    license: str
    task: str
    target: str
    positive_label: str
    negative_label: str
    rows: int
    features: int
    numeric_feature_count: int
    categorical_feature_count: int
    filename: str
    is_demo: bool
    dataset_hash: str
    hash_algorithm: str
    hash_scope: str

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
    dataset_id: str
    model_type: str
    status: str
    details: dict[str, Any]
    metrics: dict[str, Any]
    created_at: datetime

class JobOut(Schema):
    id: str
    experiment_id: str
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

class PredictionOut(Schema):
    model_id: str
    model_type: str
    positive_label: str
    negative_label: str
    probability_status: str
    decision_rule: str
    risk_thresholds: tuple[float, float]
    predictions: list[PredictionItem]
    influence: list[dict[str, Any]] | None
    limitations: list[str]
    disclaimer: str

class ExplanationRequest(Schema):
    method: Literal["permutation", "shap", "perturbation"] = "permutation"
    max_samples: int = Field(default=8, ge=2, le=32)
    repeats: int = Field(default=3, ge=1, le=10)
    max_features: int = Field(default=30, ge=1, le=60)

class ExplanationOut(Schema):
    id: str
    model_id: str
    method: str
    result: dict[str, Any]
    created_at: datetime

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
    logical_depth: int
    gate_counts: dict[str, int]
    parameter_count: int
    text: str
    gates: list[dict[str, Any]]
    limitation: str
