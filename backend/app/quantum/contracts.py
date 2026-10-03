"""Provider-neutral contracts for quantum execution and provenance."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class ProviderType(str, Enum):
    LOCAL_SIMULATOR = "LOCAL_SIMULATOR"
    REMOTE_SIMULATOR = "REMOTE_SIMULATOR"
    HARDWARE = "HARDWARE"
    CUSTOM = "CUSTOM"


class CapabilitySupport(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"


class ExecutionStatus(str, Enum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class ProviderAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    MISCONFIGURED = "MISCONFIGURED"
    DISABLED = "DISABLED"
    UNKNOWN = "UNKNOWN"


class ErrorCategory(str, Enum):
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    INVALID_CIRCUIT = "INVALID_CIRCUIT"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    TRANSIENT_ERROR = "TRANSIENT_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass(frozen=True)
class BackendCapabilities:
    supports_sampling: CapabilitySupport = CapabilitySupport.UNKNOWN
    supports_statevector: CapabilitySupport = CapabilitySupport.UNKNOWN
    supports_estimator: CapabilitySupport = CapabilitySupport.UNKNOWN
    supports_shots: CapabilitySupport = CapabilitySupport.UNKNOWN
    supports_noise_model: CapabilitySupport = CapabilitySupport.UNKNOWN
    supports_hardware_execution: CapabilitySupport = CapabilitySupport.UNSUPPORTED
    supports_async_jobs: CapabilitySupport = CapabilitySupport.UNKNOWN
    supports_cancellation: CapabilitySupport = CapabilitySupport.UNKNOWN
    supports_batching: CapabilitySupport = CapabilitySupport.UNKNOWN
    supports_gradients: CapabilitySupport = CapabilitySupport.UNKNOWN
    supports_parameterized_circuits: CapabilitySupport = CapabilitySupport.UNKNOWN
    max_qubits: int | None = None
    max_shots: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {key: value.value if isinstance(value, Enum) else value for key, value in self.__dict__.items()}


@dataclass(frozen=True)
class BackendDescriptor:
    backend_id: str
    display_name: str
    provider_id: str
    backend_type: str
    available: bool
    capabilities: BackendCapabilities

    def as_dict(self) -> dict[str, Any]:
        return {
            "backend_id": self.backend_id,
            "display_name": self.display_name,
            "provider_id": self.provider_id,
            "backend_type": self.backend_type,
            "available": self.available,
            "capabilities": self.capabilities.as_dict(),
        }


@dataclass(frozen=True)
class ExecutionRequest:
    circuit: Any | None = None
    circuits: Sequence[Any] = field(default_factory=tuple)
    shots: int | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)
    backend_id: str = "statevector"
    execution_mode: str = "local_simulator"
    noise_configuration: Mapping[str, Any] = field(default_factory=dict)
    transpile_configuration: Mapping[str, Any] = field(default_factory=dict)
    seed: int | None = None
    options: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionResult:
    status: ExecutionStatus
    provider_id: str
    backend_id: str
    job_id: str | None = None
    counts: Mapping[str, int] | None = None
    probabilities: Mapping[str, float] | None = None
    observables: Sequence[float] | None = None
    shots: int | None = None
    execution_time: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    error: Mapping[str, Any] | None = None
    raw_result_reference: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.__dict__,
            "status": self.status.value,
            "counts": dict(self.counts) if self.counts is not None else None,
            "probabilities": dict(self.probabilities) if self.probabilities is not None else None,
            "observables": list(self.observables) if self.observables is not None else None,
            "metadata": dict(self.metadata),
            "error": dict(self.error) if self.error is not None else None,
        }
