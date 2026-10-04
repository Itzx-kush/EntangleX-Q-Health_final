"""Truthful, bounded data assembly for the Quantum Lab visualization API."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from sqlalchemy import select

from ..api.schemas import HybridModelConfig, QuantumConfig, ResourceAdvisorRequest
from ..database import session_scope
from ..storage.entities import Dataset, DatasetVersion, Experiment
from ..utils.errors import AppError
from .circuits import circuit_artifacts
from .contracts import ErrorCategory, ExecutionRequest, ExecutionStatus
from .errors import QuantumProviderError
from .fingerprint import configuration_fingerprint
from .resource_advisor import POLICY_VERSION, advise_resources, resource_policy
from .schemas import (
    HybridArchitecture,
    QuantumVisualizationContract,
    QuantumVisualizationPreviewRequest,
    QuantumVisualizationSimulationRequest,
    VisualizationBloch,
    VisualizationBlochQubit,
    VisualizationCircuit,
    VisualizationDatasetContext,
    VisualizationEncoding,
    VisualizationEntanglement,
    VisualizationFeatureMapping,
    VisualizationGate,
    VisualizationMeasurement,
    VisualizationProvider,
    VisualizationResource,
    VisualizationState,
)
from .service import service


CONTRACT_VERSION = "quantum-visualization-v1"
MAX_STATEVECTOR_QUBITS = 6
MAX_RETURNED_GATES = 512
MAX_AER_SHOTS = 4096


def _provider_error(exc: QuantumProviderError) -> AppError:
    codes = {
        ErrorCategory.CONFIGURATION_ERROR: "quantum_configuration_invalid",
        ErrorCategory.BACKEND_UNAVAILABLE: "quantum_backend_unavailable",
        ErrorCategory.INVALID_CIRCUIT: "quantum_visualization_invalid_context",
        ErrorCategory.RESOURCE_LIMIT: "quantum_resource_limit",
        ErrorCategory.UNSUPPORTED_OPERATION: "quantum_simulation_unavailable",
    }
    code = codes.get(exc.category, "quantum_backend_unavailable")
    status = 422 if exc.category in {ErrorCategory.CONFIGURATION_ERROR, ErrorCategory.INVALID_CIRCUIT} else 503
    if exc.category is ErrorCategory.RESOURCE_LIMIT:
        status = 413
    return AppError(code, exc.safe_message, status)


def _request_config(request: QuantumVisualizationPreviewRequest) -> tuple[QuantumConfig | None, HybridModelConfig | None]:
    if request.model_type == "hybrid_pennylane_torch":
        return None, request.hybrid or HybridModelConfig()
    return request.quantum or QuantumConfig(), None


def _load_dataset_context(request: QuantumVisualizationPreviewRequest) -> VisualizationDatasetContext:
    dataset_id = str(request.dataset_id) if request.dataset_id else None
    experiment_id = str(request.experiment_id) if request.experiment_id else None
    version_id = str(request.dataset_version_id) if request.dataset_version_id else None

    if not dataset_id and not experiment_id:
        representation = request.representation_context
        return VisualizationDatasetContext(
            status="NOT_AVAILABLE",
            representation_status="STRUCTURE_ONLY" if representation else "NOT_AVAILABLE",
            selected_feature_names=representation.selected_feature_names if representation else None,
            configured_input_features=None,
            representation_configuration={},
            represented_feature_count=(
                len(representation.selected_feature_names)
                if representation and representation.selected_feature_names is not None
                else None
            ),
            representation_source=representation.source if representation else None,
            limitations=[
                "No registered dataset or experiment context was supplied.",
                "No preprocessing or dataset-value encoding is performed by this endpoint.",
            ],
        )

    with session_scope() as session:
        experiment = None
        experiment_config: dict[str, Any] = {}
        if experiment_id:
            experiment = session.get(Experiment, experiment_id)
            if experiment is None:
                raise AppError(
                    "quantum_visualization_invalid_context",
                    "The supplied experiment context does not exist.",
                    404,
                )
            if dataset_id and dataset_id != experiment.dataset_id:
                raise AppError(
                    "quantum_visualization_invalid_context",
                    "The supplied dataset and experiment contexts do not match.",
                    422,
                )
            dataset_id = experiment.dataset_id
            experiment_config = dict(experiment.config or {})
            if version_id is None:
                version_value = experiment_config.get("dataset_version_id")
                version_id = str(version_value) if version_value else None

        dataset = session.get(Dataset, dataset_id)
        if dataset is None:
            raise AppError(
                "quantum_visualization_invalid_context",
                "The supplied dataset context does not exist.",
                404,
            )

        version = None
        if version_id:
            version = session.scalar(
                select(DatasetVersion).where(
                    DatasetVersion.id == version_id,
                    DatasetVersion.dataset_id == dataset.id,
                )
            )
            if version is None:
                raise AppError(
                    "quantum_visualization_invalid_context",
                    "The supplied dataset version does not belong to the selected dataset.",
                    404,
                )
        elif dataset.current_version_id:
            version = session.get(DatasetVersion, dataset.current_version_id)

        provenance = (version.provenance if version else None) or dataset.provenance or {}
        raw_features = provenance.get("features")
        if not isinstance(raw_features, list) or not all(isinstance(name, str) for name in raw_features):
            raw_features = None
        row_count = version.row_count if version else provenance.get("row_count")
        feature_count = (
            version.feature_count if version
            else len(raw_features) if raw_features is not None
            else provenance.get("feature_count")
        )
        data_hash = version.content_sha256 if version else dataset.sha256
        resolved_version_id = version.id if version else None
        # Copy only scalar/list metadata out of the session; this function never loads,
        # preprocesses, or mutates the stored dataset.
        raw_feature_names = list(raw_features) if raw_features is not None else None
        configured_features = experiment_config.get("features")
        if not isinstance(configured_features, list) or not all(isinstance(name, str) for name in configured_features):
            configured_features = None
        configured_pipeline = experiment_config.get("pipeline")
        if not isinstance(configured_pipeline, dict):
            configured_pipeline = {}
        representation_configuration = {
            "source": "experiment.config.pipeline" if experiment_config else None,
            "selection": configured_pipeline.get("selection"),
            "k_features": configured_pipeline.get("k_features"),
            "configured_pca_components": configured_pipeline.get("pca_components"),
            "pca_whiten": configured_pipeline.get("pca_whiten"),
            "angle_scaling": configured_pipeline.get("angle_scaling"),
        }

    representation = request.representation_context
    selected_names = representation.selected_feature_names if representation else None
    return VisualizationDatasetContext(
        status="AVAILABLE",
        dataset_id=dataset_id,
        dataset_version_id=resolved_version_id,
        dataset_name=dataset.name,
        dataset_hash=data_hash,
        raw_feature_count=feature_count if isinstance(feature_count, int) else None,
        raw_feature_names=raw_feature_names,
        represented_feature_count=len(selected_names) if selected_names is not None else None,
        selected_feature_names=selected_names,
        representation_status="STRUCTURE_ONLY",
        representation_source=(
            representation.source if representation
            else "experiment.config.pipeline" if experiment_config else None
        ),
        configured_input_features=configured_features,
        representation_configuration=representation_configuration,
        row_count=row_count if isinstance(row_count, int) else None,
        experiment_id=experiment_id,
        limitations=[
            "Registered dataset metadata is authoritative; this request does not preprocess or read feature values.",
            "Feature-name context supplied by the caller is descriptive and does not prove a transformed representation exists.",
        ],
    )


def _provider_context(provider_id: str, backend_id: str) -> tuple[VisualizationProvider, dict[str, Any]]:
    try:
        descriptor = service.provider(provider_id)
    except QuantumProviderError as exc:
        raise _provider_error(exc) from exc
    backend = next((item for item in descriptor["backends"] if item["backend_id"] == backend_id), None)
    if backend is None:
        raise AppError("quantum_configuration_invalid", "The selected backend is not registered for this provider.", 422)
    available = bool(backend["available"])
    return (
        VisualizationProvider(
            provider_id=provider_id,
            display_name=descriptor["display_name"],
            provider_type=descriptor["provider_type"],
            availability=descriptor["availability"],
            backend_id=backend_id,
            backend_type=backend["backend_type"],
            backend_availability="AVAILABLE" if available else "UNAVAILABLE",
            execution_mode="local_simulator",
            hardware_available=backend["backend_type"] == "HARDWARE" and available,
        ),
        backend,
    )


def _require_available_backend(provider_id: str, backend_id: str) -> None:
    _provider, backend = _provider_context(provider_id, backend_id)
    if not backend["available"]:
        raise AppError(
            "quantum_dependency_unavailable",
            "The selected local simulator backend is unavailable in this runtime.",
            503,
        )


def _feature_mappings(
    feature_map: Any,
    feature_names: list[str] | None,
    qubits: int,
) -> list[VisualizationFeatureMapping]:
    parameters = sorted(feature_map.parameters, key=lambda parameter: parameter.name)
    result = []
    for index in range(qubits):
        result.append(VisualizationFeatureMapping(
            feature_index=index,
            feature_name=feature_names[index] if feature_names and index < len(feature_names) else None,
            qubit_index=index,
            parameter_name=parameters[index].name if index < len(parameters) else None,
        ))
    return result


def _architecture(model_type: str, provider_id: str, backend_id: str, hybrid: HybridModelConfig | None) -> HybridArchitecture:
    if model_type == "hybrid_pennylane_torch":
        assert hybrid is not None
        return HybridArchitecture(
            input_path=["classical input features", "AngleEmbedding(Y)"],
            quantum_operations=["StronglyEntanglingLayers", "PauliZ expectation per qubit"],
            output_path=["PyTorch classical output head", "positive-class sigmoid probability"],
            classical_hidden_dimensions=list(hybrid.classical_hidden_dimensions),
            classical_activation=hybrid.classical_activation,
            provider_id=provider_id,
            backend_id=backend_id,
            limitation="Architecture is read from the existing model implementation; no fitted weights, outputs, or sample state are generated.",
        )
    if model_type == "qsvc":
        return HybridArchitecture(
            input_path=["processed feature vector", "ZZFeatureMap"],
            quantum_operations=["ComputeUncompute fidelity kernel"],
            output_path=["quantum kernel matrix", "classical QSVC decision function"],
            provider_id=provider_id,
            backend_id=backend_id,
            limitation="Kernel behavior is represented separately from VQC; a feature-map circuit alone does not execute kernel pairs.",
        )
    if model_type == "qnn":
        return HybridArchitecture(
            input_path=["processed feature vector", "ZZFeatureMap", "RealAmplitudes"],
            quantum_operations=["SamplerQNN", "computational-basis sampling", "parity aggregation"],
            output_path=["NeuralNetworkClassifier", "two-class output"],
            provider_id=provider_id,
            backend_id=backend_id,
            limitation="This is the configured model path; preview does not train weights or produce class probabilities.",
        )
    return HybridArchitecture(
        input_path=["processed feature vector", "ZZFeatureMap", "RealAmplitudes"],
        quantum_operations=["VQC sampler evaluation"],
        output_path=["VQC class-probability output"],
        provider_id=provider_id,
        backend_id=backend_id,
        limitation="Preview does not train the variational parameters or produce class probabilities.",
    )


def _resource_section(
    *,
    model_type: str,
    quantum: QuantumConfig | None,
    hybrid: HybridModelConfig | None,
    request: QuantumVisualizationPreviewRequest,
    dataset_context: VisualizationDatasetContext,
    provider: VisualizationProvider,
    backend: dict[str, Any],
    circuit: VisualizationCircuit,
) -> VisualizationResource:
    policy = resource_policy()
    advisor = None
    if quantum is not None and request.sample_count is not None:
        try:
            advisor = advise_resources(ResourceAdvisorRequest(
                model_type=model_type,
                quantum=quantum,
                feature_dimension=quantum.qubits,
                sample_count=request.sample_count,
                dataset_id=dataset_context.dataset_id,
                experiment_id=dataset_context.experiment_id,
            ))
        except (ValueError, TypeError):
            # Resource advice is optional context; never substitute a guessed profile.
            advisor = None
    advisor_profile = advisor["resource_profile"] if advisor else {}
    bounded_status = (
        advisor["budget_status"]["status"] if advisor
        else "NOT_EVALUATED"
    )
    return VisualizationResource(
        status="AVAILABLE" if circuit.qubits is not None else "NOT_AVAILABLE",
        logical_qubits=circuit.qubits,
        circuit_depth=circuit.logical_depth,
        total_gates=circuit.total_gates,
        parameterized_gates=(
            sum(bool(gate.parameters) for gate in circuit.gate_sequence)
            if circuit.gate_sequence and model_type != "hybrid_pennylane_torch"
            else None
        ),
        entangling_gates=(
            sum(len(gate.qubits) > 1 for gate in circuit.gate_sequence)
            if circuit.gate_sequence and model_type != "hybrid_pennylane_torch"
            else None
        ),
        shots=quantum.shots if quantum and quantum.backend == "aer" else None,
        sample_count=request.sample_count,
        feature_dimension=circuit.qubits,
        optimizer_iterations=quantum.maxiter if quantum and model_type in {"vqc", "qnn"} else None,
        resource_category=advisor_profile.get("circuit_complexity"),
        bounded_policy_status=bounded_status,
        backend_availability=provider.backend_availability,
        simulator_type=circuit.execution_kind,
        policy_version=policy["version"],
        limitations=[
            "Resource categories come from the existing resource advisor only when a sample count is explicitly supplied.",
            "Dataset row count is metadata and is not assumed to equal the future training sample count.",
            "Logical estimates are not hardware cost or timing measurements.",
        ],
    )


class QuantumVisualizationService:
    def preview(
        self,
        request: QuantumVisualizationPreviewRequest,
    ) -> tuple[QuantumVisualizationContract, dict[str, Any] | None]:
        quantum, hybrid = _request_config(request)
        dataset_context = _load_dataset_context(request)
        if quantum is not None:
            provider_id, backend_id = quantum.provider_id, quantum.backend
        else:
            assert hybrid is not None
            provider_id, backend_id = hybrid.provider_id, hybrid.backend
        provider, backend_info = _provider_context(provider_id, backend_id)

        artifacts = None
        if quantum is not None:
            _require_available_backend(provider_id, backend_id)
            try:
                artifacts = circuit_artifacts(quantum, request.model_type, request.seed)
            except QuantumProviderError as exc:
                raise _provider_error(exc) from exc
            except AppError as exc:
                if exc.code in {"quantum_dependencies_missing", "quantum_backend_unavailable"}:
                    raise AppError(
                        "quantum_dependency_unavailable",
                        "The required local Qiskit visualization dependencies are unavailable.",
                        503,
                    ) from exc
                raise
            gates = [VisualizationGate.model_validate(gate) for gate in artifacts["gate_sequence"]]
            if len(gates) > MAX_RETURNED_GATES:
                raise AppError(
                    "quantum_resource_limit",
                    f"Circuit visualization exceeds the {MAX_RETURNED_GATES}-gate response limit.",
                    413,
                )
            description = artifacts["description"]
            circuit = VisualizationCircuit(
                model_type=request.model_type,
                provider_id=provider_id,
                backend_id=backend_id,
                execution_mode="local_simulator",
                execution_kind=description["execution_kind"],
                hardware_available=provider.hardware_available,
                qubits=description["qubits"],
                logical_depth=description["logical_depth"],
                parameter_count=description["parameter_count"],
                gate_counts=description["gate_counts"],
                total_gates=len(gates),
                gate_sequence=gates,
                circuit_text=description["text"],
                feature_map="ZZFeatureMap",
                ansatz="RealAmplitudes" if request.model_type in {"vqc", "qnn"} else None,
                entanglement_strategy=quantum.entanglement,
                measurement_path={
                    "vqc": "Qiskit sampler class-probability path",
                    "qnn": "SamplerQNN parity-aggregated computational-basis probabilities",
                    "qsvc": "ComputeUncompute fidelity-kernel evaluation",
                }[request.model_type],
                output_semantics={
                    "vqc": "VQC classifier class probabilities",
                    "qnn": "two-class parity-aggregated sampler output",
                    "qsvc": "quantum-kernel decision function",
                }[request.model_type],
                limitation=description["limitation"],
            )
            encoding = VisualizationEncoding(
                status="STRUCTURE_ONLY",
                method="ZZFeatureMap",
                description="The existing Qiskit ZZFeatureMap encodes one configured feature parameter per qubit.",
                feature_to_qubit_mapping=_feature_mappings(
                    artifacts["feature_map"],
                    dataset_context.selected_feature_names,
                    quantum.qubits,
                ),
                encoding_parameters={
                    "feature_map_repetitions": quantum.feature_map_reps,
                    "entanglement": quantum.entanglement,
                    "parameter_names": [
                        parameter.name
                        for parameter in sorted(artifacts["feature_map"].parameters, key=lambda item: item.name)
                    ],
                    "dataset_representation_configuration": dataset_context.representation_configuration,
                },
                encoded_dimension=quantum.qubits,
                angle_scaling=(
                    request.representation_context.angle_scaling
                    if request.representation_context and request.representation_context.angle_scaling is not None
                    else dataset_context.representation_configuration.get("angle_scaling")
                ),
                limitations=[
                    "No dataset preprocessing or value binding occurs in preview.",
                    "Circuit parameters describe the backend circuit; no trained ansatz values are inferred.",
                ],
            )
            state = VisualizationState(
                status="STRUCTURE_ONLY",
                limitations=["Preview does not execute the circuit or imply a statevector or measurement result."],
            )
            bloch = VisualizationBloch(
                status="NOT_AVAILABLE",
                limitation="Bloch vectors require an actual simulated state; circuit structure alone is insufficient.",
            )
            entanglement = VisualizationEntanglement(
                status="STRUCTURE_ONLY",
                limitations=["Gate connectivity alone does not establish state-dependent entanglement."],
            )
            measurement = VisualizationMeasurement(
                status="STRUCTURE_ONLY",
                method=circuit.measurement_path,
                output_semantics=circuit.output_semantics,
                limitations=["No circuit execution or training occurred during preview."],
            )
        else:
            assert hybrid is not None
            all_qubits = list(range(hybrid.qubits))
            gates = [
                VisualizationGate(
                    gate_index=0,
                    name="AngleEmbedding(Y)",
                    gate_type="encoding_template",
                    qubits=all_qubits,
                ),
                VisualizationGate(
                    gate_index=1,
                    name="StronglyEntanglingLayers",
                    gate_type="variational_template",
                    qubits=all_qubits,
                ),
            ]
            circuit = VisualizationCircuit(
                model_type=request.model_type,
                provider_id=provider_id,
                backend_id=backend_id,
                execution_mode="local_simulator",
                execution_kind="PennyLane default.qubit template (not executed)",
                hardware_available=provider.hardware_available,
                qubits=hybrid.qubits,
                logical_depth=None,
                parameter_count=None,
                gate_counts={},
                total_gates=None,
                gate_sequence=gates,
                circuit_text="AngleEmbedding(Y) → StronglyEntanglingLayers → PauliZ expectation per qubit",
                feature_map="AngleEmbedding(Y)",
                ansatz="StronglyEntanglingLayers",
                entanglement_strategy="StronglyEntanglingLayers template",
                measurement_path="PauliZ expectation value on each configured wire",
                output_semantics="Expectation vector passed through the PyTorch head and sigmoid positive-class probability.",
                limitation="High-level template derived from the existing model code. No PennyLane decomposition, fitted weights, or state are generated.",
            )
            encoding = VisualizationEncoding(
                status="STRUCTURE_ONLY",
                method="AngleEmbedding(Y)",
                description="The existing hybrid implementation applies AngleEmbedding with Y rotations across configured wires.",
                feature_to_qubit_mapping=[
                    VisualizationFeatureMapping(
                        feature_index=index,
                        feature_name=dataset_context.selected_feature_names[index]
                        if dataset_context.selected_feature_names else None,
                        qubit_index=index,
                    )
                    for index in range(hybrid.qubits)
                ],
                encoding_parameters={
                    "feature_map": hybrid.feature_map,
                    "rotation": "Y",
                    "quantum_layers": hybrid.quantum_layers,
                    "dataset_representation_configuration": dataset_context.representation_configuration,
                },
                encoded_dimension=hybrid.qubits,
                angle_scaling=(
                    request.representation_context.angle_scaling
                    if request.representation_context and request.representation_context.angle_scaling is not None
                    else dataset_context.representation_configuration.get("angle_scaling")
                ),
                limitations=[
                    "Feature-to-wire structure reflects the implemented AngleEmbedding call.",
                    "No dataset preprocessing, fitted weights, or circuit execution occurs during preview.",
                ],
            )
            state = VisualizationState(
                status="STRUCTURE_ONLY",
                limitations=["A hybrid state requires explicit encoded inputs and fitted quantum weights."],
            )
            bloch = VisualizationBloch(
                status="NOT_AVAILABLE",
                limitation="No reduced density matrices are computed for the unexecuted hybrid template.",
            )
            entanglement = VisualizationEntanglement(
                status="STRUCTURE_ONLY",
                limitations=["The entangling template is structural evidence, not proof of state entanglement."],
            )
            measurement = VisualizationMeasurement(
                status="STRUCTURE_ONLY",
                method=circuit.measurement_path,
                output_semantics=circuit.output_semantics,
                limitations=["No expectation values or positive-class probability were computed."],
            )

        architecture = _architecture(request.model_type, provider_id, backend_id, hybrid)
        contract = QuantumVisualizationContract(
            schema_version=CONTRACT_VERSION,
            request_fingerprint=configuration_fingerprint({
                "model_type": request.model_type,
                "quantum": quantum.model_dump(mode="json") if quantum else None,
                "hybrid": hybrid.model_dump(mode="json") if hybrid else None,
                "representation_context": (
                    request.representation_context.model_dump(mode="json")
                    if request.representation_context else None
                ),
                "provider_id": provider_id,
                "backend_id": backend_id,
                "seed": request.seed,
                "dataset_id": dataset_context.dataset_id,
                "dataset_version_id": dataset_context.dataset_version_id,
                "experiment_id": dataset_context.experiment_id,
            }),
            status="STRUCTURE_ONLY",
            model_type=request.model_type,
            dataset_context=dataset_context,
            encoding=encoding,
            circuit=circuit,
            provider=provider,
            state=state,
            bloch=bloch,
            entanglement=entanglement,
            measurement=measurement,
            resources=_resource_section(
                model_type=request.model_type,
                quantum=quantum,
                hybrid=hybrid,
                request=request,
                dataset_context=dataset_context,
                provider=provider,
                backend=backend_info,
                circuit=circuit,
            ),
            hybrid_architecture=architecture,
            limitations=[
                "This API provides structural information unless an explicit bounded simulation request is made.",
                "All execution reported here is local simulation; no quantum hardware is available.",
            ],
        )
        return contract, artifacts

    def simulate(self, request: QuantumVisualizationSimulationRequest) -> QuantumVisualizationContract:
        if request.model_type == "hybrid_pennylane_torch":
            raise AppError(
                "quantum_simulation_unavailable",
                "Hybrid simulation requires fitted PennyLane and PyTorch model weights and is not exposed by this endpoint.",
                422,
            )
        quantum = request.quantum or QuantumConfig()
        if quantum.qubits > MAX_STATEVECTOR_QUBITS:
            raise AppError(
                "quantum_resource_limit",
                f"Simulation is bounded to {MAX_STATEVECTOR_QUBITS} qubits (at most {1 << MAX_STATEVECTOR_QUBITS} amplitudes).",
                413,
            )
        policy_limits = resource_policy()["bounded_prototype_limits"]
        if quantum.feature_map_reps > policy_limits["feature_map_reps"]:
            raise AppError("quantum_resource_limit", "Feature-map repetitions exceed the bounded simulator policy.", 413)
        if request.simulation_stage == "full_model" and quantum.ansatz_reps > policy_limits["ansatz_reps"]:
            raise AppError("quantum_resource_limit", "Ansatz repetitions exceed the bounded simulator policy.", 413)
        if quantum.backend == "aer" and quantum.shots > MAX_AER_SHOTS:
            raise AppError("quantum_resource_limit", f"Aer simulation is bounded to {MAX_AER_SHOTS} shots.", 413)
        if quantum.noise_probability:
            raise AppError(
                "quantum_simulation_unavailable",
                "This visualization simulation path does not apply the configured Aer noise model; use noise_probability=0.",
                422,
            )
        _require_available_backend(quantum.provider_id, quantum.backend)
        contract, artifacts = self.preview(request)
        assert artifacts is not None
        if len(artifacts["gate_sequence"]) > MAX_RETURNED_GATES:
            raise AppError("quantum_resource_limit", "Circuit exceeds the bounded visualization gate limit.", 413)

        feature_parameters = sorted(artifacts["feature_map"].parameters, key=lambda item: item.name)
        bindings: dict[Any, float] = {
            parameter: float(value)
            for parameter, value in zip(feature_parameters, request.encoded_vector, strict=True)
        }
        if request.simulation_stage == "full_model" and request.model_type in {"vqc", "qnn"}:
            ansatz_parameters = sorted(artifacts["ansatz"].parameters, key=lambda item: item.name)
            supplied = request.ansatz_parameters
            if supplied is None or len(supplied) != len(ansatz_parameters):
                raise AppError(
                    "quantum_visualization_invalid_context",
                    f"full_model simulation requires exactly {len(ansatz_parameters)} explicit ansatz parameters.",
                    422,
                )
            bindings.update({
                parameter: float(value)
                for parameter, value in zip(ansatz_parameters, supplied, strict=True)
            })
            circuit = artifacts["circuit"].assign_parameters(bindings, inplace=False)
        else:
            circuit = artifacts["feature_map"].assign_parameters(bindings, inplace=False)

        shots = None
        if quantum.backend == "aer":
            circuit = circuit.copy()
            circuit.measure_all()
            shots = quantum.shots
        try:
            result = service.run(quantum.provider_id, ExecutionRequest(
                circuit=circuit,
                shots=shots,
                backend_id=quantum.backend,
                execution_mode="local_simulator",
                seed=request.seed,
            ))
        except QuantumProviderError as exc:
            raise _provider_error(exc) from exc
        if result.status is not ExecutionStatus.COMPLETED:
            raise AppError(
                "quantum_simulation_unavailable",
                "The selected local simulator did not return a completed result.",
                503,
            )

        request_fingerprint = configuration_fingerprint({
            "preview_fingerprint": contract.request_fingerprint,
            "encoded_vector": request.encoded_vector,
            "simulation_stage": request.simulation_stage,
            "ansatz_parameters": request.ansatz_parameters,
            "seed": request.seed,
        })
        if result.amplitudes is not None:
            amplitudes = list(result.amplitudes)
            probabilities = [float(abs(value) ** 2) for value in amplitudes]
            total_probability = math.fsum(probabilities)
            if not math.isfinite(total_probability) or total_probability <= 0:
                raise AppError("quantum_statevector_unavailable", "Simulator returned a non-normalizable statevector.", 503)
            normalized = [value / total_probability for value in probabilities]
            width = circuit.num_qubits
            basis = [format(index, f"0{width}b") for index in range(len(amplitudes))]
            real = [float(value.real) for value in amplitudes]
            imaginary = [float(value.imag) for value in amplitudes]
            magnitude = [float(abs(value)) for value in amplitudes]
            phases = [
                float(math.atan2(value.imag, value.real)) if abs(value) > 1e-15 else None
                for value in amplitudes
            ]
            bloch_qubits, reduced_measures = _reduced_states(amplitudes, width)
            entangled = any(item["linear_entropy"] > 1e-10 for item in reduced_measures)
            contract.state = VisualizationState(
                status="AVAILABLE",
                execution_source="local_simulator",
                simulator="qiskit_local",
                backend_id=quantum.backend,
                circuit_scope=request.simulation_stage if request.simulation_stage == "full_model" else "feature_map",
                input_sample_count=1,
                basis_states=basis,
                amplitude_real=real,
                amplitude_imaginary=imaginary,
                amplitude_magnitude=magnitude,
                phase=phases,
                probability=probabilities,
                normalized_probability=normalized,
                limitations=[
                    "Amplitudes and probabilities are from the Qiskit Statevector simulator for the explicitly supplied encoded vector.",
                    "Phase is undefined for exactly zero amplitudes and is returned as null for those basis states.",
                ],
            )
            contract.bloch = VisualizationBloch(
                status="AVAILABLE",
                representation="single-qubit reduced density matrices",
                qubits=bloch_qubits,
                limitation="Each Bloch vector is computed from the corresponding one-qubit reduced state of the simulated multi-qubit pure state.",
            )
            contract.entanglement = VisualizationEntanglement(
                status="AVAILABLE",
                indicator=entangled,
                participating_qubits=[
                    int(item["qubit_index"])
                    for item in reduced_measures
                    if item["linear_entropy"] > 1e-10
                ],
                method="one-qubit reduced-state linear entropy (1 - purity) for the simulated pure state",
                reduced_state_measures=reduced_measures,
                limitations=[
                    "This reports one-qubit-versus-rest entanglement from the simulated pure state; it is not a pairwise entanglement measure.",
                ],
            )
            contract.measurement = VisualizationMeasurement(
                status="AVAILABLE",
                method="exact computational-basis probabilities from Qiskit Statevector",
                output_semantics="Raw basis probabilities for the explicitly simulated circuit; no fitted classifier output was computed.",
                limitations=[
                    "Exact statevector probabilities are simulator outputs, not hardware measurements.",
                    "Fitted VQC/QNN/QSVC model outputs are not inferred from a structure-only preview.",
                ],
            )
        else:
            counts = dict(result.counts or {})
            probability_map = dict(result.probabilities or {})
            basis = sorted(probability_map, key=lambda state: int(state, 2))
            probabilities = [float(probability_map[state]) for state in basis]
            total_probability = math.fsum(probabilities)
            if not math.isfinite(total_probability) or total_probability <= 0:
                raise AppError("quantum_simulation_unavailable", "Simulator returned no valid measurement probability.", 503)
            contract.state = VisualizationState(
                status="AVAILABLE",
                execution_source="local_simulator",
                simulator="qiskit_aer",
                backend_id=quantum.backend,
                circuit_scope=request.simulation_stage if request.simulation_stage == "full_model" else "feature_map",
                input_sample_count=1,
                basis_states=basis,
                probability=probabilities,
                normalized_probability=[value / total_probability for value in probabilities],
                measurement_counts=counts,
                shots=result.shots,
                limitations=["Finite-shot counts and probabilities are Qiskit Aer local-simulator outputs."],
            )
            contract.bloch = VisualizationBloch(
                status="NOT_AVAILABLE",
                limitation="A computational-basis shot histogram does not determine phase or reduced-state Bloch vectors.",
            )
            contract.entanglement = VisualizationEntanglement(
                status="STRUCTURE_ONLY",
                limitations=["Finite-shot computational-basis counts alone do not establish state-dependent entanglement."],
            )
            contract.measurement = VisualizationMeasurement(
                status="AVAILABLE",
                method="finite-shot computational-basis measurement",
                output_semantics="Raw finite-shot basis counts for the explicitly simulated circuit; no fitted classifier output was computed.",
                counts=counts,
                shots=result.shots,
                limitations=[
                    "These are local simulator shots, not hardware measurements.",
                    "Fitted classifier outputs and decision functions were not computed.",
                ],
            )

        contract.request_fingerprint = request_fingerprint
        contract.status = "SIMULATION_AVAILABLE"
        contract.encoding.status = "SIMULATION_AVAILABLE"
        contract.dataset_context.representation_status = "SIMULATION_AVAILABLE"
        contract.dataset_context.representation_source = "request.encoded_vector"
        contract.dataset_context.represented_feature_count = len(request.encoded_vector)
        contract.resources.shots = result.shots
        return contract


def _reduced_states(
    amplitudes: list[complex],
    qubits: int,
) -> tuple[list[VisualizationBlochQubit], list[dict[str, float | int]]]:
    from qiskit.quantum_info import Statevector, partial_trace

    state = Statevector(np.asarray(amplitudes, dtype=complex))
    pauli_x = np.array([[0, 1], [1, 0]], dtype=complex)
    pauli_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    pauli_z = np.array([[1, 0], [0, -1]], dtype=complex)
    bloch: list[VisualizationBlochQubit] = []
    measures: list[dict[str, float | int]] = []
    for qubit_index in range(qubits):
        traced = [index for index in range(qubits) if index != qubit_index]
        reduced = np.asarray(partial_trace(state, traced).data, dtype=complex)
        x = float(np.trace(reduced @ pauli_x).real)
        y = float(np.trace(reduced @ pauli_y).real)
        z = float(np.trace(reduced @ pauli_z).real)
        purity = float(np.trace(reduced @ reduced).real)
        radius = math.sqrt(x * x + y * y + z * z)
        polar = math.atan2(math.sqrt(x * x + y * y), z) if radius > 1e-12 else None
        azimuth = math.atan2(y, x) if radius > 1e-12 else None
        bloch.append(VisualizationBlochQubit(
            qubit_index=qubit_index,
            x=x,
            y=y,
            z=z,
            polar_angle=polar,
            azimuth=azimuth,
            purity=purity,
            state_representation_status="AVAILABLE_REDUCED_SINGLE_QUBIT_STATE",
        ))
        measures.append({
            "qubit_index": qubit_index,
            "purity": purity,
            "linear_entropy": float(max(0.0, 1.0 - purity)),
        })
    return bloch, measures


visualization_service = QuantumVisualizationService()