"""Canonical SIH judge-alignment metadata. No model execution lives here."""
from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec
from .data.catalog import get_builtin_dataset

HYBRID_MODEL_ID = "hybrid_pennylane_torch"
FEATURED_CONTEXT_ID = "early-stage-diabetes"
IMPLEMENTATION_AVAILABLE = "AVAILABLE"
IMPLEMENTATION_PENDING = "NOT_YET_IMPLEMENTED"
IMPLEMENTATION_UNAVAILABLE = "UNAVAILABLE"

MODEL_CAPABILITIES = (
    {"model_id": "logistic_regression", "display_name": "Logistic Regression", "category": "classical", "implementation_status": IMPLEMENTATION_AVAILABLE, "executable": True},
    {"model_id": "svm", "display_name": "SVM", "category": "classical", "implementation_status": IMPLEMENTATION_AVAILABLE, "executable": True},
    {"model_id": "random_forest", "display_name": "Random Forest", "category": "classical", "implementation_status": IMPLEMENTATION_AVAILABLE, "executable": True},
    {"model_id": "vqc", "display_name": "VQC", "category": "quantum", "implementation_status": IMPLEMENTATION_AVAILABLE, "executable": True},
    {"model_id": "qsvc", "display_name": "QSVC", "category": "quantum", "implementation_status": IMPLEMENTATION_AVAILABLE, "executable": True},
    {"model_id": "qnn", "display_name": "QNN", "category": "quantum", "implementation_status": IMPLEMENTATION_AVAILABLE, "executable": True},
    {
        "model_id": HYBRID_MODEL_ID,
        "display_name": "PennyLane + PyTorch Hybrid",
        "category": "hybrid quantum-classical",
        "implementation_status": IMPLEMENTATION_UNAVAILABLE,
        "executable": False,
        "quantum_framework": "PennyLane",
        "classical_framework": "PyTorch",
        "execution": "local PennyLane quantum simulation",
        "hardware_execution": IMPLEMENTATION_UNAVAILABLE,
        "probability_output": "positive-class probability",
        "explainability": "SHAP contribution to the final hybrid model output",
        "supported_prediction": "available when dependencies are importable",
        "supported_comparison": "available when dependencies are importable",
        "supported_thresholding": "existing OOF threshold engine",
        "supported_robustness": "existing frozen-artifact robustness engine",
        "training": IMPLEMENTATION_UNAVAILABLE,
    },
)

ARCHITECTURE_STAGES = (
    "Data validation", "Classical preprocessing", "Feature selection / dimension reduction",
    "Quantum feature transformation", "PennyLane quantum circuit", "Expectation values / quantum representation",
    "PyTorch classical output head", "Positive-class probability", "OOF validated sensitivity-first threshold",
    "Research risk stratification", "SHAP explanation",
)

def package_status(package: str) -> dict:
    installed = find_spec(package) is not None
    importable = False
    if installed:
        try:
            import_module(package)
            importable = True
        except (ImportError, OSError):
            importable = False
    return {"package_installed": installed, "package_importable": importable}

def alignment_contract() -> dict:
    dataset = get_builtin_dataset(FEATURED_CONTEXT_ID)
    qiskit, aer, pennylane, torch = (package_status(name) for name in ("qiskit", "qiskit_aer", "pennylane", "torch"))
    hybrid_executable = pennylane["package_importable"] and torch["package_importable"]
    frameworks = {
        "qiskit": {**qiskit, "model_implemented": True, "model_executable": qiskit["package_importable"], "simulator_available": qiskit["package_importable"], "real_hardware_available": False, "runtime_verified": False},
        "qiskit_aer": {**aer, "model_implemented": True, "model_executable": aer["package_importable"], "simulator_available": aer["package_importable"], "real_hardware_available": False, "runtime_verified": False},
        "pennylane": {**pennylane, "model_implemented": True, "model_executable": hybrid_executable, "simulator_available": pennylane["package_importable"], "real_hardware_available": False, "runtime_verified": False},
        "torch": {**torch, "model_implemented": True, "model_executable": hybrid_executable, "simulator_available": False, "real_hardware_available": False, "runtime_verified": False},
    }
    models = [dict(item) for item in MODEL_CAPABILITIES]
    hybrid = next(item for item in models if item["model_id"] == HYBRID_MODEL_ID)
    hybrid.update({
        "implementation_status": IMPLEMENTATION_AVAILABLE if hybrid_executable else IMPLEMENTATION_UNAVAILABLE,
        "executable": hybrid_executable,
        "training": IMPLEMENTATION_AVAILABLE if hybrid_executable else IMPLEMENTATION_UNAVAILABLE,
    })
    return {
        "contract_version": "2026-09-30",
        "models": models,
        "frameworks": frameworks,
        "showcase": {
            "id": FEATURED_CONTEXT_ID,
            "display_name": "Early Stage Diabetes Risk Prediction",
            "label": "Featured SIH demonstration",
            "featured_dataset_slug": FEATURED_CONTEXT_ID,
            "disease_domain": dataset["domain"],
            "target": dataset["target"],
            "positive_class": dataset["positive_label"],
            "dataset_hash": dataset["sha256"],
            "research_only_disclaimer": "Research benchmark only; not a diagnosis, clinical validation, or treatment recommendation.",
            "recommended_models": ["logistic_regression", "svm", "random_forest", "vqc", "qsvc", "qnn", HYBRID_MODEL_ID],
        },
        "flagship_experiment_preset": {
            "id": "sih-diabetes-demonstration",
            "display_name": "SIH Diabetes Demonstration",
            "dataset_slug": FEATURED_CONTEXT_ID,
            "models": ["logistic_regression", "svm", "random_forest", "vqc", "qsvc", "qnn", HYBRID_MODEL_ID],
            "auto_start_training": False,
            "threshold_strategy": "target_sensitivity",
            "evidence_requirements": ["same dataset hash", "same preprocessing", "same split", "same sample policy", "same evaluation configuration"],
        },
        "flagship_architecture": {"model_id": HYBRID_MODEL_ID, "status": "IMPLEMENTED" if hybrid_executable else "UNAVAILABLE", "stages": list(ARCHITECTURE_STAGES)},
    }

def model_capability(model_id: str) -> dict:
    return next(item for item in alignment_contract()["models"] if item["model_id"] == model_id)
