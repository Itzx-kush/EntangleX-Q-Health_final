from ..api.schemas import QuantumConfig
from .backends import make_backend, require_quantum

def build_circuits(config: QuantumConfig):
    require_quantum()
    from qiskit.circuit.library import zz_feature_map, real_amplitudes
    feature_map = zz_feature_map(config.qubits, reps=config.feature_map_reps, entanglement=config.entanglement)
    ansatz = real_amplitudes(config.qubits, reps=config.ansatz_reps, entanglement=config.entanglement)
    return feature_map, ansatz

def circuit_description(config: QuantumConfig, kind: str, seed: int) -> dict:
    feature_map, ansatz = build_circuits(config)
    circuit = feature_map.compose(ansatz) if kind == "vqc" else feature_map
    # These are circuit properties calculated at request time, not fabricated results.
    decomposed = circuit.decompose(reps=1)
    gates = [{"name": instruction.operation.name, "qubits": [decomposed.find_bit(q).index for q in instruction.qubits], "parameters": [str(p) for p in instruction.operation.params]} for instruction in decomposed.data]
    backend = make_backend(config, seed)
    return {
        "model_type": kind, "execution_kind": backend.metadata()["execution_kind"], "backend": config.backend,
        "qubits": circuit.num_qubits, "logical_depth": circuit.depth(), "gate_counts": dict(circuit.count_ops()),
        "parameter_count": circuit.num_parameters, "text": str(circuit.draw(output="text", fold=120)), "gates": gates,
        "limitation": "Parameterized logical circuit only. QSVC displays its feature map; kernel evaluation uses compute-uncompute circuit pairs. Depth is not a hardware timing measurement. This endpoint does not execute a circuit.",
    }
