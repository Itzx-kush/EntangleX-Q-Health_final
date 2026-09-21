from abc import ABC, abstractmethod
from importlib.util import find_spec
from ..api.schemas import QuantumConfig
from ..utils.errors import AppError

def availability() -> dict:
    packages = {name: find_spec(name) is not None for name in ["qiskit", "qiskit_machine_learning", "qiskit_aer"]}
    return {"packages_present": packages, "available": all(packages.values()), "runtime_verified": False, "execution": "local quantum simulation only; no hardware credentials or hardware execution"}

def require_quantum() -> None:
    if not availability()["available"]:
        raise AppError("quantum_dependencies_missing", "Install backend/requirements-quantum.txt in the backend environment before requesting quantum operations.", 503)

class QuantumBackend(ABC):
    """Replaceable primitive provider. Implementations must declare simulation/hardware."""
    @abstractmethod
    def sampler(self):
        raise NotImplementedError
    @abstractmethod
    def pass_manager(self):
        raise NotImplementedError
    @abstractmethod
    def metadata(self) -> dict:
        raise NotImplementedError

class StatevectorBackend(QuantumBackend):
    def __init__(self, config: QuantumConfig, seed: int):
        self.config, self.seed = config, seed
    def sampler(self):
        from qiskit_machine_learning.primitives import QMLSampler
        return QMLSampler(shots=None, seed=self.seed)
    def pass_manager(self):
        return None
    def metadata(self):
        return {"backend": "statevector", "execution_kind": "exact local quantum simulation", "shots": None, "noise_probability": 0.0, "real_hardware": False}

class AerBackend(QuantumBackend):
    def __init__(self, config: QuantumConfig, seed: int):
        self.config, self.seed = config, seed
    def sampler(self):
        from qiskit_aer.primitives import SamplerV2
        from qiskit_aer.noise import NoiseModel, depolarizing_error
        options = {"method": "statevector", "max_parallel_threads": 1}
        p = self.config.noise_probability
        if p:
            noise = NoiseModel()
            noise.add_all_qubit_quantum_error(depolarizing_error(p, 1), ["rz", "sx", "x"])
            noise.add_all_qubit_quantum_error(depolarizing_error(p, 2), ["cx"])
            options.update({"noise_model": noise, "method": "density_matrix"})
        return SamplerV2(default_shots=self.config.shots, seed=self.seed, options={"backend_options": options})
    def pass_manager(self):
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        return generate_preset_pass_manager(optimization_level=1, basis_gates=["rz", "sx", "x", "cx"], seed_transpiler=self.seed)
    def metadata(self):
        return {"backend": "aer", "execution_kind": "finite-shot local quantum simulation", "shots": self.config.shots, "noise_probability": self.config.noise_probability, "real_hardware": False, "noise_interpretation": "Illustrative depolarizing channel, not a characterized physical device."}

def make_backend(config: QuantumConfig, seed: int) -> QuantumBackend:
    require_quantum()
    return StatevectorBackend(config, seed) if config.backend == "statevector" else AerBackend(config, seed)
