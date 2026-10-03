from typing import Dict, Any, List, Optional
from uuid import uuid4
import json
import hashlib
from sqlalchemy import select
from backend.app.storage.entities import QuantumDiagnosticReport, Experiment, ModelRecord
from backend.app.quantum.schemas import QuantumPreflightRequest, QuantumDiagnosticReportOut, QuantumDiagnosticFinding, QuantumDiagnosticPreflightResponse
from backend.app.evaluation.context import resolve_model_evaluation_context
from backend.app.utils.errors import AppError


def _diagnostic_source_context(session, exp: Experiment, model: ModelRecord) -> dict:
    """Resolve full evaluation provenance, preserving honest legacy diagnostics.

    Older quantum records could be created before Runs existed. They remain
    diagnosable from their own experiment/model configuration, but are labeled
    explicitly rather than being represented as live or verified-demo Runs.
    """
    try:
        return resolve_model_evaluation_context(
            session, model.id, model.dataset_id
        ).source_context()
    except AppError:
        if model.run_id or (model.details or {}).get("experiment_kind") == "precomputed_verified_demo":
            raise
        if exp.id != model.experiment_id or exp.dataset_id != model.dataset_id:
            raise
        return {
            "type": "legacy_experiment_model",
            "model_id": model.id,
            "experiment_id": exp.id,
            "run_id": None,
            "dataset_id": model.dataset_id,
            "model_artifact_sha256": model.artifact_sha256,
            "configuration_fingerprint": hashlib.sha256(
                json.dumps(exp.config or {}, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "provenance": {
                "limitation": "Legacy record has no persisted Run or verified-demo package identity."
            },
        }

def compute_circuit_fingerprint(model_type: str, quantum_config: Dict[str, Any]) -> str:
    """Computes a deterministic fingerprint of the circuit configuration."""
    safe_dict = {
        "model_type": model_type,
        "qubits": quantum_config.get("qubits"),
        "reps": quantum_config.get("reps"),
        "entanglement": quantum_config.get("entanglement"),
        "feature_map": quantum_config.get("feature_map"),
        "ansatz": quantum_config.get("ansatz")
    }
    dumped = json.dumps(safe_dict, sort_keys=True)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()

def preflight_quantum_diagnostics(session, experiment_id: str, model_record_id: str) -> QuantumDiagnosticPreflightResponse:
    exp = session.query(Experiment).filter_by(id=experiment_id).first()
    if not exp:
        return QuantumDiagnosticPreflightResponse(feasible=False, blockers=["Experiment not found"])
        
    model = session.query(ModelRecord).filter_by(id=model_record_id, experiment_id=experiment_id).first()
    if not model:
        return QuantumDiagnosticPreflightResponse(feasible=False, blockers=["Model record not found"])
        
    if model.model_type not in ["vqc", "qsvc", "qnn", "hybrid_pennylane_torch"]:
        return QuantumDiagnosticPreflightResponse(
            feasible=False,
            unsupported_fields=[],
            warnings=["Model is not a supported quantum model type."],
            limitations=["Classical models do not support quantum diagnostics."]
        )
    _diagnostic_source_context(session, exp, model)
        
    return QuantumDiagnosticPreflightResponse(
        feasible=True,
        unsupported_fields=["gradient_history", "measurement_noise"],
        warnings=[],
        limitations=["Runtime shot timing is unavailable from local simulators."]
    )

def generate_quantum_diagnostics(session, experiment_id: str, model_record_id: str) -> QuantumDiagnosticReport:
    exp = session.query(Experiment).filter_by(id=experiment_id).first()
    model = session.query(ModelRecord).filter_by(id=model_record_id, experiment_id=experiment_id).first()
    
    if not exp or not model:
        raise ValueError("Invalid experiment or model record")
        
    source_context = _diagnostic_source_context(session, exp, model)
    quantum_config = exp.config.get("quantum", {})
    if model.model_type == "hybrid_pennylane_torch":
        quantum_config = exp.config.get("hybrid", {})
        
    # Analyze Feature Encoding
    pca_comps = exp.config.get("pipeline", {}).get("pca_components", quantum_config.get("qubits", 4))
    qubits = quantum_config.get("qubits", 4)
    
    warnings = []
    if pca_comps != qubits and model.model_type in ["vqc", "qsvc"]:
        warnings.append(QuantumDiagnosticFinding(
            severity="BLOCKER",
            code="ENCODING_MISMATCH",
            title="Feature Encoding Mismatch",
            description="The configured feature dimension is incompatible with the quantum encoding qubit count.",
            recommendation="Align PCA components with quantum qubits."
        ).dict())
        
    feature_encoding = {
        "original_features": pca_comps,
        "encoded_features": pca_comps,
        "qubit_count": qubits,
        "mapping_strategy": quantum_config.get("feature_map", "ZZFeatureMap"),
        "dimensionality_reduction": "pca"
    }
    
    # Circuit Structure
    reps = quantum_config.get("ansatz_reps", quantum_config.get("quantum_layers", quantum_config.get("reps", 2)))
    entanglement = quantum_config.get("entanglement", "linear")
    ansatz = quantum_config.get("ansatz", "RealAmplitudes")
    
    # Estimate depth based on config since we don't build it dynamically for non-Qiskit
    # If it's ZZFeatureMap + RealAmplitudes:
    depth = 1 + (2 * reps)
    parameterized_gates = qubits * (reps + 1)
    
    circuit_structure = {
        "qubits": qubits,
        "depth": depth,
        "parameterized_gates": parameterized_gates,
        "measurements": qubits,
        "entanglement_pattern": entanglement,
        "ansatz": ansatz
    }
    
    optimizer_profile = {
        "optimizer": quantum_config.get("optimizer", "COBYLA"),
        "iterations": quantum_config.get("maxiter", 100)
    }
    
    execution_evidence = (model.details or {}).get("quantum") or {}
    execution_profile = {
        "backend": quantum_config.get("backend", "statevector_simulator"),
        "execution_mode": quantum_config.get(
            "execution_mode",
            execution_evidence.get("execution_mode", "local_simulator"),
        ),
        "real_hardware": execution_evidence.get("real_hardware", False),
    }
    if quantum_config.get("shots") is not None:
        execution_profile["shots"] = quantum_config["shots"]
    measured_runtime = (model.metrics or {}).get("timing", {}).get("final_training_seconds")
    if measured_runtime is not None:
        execution_profile["runtime_seconds"] = measured_runtime
    
    resource_profile = {
        "qubits_configured": qubits,
        "qubits_observed": qubits,
        "circuit_depth": depth,
        "parameter_count": parameterized_gates,
        "shots_configured": quantum_config.get("shots")
    }
    
    noise_profile = {
        "noise_model": "NO_NOISE_MODEL",
        "noise_enabled": False
    }
    
    provenance = {
        **source_context,
        "model_record_id": model.id,
        "model_type": model.model_type,
        "seed": exp.config.get("seed", "SEED_UNSPECIFIED"),
        "diagnostic_basis": "persisted configuration and model provenance",
    }
    
    fingerprint = compute_circuit_fingerprint(model.model_type, quantum_config)
    
    existing = session.scalar(
        select(QuantumDiagnosticReport).where(
            QuantumDiagnosticReport.experiment_id == exp.id,
            QuantumDiagnosticReport.model_record_id == model.id,
            QuantumDiagnosticReport.configuration_fingerprint == fingerprint,
            QuantumDiagnosticReport.status == "completed",
        ).order_by(QuantumDiagnosticReport.created_at.desc())
    )
    if existing is not None:
        return existing

    limitations = [
        "Loss curve history unavailable when the persisted estimator does not expose it.",
        "Gradient magnitudes unavailable.",
        "Local simulation evidence does not represent real quantum hardware timing.",
        "This diagnostic report does not establish quantum advantage.",
    ]
    report = QuantumDiagnosticReport(
        id=str(uuid4()),
        experiment_id=exp.id,
        model_record_id=model.id,
        model_type=model.model_type,
        status="completed",
        model_configuration=quantum_config,
        feature_encoding=feature_encoding,
        circuit_structure=circuit_structure,
        resource_profile=resource_profile,
        optimizer_profile=optimizer_profile,
        training_profile={"loss_history_status": "not_available"},
        execution_profile=execution_profile,
        stability_profile={}, # Could be populated for multi-seed
        noise_profile=noise_profile,
        warnings=warnings,
        limitations=limitations,
        configuration_fingerprint=fingerprint,
        provenance=provenance
    )
    
    session.add(report)
    session.commit()
    return report
