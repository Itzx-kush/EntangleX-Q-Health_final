"""Adapter for the repository's existing PennyLane default.qubit execution path."""
from __future__ import annotations

from importlib.util import find_spec
from typing import Any, Mapping

from ..contracts import (
    BackendCapabilities, BackendDescriptor, CapabilitySupport, ErrorCategory,
    ExecutionRequest, ExecutionResult, ProviderAvailability, ProviderType,
)
from ..errors import QuantumProviderError
from ..fingerprint import configuration_fingerprint, safe_configuration
from .base import ModelRuntime, QuantumProvider


class PennyLaneLocalProvider(QuantumProvider):
    provider_id = "pennylane_local"
    provider_name = "PennyLane Local Simulator"
    provider_type = ProviderType.LOCAL_SIMULATOR

    def list_backends(self) -> list[BackendDescriptor]:
        return [BackendDescriptor(
            backend_id="default.qubit",
            display_name="PennyLane default.qubit",
            provider_id=self.provider_id,
            backend_type="LOCAL_SIMULATOR",
            available=find_spec("pennylane") is not None,
            capabilities=BackendCapabilities(
                supports_sampling=CapabilitySupport.SUPPORTED,
                supports_statevector=CapabilitySupport.UNKNOWN,
                supports_estimator=CapabilitySupport.SUPPORTED,
                supports_shots=CapabilitySupport.SUPPORTED,
                supports_noise_model=CapabilitySupport.UNSUPPORTED,
                supports_hardware_execution=CapabilitySupport.UNSUPPORTED,
                supports_async_jobs=CapabilitySupport.UNSUPPORTED,
                supports_cancellation=CapabilitySupport.UNSUPPORTED,
                supports_batching=CapabilitySupport.UNKNOWN,
                supports_gradients=CapabilitySupport.SUPPORTED,
                supports_parameterized_circuits=CapabilitySupport.SUPPORTED,
                max_qubits=None,
                max_shots=None,
            ),
        )]

    def validate_config(self, backend_id: str, configuration: Mapping[str, Any]) -> list[str]:
        backend = self.get_backend(backend_id)
        blockers = []
        if not backend.available:
            blockers.append("backend_dependencies_unavailable")
        qubits = configuration.get("qubits")
        if not isinstance(qubits, int) or not 2 <= qubits <= 8:
            blockers.append("qubits_out_of_range")
        return blockers

    def create_model_runtime(self, backend_id: str, configuration: Mapping[str, Any], seed: int) -> ModelRuntime:
        blockers = self.validate_config(backend_id, configuration)
        if blockers:
            category = ErrorCategory.BACKEND_UNAVAILABLE if "backend_dependencies_unavailable" in blockers else ErrorCategory.CONFIGURATION_ERROR
            raise QuantumProviderError(category, "The PennyLane local backend is not ready for this configuration.", provider_context={"blockers": blockers})
        try:
            import pennylane as qml
            device = qml.device(backend_id, wires=int(configuration["qubits"]), shots=None)
        except Exception as exc:
            raise QuantumProviderError(ErrorCategory.PROVIDER_ERROR, "The PennyLane local provider could not initialize.", provider_context={"exception_type": type(exc).__name__}) from exc
        safe = safe_configuration({
            "provider_id": self.provider_id, "backend_id": backend_id,
            "execution_mode": "local_simulator", "seed": seed, **dict(configuration),
        })
        return ModelRuntime(
            native_context=device,
            metadata={
                "provider_id": self.provider_id,
                "provider_name": self.provider_name,
                "provider_type": self.provider_type.value,
                "backend_id": backend_id,
                "backend": backend_id,
                "backend_type": "LOCAL_SIMULATOR",
                "execution_mode": "local_simulator",
                "execution_kind": "local PennyLane quantum simulation",
                "shots": None,
                "real_hardware": False,
                "capabilities_snapshot": self.get_backend(backend_id).capabilities.as_dict(),
                "provider_configuration": safe,
                "provider_configuration_fingerprint": configuration_fingerprint(safe),
                "seed_status": "APPLIED",
            },
        )

    def run(self, request: ExecutionRequest) -> ExecutionResult:
        raise QuantumProviderError(
            ErrorCategory.UNSUPPORTED_OPERATION,
            "Direct circuit submission is not supported by the PennyLane template adapter; execute the bound QNode runtime.",
        )

    def health_check(self) -> dict[str, Any]:
        present = find_spec("pennylane") is not None
        return {
            "provider_id": self.provider_id,
            "availability": ProviderAvailability.AVAILABLE.value if present else ProviderAvailability.UNAVAILABLE.value,
            "packages_present": {"pennylane": present},
            "runtime_verified": False,
            "execution": "local quantum simulation only; no hardware credentials or hardware execution",
        }
