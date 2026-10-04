from ..api.schemas import QuantumConfig
from .backends import require_quantum
from .service import service


def build_circuits(config: QuantumConfig):
    require_quantum()
    from qiskit.circuit.library import zz_feature_map, real_amplitudes

    feature_map = zz_feature_map(config.qubits, reps=config.feature_map_reps, entanglement=config.entanglement)
    ansatz = real_amplitudes(config.qubits, reps=config.ansatz_reps, entanglement=config.entanglement)
    return feature_map, ansatz


def circuit_artifacts(config: QuantumConfig, kind: str, seed: int) -> dict:
    """Build the one canonical Qiskit structure and its backend-derived description."""
    feature_map, ansatz = build_circuits(config)
    circuit = feature_map.compose(ansatz) if kind in {"vqc", "qnn"} else feature_map
    decomposed = circuit.decompose(reps=1)
    gates = []
    for gate_index, instruction in enumerate(decomposed.data):
        operation = instruction.operation
        qubits = [decomposed.find_bit(qubit).index for qubit in instruction.qubits]
        control_count = int(getattr(operation, "num_ctrl_qubits", 0) or 0)
        gate_type = (
            "measurement" if operation.name == "measure"
            else "controlled" if control_count
            else "multi_qubit" if len(qubits) > 1
            else "single_qubit"
        )
        parameters = [str(parameter) for parameter in operation.params]
        gates.append({
            "gate_index": gate_index,
            "name": operation.name,
            "gate_type": gate_type,
            "qubits": qubits,
            "parameters": parameters,
            "control_qubits": qubits[:control_count] if control_count else [],
            "target_qubits": qubits[control_count:] if control_count else [],
        })

    runtime = service.prepare_model_runtime(config.provider_id, config.backend, config.model_dump(), seed)
    description = {
        "model_type": kind, "execution_kind": runtime.metadata["execution_kind"], "backend": config.backend,
        "qubits": circuit.num_qubits, "logical_depth": circuit.depth(), "gate_counts": dict(circuit.count_ops()),
        "parameter_count": circuit.num_parameters, "text": str(circuit.draw(output="text", fold=120)),
        "gates": [
            {"name": gate["name"], "qubits": gate["qubits"], "parameters": gate["parameters"]}
            for gate in gates
        ],
        "limitation": "Parameterized logical circuit only. QSVC displays its feature map; kernel evaluation uses compute-uncompute circuit pairs. VQC and QNN include the feature map plus ansatz. Depth is not a hardware timing measurement. This endpoint does not execute a circuit.",
    }
    return {
        "feature_map": feature_map,
        "ansatz": ansatz,
        "circuit": circuit,
        "decomposed_circuit": decomposed,
        "description": description,
        "gate_sequence": gates,
    }


def circuit_description(config: QuantumConfig, kind: str, seed: int) -> dict:
    """Backward-compatible API description generated from the canonical circuit."""
    return circuit_artifacts(config, kind, seed)["description"]
