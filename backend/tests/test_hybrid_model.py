from uuid import uuid4
import numpy as np
from sklearn.base import clone

from app.models.hybrid import PennyLaneTorchClassifier
from app.storage.files import load_model, save_model


def tiny_data():
    rng = np.random.default_rng(12)
    X = rng.normal(size=(16, 2))
    y = (X[:, 0] - 0.35 * X[:, 1] > 0).astype(int)
    return X, y


def estimator(seed=19):
    return PennyLaneTorchClassifier(
        qubits=2, quantum_layers=1, hidden_dimensions=(4,), activation="tanh",
        optimizer="adam", learning_rate=0.02, epochs=3, batch_size=4,
        deterministic_seed=seed,
    )


def test_real_estimator_fit_probability_decision_clone_and_quantum_update():
    X, y = tiny_data()
    model = estimator()
    copied = clone(model)
    assert copied.get_params()["qubits"] == 2
    model.fit(X, y)
    probabilities = model.predict_proba(X)
    assert probabilities.shape == (len(X), 2)
    assert np.all(np.isfinite(probabilities))
    assert np.allclose(probabilities.sum(axis=1), 1.0)
    assert model.decision_function(X).shape == (len(X),)
    assert set(model.predict(X)) <= {0, 1}
    assert model.classes_.tolist() == [0, 1]
    assert model.n_features_in_ == 2
    assert model.quantum_features(X[:3]).shape == (3, 2)
    assert model.quantum_metadata_["quantum_parameter_count"] > 0
    assert model.quantum_parameters_changed_ is True


def test_deterministic_seed_reproduces_probabilities():
    X, y = tiny_data()
    first, second = estimator(), estimator()
    first.fit(X, y); second.fit(X, y)
    assert np.allclose(first.predict_proba(X), second.predict_proba(X), atol=1e-10)


def test_restricted_artifact_round_trip_reconstructs_runtime():
    X, y = tiny_data()
    model = estimator().fit(X, y)
    before = model.predict_proba(X[:2])
    identity = str(uuid4())
    digest = save_model(identity, {"estimator": model})
    restored = load_model(identity, digest)["estimator"]
    after = restored.predict_proba(X[:2])
    assert np.allclose(before, after, atol=1e-10)
