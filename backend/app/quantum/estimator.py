import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.utils.metaestimators import available_if
from sklearn.utils.validation import check_is_fitted
from ..api.schemas import QuantumConfig
from .backends import make_backend
from .circuits import build_circuits, circuit_description

class QuantumClassifier(ClassifierMixin, BaseEstimator):
    """sklearn-compatible adapter. All outputs come from actual Qiskit calculations."""
    def __init__(self, kind="vqc", quantum=None, seed=42, c=1.0):
        self.kind = kind
        self.quantum = quantum
        self.seed = seed
        self.c = c

    def fit(self, X, y):
        config = QuantumConfig.model_validate(self.quantum or {})
        X, y = np.asarray(X, dtype=float), np.asarray(y, dtype=int)
        if X.ndim != 2 or X.shape[1] != config.qubits or not np.isfinite(X).all():
            raise ValueError("Quantum input dimensions must equal qubits and contain finite angle features.")
        self.classes_ = np.unique(y)
        if not np.array_equal(self.classes_, [0, 1]):
            raise ValueError("Quantum adapter requires encoded binary labels 0 and 1.")
        self.n_features_in_ = X.shape[1]
        backend = make_backend(config, self.seed)
        sampler, pm = backend.sampler(), backend.pass_manager()
        fmap, ansatz = build_circuits(config)
        self.loss_curve_ = []
        if self.kind == "vqc":
            from qiskit_machine_learning.algorithms import VQC
            from qiskit_machine_learning.optimizers import COBYLA, SPSA
            from qiskit_machine_learning.utils import algorithm_globals
            algorithm_globals.random_seed = self.seed
            optimizer = COBYLA(maxiter=config.maxiter) if config.optimizer == "COBYLA" else SPSA(maxiter=config.maxiter)
            def callback(_weights, objective):
                self.loss_curve_.append(float(objective))
            self.model_ = VQC(
                num_qubits=config.qubits, feature_map=fmap, ansatz=ansatz,
                optimizer=optimizer, sampler=sampler, pass_manager=pm,
                initial_point=np.random.default_rng(self.seed).uniform(-np.pi, np.pi, ansatz.num_parameters),
                callback=callback,
            )
        elif self.kind == "qsvc":
            from qiskit_machine_learning.algorithms import QSVC
            from qiskit_machine_learning.kernels import FidelityQuantumKernel
            from qiskit_machine_learning.state_fidelities import ComputeUncompute
            fidelity = ComputeUncompute(sampler=sampler, pass_manager=pm)
            kernel = FidelityQuantumKernel(feature_map=fmap, fidelity=fidelity, enforce_psd=True)
            self.model_ = QSVC(quantum_kernel=kernel, C=self.c, probability=False, random_state=self.seed)
        elif self.kind == "qnn":
            # SamplerQNN aggregates computational-basis probabilities by the least-significant bit into
            # two classes. NeuralNetworkClassifier then optimizes the trainable
            # ansatz weights while preserving a sklearn-compatible adapter.
            from qiskit_machine_learning.algorithms import NeuralNetworkClassifier
            from qiskit_machine_learning.neural_networks import SamplerQNN
            from qiskit_machine_learning.optimizers import COBYLA, SPSA
            from qiskit_machine_learning.utils import algorithm_globals

            algorithm_globals.random_seed = self.seed
            optimizer = COBYLA(maxiter=config.maxiter) if config.optimizer == "COBYLA" else SPSA(maxiter=config.maxiter)
            qnn = SamplerQNN(
                circuit=fmap.compose(ansatz),
                sampler=sampler,
                input_params=list(fmap.parameters),
                weight_params=list(ansatz.parameters),
                interpret=lambda bitstring: bitstring % 2,
                output_shape=2,
                pass_manager=pm,
            )
            def callback(_weights, objective):
                self.loss_curve_.append(float(objective))
            self.model_ = NeuralNetworkClassifier(
                neural_network=qnn,
                loss="squared_error",
                optimizer=optimizer,
                initial_point=np.random.default_rng(self.seed).uniform(-np.pi, np.pi, ansatz.num_parameters),
                callback=callback,
            )
        else:
            raise ValueError("Unknown quantum classifier.")
        self.model_.fit(X, y)
        if self.kind in {"vqc", "qnn"}:
            self.model_.callback = None
        self.quantum_metadata_ = {
            **backend.metadata(),
            "model_type": self.kind,
            "configuration": config.model_dump(),
            "circuit": circuit_description(config, self.kind, self.seed),
            "objective_evaluations": len(self.loss_curve_),
            "trainable_parameter_count": int(ansatz.num_parameters) if self.kind in {"vqc", "qnn"} else 0,
            "output_semantics": "SamplerQNN computational-basis probabilities grouped by the least-significant bit (bitstring % 2) for classes 0 and 1; not full bitstring parity." if self.kind == "qnn" else None,
        }
        return self

    def predict(self, X):
        check_is_fitted(self, "model_")
        return np.asarray(self.model_.predict(np.asarray(X, dtype=float))).reshape(-1).astype(int)

    @available_if(lambda self: self.kind in {"vqc", "qnn"})
    def predict_proba(self, X):
        check_is_fitted(self, "model_")
        return np.asarray(self.model_.predict_proba(np.asarray(X, dtype=float)), dtype=float)

    def decision_function(self, X):
        check_is_fitted(self, "model_")
        values = np.asarray(X, dtype=float)
        if self.kind in {"vqc", "qnn"}:
            return self.predict_proba(values)[:, 1] - 0.5
        return np.asarray(self.model_.decision_function(values), dtype=float).reshape(-1)
