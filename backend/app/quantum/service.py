"""Application-facing quantum execution service; research code depends here."""
from __future__ import annotations

from typing import Any, Mapping
from .contracts import CapabilitySupport, ErrorCategory, ExecutionRequest, ExecutionResult
from .errors import QuantumProviderError
from .fingerprint import configuration_fingerprint
from .providers.base import ModelRuntime
from .registry import ProviderRegistry, registry


class QuantumExecutionService:
    def __init__(self, provider_registry: ProviderRegistry = registry):
        self.registry = provider_registry

    def list_providers(self) -> list[dict[str, Any]]:
        return [provider.descriptor() for provider in self.registry.list()]

    def provider(self, provider_id: str) -> dict[str, Any]:
        return self.registry.get(provider_id).descriptor()

    def list_backends(self, provider_id: str) -> list[dict[str, Any]]:
        return [item.as_dict() for item in self.registry.get(provider_id).list_backends()]

    def prepare_model_runtime(self, provider_id: str, backend_id: str, configuration: Mapping[str, Any], seed: int) -> ModelRuntime:
        return self.registry.get(provider_id).create_model_runtime(backend_id, configuration, seed)

    def run(self, provider_id: str, request: ExecutionRequest) -> ExecutionResult:
        return self.registry.get(provider_id).run(request)

    def preflight(self, provider_id: str, backend_id: str, configuration: Mapping[str, Any], requested_capabilities: list[str] | None = None) -> dict[str, Any]:
        provider = self.registry.get(provider_id)
        backend = provider.get_backend(backend_id)
        blockers = provider.validate_config(backend_id, configuration)
        warnings: list[str] = []
        capabilities = backend.capabilities.as_dict()
        for requested in requested_capabilities or []:
            support = capabilities.get(requested, CapabilitySupport.UNKNOWN.value)
            if support == CapabilitySupport.UNSUPPORTED.value:
                blockers.append(f"unsupported_capability:{requested}")
            elif support == CapabilitySupport.UNKNOWN.value:
                warnings.append(f"unknown_capability:{requested}")
        safe_config = {"provider_id": provider_id, "backend_id": backend_id, **dict(configuration)}
        return {
            "status": "BLOCKED" if blockers else "READY",
            "provider_id": provider_id,
            "backend_id": backend_id,
            "execution_mode": "local_simulator",
            "blockers": sorted(set(blockers)),
            "warnings": sorted(set(warnings)),
            "capabilities": capabilities,
            "configuration_fingerprint": configuration_fingerprint(safe_config),
        }

    def health(self) -> dict[str, Any]:
        return {"providers": [provider.health_check() for provider in self.registry.list()]}

    def execution_plan(self, configuration: Mapping[str, Any]) -> list[dict[str, Any]]:
        """Safe provider provenance captured when a run is queued."""
        plans: list[dict[str, Any]] = []
        models = set(configuration.get("models", []))
        if models.intersection({"vqc", "qsvc", "qnn"}):
            quantum = dict(configuration.get("quantum", {}))
            plans.append(self.preflight(
                str(quantum.get("provider_id", "qiskit_local")),
                str(quantum.get("backend", "statevector")),
                quantum,
            ))
        if "hybrid_pennylane_torch" in models:
            hybrid = dict(configuration.get("hybrid", {}))
            plans.append(self.preflight(
                str(hybrid.get("provider_id", "pennylane_local")),
                str(hybrid.get("backend", "default.qubit")),
                hybrid,
            ))
        return plans


service = QuantumExecutionService()
