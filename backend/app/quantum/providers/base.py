"""Adapter contract implemented by each quantum execution provider."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping
from ..contracts import BackendDescriptor, ExecutionRequest, ExecutionResult, ProviderAvailability, ProviderType


@dataclass(frozen=True)
class ModelRuntime:
    metadata: Mapping[str, Any]
    sampler: Any = None
    pass_manager: Any = None
    native_context: Any = None


class QuantumProvider(ABC):
    provider_id: str
    provider_name: str
    provider_type: ProviderType
    enabled: bool = True

    @abstractmethod
    def list_backends(self) -> list[BackendDescriptor]: ...

    def get_backend(self, backend_id: str) -> BackendDescriptor:
        from ..errors import QuantumProviderError
        from ..contracts import ErrorCategory
        match = next((item for item in self.list_backends() if item.backend_id == backend_id), None)
        if match is None:
            raise QuantumProviderError(ErrorCategory.CONFIGURATION_ERROR, "The requested quantum backend is not registered.")
        return match

    @abstractmethod
    def validate_config(self, backend_id: str, configuration: Mapping[str, Any]) -> list[str]: ...

    @abstractmethod
    def create_model_runtime(self, backend_id: str, configuration: Mapping[str, Any], seed: int) -> ModelRuntime: ...

    @abstractmethod
    def run(self, request: ExecutionRequest) -> ExecutionResult: ...

    @abstractmethod
    def health_check(self) -> dict[str, Any]: ...

    def cancel(self, job_id: str) -> bool:
        from ..errors import QuantumProviderError
        from ..contracts import ErrorCategory
        raise QuantumProviderError(ErrorCategory.UNSUPPORTED_OPERATION, "Cancellation is not supported by this provider.")

    def estimate_resources(self, request: ExecutionRequest) -> dict[str, Any]:
        circuit = request.circuit or (request.circuits[0] if request.circuits else None)
        return {
            "status": "ESTIMATED",
            "qubits": getattr(circuit, "num_qubits", None),
            "logical_depth": circuit.depth() if circuit is not None and hasattr(circuit, "depth") else None,
            "shots": request.shots,
            "note": "Logical estimate only; not observed hardware cost.",
        }

    def descriptor(self) -> dict[str, Any]:
        health = self.health_check()
        return {
            "provider_id": self.provider_id,
            "display_name": self.provider_name,
            "provider_type": self.provider_type.value,
            "enabled": self.enabled,
            "availability": health.get("availability", ProviderAvailability.UNKNOWN.value),
            "backends": [backend.as_dict() for backend in self.list_backends()],
        }
