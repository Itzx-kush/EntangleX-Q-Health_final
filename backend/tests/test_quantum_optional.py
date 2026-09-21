"""Opt-in genuine circuit/model tests; no fabricated quantum outputs."""
import os
import numpy as np
import pytest
pytestmark = [pytest.mark.quantum, pytest.mark.skipif(os.getenv("RUN_QUANTUM_TESTS") != "1", reason="Set RUN_QUANTUM_TESTS=1 to execute quantum tests explicitly.")]

def test_quantum_circuit_structure():
    pytest.importorskip("qiskit_machine_learning")
    from app.quantum.circuits import circuit_description
    from app.api.schemas import QuantumConfig
    result = circuit_description(QuantumConfig(qubits=2), "vqc", 42)
    assert result["qubits"] == 2
    assert result["logical_depth"] > 0
    assert result["gates"]

@pytest.mark.parametrize("kind", ["vqc", "qsvc"])
def test_small_actual_quantum_prediction(kind):
    pytest.importorskip("qiskit_machine_learning")
    from sklearn.base import clone
    from app.quantum.estimator import QuantumClassifier
    from app.api.schemas import QuantumConfig
    X = np.array([[.1, .2], [.2, .1], [2., 2.1], [2.2, 2.]])
    y = np.array([0, 0, 1, 1])
    estimator = QuantumClassifier(kind=kind, quantum=QuantumConfig(qubits=2, maxiter=5).model_dump(), seed=42)
    model = clone(estimator).fit(X, y)
    assert model.predict(X).shape == (4,)
    if kind == "vqc":
        probabilities = model.predict_proba(X)
        np.testing.assert_allclose(probabilities.sum(axis=1), 1, atol=1e-6)
    else:
        assert model.decision_function(X).shape == (4,)
