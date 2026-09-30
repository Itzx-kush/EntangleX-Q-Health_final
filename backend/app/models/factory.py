from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from ..api.schemas import TrainingConfig
from ..evaluation.calibration import with_calibration
from ..feature_engineering.pipeline import build_preprocessor
from ..quantum.estimator import QuantumClassifier
from .hybrid import PennyLaneTorchClassifier

def build_estimator(kind: str, config: TrainingConfig, features: list[str], numeric: list[str]):
    p = config.parameters
    if kind == "logistic_regression":
        model = LogisticRegression(C=p.logistic_c, max_iter=2000, random_state=config.seed, class_weight=p.class_weight)
    elif kind == "svm":
        # No internal SVC probability CV over already-fitted transforms.
        # Optional calibration wraps the entire pipeline instead.
        model = SVC(C=p.svm_c, kernel=p.svm_kernel, probability=False, random_state=config.seed, class_weight=p.class_weight)
    elif kind == "random_forest":
        model = RandomForestClassifier(n_estimators=p.forest_trees, max_depth=p.forest_max_depth, n_jobs=1, random_state=config.seed, class_weight=p.class_weight)
    elif kind in {"vqc", "qsvc", "qnn"}:
        model = QuantumClassifier(kind=kind, quantum=config.quantum.model_dump(), seed=config.seed, c=p.svm_c)
    elif kind == "hybrid_pennylane_torch":
        h = config.hybrid
        model = PennyLaneTorchClassifier(
            qubits=h.qubits, quantum_layers=h.quantum_layers,
            hidden_dimensions=tuple(h.classical_hidden_dimensions), activation=h.classical_activation,
            optimizer=h.optimizer, learning_rate=h.learning_rate, epochs=h.epochs,
            batch_size=h.batch_size, deterministic_seed=h.deterministic_seed,
            backend=h.backend, feature_map=h.feature_map,
        )
    else:
        raise ValueError("Unsupported model type.")
    pipe = Pipeline([("preprocessor", build_preprocessor(config.pipeline, features, numeric, config.seed)), ("classifier", model)])
    return with_calibration(pipe, config.calibration, config.calibration_folds, config.seed)
