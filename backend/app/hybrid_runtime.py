"""Live end-to-end verification for the flagship PennyLane + PyTorch hybrid path.

This verifier deliberately reuses the existing Early Stage Diabetes packaged
configuration and existing training/evaluation/artifact helpers. It never
changes the precomputed verified demo package and never falls back to a
classical model.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from importlib.util import find_spec
from threading import RLock
from typing import Any
from uuid import uuid4

import numpy as np

from .demo_readiness import validate_packaged_dataset
from .evaluation.metrics import score_outputs
from .evaluation.calibration import base_pipeline
from .explainability.hybrid_shap import HybridShapAdapter
from .models.training import train_model
from .data.splitting import prepare_data
from .quantum.service import service
from .storage.files import load_model, safe_path, save_model

_lock = RLock()
_last_result: dict[str, Any] | None = None

CHECK_NAMES = (
    "pennylane_import",
    "pytorch_import",
    "quantum_device_initialization",
    "preprocessing_and_feature_reduction",
    "quantum_forward_pass",
    "trainable_quantum_parameters",
    "hybrid_training",
    "positive_class_probability",
    "sensitivity_first_threshold",
    "shap_explainability",
    "artifact_save",
    "artifact_reload",
)


def _check(passed: bool, detail: str) -> dict[str, Any]:
    return {"status": "PASS" if passed else "FAIL", "detail": detail}


def _failed_result(checks: dict[str, Any], error: str, *, phases: list[str] | None = None) -> dict[str, Any]:
    return {
        "status": "FAILED",
        "verified": False,
        "verification_kind": "live_runtime",
        "dataset": "Early Stage Diabetes Risk Prediction",
        "model_type": "hybrid_pennylane_torch",
        "framework": "PennyLane",
        "classical_framework": "PyTorch",
        "execution": "local PennyLane quantum simulation",
        "backend": "default.qubit",
        "real_hardware": False,
        "checks": checks,
        "error": error,
        "phases": phases or [],
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "scientific_status": "Research prototype runtime verification; not clinical validation and not evidence of quantum advantage.",
    }


def _run_verification() -> dict[str, Any]:
    checks: dict[str, Any] = {}
    phases: list[str] = []
    packaged = validate_packaged_dataset("early-stage-diabetes")
    config_payload = packaged["experiment"]["config"]

    # Keep every flagship experiment condition intact while isolating this run to
    # the real hybrid model. No dataset, preprocessing, split, or threshold rule
    # is invented here.
    from .api.schemas import TrainingConfig

    config = TrainingConfig.model_validate(config_payload).model_copy(
        update={"models": ["hybrid_pennylane_torch"]}
    )
    phases.append("Loaded immutable Early Stage Diabetes flagship configuration")

    if find_spec("pennylane") is None:
        checks["pennylane_import"] = _check(False, "PennyLane is not installed in the backend environment.")
        checks["pytorch_import"] = _check(find_spec("torch") is not None, "PyTorch dependency probe completed.")
        return _failed_result(checks, "The live hybrid path cannot execute because PennyLane is unavailable.", phases=phases)

    try:
        import pennylane as qml
        checks["pennylane_import"] = _check(True, f"PennyLane {qml.__version__} imported successfully.")
    except (ImportError, OSError):
        checks["pennylane_import"] = _check(False, "PennyLane could not be imported.")
        return _failed_result(checks, "The live hybrid path cannot execute because PennyLane import failed.", phases=phases)

    if find_spec("torch") is None:
        checks["pytorch_import"] = _check(False, "PyTorch is not installed in the backend environment.")
        return _failed_result(checks, "The live hybrid path cannot execute because PyTorch is unavailable.", phases=phases)

    try:
        import torch
        checks["pytorch_import"] = _check(True, f"PyTorch {torch.__version__} imported successfully.")
    except (ImportError, OSError):
        checks["pytorch_import"] = _check(False, "PyTorch could not be imported.")
        return _failed_result(checks, "The live hybrid path cannot execute because PyTorch import failed.", phases=phases)

    try:
        runtime = service.prepare_model_runtime(
            "pennylane_local",
            "default.qubit",
            config.hybrid.model_dump(mode="json"),
            config.hybrid.deterministic_seed,
        )
        checks["quantum_device_initialization"] = _check(
            runtime.native_context is not None,
            "PennyLane default.qubit initialized successfully.",
        )
    except Exception:
        checks["quantum_device_initialization"] = _check(False, "PennyLane default.qubit initialization failed.")
        return _failed_result(checks, "The configured PennyLane local simulator could not initialize.", phases=phases)

    try:
        data = prepare_data(config)
        checks["preprocessing_and_feature_reduction"] = _check(
            len(data.train) > 0
            and len(data.test) > 0
            and config.pipeline.pca_components == config.hybrid.qubits,
            f"Existing preprocessing produced a {config.pipeline.pca_components}-component representation for the {config.hybrid.qubits}-qubit hybrid model.",
        )
        phases.append("Executed existing preprocessing, feature selection, PCA, and angle scaling")
    except Exception:
        checks["preprocessing_and_feature_reduction"] = _check(False, "The existing flagship preprocessing pipeline could not be fitted.")
        return _failed_result(checks, "The Early Stage Diabetes preprocessing path could not be executed.", phases=phases)

    phase_log: list[str] = []

    def checkpoint(message: str) -> None:
        phase_log.append(message)

    try:
        bundle, metrics, details = train_model(
            "hybrid_pennylane_torch",
            config,
            data,
            checkpoint,
        )
        phases.extend(phase_log)
        checks["hybrid_training"] = _check(True, "Real hybrid CV training and final fitting completed.")
    except Exception:
        checks["hybrid_training"] = _check(False, "The PennyLane + PyTorch training path raised an execution failure.")
        return _failed_result(checks, "The existing live hybrid training path did not complete successfully.", phases=phases)

    estimator = bundle["estimator"]
    pipeline = base_pipeline(estimator)
    classifier = pipeline.named_steps["classifier"]

    try:
        transformed_test = pipeline.named_steps["preprocessor"].transform(
            data.X.iloc[data.test[: min(4, len(data.test))]]
        )
        quantum_values = np.asarray(classifier.quantum_features(transformed_test), dtype=float)
        checks["quantum_forward_pass"] = _check(
            quantum_values.ndim == 2
            and quantum_values.shape[1] == config.hybrid.qubits
            and np.isfinite(quantum_values).all(),
            f"Quantum layer returned {quantum_values.shape[1]} expectation values per sample.",
        )
        checks["trainable_quantum_parameters"] = _check(
            bool(getattr(classifier, "quantum_parameters_changed_", False)),
            "Recorded quantum parameters changed between initialization and the final optimizer step.",
        )
    except Exception:
        checks["quantum_forward_pass"] = _check(False, "The executed quantum layer did not return a valid expectation-value representation.")
        checks["trainable_quantum_parameters"] = _check(False, "The hybrid verifier could not confirm trainable quantum parameter updates.")
        return _failed_result(checks, "The live quantum representation could not be verified after training.", phases=phases)

    try:
        test_frame = data.X.iloc[data.test]
        _, score, probabilities = score_outputs(
            estimator,
            test_frame,
            config.probability_threshold,
        )
        if probabilities is None or not np.isfinite(probabilities).all():
            raise ValueError("positive-class probabilities unavailable")
        positive_probability = float(probabilities[0])
        evaluation_threshold = float(bundle["operating_threshold"])
        predicted_label = int(positive_probability >= evaluation_threshold)
        threshold_source = str(bundle["threshold_source"])
        checks["positive_class_probability"] = _check(
            0.0 <= positive_probability <= 1.0,
            "The real PyTorch output head produced a finite positive-class probability.",
        )
        checks["sensitivity_first_threshold"] = _check(
            config.threshold_strategy == "target_sensitivity"
            and threshold_source in {
                "out_of_fold_validation",
                "configured_fixed_fallback_after_infeasible_validation",
            },
            f"Prediction used the existing {config.threshold_strategy} operating-point logic with threshold source '{threshold_source}'.",
        )
    except Exception:
        checks["positive_class_probability"] = _check(False, "The trained hybrid estimator did not produce a valid positive-class probability.")
        checks["sensitivity_first_threshold"] = _check(False, "The existing operating-point threshold could not be applied.")
        return _failed_result(checks, "The hybrid prediction/threshold path could not be verified.", phases=phases)

    try:
        background = data.X.iloc[data.train]
        explained = test_frame.iloc[[0]]
        shap_result = HybridShapAdapter(
            estimator,
            background,
            data.features,
            data.numeric,
            evaluation_threshold,
            config.seed,
        ).explain(explained, repeats=1)
        checks["shap_explainability"] = _check(
            shap_result.values.shape == (1, len(data.features))
            and np.isfinite(shap_result.values).all()
            and np.isfinite(shap_result.probabilities).all(),
            "SHAP evaluated the real hybrid positive-class output for one held-out case.",
        )
    except Exception:
        checks["shap_explainability"] = _check(False, "The existing hybrid SHAP path did not produce a valid contribution array.")
        return _failed_result(checks, "The live hybrid model trained successfully but its real SHAP path failed.", phases=phases)

    artifact_id = str(uuid4())
    artifact_sha256 = None
    try:
        artifact_sha256 = save_model(artifact_id, bundle)
        checks["artifact_save"] = _check(bool(artifact_sha256), "Existing HMAC-protected model artifact save completed.")
        reloaded = load_model(artifact_id, artifact_sha256)
        reload_probability = float(
            score_outputs(reloaded["estimator"], test_frame.iloc[[0]], config.probability_threshold)[2][0]
        )
        checks["artifact_reload"] = _check(
            np.isfinite(reload_probability) and 0.0 <= reload_probability <= 1.0,
            "Saved hybrid artifact reloaded into a rebuilt PennyLane runtime and produced a valid probability.",
        )
    except Exception:
        checks["artifact_save"] = _check(False, "Existing model artifact serialization failed.")
        checks["artifact_reload"] = _check(False, "Existing model artifact reload failed.")
        return _failed_result(checks, "The hybrid artifact could not be saved and reloaded through the existing storage mechanism.", phases=phases)
    finally:
        try:
            safe_path("models", artifact_id, ".dill").unlink(missing_ok=True)
        except OSError:
            pass

    passed = all(check["status"] == "PASS" for check in checks.values())
    result = {
        "status": "VERIFIED" if passed else "FAILED",
        "verified": passed,
        "verification_kind": "live_runtime",
        "dataset": "Early Stage Diabetes Risk Prediction",
        "model_type": "hybrid_pennylane_torch",
        "framework": "PennyLane",
        "classical_framework": "PyTorch",
        "execution": "local PennyLane quantum simulation",
        "backend": "default.qubit",
        "real_hardware": False,
        "checks": checks,
        "configuration": {
            "qubits": config.hybrid.qubits,
            "quantum_layers": config.hybrid.quantum_layers,
            "hidden_dimensions": config.hybrid.classical_hidden_dimensions,
            "epochs": config.hybrid.epochs,
            "batch_size": config.hybrid.batch_size,
            "sample_cap": config.max_samples,
            "cv_folds": config.cv_folds,
            "seed": config.hybrid.deterministic_seed,
        },
        "prediction": {
            "positive_class_probability": positive_probability,
            "predicted_positive_class": predicted_label,
            "operating_threshold": evaluation_threshold,
            "threshold_source": threshold_source,
            "threshold_strategy": config.threshold_strategy,
            "target_sensitivity": config.target_sensitivity,
        },
        "quantum": {
            "expectation_value_dimension": int(quantum_values.shape[1]),
            "quantum_parameters_changed": bool(getattr(classifier, "quantum_parameters_changed_", False)),
            "metadata": details.get("quantum"),
        },
        "artifact": {
            "saved": checks["artifact_save"]["status"] == "PASS",
            "reloaded": checks["artifact_reload"]["status"] == "PASS",
        },
        "shap": {
            "explained_case_count": 1,
            "background_count": int(shap_result.background_count),
            "output_semantics": "final positive-class probability",
        },
        "timing": metrics.get("timing", {}),
        "phases": phases,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "scientific_status": "Verified live hybrid runtime using local quantum simulation; not clinical validation and not evidence of quantum advantage.",
    }
    return result


def verify_hybrid_runtime(*, force: bool = False) -> dict[str, Any]:
    global _last_result
    with _lock:
        if _last_result is not None and not force:
            return deepcopy(_last_result)
        try:
            _last_result = _run_verification()
        except Exception:
            _last_result = _failed_result({}, "The live hybrid verification could not complete. Inspect backend logs for the safe exception type.")
        return deepcopy(_last_result)


def runtime_verification_status() -> dict[str, Any]:
    with _lock:
        if _last_result is None:
            return {"status": "NOT_RUN", "verified": False, "verification_kind": "live_runtime"}
        return {
            "status": _last_result["status"],
            "verified": _last_result["verified"],
            "verification_kind": "live_runtime",
            "verified_at": _last_result.get("verified_at"),
        }
