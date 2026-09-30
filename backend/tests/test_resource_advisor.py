from uuid import uuid4

from app.api.schemas import ResourceAdvisorRequest, TrainingConfig
from app.database import session_scope
from app.quantum.resource_advisor import POLICY_VERSION, advise_resources, resource_policy
from app.storage.entities import Experiment, ModelRecord


def request(**updates):
    values = {
        "model_type": "qnn",
        "quantum": {
            "backend": "aer",
            "qubits": 4,
            "feature_map_reps": 1,
            "ansatz_reps": 1,
            "entanglement": "linear",
            "optimizer": "COBYLA",
            "maxiter": 30,
            "shots": 1024,
            "noise_probability": 0,
        },
        "feature_dimension": 4,
        "sample_count": 160,
    }
    values.update(updates)
    return ResourceAdvisorRequest.model_validate(values)


def test_within_near_and_exceeded_budget_are_explicit_and_deterministic():
    within = advise_resources(request())
    assert within["budget_status"]["status"] == "within_budget"
    assert within["recommendation"]["available"] is False
    near = advise_resources(request(quantum={**request().quantum.model_dump(), "qubits": 5}, feature_dimension=5))
    assert near["budget_status"]["status"] == "near_budget"
    over_request = request(
        quantum={
            "backend": "aer", "qubits": 8, "feature_map_reps": 3, "ansatz_reps": 3,
            "entanglement": "full", "optimizer": "SPSA", "maxiter": 300,
            "shots": 16384, "noise_probability": .05,
        },
        feature_dimension=8,
        sample_count=300,
    )
    first = advise_resources(over_request)
    second = advise_resources(over_request)
    assert first["resource_profile"] == second["resource_profile"]
    assert first["recommendation"] == second["recommendation"]
    assert first["budget_status"]["status"] == "exceeds_budget"
    assert first["recommendation"]["available"] is True
    assert first["recommendation"]["budget_status_after"]["status"] != "exceeds_budget"


def test_recommendation_is_valid_training_config_and_does_not_mutate_request():
    original = request(
        quantum={**request().quantum.model_dump(), "qubits": 8, "feature_map_reps": 3, "ansatz_reps": 3, "maxiter": 300, "shots": 16384},
        feature_dimension=8,
        sample_count=1000,
    )
    snapshot = original.model_dump()
    result = advise_resources(original)
    recommended = result["recommendation"]["configuration"]
    assert original.model_dump() == snapshot
    assert recommended["feature_dimension"] == recommended["quantum"]["qubits"]
    validated = TrainingConfig(
        dataset_id=uuid4(),
        models=[recommended["model_type"]],
        quantum=recommended["quantum"],
        pipeline={"pca_components": recommended["quantum"]["qubits"], "angle_scaling": True},
        max_samples=recommended["sample_count"],
    )
    assert validated.pipeline.pca_components == validated.quantum.qubits
    assert [change["field"] for change in result["recommendation"]["changes"]] == [
        "shots", "maxiter", "ansatz_reps", "feature_map_reps", "qubits", "sample_count"
    ]


def test_statevector_has_no_fabricated_measurement_or_runtime_estimate():
    result = advise_resources(request(quantum={**request().quantum.model_dump(), "backend": "statevector", "shots": 16384}))
    assert result["budget_status"]["status"] == "within_budget"
    assert result["resource_profile"]["shots_per_circuit_evaluation"] is None
    assert result["resource_profile"]["measurement_workload"] == "not_applicable_exact_statevector"
    assert "estimated_runtime" not in str(result).lower()
    assert result["resource_profile"]["hardware_execution"] is False
    assert any("Hardware execution is not available" in value for value in result["limitations"])


def test_policy_uses_schema_bounds_and_version():
    policy = resource_policy()
    assert policy["version"] == POLICY_VERSION
    assert policy["schema_bounds"]["qubits"] == {"minimum": 2, "maximum": 8}
    assert policy["schema_bounds"]["shots"] == {"minimum": 128, "maximum": 16384}
    assert policy["bounded_prototype_limits"]["sample_count"] > 0


def test_historical_evidence_uses_only_recorded_measurements(registered):
    model_id = str(uuid4())
    experiment_id = str(uuid4())
    with session_scope() as session:
        session.add(Experiment(
            id=experiment_id,
            dataset_id=registered.id,
            status="succeeded",
            config={},
            summary={},
        ))
        session.flush()
        session.add(ModelRecord(
            id=model_id,
            experiment_id=experiment_id,
            dataset_id=registered.id,
            model_type="qnn",
            status="ready",
            metrics={"timing": {"final_training_seconds": 12.5, "cv_total_seconds": 30.0, "test_inference_seconds": .2}},
            details={
                "split": {"evaluated_sample_count": 80},
                "quantum": {
                    "backend": "aer",
                    "shots": 1024,
                    "configuration": request().quantum.model_dump(),
                    "objective_evaluations": 9,
                    "circuit": {"qubits": 4, "logical_depth": 7, "gate_counts": {"cx": 2, "rz": 5}},
                },
            },
        ))
    history = advise_resources(request())["historical_evidence"]
    found = next(item for item in history["runs"] if item["model_id"] == model_id)
    assert found["final_training_seconds"] == 12.5
    assert found["gate_count"] == 7
    assert history["median_training_seconds"] is not None


def test_no_matching_historical_evidence_returns_null_measurements():
    result = advise_resources(request(model_type="vqc", quantum={**request().quantum.model_dump(), "qubits": 7}, feature_dimension=7))
    history = result["historical_evidence"]
    assert history["matched_runs"] == 0
    assert history["median_training_seconds"] is None


def test_api_validation_and_policy_endpoints(client):
    malformed = client.post("/api/quantum/resource-advisor", json={
        "model_type": "qnn",
        "quantum": {**request().quantum.model_dump(), "qubits": 4},
        "feature_dimension": 3,
        "sample_count": 80,
    })
    assert malformed.status_code == 422
    response = client.post("/api/quantum/resource-advisor", json=request().model_dump(mode="json"))
    assert response.status_code == 200, response.text
    assert response.json()["budget_policy"]["version"] == POLICY_VERSION
    assert client.get("/api/quantum/resource-policy").json()["version"] == POLICY_VERSION