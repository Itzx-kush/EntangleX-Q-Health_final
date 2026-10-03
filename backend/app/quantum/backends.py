"""Backward-compatible facade over the provider architecture."""
from __future__ import annotations

from abc import ABC, abstractmethod
from ..api.schemas import QuantumConfig
from ..utils.errors import AppError
from .service import service


def availability() -> dict:
    health = service.registry.get("qiskit_local").health_check()
    return {
        "packages_present": health["packages_present"],
        "available": health["availability"] == "AVAILABLE",
        "runtime_verified": health["runtime_verified"],
        "execution": health["execution"],
        "provider_id": "qiskit_local",
    }


def require_quantum() -> None:
    if not availability()["available"]:
        raise AppError("quantum_dependencies_missing", "Install backend/requirements-quantum.txt in the backend environment before requesting quantum operations.", 503)


class QuantumBackend(ABC):
    """Compatibility adapter retained for callers outside the research layer."""
    @abstractmethod
    def sampler(self): ...
    @abstractmethod
    def pass_manager(self): ...
    @abstractmethod
    def metadata(self) -> dict: ...


class ProviderBackend(QuantumBackend):
    def __init__(self, config: QuantumConfig, seed: int):
        self.runtime = service.prepare_model_runtime(config.provider_id, config.backend, config.model_dump(), seed)
    def sampler(self):
        return self.runtime.sampler
    def pass_manager(self):
        return self.runtime.pass_manager
    def metadata(self) -> dict:
        return dict(self.runtime.metadata)


class StatevectorBackend(ProviderBackend):
    pass


class AerBackend(ProviderBackend):
    pass


def make_backend(config: QuantumConfig, seed: int) -> QuantumBackend:
    require_quantum()
    return StatevectorBackend(config, seed) if config.backend == "statevector" else AerBackend(config, seed)
