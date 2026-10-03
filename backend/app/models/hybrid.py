"""Persistence-safe PennyLane + PyTorch sklearn-compatible hybrid classifier."""
from __future__ import annotations

import random
from typing import Any
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.utils.validation import check_array, check_is_fitted


def require_hybrid_dependencies() -> tuple[Any, Any]:
    try:
        import pennylane as qml
        import torch
    except (ImportError, OSError) as exc:
        from ..utils.errors import AppError
        raise AppError(
            "hybrid_dependencies_missing",
            "Install backend/requirements-hybrid.txt before requesting PennyLane + PyTorch hybrid execution.",
            503,
        ) from exc
    return qml, torch


class PennyLaneTorchClassifier(ClassifierMixin, BaseEstimator):
    """Trainable AngleEmbedding/StronglyEntanglingLayers circuit plus a Torch head.

    ``predict`` uses conventional 0.5 sklearn semantics. Experiment evaluation uses
    the platform's separately locked OOF operating threshold instead.
    """

    def __init__(
        self,
        provider_id: str = "pennylane_local",
        execution_mode: str = "local_simulator",
        qubits: int = 4,
        quantum_layers: int = 2,
        hidden_dimensions: tuple[int, ...] = (16, 8),
        activation: str = "relu",
        optimizer: str = "adam",
        learning_rate: float = 0.001,
        epochs: int = 50,
        batch_size: int = 16,
        deterministic_seed: int = 42,
        backend: str = "default.qubit",
        feature_map: str = "angle",
    ):
        self.provider_id = provider_id
        self.execution_mode = execution_mode
        self.qubits = qubits
        self.quantum_layers = quantum_layers
        self.hidden_dimensions = hidden_dimensions
        self.activation = activation
        self.optimizer = optimizer
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.deterministic_seed = deterministic_seed
        self.backend = backend
        self.feature_map = feature_map

    def _validate_configuration(self) -> None:
        if not 2 <= self.qubits <= 8:
            raise ValueError("Hybrid qubits must be between 2 and 8.")
        if not 1 <= self.quantum_layers <= 6:
            raise ValueError("Hybrid quantum layers must be between 1 and 6.")
        if not 1 <= len(self.hidden_dimensions) <= 3 or any(not 2 <= int(v) <= 128 for v in self.hidden_dimensions):
            raise ValueError("Hybrid hidden dimensions must contain one to three values between 2 and 128.")
        if self.activation not in {"relu", "tanh"} or self.optimizer not in {"adam", "sgd"}:
            raise ValueError("Unsupported hybrid activation or optimizer.")
        if self.provider_id != "pennylane_local" or self.execution_mode != "local_simulator":
            raise ValueError("This hybrid model supports the registered PennyLane local provider only.")
        if self.backend != "default.qubit" or self.feature_map != "angle":
            raise ValueError("This bounded implementation supports AngleEmbedding on default.qubit only.")
        if not 1 <= self.epochs <= 500 or not 1 <= self.batch_size <= 256 or not 0.00001 <= self.learning_rate <= 0.1:
            raise ValueError("Hybrid training configuration is outside bounded limits.")

    def _seed(self, torch) -> None:
        random.seed(self.deterministic_seed)
        np.random.seed(self.deterministic_seed)
        torch.manual_seed(self.deterministic_seed)
        torch.use_deterministic_algorithms(True, warn_only=True)
        torch.set_num_threads(1)

    def _build_runtime(self) -> None:
        qml, torch = require_hybrid_dependencies()
        self._seed(torch)
        from ..quantum.service import service
        runtime = service.prepare_model_runtime(
            self.provider_id,
            self.backend,
            {
                "provider_id": self.provider_id,
                "execution_mode": self.execution_mode,
                "backend": self.backend,
                "qubits": self.qubits,
                "quantum_layers": self.quantum_layers,
                "feature_map": self.feature_map,
            },
            self.deterministic_seed,
        )
        device = runtime.native_context
        self._provider_metadata = dict(runtime.metadata)

        @qml.qnode(device, interface="torch", diff_method="backprop")
        def circuit(inputs, weights):
            qml.AngleEmbedding(inputs, wires=range(self.qubits), rotation="Y")
            qml.StronglyEntanglingLayers(weights, wires=range(self.qubits))
            return [qml.expval(qml.PauliZ(wire)) for wire in range(self.qubits)]

        quantum = qml.qnn.TorchLayer(
            circuit,
            {"weights": qml.StronglyEntanglingLayers.shape(self.quantum_layers, self.qubits)},
        )
        layers = [quantum]
        width = self.qubits
        activation_class = torch.nn.ReLU if self.activation == "relu" else torch.nn.Tanh
        for hidden in self.hidden_dimensions:
            layers.extend([torch.nn.Linear(width, int(hidden)), activation_class()])
            width = int(hidden)
        layers.append(torch.nn.Linear(width, 1))
        self._model = torch.nn.Sequential(*layers).to(dtype=torch.float64, device="cpu")
        self._qnode = circuit

    def fit(self, X, y):
        self._validate_configuration()
        X = check_array(X, ensure_2d=True, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        if X.shape[1] != self.qubits:
            raise ValueError(f"Hybrid estimator requires exactly {self.qubits} reduced input features.")
        if len(X) != len(y) or set(np.unique(y)) - {0.0, 1.0}:
            raise ValueError("Hybrid estimator requires aligned binary labels encoded as 0/1.")
        self._build_runtime()
        _, torch = require_hybrid_dependencies()
        self.classes_ = np.array([0, 1], dtype=int)
        self.n_features_in_ = X.shape[1]
        self.sample_count_ = len(X)
        features = torch.tensor(X, dtype=torch.float64)
        labels = torch.tensor(y, dtype=torch.float64).reshape(-1, 1)
        generator = torch.Generator(device="cpu").manual_seed(self.deterministic_seed)
        loader = torch.utils.data.DataLoader(
            torch.utils.data.TensorDataset(features, labels),
            batch_size=min(self.batch_size, len(X)), shuffle=True, generator=generator,
        )
        optimizer_class = torch.optim.Adam if self.optimizer == "adam" else torch.optim.SGD
        optimizer = optimizer_class(self._model.parameters(), lr=self.learning_rate)
        criterion = torch.nn.BCEWithLogitsLoss()
        quantum_parameter = next(self._model[0].parameters())
        self.initial_quantum_weights_ = quantum_parameter.detach().cpu().numpy().copy()
        self.loss_curve_ = []
        self._model.train()
        for _ in range(self.epochs):
            total = 0.0
            for batch_X, batch_y in loader:
                optimizer.zero_grad(set_to_none=True)
                logits = self._model(batch_X)
                loss = criterion(logits, batch_y)
                loss.backward()
                optimizer.step()
                total += float(loss.detach()) * len(batch_X)
            self.loss_curve_.append(total / len(X))
        self.final_quantum_weights_ = quantum_parameter.detach().cpu().numpy().copy()
        self.quantum_parameters_changed_ = bool(not np.allclose(self.initial_quantum_weights_, self.final_quantum_weights_))
        self._model.eval()
        self.quantum_metadata_ = self._metadata(qml_module=__import__("pennylane"), torch_module=torch)
        return self

    def _metadata(self, qml_module, torch_module) -> dict:
        quantum_count = sum(p.numel() for p in self._model[0].parameters())
        classical_count = sum(p.numel() for layer in list(self._model)[1:] for p in layer.parameters(recurse=False))
        circuit = {
            "model_type": "hybrid_pennylane_torch",
            "execution_kind": "local PennyLane quantum simulation",
            "backend": self.backend,
            "qubits": self.qubits,
            "logical_depth": None,
            "gate_counts": {},
            "parameter_count": int(quantum_count),
            "text": "AngleEmbedding(Y) → StronglyEntanglingLayers → PauliZ expectation per qubit",
            "gates": [],
            "limitation": "Structured summary of the executed PennyLane template; not a hardware-transpiled circuit.",
        }
        try:
            _, torch = require_hybrid_dependencies()
            weights = next(self._model[0].parameters()).detach()
            specs = qml_module.specs(self._qnode)(torch.zeros(self.qubits, dtype=torch.float64), weights)
            resources = specs.get("resources") if hasattr(specs, "get") else None
            if resources is not None:
                circuit["logical_depth"] = int(resources.depth)
                circuit["gate_counts"] = {str(k): int(v) for k, v in resources.gate_types.items()}
        except Exception:
            pass
        return {
            **self._provider_metadata,
            "framework": "PennyLane", "classical_framework": "PyTorch", "backend": self.backend,
            "execution_kind": "local PennyLane quantum simulation", "real_hardware": False,
            "qubits": self.qubits, "quantum_layers": self.quantum_layers, "feature_map": self.feature_map,
            "expectation_observables": [f"PauliZ({wire})" for wire in range(self.qubits)],
            "optimizer": self.optimizer, "learning_rate": self.learning_rate, "epochs": self.epochs,
            "batch_size": self.batch_size, "quantum_parameter_count": int(quantum_count),
            "classical_parameter_count": int(classical_count), "total_parameter_count": int(quantum_count + classical_count),
            "sample_count": int(self.sample_count_), "deterministic_seed": self.deterministic_seed,
            "framework_versions": {"pennylane": str(qml_module.__version__), "torch": str(torch_module.__version__)},
            "quantum_parameters_changed": self.quantum_parameters_changed_, "circuit": circuit,
            "configuration": self.get_params(deep=False),
            "determinism_limitation": "Seeded CPU execution is reproducible in the verified environment; bit-for-bit cross-platform determinism is not claimed.",
        }

    def decision_function(self, X):
        check_is_fitted(self, "classes_")
        X = check_array(X, ensure_2d=True, dtype=np.float64)
        if X.shape[1] != self.n_features_in_:
            raise ValueError("Hybrid prediction feature dimension does not match fitted input.")
        _, torch = require_hybrid_dependencies()
        self._model.eval()
        with torch.no_grad():
            return self._model(torch.tensor(X, dtype=torch.float64)).reshape(-1).cpu().numpy()

    def predict_proba(self, X):
        logits = self.decision_function(X)
        positive = 1.0 / (1.0 + np.exp(-np.clip(logits, -700, 700)))
        return np.column_stack([1.0 - positive, positive])

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)

    def quantum_features(self, X):
        """Testing/technical-evidence helper returning actual expectation values."""
        check_is_fitted(self, "classes_")
        X = check_array(X, ensure_2d=True, dtype=np.float64)
        _, torch = require_hybrid_dependencies()
        with torch.no_grad():
            return self._model[0](torch.tensor(X, dtype=torch.float64)).cpu().numpy()

    def __getstate__(self):
        state = self.__dict__.copy()
        model = state.pop("_model", None)
        state.pop("_qnode", None)
        if model is not None:
            state["_serialized_weights"] = {
                name: value.detach().cpu().numpy() for name, value in model.state_dict().items()
            }
        return state

    def __setstate__(self, state):
        weights = state.pop("_serialized_weights", None)
        self.__dict__.update(state)
        # Historical artifacts predate explicit provider identity. Preserve their
        # verified local execution path without mutating the stored artifact.
        self.provider_id = getattr(self, "provider_id", "pennylane_local")
        self.execution_mode = getattr(self, "execution_mode", "local_simulator")
        if weights is not None:
            self._build_runtime()
            _, torch = require_hybrid_dependencies()
            self._model.load_state_dict({name: torch.tensor(value, dtype=torch.float64) for name, value in weights.items()})
            self._model.eval()
