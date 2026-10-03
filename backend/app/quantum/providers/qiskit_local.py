"""Current local Qiskit simulation path behind the provider contract."""
from __future__ import annotations

import time
from importlib.util import find_spec
from typing import Any, Mapping

from ..contracts import (
    BackendCapabilities, BackendDescriptor, CapabilitySupport, ErrorCategory,
    ExecutionRequest, ExecutionResult, ExecutionStatus, ProviderAvailability, ProviderType,
)
from ..errors import QuantumProviderError
from ..fingerprint import configuration_fingerprint, safe_configuration
from .base import ModelRuntime, QuantumProvider


class QiskitLocalProvider(QuantumProvider):
    provider_id = "qiskit_local"
    provider_name = "Qiskit Local Simulator"
    provider_type = ProviderType.LOCAL_SIMULATOR

    @staticmethod
    def package_availability() -> dict[str, bool]:
        return {name: find_spec(name) is not None for name in ("qiskit", "qiskit_machine_learning", "qiskit_aer")}

    def list_backends(self) -> list[BackendDescriptor]:
        packages = self.package_availability()
        common = dict(
            supports_sampling=CapabilitySupport.SUPPORTED,
            supports_estimator=CapabilitySupport.UNKNOWN,
            supports_hardware_execution=CapabilitySupport.UNSUPPORTED,
            supports_async_jobs=CapabilitySupport.UNSUPPORTED,
            supports_cancellation=CapabilitySupport.UNSUPPORTED,
            supports_batching=CapabilitySupport.SUPPORTED,
            supports_parameterized_circuits=CapabilitySupport.SUPPORTED,
            max_qubits=None,
        )
        return [
            BackendDescriptor(
                backend_id="statevector", display_name="Exact Statevector", provider_id=self.provider_id,
                backend_type="LOCAL_SIMULATOR", available=packages["qiskit"] and packages["qiskit_machine_learning"],
                capabilities=BackendCapabilities(
                    **common, supports_statevector=CapabilitySupport.SUPPORTED,
                    supports_shots=CapabilitySupport.UNSUPPORTED, supports_noise_model=CapabilitySupport.UNSUPPORTED,
                    supports_gradients=CapabilitySupport.UNKNOWN, max_shots=None,
                ),
            ),
            BackendDescriptor(
                backend_id="aer", display_name="Qiskit Aer Simulator", provider_id=self.provider_id,
                backend_type="LOCAL_SIMULATOR", available=all(packages.values()),
                capabilities=BackendCapabilities(
                    **common, supports_statevector=CapabilitySupport.SUPPORTED,
                    supports_shots=CapabilitySupport.SUPPORTED, supports_noise_model=CapabilitySupport.SUPPORTED,
                    supports_gradients=CapabilitySupport.UNKNOWN, max_shots=16384,
                ),
            ),
        ]

    def validate_config(self, backend_id: str, configuration: Mapping[str, Any]) -> list[str]:
        backend = self.get_backend(backend_id)
        blockers: list[str] = []
        if not self.enabled:
            blockers.append("provider_disabled")
        if not backend.available:
            blockers.append("backend_dependencies_unavailable")
        shots = configuration.get("shots")
        if backend_id == "aer" and (not isinstance(shots, int) or not 1 <= shots <= 16384):
            blockers.append("shots_out_of_range")
        if backend_id == "statevector" and float(configuration.get("noise_probability", 0) or 0) != 0:
            blockers.append("noise_unsupported")
        return blockers

    def create_model_runtime(self, backend_id: str, configuration: Mapping[str, Any], seed: int) -> ModelRuntime:
        blockers = self.validate_config(backend_id, configuration)
        if blockers:
            category = ErrorCategory.BACKEND_UNAVAILABLE if "backend_dependencies_unavailable" in blockers else ErrorCategory.CONFIGURATION_ERROR
            raise QuantumProviderError(category, "The local quantum backend is not ready for this configuration.", provider_context={"blockers": blockers})
        try:
            if backend_id == "statevector":
                from qiskit_machine_learning.primitives import QMLSampler
                sampler, pass_manager = QMLSampler(shots=None, seed=seed), None
                execution_kind, shots = "exact local quantum simulation", None
            else:
                from qiskit_aer.noise import NoiseModel, depolarizing_error
                from qiskit_aer.primitives import SamplerV2
                from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
                options: dict[str, Any] = {"method": "statevector", "max_parallel_threads": 1}
                probability = float(configuration.get("noise_probability", 0) or 0)
                if probability:
                    noise = NoiseModel()
                    noise.add_all_qubit_quantum_error(depolarizing_error(probability, 1), ["rz", "sx", "x"])
                    noise.add_all_qubit_quantum_error(depolarizing_error(probability, 2), ["cx"])
                    options.update({"noise_model": noise, "method": "density_matrix"})
                shots = int(configuration["shots"])
                sampler = SamplerV2(default_shots=shots, seed=seed, options={"backend_options": options})
                pass_manager = generate_preset_pass_manager(
                    optimization_level=1, basis_gates=["rz", "sx", "x", "cx"], seed_transpiler=seed,
                )
                execution_kind = "finite-shot local quantum simulation"
        except QuantumProviderError:
            raise
        except Exception as exc:
            raise self._translate_exception(exc, backend_id) from exc
        metadata = self.execution_metadata(backend_id, configuration, seed, execution_kind, shots)
        return ModelRuntime(sampler=sampler, pass_manager=pass_manager, metadata=metadata)

    def execution_metadata(self, backend_id: str, configuration: Mapping[str, Any], seed: int, execution_kind: str, shots: int | None) -> dict[str, Any]:
        safe = safe_configuration({
            "provider_id": self.provider_id, "backend_id": backend_id,
            "execution_mode": "local_simulator", "seed": seed, **dict(configuration),
        })
        backend = self.get_backend(backend_id)
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_type": self.provider_type.value,
            "backend_id": backend_id,
            "backend": backend_id,
            "backend_type": backend.backend_type,
            "execution_mode": "local_simulator",
            "execution_kind": execution_kind,
            "shots": shots,
            "noise_probability": float(configuration.get("noise_probability", 0) or 0),
            "real_hardware": False,
            "capabilities_snapshot": backend.capabilities.as_dict(),
            "provider_configuration": safe,
            "provider_configuration_fingerprint": configuration_fingerprint(safe),
            "seed_status": "APPLIED",
            "noise_interpretation": (
                "Illustrative depolarizing channel, not a characterized physical device."
                if configuration.get("noise_probability") else None
            ),
        }

    def run(self, request: ExecutionRequest) -> ExecutionResult:
        started = time.perf_counter()
        if request.circuit is None and not request.circuits:
            raise QuantumProviderError(ErrorCategory.INVALID_CIRCUIT, "At least one circuit is required.")
        blockers = self.validate_config(request.backend_id, {
            "shots": request.shots or 1024,
            "noise_probability": request.noise_configuration.get("probability", 0),
        })
        if blockers:
            raise QuantumProviderError(ErrorCategory.CONFIGURATION_ERROR, "The execution request is not supported.", provider_context={"blockers": blockers})
        circuits = list(request.circuits) if request.circuits else [request.circuit]
        try:
            if request.backend_id == "statevector":
                from qiskit.quantum_info import Statevector
                probabilities = Statevector.from_instruction(circuits[0]).probabilities_dict()
                return ExecutionResult(
                    status=ExecutionStatus.COMPLETED, provider_id=self.provider_id, backend_id=request.backend_id,
                    probabilities={str(key): float(value) for key, value in probabilities.items()}, shots=None,
                    execution_time=time.perf_counter() - started,
                    metadata={"execution_mode": request.execution_mode, "seed_status": "UNSPECIFIED" if request.seed is None else "APPLIED"},
                )
            from qiskit import transpile
            from qiskit_aer import AerSimulator
            options: dict[str, Any] = {"seed_simulator": request.seed}
            backend = AerSimulator(method="statevector", max_parallel_threads=1)
            transpiled = transpile(circuits, backend, seed_transpiler=request.seed, **dict(request.transpile_configuration))
            job = backend.run(transpiled, shots=request.shots or 1024, **options)
            result = job.result()
            counts = result.get_counts(0)
            shots = int(sum(counts.values()))
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED, provider_id=self.provider_id, backend_id=request.backend_id,
                job_id=str(job.job_id()), counts={str(key): int(value) for key, value in counts.items()},
                probabilities={str(key): float(value / shots) for key, value in counts.items()}, shots=shots,
                execution_time=time.perf_counter() - started,
                metadata={"execution_mode": request.execution_mode, "seed_status": "UNSPECIFIED" if request.seed is None else "APPLIED"},
            )
        except QuantumProviderError:
            raise
        except Exception as exc:
            raise self._translate_exception(exc, request.backend_id) from exc

    def _translate_exception(self, exc: Exception, backend_id: str) -> QuantumProviderError:
        name = type(exc).__name__.lower()
        text = str(exc).lower()
        if isinstance(exc, (ImportError, ModuleNotFoundError)):
            category = ErrorCategory.BACKEND_UNAVAILABLE
        elif "cancel" in name or "cancel" in text:
            category = ErrorCategory.CANCELLED
        elif "timeout" in name or "timeout" in text:
            category = ErrorCategory.TIMEOUT
        elif "circuit" in name or "circuit" in text:
            category = ErrorCategory.INVALID_CIRCUIT
        elif "memory" in name or "qubit" in text or "shot" in text:
            category = ErrorCategory.RESOURCE_LIMIT
        else:
            category = ErrorCategory.PROVIDER_ERROR
        return QuantumProviderError(category, "The local quantum provider could not complete the operation.", provider_context={"provider_id": self.provider_id, "backend_id": backend_id, "exception_type": type(exc).__name__})

    def health_check(self) -> dict[str, Any]:
        packages = self.package_availability()
        available = packages["qiskit"] and packages["qiskit_machine_learning"]
        return {
            "provider_id": self.provider_id,
            "availability": ProviderAvailability.AVAILABLE.value if available else ProviderAvailability.UNAVAILABLE.value,
            "packages_present": packages,
            "runtime_verified": False,
            "execution": "local quantum simulation only; no hardware credentials or hardware execution",
        }
