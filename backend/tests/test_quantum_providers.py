"""Prompt 21 provider contracts, provenance, API and compatibility tests."""
from __future__ import annotations

import os
from typing import Any, Mapping
import pytest

from app.quantum.contracts import (
    BackendCapabilities, BackendDescriptor, CapabilitySupport, ErrorCategory,
    ExecutionRequest, ExecutionResult, ExecutionStatus, ProviderAvailability, ProviderType,
)
from app.quantum.errors import QuantumProviderError
from app.quantum.fingerprint import configuration_fingerprint, safe_configuration
from app.quantum.providers.base import ModelRuntime, QuantumProvider
from app.quantum.providers.qiskit_local import QiskitLocalProvider
from app.quantum.providers.pennylane_local import PennyLaneLocalProvider
from app.quantum.registry import ProviderRegistry
from app.quantum.service import QuantumExecutionService


class FakeProvider(QuantumProvider):
    provider_id = "fake"
    provider_name = "Fake local provider"
    provider_type = ProviderType.LOCAL_SIMULATOR

    def list_backends(self):
        return [BackendDescriptor(
            "fake_backend", "Fake backend", self.provider_id, "LOCAL_SIMULATOR", True,
            BackendCapabilities(
                supports_sampling=CapabilitySupport.SUPPORTED,
                supports_statevector=CapabilitySupport.UNKNOWN,
                supports_shots=CapabilitySupport.UNSUPPORTED,
            ),
        )]

    def validate_config(self, backend_id: str, configuration: Mapping[str, Any]):
        self.get_backend(backend_id)
        return ["invalid_test_configuration"] if configuration.get("invalid") else []

    def create_model_runtime(self, backend_id: str, configuration: Mapping[str, Any], seed: int):
        self.get_backend(backend_id)
        return ModelRuntime(metadata={"provider_id": self.provider_id, "backend_id": backend_id}, sampler="sampler")

    def run(self, request: ExecutionRequest):
        self.get_backend(request.backend_id)
        if request.circuit is None:
            raise QuantumProviderError(ErrorCategory.INVALID_CIRCUIT, "Circuit required.")
        return ExecutionResult(ExecutionStatus.COMPLETED, self.provider_id, request.backend_id, counts={"0": 1}, shots=1)

    def health_check(self):
        return {"provider_id": self.provider_id, "availability": ProviderAvailability.AVAILABLE.value}


def test_registry_creation_discovery_and_lookup():
    provider = FakeProvider()
    registry = ProviderRegistry([provider])
    assert registry.list() == [provider]
    assert registry.get("fake") is provider


def test_registry_rejects_duplicate_provider():
    registry = ProviderRegistry([FakeProvider()])
    with pytest.raises(QuantumProviderError) as caught:
        registry.register(FakeProvider())
    assert caught.value.category is ErrorCategory.CONFIGURATION_ERROR


def test_registry_unknown_provider_has_no_silent_fallback():
    registry = ProviderRegistry([FakeProvider()])
    with pytest.raises(QuantumProviderError, match="not registered"):
        registry.get("missing")


def test_backend_lookup_and_invalid_backend():
    provider = FakeProvider()
    assert provider.get_backend("fake_backend").provider_id == "fake"
    with pytest.raises(QuantumProviderError, match="backend"):
        provider.get_backend("missing")


def test_capability_unknown_is_preserved():
    capabilities = FakeProvider().get_backend("fake_backend").capabilities.as_dict()
    assert capabilities["supports_sampling"] == "SUPPORTED"
    assert capabilities["supports_statevector"] == "UNKNOWN"
    assert capabilities["supports_shots"] == "UNSUPPORTED"


def test_provider_descriptor_distinguishes_provider_and_backend():
    descriptor = FakeProvider().descriptor()
    assert descriptor["provider_id"] == "fake"
    assert descriptor["backends"][0]["backend_id"] == "fake_backend"
    assert descriptor["provider_type"] == "LOCAL_SIMULATOR"


def test_service_discovery_runtime_and_normalized_result():
    service = QuantumExecutionService(ProviderRegistry([FakeProvider()]))
    assert service.list_providers()[0]["display_name"] == "Fake local provider"
    runtime = service.prepare_model_runtime("fake", "fake_backend", {}, 42)
    assert runtime.sampler == "sampler"
    result = service.run("fake", ExecutionRequest(circuit=object(), backend_id="fake_backend"))
    assert result.as_dict()["status"] == "COMPLETED"
    assert result.as_dict()["counts"] == {"0": 1}


def test_preflight_ready_with_unknown_warning():
    service = QuantumExecutionService(ProviderRegistry([FakeProvider()]))
    result = service.preflight("fake", "fake_backend", {}, ["supports_sampling", "supports_statevector"])
    assert result["status"] == "READY"
    assert result["warnings"] == ["unknown_capability:supports_statevector"]


def test_preflight_blocks_unsupported_capability_and_bad_config():
    service = QuantumExecutionService(ProviderRegistry([FakeProvider()]))
    result = service.preflight("fake", "fake_backend", {"invalid": True}, ["supports_shots"])
    assert result["status"] == "BLOCKED"
    assert result["blockers"] == ["invalid_test_configuration", "unsupported_capability:supports_shots"]


def test_configuration_fingerprint_deterministic_and_order_independent():
    first = configuration_fingerprint({"backend": "aer", "shots": 128})
    second = configuration_fingerprint({"shots": 128, "backend": "aer"})
    assert first == second
    assert len(first) == 64


def test_fingerprint_and_safe_configuration_exclude_secrets():
    public = {"provider_id": "fake", "nested": {"shots": 128}}
    with_secrets = {**public, "api_token": "never-persist", "nested": {"shots": 128, "password": "nope"}}
    assert safe_configuration(with_secrets) == public
    assert configuration_fingerprint(with_secrets) == configuration_fingerprint(public)
    assert "never-persist" not in str(safe_configuration(with_secrets))


def test_configuration_change_changes_fingerprint():
    assert configuration_fingerprint({"shots": 128}) != configuration_fingerprint({"shots": 256})


def test_cancellation_is_explicitly_unsupported():
    with pytest.raises(QuantumProviderError) as caught:
        FakeProvider().cancel("job")
    assert caught.value.category is ErrorCategory.UNSUPPORTED_OPERATION


def test_malformed_execution_request_is_normalized():
    service = QuantumExecutionService(ProviderRegistry([FakeProvider()]))
    with pytest.raises(QuantumProviderError) as caught:
        service.run("fake", ExecutionRequest(backend_id="fake_backend"))
    assert caught.value.category is ErrorCategory.INVALID_CIRCUIT


def test_resource_estimate_is_labeled_estimated():
    class Circuit:
        num_qubits = 3
        def depth(self): return 7
    result = FakeProvider().estimate_resources(ExecutionRequest(circuit=Circuit(), backend_id="fake_backend", shots=128))
    assert result == {"status": "ESTIMATED", "qubits": 3, "logical_depth": 7, "shots": 128, "note": "Logical estimate only; not observed hardware cost."}


def test_qiskit_backend_discovery_and_known_capabilities(monkeypatch):
    monkeypatch.setattr(QiskitLocalProvider, "package_availability", staticmethod(lambda: {"qiskit": True, "qiskit_machine_learning": True, "qiskit_aer": True}))
    provider = QiskitLocalProvider()
    backends = {item.backend_id: item for item in provider.list_backends()}
    assert set(backends) == {"statevector", "aer"}
    assert backends["aer"].capabilities.supports_noise_model is CapabilitySupport.SUPPORTED
    assert backends["statevector"].capabilities.supports_noise_model is CapabilitySupport.UNSUPPORTED


@pytest.mark.parametrize(
    ("backend_id", "config", "blocker"),
    [
        ("aer", {"shots": 0}, "shots_out_of_range"),
        ("aer", {"shots": 20000}, "shots_out_of_range"),
        ("statevector", {"noise_probability": 0.01}, "noise_unsupported"),
    ],
)
def test_qiskit_configuration_validation(monkeypatch, backend_id, config, blocker):
    monkeypatch.setattr(QiskitLocalProvider, "package_availability", staticmethod(lambda: {"qiskit": True, "qiskit_machine_learning": True, "qiskit_aer": True}))
    assert blocker in QiskitLocalProvider().validate_config(backend_id, config)


def test_qiskit_unavailable_backend_is_reported(monkeypatch):
    monkeypatch.setattr(QiskitLocalProvider, "package_availability", staticmethod(lambda: {"qiskit": False, "qiskit_machine_learning": False, "qiskit_aer": False}))
    provider = QiskitLocalProvider()
    assert provider.health_check()["availability"] == "UNAVAILABLE"
    assert "backend_dependencies_unavailable" in provider.validate_config("aer", {"shots": 128})


@pytest.mark.parametrize(
    ("exception", "category"),
    [
        (ModuleNotFoundError("missing"), ErrorCategory.BACKEND_UNAVAILABLE),
        (TimeoutError("timeout"), ErrorCategory.TIMEOUT),
        (MemoryError("memory"), ErrorCategory.RESOURCE_LIMIT),
        (ValueError("bad circuit"), ErrorCategory.INVALID_CIRCUIT),
        (RuntimeError("sdk-private-detail"), ErrorCategory.PROVIDER_ERROR),
    ],
)
def test_qiskit_error_translation_is_sanitized(exception, category):
    translated = QiskitLocalProvider()._translate_exception(exception, "aer")
    assert translated.category is category
    assert str(exception) not in translated.safe_message
    assert translated.provider_context["exception_type"] == type(exception).__name__


def test_qiskit_execution_metadata_has_identity_capability_snapshot_and_safe_fingerprint(monkeypatch):
    monkeypatch.setattr(QiskitLocalProvider, "package_availability", staticmethod(lambda: {"qiskit": True, "qiskit_machine_learning": True, "qiskit_aer": True}))
    metadata = QiskitLocalProvider().execution_metadata(
        "aer", {"shots": 128, "noise_probability": 0.0, "api_token": "secret"}, 42,
        "finite-shot local quantum simulation", 128,
    )
    assert metadata["provider_id"] == "qiskit_local"
    assert metadata["backend_id"] == "aer"
    assert metadata["execution_mode"] == "local_simulator"
    assert metadata["capabilities_snapshot"]["supports_shots"] == "SUPPORTED"
    assert "api_token" not in metadata["provider_configuration"]
    assert len(metadata["provider_configuration_fingerprint"]) == 64


def test_pennylane_adapter_declares_existing_backend_without_hardware_claim():
    provider = PennyLaneLocalProvider()
    backend = provider.get_backend("default.qubit")
    assert backend.provider_id == "pennylane_local"
    assert backend.capabilities.supports_hardware_execution is CapabilitySupport.UNSUPPORTED
    with pytest.raises(QuantumProviderError) as caught:
        provider.run(ExecutionRequest(circuit=object(), backend_id="default.qubit"))
    assert caught.value.category is ErrorCategory.UNSUPPORTED_OPERATION


def test_execution_plan_captures_only_selected_provider_paths(monkeypatch):
    registry = ProviderRegistry([FakeProvider()])
    service = QuantumExecutionService(registry)
    # Exercise the no-quantum path without needing registered production IDs.
    assert service.execution_plan({"models": ["logistic_regression"]}) == []


def test_provider_api_discovery_preflight_and_unknown_provider(client):
    providers = client.get("/api/quantum/providers")
    assert providers.status_code == 200
    identities = {item["provider_id"] for item in providers.json()}
    assert {"qiskit_local", "pennylane_local"}.issubset(identities)

    backends = client.get("/api/quantum/providers/qiskit_local/backends")
    assert backends.status_code == 200
    assert {item["backend_id"] for item in backends.json()} == {"statevector", "aer"}

    preflight = client.post("/api/quantum/providers/preflight", json={
        "provider_id": "qiskit_local", "backend_id": "statevector",
        "requested_capabilities": ["supports_statevector"], "configuration": {},
    })
    assert preflight.status_code == 200
    assert preflight.json()["status"] in {"READY", "BLOCKED"}
    assert len(preflight.json()["configuration_fingerprint"]) == 64

    missing = client.get("/api/quantum/providers/not-registered")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "quantum_provider_configuration_error"


def test_provider_health_and_capability_api(client):
    health = client.get("/api/quantum/providers/health")
    assert health.status_code == 200
    assert len(health.json()["providers"]) >= 2
    capabilities = client.get("/api/quantum/providers/qiskit_local/capabilities")
    assert capabilities.status_code == 200
    assert capabilities.json()["provider_id"] == "qiskit_local"


@pytest.mark.quantum
@pytest.mark.skipif(os.getenv("RUN_QUANTUM_TESTS") != "1", reason="Set RUN_QUANTUM_TESTS=1 for actual Aer execution.")
def test_aer_provider_actual_execution():
    qiskit = pytest.importorskip("qiskit")
    pytest.importorskip("qiskit_aer")
    circuit = qiskit.QuantumCircuit(1)
    circuit.x(0)
    circuit.measure_all()
    result = QiskitLocalProvider().run(ExecutionRequest(circuit=circuit, backend_id="aer", shots=128, seed=42))
    assert result.status is ExecutionStatus.COMPLETED
    assert result.counts == {"1": 128}
    assert result.shots == 128
