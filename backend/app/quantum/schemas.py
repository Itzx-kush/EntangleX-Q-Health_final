from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import Field, model_validator

from ..api.schemas import HybridModelConfig, QuantumConfig, Schema
from datetime import datetime


class QuantumPreflightRequest(Schema):
    experiment_id: str
    model_record_id: str


class QuantumDiagnosticFinding(Schema):
    severity: str # INFO, WARNING, BLOCKER
    code: str
    title: str
    description: str
    evidence: Optional[dict[str, Any]] = None
    recommendation: Optional[str] = None

class QuantumDiagnosticReportOut(Schema):
    id: str
    experiment_id: str
    model_record_id: str
    model_type: str
    status: str
    created_at: datetime
    
    model_configuration: dict[str, Any]
    feature_encoding: dict[str, Any]
    circuit_structure: dict[str, Any]
    resource_profile: dict[str, Any]
    optimizer_profile: dict[str, Any]
    training_profile: dict[str, Any]
    execution_profile: dict[str, Any]
    stability_profile: dict[str, Any]
    noise_profile: dict[str, Any]
    
    warnings: list[QuantumDiagnosticFinding]
    limitations: list[str]
    
    configuration_fingerprint: Optional[str] = None
    provenance: dict[str, Any]

class QuantumDiagnosticPreflightResponse(Schema):
    feasible: bool
    blockers: list[str] = Field(default_factory=list)
    unsupported_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class RepresentationContext(Schema):
    """Descriptive metadata only; it does not assert that preprocessing was run."""

    selected_feature_names: list[str] | None = Field(default=None, max_length=8)
    source: str | None = Field(default=None, max_length=120)
    angle_scaling: bool | None = None


class QuantumVisualizationPreviewRequest(Schema):
    model_type: Literal["vqc", "qsvc", "qnn", "hybrid_pennylane_torch"] = "vqc"
    quantum: QuantumConfig | None = None
    hybrid: HybridModelConfig | None = None
    dataset_id: UUID | None = None
    dataset_version_id: UUID | None = None
    experiment_id: UUID | None = None
    representation_context: RepresentationContext | None = None
    sample_count: int | None = Field(default=None, ge=30, le=100000)
    seed: int = Field(default=42, ge=0, le=2147483647)

    @model_validator(mode="after")
    def validate_visualization_context(self):
        if self.model_type == "hybrid_pennylane_torch" and self.quantum is not None:
            raise ValueError("Use the hybrid configuration for hybrid_pennylane_torch.")
        if self.model_type != "hybrid_pennylane_torch" and self.hybrid is not None:
            raise ValueError("Hybrid configuration is only valid for hybrid_pennylane_torch.")
        if self.dataset_version_id is not None and self.dataset_id is None and self.experiment_id is None:
            raise ValueError("A dataset version requires a dataset or experiment context.")
        dimension = (
            self.hybrid.qubits if self.model_type == "hybrid_pennylane_torch" and self.hybrid
            else self.quantum.qubits if self.quantum
            else HybridModelConfig().qubits if self.model_type == "hybrid_pennylane_torch"
            else QuantumConfig().qubits
        )
        names = self.representation_context.selected_feature_names if self.representation_context else None
        if names is not None and len(names) != dimension:
            raise ValueError("Selected feature names must match the configured encoded dimension.")
        return self


class QuantumVisualizationSimulationRequest(QuantumVisualizationPreviewRequest):
    encoded_vector: list[float] = Field(min_length=2, max_length=8)
    simulation_stage: Literal["encoding", "full_model"] = "encoding"
    ansatz_parameters: list[float] | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_simulation_inputs(self):
        if self.model_type == "hybrid_pennylane_torch":
            raise ValueError("Hybrid simulation is unavailable without fitted model weights.")
        config = self.quantum or QuantumConfig()
        if len(self.encoded_vector) != config.qubits:
            raise ValueError("Encoded vector length must match the configured qubit count.")
        if self.model_type == "qsvc" and self.simulation_stage == "full_model":
            raise ValueError("QSVC uses feature-map kernel evaluation, not a variational ansatz.")
        if self.simulation_stage == "encoding" and self.ansatz_parameters is not None:
            raise ValueError("Ansatz parameters are only accepted for full_model simulation.")
        return self


class VisualizationFeatureMapping(Schema):
    feature_index: int
    feature_name: str | None = None
    qubit_index: int
    parameter_name: str | None = None


class VisualizationGate(Schema):
    gate_index: int
    name: str
    gate_type: str
    qubits: list[int]
    parameters: list[str] = Field(default_factory=list)
    control_qubits: list[int] = Field(default_factory=list)
    target_qubits: list[int] = Field(default_factory=list)


class VisualizationDatasetContext(Schema):
    status: Literal["AVAILABLE", "NOT_AVAILABLE", "INSUFFICIENT_REPRESENTATION"]
    dataset_id: str | None = None
    dataset_version_id: str | None = None
    dataset_name: str | None = None
    dataset_hash: str | None = None
    raw_feature_count: int | None = None
    raw_feature_names: list[str] | None = None
    represented_feature_count: int | None = None
    selected_feature_names: list[str] | None = None
    configured_input_features: list[str] | None = None
    representation_configuration: dict[str, Any] = Field(default_factory=dict)
    representation_status: Literal[
        "STRUCTURE_ONLY", "SIMULATION_AVAILABLE", "NOT_AVAILABLE", "INSUFFICIENT_REPRESENTATION"
    ]
    representation_source: str | None = None
    row_count: int | None = None
    experiment_id: str | None = None
    limitations: list[str] = Field(default_factory=list)


class VisualizationEncoding(Schema):
    status: Literal[
        "AVAILABLE", "STRUCTURE_ONLY", "SIMULATION_AVAILABLE", "NOT_AVAILABLE", "INSUFFICIENT_REPRESENTATION"
    ]
    method: str
    description: str
    feature_to_qubit_mapping: list[VisualizationFeatureMapping] = Field(default_factory=list)
    encoding_parameters: dict[str, Any] = Field(default_factory=dict)
    encoded_dimension: int | None = None
    angle_scaling: bool | None = None
    limitations: list[str] = Field(default_factory=list)


class VisualizationCircuit(Schema):
    model_type: str
    provider_id: str
    backend_id: str
    execution_mode: str
    execution_kind: str
    hardware_available: bool
    qubits: int | None = None
    logical_depth: int | None = None
    parameter_count: int | None = None
    gate_counts: dict[str, int] = Field(default_factory=dict)
    total_gates: int | None = None
    gate_sequence: list[VisualizationGate] = Field(default_factory=list)
    circuit_text: str | None = None
    feature_map: str | None = None
    ansatz: str | None = None
    entanglement_strategy: str | None = None
    measurement_path: str | None = None
    output_semantics: str | None = None
    limitation: str | None = None


class VisualizationState(Schema):
    status: Literal[
        "AVAILABLE", "STRUCTURE_ONLY", "SIMULATION_AVAILABLE", "NOT_AVAILABLE", "NOT_APPLICABLE",
        "INSUFFICIENT_REPRESENTATION"
    ]
    execution_source: str | None = None
    simulator: str | None = None
    backend_id: str | None = None
    circuit_scope: str | None = None
    input_sample_count: int | None = None
    basis_states: list[str] | None = None
    amplitude_real: list[float] | None = None
    amplitude_imaginary: list[float] | None = None
    amplitude_magnitude: list[float] | None = None
    phase: list[float | None] | None = None
    probability: list[float] | None = None
    normalized_probability: list[float] | None = None
    measurement_counts: dict[str, int] | None = None
    shots: int | None = None
    limitations: list[str] = Field(default_factory=list)


class VisualizationBlochQubit(Schema):
    qubit_index: int
    x: float
    y: float
    z: float
    polar_angle: float | None
    azimuth: float | None
    purity: float
    state_representation_status: str


class VisualizationBloch(Schema):
    status: Literal["AVAILABLE", "NOT_AVAILABLE", "NOT_APPLICABLE"]
    representation: str | None = None
    qubits: list[VisualizationBlochQubit] | None = None
    limitation: str | None = None


class VisualizationEntanglement(Schema):
    status: Literal["AVAILABLE", "STRUCTURE_ONLY", "NOT_AVAILABLE", "NOT_APPLICABLE"]
    indicator: bool | None = None
    participating_qubits: list[int] | None = None
    method: str | None = None
    reduced_state_measures: list[dict[str, float | int]] | None = None
    limitations: list[str] = Field(default_factory=list)


class VisualizationMeasurement(Schema):
    status: Literal["AVAILABLE", "STRUCTURE_ONLY", "NOT_AVAILABLE", "NOT_APPLICABLE"]
    method: str | None = None
    output_semantics: str | None = None
    counts: dict[str, int] | None = None
    shots: int | None = None
    limitations: list[str] = Field(default_factory=list)


class VisualizationResource(Schema):
    status: Literal["AVAILABLE", "NOT_AVAILABLE"]
    logical_qubits: int | None = None
    circuit_depth: int | None = None
    total_gates: int | None = None
    parameterized_gates: int | None = None
    entangling_gates: int | None = None
    shots: int | None = None
    sample_count: int | None = None
    feature_dimension: int | None = None
    optimizer_iterations: int | None = None
    resource_category: str | None = None
    bounded_policy_status: str
    backend_availability: str
    simulator_type: str
    policy_version: str
    limitations: list[str] = Field(default_factory=list)


class VisualizationProvider(Schema):
    provider_id: str
    display_name: str
    provider_type: str
    availability: str
    backend_id: str
    backend_type: str
    backend_availability: str
    execution_mode: str
    hardware_available: bool


class HybridArchitecture(Schema):
    input_path: list[str]
    quantum_operations: list[str]
    output_path: list[str]
    classical_hidden_dimensions: list[int] | None = None
    classical_activation: str | None = None
    provider_id: str
    backend_id: str
    limitation: str


class QuantumVisualizationContract(Schema):
    schema_version: str
    request_fingerprint: str
    status: Literal["AVAILABLE", "STRUCTURE_ONLY", "SIMULATION_AVAILABLE", "NOT_AVAILABLE"]
    model_type: str
    dataset_context: VisualizationDatasetContext
    encoding: VisualizationEncoding
    circuit: VisualizationCircuit
    provider: VisualizationProvider
    state: VisualizationState
    bloch: VisualizationBloch
    entanglement: VisualizationEntanglement
    measurement: VisualizationMeasurement
    resources: VisualizationResource
    hybrid_architecture: HybridArchitecture | None = None
    limitations: list[str] = Field(default_factory=list)
