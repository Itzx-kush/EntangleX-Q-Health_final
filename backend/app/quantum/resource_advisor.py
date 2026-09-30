"""Cheap, deterministic planning advice for the bounded simulator prototype."""

from __future__ import annotations

from copy import deepcopy
from statistics import median
from uuid import UUID

from sqlalchemy import select

from ..api.schemas import PipelineConfig, ResourceAdvisorRequest, TrainingConfig
from ..config import get_settings
from ..database import session_scope
from ..storage.entities import ModelRecord
from ..utils.serialization import clean_json


POLICY_VERSION = "bounded-simulator-resource-policy-v1"


def _schema_bounds() -> dict:
    from ..api.schemas import QuantumConfig

    properties = QuantumConfig.model_json_schema()["properties"]
    return {
        name: {"minimum": properties[name].get("minimum"), "maximum": properties[name].get("maximum")}
        for name in ["qubits", "feature_map_reps", "ansatz_reps", "maxiter", "shots", "noise_probability"]
    }


def resource_policy() -> dict:
    """One canonical policy; schema bounds remain owned by Pydantic."""

    return {
        "version": POLICY_VERSION,
        "scope": "single-workstation local/statevector/Aer research prototype",
        "schema_bounds": _schema_bounds(),
        "bounded_prototype_limits": {
            "qubits": 6,
            "feature_map_reps": 2,
            "ansatz_reps": 2,
            "maxiter": 100,
            "aer_shots": 4096,
            "sample_count": get_settings().quantum_max_samples,
        },
        "near_budget_fraction": 0.75,
        "safe_baseline": {
            "qubits": 4,
            "feature_map_reps": 1,
            "ansatz_reps": 1,
            "maxiter": 30,
            "shots": 1024,
            "sample_count": min(160, get_settings().quantum_max_samples),
        },
        "recommendation_order": ["shots", "maxiter", "ansatz_reps", "feature_map_reps", "qubits", "sample_count"],
        "semantics": (
            "Budget limits are explicit engineering guardrails inside the wider validated schema. "
            "They are not wall-clock predictions, model-quality rankings, or QPU capacity claims."
        ),
    }


def _load_label(ratio: float) -> str:
    if ratio <= 0.5:
        return "low"
    if ratio <= 0.75:
        return "moderate"
    return "high"


def _resource_profile(request: ResourceAdvisorRequest, policy: dict) -> dict:
    q = request.quantum
    limits = policy["bounded_prototype_limits"]
    circuit_ratio = max(
        q.qubits / limits["qubits"],
        q.feature_map_reps / limits["feature_map_reps"],
        q.ansatz_reps / limits["ansatz_reps"],
    )
    if q.entanglement == "full":
        circuit_ratio += 0.15
    optimization_ratio = q.maxiter / limits["maxiter"]
    measurement_ratio = q.shots / limits["aer_shots"] if q.backend == "aer" else 0.0
    sample_ratio = request.sample_count / limits["sample_count"]
    return {
        "logical_qubits": q.qubits,
        "feature_dimension": request.feature_dimension,
        "feature_map_repetitions": q.feature_map_reps,
        "ansatz_repetitions": q.ansatz_reps if request.model_type in {"vqc", "qnn"} else 0,
        "entanglement": q.entanglement,
        "logical_depth": None,
        "gate_count": None,
        "parameter_count": None,
        "circuit_complexity": _load_label(circuit_ratio),
        "optimizer": q.optimizer,
        "optimizer_iteration_budget": q.maxiter,
        "optimization_workload": _load_label(optimization_ratio),
        "backend": q.backend,
        "execution_kind": "exact local statevector simulation" if q.backend == "statevector" else "finite-shot local Aer simulation",
        "shots_per_circuit_evaluation": None if q.backend == "statevector" else q.shots,
        "measurement_workload": "not_applicable_exact_statevector" if q.backend == "statevector" else _load_label(measurement_ratio),
        "noise_probability": q.noise_probability,
        "noise_mode": "density-matrix simulator path" if q.noise_probability else "no configured simulator noise",
        "sample_count": request.sample_count,
        "bounded_quantum_sample_cap": limits["sample_count"],
        "sample_workload": _load_label(sample_ratio),
        "structural_metadata_status": "Logical depth, gate count, and parameter count require a generated or fitted circuit and are not guessed by this advisor.",
        "hardware_execution": False,
    }


def _budget_status(request: ResourceAdvisorRequest, policy: dict) -> dict:
    q, limits = request.quantum, policy["bounded_prototype_limits"]
    values = {
        "qubits": q.qubits,
        "feature_map_reps": q.feature_map_reps,
        "ansatz_reps": q.ansatz_reps if request.model_type in {"vqc", "qnn"} else 0,
        "maxiter": q.maxiter,
        "sample_count": request.sample_count,
    }
    if q.backend == "aer":
        values["shots"] = q.shots
    limit_names = {**limits, "shots": limits["aer_shots"]}
    reasons = [
        f"{name}={value} exceeds the bounded prototype limit {limit_names[name]}."
        for name, value in values.items()
        if value > limit_names[name]
    ]
    if reasons:
        return {"status": "exceeds_budget", "reasons": reasons}
    near = [
        f"{name}={value} is at least {int(policy['near_budget_fraction'] * 100)}% of the bounded limit {limit_names[name]}."
        for name, value in values.items()
        if value >= policy["near_budget_fraction"] * limit_names[name]
    ]
    if q.noise_probability:
        near.append("Noise-enabled Aer uses the density-matrix simulator path and increases simulator pressure.")
    return {
        "status": "near_budget" if near else "within_budget",
        "reasons": near or ["Every evaluated resource dimension is inside the bounded prototype policy."],
    }


def _recommendation(request: ResourceAdvisorRequest, policy: dict, budget: dict) -> dict:
    original = request.model_dump(mode="json")
    if budget["status"] == "within_budget":
        return {
            "available": False,
            "original_configuration": original,
            "configuration": None,
            "changes": [],
            "rationale": "The requested configuration is already inside the bounded prototype resource policy.",
            "valid": True,
            "policy_version": policy["version"],
        }

    q = deepcopy(original["quantum"])
    sample_count = request.sample_count
    limits, baseline = policy["bounded_prototype_limits"], policy["safe_baseline"]
    near = policy["near_budget_fraction"]
    changes = []

    def reduce(field: str, current, target, reason: str):
        if current > target:
            q[field] = target
            changes.append({"field": field, "from": current, "to": target, "reason": reason})

    if q["backend"] == "aer" and q["shots"] >= limits["aer_shots"] * near:
        reduce("shots", q["shots"], baseline["shots"], "Reduces finite-shot measurement workload while preserving the requested circuit structure.")
    if q["maxiter"] >= limits["maxiter"] * near:
        reduce("maxiter", q["maxiter"], baseline["maxiter"], "Bounds the requested optimizer iteration budget; this does not guarantee convergence or runtime.")
    if request.model_type in {"vqc", "qnn"} and q["ansatz_reps"] >= limits["ansatz_reps"] * near:
        reduce("ansatz_reps", q["ansatz_reps"], baseline["ansatz_reps"], "Reduces trainable circuit repetition pressure.")
    if q["feature_map_reps"] >= limits["feature_map_reps"] * near:
        reduce("feature_map_reps", q["feature_map_reps"], baseline["feature_map_reps"], "Reduces repeated feature-encoding circuit structure.")
    if q["qubits"] >= limits["qubits"] * near:
        previous = q["qubits"]
        q["qubits"] = baseline["qubits"]
        changes.append({"field": "qubits", "from": previous, "to": q["qubits"], "reason": "Reduces simulator state/circuit width and keeps PCA dimension equal to qubits."})
    if sample_count >= limits["sample_count"] * near:
        previous = sample_count
        sample_count = baseline["sample_count"]
        changes.append({"field": "sample_count", "from": previous, "to": sample_count, "reason": "Restores the repository's bounded common quantum sample budget."})

    if not changes:
        return {
            "available": False,
            "original_configuration": original,
            "configuration": None,
            "changes": [],
            "rationale": "The configuration is near budget only because of the requested noise-enabled simulator path; no numeric setting is automatically discouraged.",
            "valid": True,
            "policy_version": policy["version"],
        }

    recommended = {
        "model_type": request.model_type,
        "quantum": q,
        "feature_dimension": q["qubits"],
        "sample_count": sample_count,
        "dataset_id": original["dataset_id"],
        "experiment_id": original["experiment_id"],
    }
    # Reuse the exact training contract, including quantum/PCA compatibility.
    TrainingConfig(
        dataset_id=request.dataset_id or UUID("00000000-0000-0000-0000-000000000001"),
        models=[request.model_type],
        quantum=q,
        pipeline=PipelineConfig(pca_components=q["qubits"], angle_scaling=True),
        max_samples=sample_count,
    )
    after_request = ResourceAdvisorRequest.model_validate(recommended)
    return {
        "available": True,
        "original_configuration": original,
        "configuration": recommended,
        "changes": changes,
        "rationale": "Changes follow the documented policy order and reduce dimensions responsible for a near- or over-budget state.",
        "valid": True,
        "policy_version": policy["version"],
        "resource_profile_after": _resource_profile(after_request, policy),
        "budget_status_after": _budget_status(after_request, policy),
    }


def _historical_evidence(request: ResourceAdvisorRequest) -> dict:
    with session_scope() as session:
        records = list(session.scalars(
            select(ModelRecord)
            .where(ModelRecord.status == "ready", ModelRecord.model_type == request.model_type)
            .order_by(ModelRecord.created_at.desc())
            .limit(100)
        ))
    matches = []
    for record in records:
        details, metrics = record.details or {}, record.metrics or {}
        quantum = details.get("quantum") or {}
        configuration = quantum.get("configuration") or details.get("configuration", {}).get("quantum") or {}
        circuit = quantum.get("circuit") or {}
        if configuration.get("backend", quantum.get("backend")) != request.quantum.backend:
            continue
        if circuit.get("qubits", configuration.get("qubits")) != request.quantum.qubits:
            continue
        timing = metrics.get("timing") or {}
        training = timing.get("final_training_seconds")
        if not isinstance(training, (int, float)):
            continue
        split = details.get("split") or {}
        sample_count = split.get("evaluated_sample_count")
        matching_factors = {
            "dataset_context": request.dataset_id is not None and record.dataset_id == str(request.dataset_id),
            "experiment_context": request.experiment_id is not None and record.experiment_id == str(request.experiment_id),
            "optimizer": configuration.get("optimizer") == request.quantum.optimizer,
            "maxiter": configuration.get("maxiter") == request.quantum.maxiter,
            "shots": request.quantum.backend == "statevector" or quantum.get("shots", configuration.get("shots")) == request.quantum.shots,
            "sample_count": sample_count == request.sample_count,
        }
        matches.append({
            "model_id": record.id,
            "experiment_id": record.experiment_id,
            "model_type": record.model_type,
            "backend": request.quantum.backend,
            "qubits": request.quantum.qubits,
            "shots": quantum.get("shots", configuration.get("shots")),
            "maxiter": configuration.get("maxiter"),
            "optimizer": configuration.get("optimizer"),
            "feature_dimension": circuit.get("qubits", configuration.get("qubits")),
            "sample_count": sample_count,
            "final_training_seconds": training,
            "cv_total_seconds": timing.get("cv_total_seconds"),
            "inference_seconds": timing.get("test_inference_seconds"),
            "objective_evaluations": quantum.get("objective_evaluations"),
            "logical_depth": circuit.get("logical_depth"),
            "gate_count": sum((circuit.get("gate_counts") or {}).values()) if circuit.get("gate_counts") else None,
            "matching_factors": matching_factors,
            "_match_count": sum(matching_factors.values()),
        })
    matches = sorted(matches, key=lambda item: item["_match_count"], reverse=True)[:20]
    for item in matches:
        item.pop("_match_count")
    training_times = [item["final_training_seconds"] for item in matches]
    return {
        "matched_runs": len(matches),
        "median_training_seconds": median(training_times) if training_times else None,
        "min_training_seconds": min(training_times) if training_times else None,
        "max_training_seconds": max(training_times) if training_times else None,
        "measured_fields": ["final_training_seconds", "cv_total_seconds", "inference_seconds", "objective_evaluations", "logical_depth", "gate_count"],
        "matching_policy": "Exact quantum model type, backend, and qubit count; up to 20 records ranked by matching dataset/experiment context, optimizer, iterations, shots, and sample count. Differences remain visible.",
        "runs": matches,
        "limitations": [
            "Observed historical runtime is not a guaranteed runtime estimate for the requested configuration.",
            "Machine load, software versions, optimizer behavior, data, and circuit structure can differ between runs.",
        ],
    }


def advise_resources(request: ResourceAdvisorRequest) -> dict:
    policy = resource_policy()
    budget = _budget_status(request, policy)
    recommendation = _recommendation(request, policy, budget)
    return clean_json({
        "requested_configuration": request.model_dump(mode="json"),
        "resource_profile": _resource_profile(request, policy),
        "budget_status": budget,
        "budget_policy": policy,
        "recommendation": recommendation,
        "changed_parameters": recommendation["changes"],
        "historical_evidence": _historical_evidence(request),
        "limitations": [
            "Resource labels are deterministic engineering heuristics, not wall-clock predictions or model-quality scores.",
            "Historical timing is displayed only from recorded completed runs; no runtime value is fabricated.",
            "Logical circuit resources and simulator workload do not imply real-QPU cost or performance.",
            "Hardware execution is not available in the current verified configuration.",
            "Applying a recommendation requires an explicit user action and does not start training.",
        ],
    })