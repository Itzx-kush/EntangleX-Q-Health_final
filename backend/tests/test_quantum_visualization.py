"""Quantum visualization tests use backend structures and actual simulator output."""
from __future__ import annotations

import numpy as np
import pytest
from sqlalchemy import func, select

from app.database import session_scope
from app.quantum.schemas import (
    QuantumVisualizationPreviewRequest,
    QuantumVisualizationSimulationRequest,
)
from app.quantum.visualization import (
    MAX_STATEVECTOR_QUBITS,
    _load_dataset_context,
    visualization_service,
)
from app.storage.entities import Experiment, Job, ModelRecord, QuantumDiagnosticReport
from app.utils.errors import AppError


def _hybrid_request(**kwargs):
    return QuantumVisualizationPreviewRequest(
        model_type="hybrid_pennylane_torch",
        hybrid={"qubits": 2, "quantum_layers": 1},
        **kwargs,
    )


def test_hybrid_preview_exposes_real_architecture_without_execution(client):
    response = client.post("/api/quantum/visualization/preview", json={
        "model_type": "hybrid_pennylane_torch",
        "hybrid": {
            "qubits": 2,
            "quantum_layers": 1,
            "classical_hidden_dimensions": [8],
        },
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "STRUCTURE_ONLY"
    assert data["provider"]["provider_id"] == "pennylane_local"
    assert data["provider"]["backend_id"] == "default.qubit"
    assert data["provider"]["execution_mode"] == "local_simulator"
    assert data["provider"]["hardware_available"] is False
    assert data["circuit"]["gate_sequence"][0]["name"] == "AngleEmbedding(Y)"
    assert data["circuit"]["gate_sequence"][1]["name"] == "StronglyEntanglingLayers"
    assert data["circuit"]["logical_depth"] is None
    assert data["state"]["status"] == "STRUCTURE_ONLY"
    assert data["bloch"]["status"] == "NOT_AVAILABLE"
    assert data["entanglement"]["status"] == "STRUCTURE_ONLY"
    assert data["resources"]["parameterized_gates"] is None
    assert data["resources"]["entangling_gates"] is None
    assert data["resources"]["total_gates"] is None
    assert data["hybrid_architecture"]["output_path"] == [
        "PyTorch classical output head",
        "positive-class sigmoid probability",
    ]


def test_preview_has_no_training_or_database_side_effects(client):
    with session_scope() as session:
        before = {
            table.__name__: session.scalar(select(func.count()).select_from(table))
            for table in (Experiment, Job, ModelRecord, QuantumDiagnosticReport)
        }
    response = client.post("/api/quantum/visualization/preview", json={
        "model_type": "hybrid_pennylane_torch",
        "hybrid": {"qubits": 2},
    })
    assert response.status_code == 200, response.text
    with session_scope() as session:
        after = {
            table.__name__: session.scalar(select(func.count()).select_from(table))
            for table in (Experiment, Job, ModelRecord, QuantumDiagnosticReport)
        }
    assert before == after


def test_hybrid_preview_is_deterministic_and_fingerprints_context():
    first = visualization_service.preview(_hybrid_request())[0]
    second = visualization_service.preview(_hybrid_request())[0]
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    with_dataset_context = visualization_service.preview(
        _hybrid_request(representation_context={"source": "caller metadata"})
    )[0]
    assert first.request_fingerprint != with_dataset_context.request_fingerprint


def test_registered_dataset_metadata_is_reported_without_preprocessing(registered):
    request = _hybrid_request(dataset_id=registered.id)
    context = _load_dataset_context(request)
    assert context.status == "AVAILABLE"
    assert context.dataset_id == registered.id
    assert context.dataset_hash == registered.sha256
    assert context.raw_feature_count == 6
    assert context.representation_status == "STRUCTURE_ONLY"
    assert context.represented_feature_count is None
    assert context.limitations


def test_visualization_fingerprint_isolated_by_dataset_identity(registered):
    without_dataset = visualization_service.preview(_hybrid_request())[0]
    with_dataset = visualization_service.preview(
        _hybrid_request(dataset_id=registered.id)
    )[0]
    assert without_dataset.request_fingerprint != with_dataset.request_fingerprint
    assert with_dataset.dataset_context.dataset_id == registered.id


def test_invalid_dataset_context_is_domain_error():
    request = _hybrid_request(dataset_id="11111111-1111-1111-1111-111111111111")
    with pytest.raises(AppError) as caught:
        _load_dataset_context(request)
    assert caught.value.code == "quantum_visualization_invalid_context"


def test_invalid_representation_dimensions_are_rejected():
    with pytest.raises(ValueError, match="match the configured encoded dimension"):
        QuantumVisualizationPreviewRequest(
            model_type="vqc",
            quantum={"qubits": 2},
            representation_context={"selected_feature_names": ["a", "b", "c"]},
        )


def test_quantum_preview_reports_dependency_failure_precisely(monkeypatch):
    monkeypatch.setattr(
        "app.quantum.visualization.service.provider",
        lambda _provider_id: {
            "display_name": "Qiskit Local Simulator",
            "provider_type": "LOCAL_SIMULATOR",
            "availability": "UNAVAILABLE",
            "backends": [{
                "backend_id": "statevector",
                "backend_type": "LOCAL_SIMULATOR",
                "available": False,
            }],
        },
    )
    request = QuantumVisualizationPreviewRequest(
        model_type="vqc",
        quantum={"qubits": 2, "maxiter": 5},
    )
    with pytest.raises(AppError) as caught:
        visualization_service.preview(request)
    assert caught.value.code == "quantum_dependency_unavailable"


def test_simulation_enforces_bounded_statevector_before_provider_call():
    qubits = MAX_STATEVECTOR_QUBITS + 1
    request = QuantumVisualizationSimulationRequest(
        model_type="vqc",
        quantum={"qubits": qubits, "maxiter": 5},
        encoded_vector=[0.1] * qubits,
    )
    with pytest.raises(AppError) as caught:
        visualization_service.simulate(request)
    assert caught.value.code == "quantum_resource_limit"


def test_visualization_preview_api_returns_versioned_contract(client):
    pytest.importorskip("qiskit_machine_learning")
    response = client.post("/api/quantum/visualization/preview", json={
        "model_type": "qsvc",
        "quantum": {"qubits": 2, "maxiter": 5},
        "seed": 42,
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_version"] == "quantum-visualization-v1"
    assert body["model_type"] == "qsvc"
    assert body["circuit"]["feature_map"] == "ZZFeatureMap"
    assert body["circuit"]["ansatz"] is None
    assert body["state"]["status"] == "STRUCTURE_ONLY"


def test_visualization_simulation_api_returns_actual_state(client):
    pytest.importorskip("qiskit_machine_learning")
    response = client.post("/api/quantum/visualization/simulate", json={
        "model_type": "vqc",
        "quantum": {"qubits": 2, "maxiter": 5},
        "encoded_vector": [0.12, 0.34],
        "seed": 42,
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "SIMULATION_AVAILABLE"
    assert body["state"]["status"] == "AVAILABLE"
    assert body["state"]["execution_source"] == "local_simulator"
    assert sum(body["state"]["normalized_probability"]) == pytest.approx(1.0)
    assert body["provider"]["hardware_available"] is False


@pytest.mark.parametrize("model_type", ["vqc", "qsvc", "qnn"])
def test_qiskit_structural_contract_is_canonical_and_deterministic(model_type):
    pytest.importorskip("qiskit_machine_learning")
    request = QuantumVisualizationPreviewRequest(
        model_type=model_type,
        quantum={"qubits": 2, "maxiter": 5},
        representation_context={"selected_feature_names": ["feature_a", "feature_b"]},
        sample_count=30,
    )
    first = visualization_service.preview(request)[0]
    second = visualization_service.preview(request)[0]
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.circuit.qubits == 2
    assert first.circuit.logical_depth is not None
    assert first.circuit.parameter_count is not None
    assert first.circuit.gate_sequence
    assert [gate.gate_index for gate in first.circuit.gate_sequence] == list(range(len(first.circuit.gate_sequence)))
    assert [mapping.feature_name for mapping in first.encoding.feature_to_qubit_mapping] == [
        "feature_a", "feature_b",
    ]
    assert [mapping.qubit_index for mapping in first.encoding.feature_to_qubit_mapping] == [0, 1]
    assert first.provider.hardware_available is False
    assert first.resources.bounded_policy_status in {"within_budget", "near_budget", "exceeds_budget"}
    if model_type == "qsvc":
        assert first.circuit.ansatz is None
        assert "kernel" in first.hybrid_architecture.quantum_operations[0].lower()
    else:
        assert first.circuit.ansatz == "RealAmplitudes"
        assert first.circuit.parameter_count > 0


def test_statevector_contract_matches_actual_qiskit_simulation():
    pytest.importorskip("qiskit_machine_learning")
    from qiskit.quantum_info import Statevector
    from app.api.schemas import QuantumConfig
    from app.quantum.circuits import build_circuits

    encoded = [0.17, -0.42]
    request = QuantumVisualizationSimulationRequest(
        model_type="vqc",
        quantum={"qubits": 2, "maxiter": 5},
        encoded_vector=encoded,
        simulation_stage="encoding",
        seed=19,
    )
    contract = visualization_service.simulate(request)
    feature_map, _ansatz = build_circuits(QuantumConfig(qubits=2, maxiter=5))
    parameters = sorted(feature_map.parameters, key=lambda item: item.name)
    expected = Statevector.from_instruction(
        feature_map.assign_parameters(dict(zip(parameters, encoded, strict=True)))
    ).data
    actual = np.asarray(contract.state.amplitude_real) + 1j * np.asarray(contract.state.amplitude_imaginary)
    np.testing.assert_allclose(actual, expected, atol=1e-10)
    np.testing.assert_allclose(contract.state.probability, np.abs(expected) ** 2, atol=1e-10)
    assert contract.state.status == "AVAILABLE"
    assert contract.state.execution_source == "local_simulator"
    assert contract.state.simulator == "qiskit_local"
    assert contract.state.circuit_scope == "feature_map"
    assert sum(contract.state.normalized_probability) == pytest.approx(1.0)
    assert len(contract.state.phase) == 2 ** request.quantum.qubits
    np.testing.assert_allclose(
        [phase for phase in contract.state.phase if phase is not None],
        [float(np.angle(value)) for value in expected if abs(value) > 1e-15],
        atol=1e-10,
    )
    assert all(
        contract.state.phase[index] is None
        for index, value in enumerate(expected)
        if abs(value) <= 1e-15
    )
    assert contract.bloch.status == "AVAILABLE"
    assert len(contract.bloch.qubits) == request.quantum.qubits
    assert contract.entanglement.status == "AVAILABLE"
    assert contract.state.input_sample_count == 1


def test_full_model_simulation_requires_explicit_ansatz_parameters():
    pytest.importorskip("qiskit_machine_learning")
    request = QuantumVisualizationSimulationRequest(
        model_type="vqc",
        quantum={"qubits": 2, "maxiter": 5},
        encoded_vector=[0.1, 0.2],
        simulation_stage="full_model",
    )
    with pytest.raises(AppError) as caught:
        visualization_service.simulate(request)
    assert caught.value.code == "quantum_visualization_invalid_context"
    assert "explicit ansatz parameters" in caught.value.message


def test_aer_shot_output_does_not_claim_phase_or_bloch():
    pytest.importorskip("qiskit_machine_learning")
    pytest.importorskip("qiskit_aer")
    request = QuantumVisualizationSimulationRequest(
        model_type="qsvc",
        quantum={"backend": "aer", "qubits": 2, "shots": 128},
        encoded_vector=[0.15, 0.35],
        seed=7,
    )
    contract = visualization_service.simulate(request)
    assert contract.state.measurement_counts
    assert sum(contract.state.measurement_counts.values()) == 128
    assert contract.state.shots == 128
    assert contract.state.amplitude_real is None
    assert contract.state.phase is None
    assert contract.bloch.status == "NOT_AVAILABLE"
    assert contract.entanglement.status == "STRUCTURE_ONLY"
    assert "not hardware" in contract.measurement.limitations[0].lower()


def test_qsvc_full_model_simulation_is_rejected():
    with pytest.raises(ValueError, match="not a variational ansatz"):
        QuantumVisualizationSimulationRequest(
            model_type="qsvc",
            quantum={"qubits": 2},
            encoded_vector=[0.1, 0.2],
            simulation_stage="full_model",
        )


def test_aer_shot_limit_is_enforced_before_simulation():
    request = QuantumVisualizationSimulationRequest(
        model_type="qsvc",
        quantum={"backend": "aer", "qubits": 2, "shots": 8192},
        encoded_vector=[0.1, 0.2],
    )
    with pytest.raises(AppError) as caught:
        visualization_service.simulate(request)
    assert caught.value.code == "quantum_resource_limit"