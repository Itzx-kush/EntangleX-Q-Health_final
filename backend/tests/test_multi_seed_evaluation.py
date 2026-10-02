import json
import time
from uuid import uuid4
import numpy as np
import pytest

from sqlalchemy import select

from app.api.schemas import MultiSeedStudyRequest, TrainingConfig
from app.database import session_scope
from app.storage.entities import Artifact, Experiment, MultiSeedStudy, Run, StudyRun
from app.storage.repository import require
from app.studies.service import create_study, execute_study
from app.studies.stats import (
    MULTI_SEED_LIMITATIONS,
    aggregate_study_results,
    compute_bootstrap_interval,
    compute_descriptive_stats,
    compute_paired_comparison,
)
from app.utils.serialization import canonical_json_bytes, fingerprint


def poll_study(client, study_id: str, timeout: int = 60) -> dict:
    for _ in range(timeout):
        res = client.get(f"/api/studies/multi-seed/{study_id}")
        assert res.status_code == 200, res.text
        data = res.json()
        if data["study"]["status"] in {"completed", "partial", "failed", "cancelled"}:
            return data
        time.sleep(0.2)
    raise TimeoutError(f"Study {study_id} did not finish within {timeout} iterations.")


# ---------------------------------------------------------------------------
# 1. Valid multi-seed study creation & end-to-end execution
# ---------------------------------------------------------------------------
def test_valid_multi_seed_study_creation_and_execution(client, registered):
    cfg = TrainingConfig(
        dataset_id=registered.id,
        models=["logistic_regression"],
        max_samples=100,
    )
    payload = {
        "config": cfg.model_dump(mode="json"),
        "seeds": [23, 42, 71],
    }
    create_res = client.post("/api/studies/multi-seed", json=payload)
    assert create_res.status_code == 202, create_res.text
    created = create_res.json()
    study_id = created["study"]["id"]
    assert created["study"]["status"] in {"queued", "running", "completed"}
    assert created["study"]["requested_seeds"] == [23, 42, 71]
    assert len(created["runs"]) == 3

    detail = poll_study(client, study_id)
    assert detail["study"]["status"] == "completed"
    assert detail["study"]["completed_seeds"] == [23, 42, 71]
    assert detail["study"]["failed_seeds"] == []
    assert detail["summary"] is not None
    assert "aggregates" in detail["summary"]
    assert "logistic_regression" in detail["summary"]["aggregates"]


# ---------------------------------------------------------------------------
# 2. Duplicate seeds rejected
# ---------------------------------------------------------------------------
def test_duplicate_seeds_rejected(client, registered):
    cfg = TrainingConfig(dataset_id=registered.id, models=["logistic_regression"])
    payload = {
        "config": cfg.model_dump(mode="json"),
        "seeds": [42, 71, 42],
    }
    res = client.post("/api/studies/multi-seed", json=payload)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"
    assert any("seeds" in f.get("location", []) for f in res.json()["error"]["fields"])



# ---------------------------------------------------------------------------
# 3. Invalid seed rejected
# ---------------------------------------------------------------------------
def test_invalid_seed_rejected(client, registered):
    cfg = TrainingConfig(dataset_id=registered.id, models=["logistic_regression"])
    # Negative seed
    res_neg = client.post(
        "/api/studies/multi-seed",
        json={"config": cfg.model_dump(mode="json"), "seeds": [-1, 42]},
    )
    assert res_neg.status_code == 422

    # Seed exceeding upper bound
    res_big = client.post(
        "/api/studies/multi-seed",
        json={"config": cfg.model_dump(mode="json"), "seeds": [42, 3000000000]},
    )
    assert res_big.status_code == 422


# ---------------------------------------------------------------------------
# 4. Minimum/maximum seed bound
# ---------------------------------------------------------------------------
def test_min_and_max_seed_bounds(client, registered):
    cfg = TrainingConfig(dataset_id=registered.id, models=["logistic_regression"])
    # Less than 2 seeds
    res_one = client.post(
        "/api/studies/multi-seed",
        json={"config": cfg.model_dump(mode="json"), "seeds": [42]},
    )
    assert res_one.status_code == 422

    # More than 20 seeds
    res_many = client.post(
        "/api/studies/multi-seed",
        json={"config": cfg.model_dump(mode="json"), "seeds": list(range(25))},
    )
    assert res_many.status_code == 422


# ---------------------------------------------------------------------------
# 5. Exact configuration locking
# ---------------------------------------------------------------------------
def test_exact_configuration_locking(client, registered):
    cfg = TrainingConfig(
        dataset_id=registered.id,
        models=["logistic_regression"],
        max_samples=100,
        test_size=0.25,
        cv_folds=3,
    )
    create_res = client.post(
        "/api/studies/multi-seed",
        json={"config": cfg.model_dump(mode="json"), "seeds": [11, 22]},
    )
    assert create_res.status_code == 202
    study_id = create_res.json()["study"]["id"]
    poll_study(client, study_id)

    with session_scope() as session:
        study = require(session, MultiSeedStudy, study_id)
        runs = list(session.scalars(select(Run).join(StudyRun, StudyRun.run_id == Run.id).where(StudyRun.study_id == study_id)))
        assert len(runs) == 2
        for run in runs:
            # Check configuration matches locked config except seed
            for key in ["dataset_id", "test_size", "cv_folds", "max_samples", "models", "pipeline"]:
                assert run.config[key] == study.locked_config[key]


# ---------------------------------------------------------------------------
# 6. One Run created per requested seed
# ---------------------------------------------------------------------------
def test_one_run_created_per_requested_seed(client, registered):
    cfg = TrainingConfig(dataset_id=registered.id, models=["logistic_regression"], max_samples=80)
    seeds = [101, 202, 303]
    res = client.post(
        "/api/studies/multi-seed",
        json={"config": cfg.model_dump(mode="json"), "seeds": seeds},
    )
    assert res.status_code == 202
    study_id = res.json()["study"]["id"]
    poll_study(client, study_id)

    with session_scope() as session:
        study_runs = list(session.scalars(select(StudyRun).where(StudyRun.study_id == study_id)))
        assert len(study_runs) == 3
        run_ids = [sr.run_id for sr in study_runs]
        assert len(set(run_ids)) == 3
        assert all(rid is not None for rid in run_ids)


# ---------------------------------------------------------------------------
# 7. Correct study-to-run association
# ---------------------------------------------------------------------------
def test_correct_study_to_run_association(client, registered):
    cfg = TrainingConfig(dataset_id=registered.id, models=["logistic_regression"], max_samples=80)
    seeds = [55, 66]
    res = client.post(
        "/api/studies/multi-seed",
        json={"config": cfg.model_dump(mode="json"), "seeds": seeds},
    )
    study_id = res.json()["study"]["id"]
    poll_study(client, study_id)

    runs_res = client.get(f"/api/studies/multi-seed/{study_id}/runs")
    assert runs_res.status_code == 200
    runs = runs_res.json()
    assert len(runs) == 2
    assert [r["seed"] for r in runs] == seeds
    assert [r["seed_order"] for r in runs] == [0, 1]
    assert all(r["study_id"] == study_id for r in runs)
    assert all(r["status"] == "completed" for r in runs)


# ---------------------------------------------------------------------------
# 8. Successful aggregate calculation
# ---------------------------------------------------------------------------
def test_successful_aggregate_calculation(client, registered):
    cfg = TrainingConfig(dataset_id=registered.id, models=["logistic_regression"], max_samples=80)
    res = client.post(
        "/api/studies/multi-seed",
        json={"config": cfg.model_dump(mode="json"), "seeds": [7, 14]},
    )
    study_id = res.json()["study"]["id"]
    poll_study(client, study_id)

    summary_res = client.get(f"/api/studies/multi-seed/{study_id}/summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert "aggregates" in summary
    model_agg = summary["aggregates"]["logistic_regression"]
    assert "accuracy" in model_agg["metrics"]
    acc_metric = model_agg["metrics"]["accuracy"]
    assert acc_metric["valid_count"] == 2
    assert acc_metric["missing_count"] == 0
    assert 0 <= acc_metric["mean"] <= 1
    assert acc_metric["interval_95"] is not None


# ---------------------------------------------------------------------------
# 9. Missing metric handling
# ---------------------------------------------------------------------------
def test_missing_metric_handling():
    values_by_seed = {10: 0.85, 20: None, 30: 0.90}
    all_seeds = [10, 20, 30]
    stats = compute_descriptive_stats("roc_auc", values_by_seed, all_seeds, bootstrap_seed=42)
    assert stats["n"] == 3
    assert stats["valid_count"] == 2
    assert stats["missing_count"] == 1
    assert stats["missing_seeds"] == [20]
    assert stats["mean"] == round((0.85 + 0.90) / 2, 6)

    # All missing
    all_missing = {10: None, 20: None}
    stats_empty = compute_descriptive_stats("pr_auc", all_missing, [10, 20], bootstrap_seed=42)
    assert stats_empty["valid_count"] == 0
    assert stats_empty["missing_count"] == 2
    assert stats_empty["mean"] is None
    assert stats_empty["interval_95"] is None


# ---------------------------------------------------------------------------
# 10. Mean calculation
# ---------------------------------------------------------------------------
def test_mean_calculation():
    values = {1: 0.80, 2: 0.85, 3: 0.90}
    stats = compute_descriptive_stats("accuracy", values, [1, 2, 3], bootstrap_seed=123)
    assert stats["mean"] == 0.85


# ---------------------------------------------------------------------------
# 11. Median calculation
# ---------------------------------------------------------------------------
def test_median_calculation():
    values = {1: 0.70, 2: 0.85, 3: 0.95}
    stats = compute_descriptive_stats("accuracy", values, [1, 2, 3], bootstrap_seed=123)
    assert stats["median"] == 0.85


# ---------------------------------------------------------------------------
# 12. Standard deviation calculation
# ---------------------------------------------------------------------------
def test_standard_deviation_calculation():
    values = {1: 0.80, 2: 0.90}
    stats = compute_descriptive_stats("accuracy", values, [1, 2], bootstrap_seed=123)
    expected_std = round(float(np.std([0.80, 0.90], ddof=1)), 6)
    assert stats["std"] == expected_std


# ---------------------------------------------------------------------------
# 13. Min/Max calculation
# ---------------------------------------------------------------------------
def test_min_max_calculation():
    values = {1: 0.72, 2: 0.91, 3: 0.84}
    stats = compute_descriptive_stats("accuracy", values, [1, 2, 3], bootstrap_seed=123)
    assert stats["min"] == 0.72
    assert stats["max"] == 0.91


# ---------------------------------------------------------------------------
# 14. Deterministic interval calculation
# ---------------------------------------------------------------------------
def test_deterministic_interval_calculation():
    values = [0.81, 0.85, 0.88, 0.92, 0.86]
    int1 = compute_bootstrap_interval(values, seed=999)
    int2 = compute_bootstrap_interval(values, seed=999)
    assert int1 == int2
    assert int1["lower"] is not None
    assert int1["upper"] is not None
    assert int1["lower"] <= int1["upper"]
    assert "descriptive" in int1["interpretation"]


# ---------------------------------------------------------------------------
# 15. Paired seed delta calculation
# ---------------------------------------------------------------------------
def test_paired_seed_delta_calculation(client, registered):
    cfg = TrainingConfig(
        dataset_id=registered.id,
        models=["logistic_regression", "random_forest"],
        max_samples=80,
    )
    seeds = [12, 34]
    res = client.post(
        "/api/studies/multi-seed",
        json={"config": cfg.model_dump(mode="json"), "seeds": seeds},
    )
    study_id = res.json()["study"]["id"]
    poll_study(client, study_id)

    comp_res = client.get(f"/api/studies/multi-seed/{study_id}/comparison")
    assert comp_res.status_code == 200
    comparisons = comp_res.json()
    assert len(comparisons) > 0
    acc_comp = next((c for c in comparisons if c["metric_name"] == "accuracy"), None)
    assert acc_comp is not None
    assert acc_comp["available"] is True
    assert len(acc_comp["observations"]) == 2
    for obs in acc_comp["observations"]:
        assert obs["delta"] == round(obs["value_a"] - obs["value_b"], 6)


# ---------------------------------------------------------------------------
# 16. Mismatched seed sets rejected from paired comparison
# ---------------------------------------------------------------------------
def test_mismatched_seed_sets_rejected_from_paired_comparison():
    # Disjoint seeds
    a_values = {10: 0.85, 20: 0.88}
    b_values = {30: 0.82, 40: 0.84}
    comp = compute_paired_comparison("model_a", "model_b", "accuracy", a_values, b_values, [10, 20, 30, 40], bootstrap_seed=42)
    assert comp["available"] is False
    assert comp["valid_pairs_count"] == 0
    assert comp["mean_delta"] is None
    assert "no matching seed" in comp["reason"].lower()


# ---------------------------------------------------------------------------
# 17. Partial failure handling
# ---------------------------------------------------------------------------
def test_partial_failure_handling(client, registered):
    with session_scope() as session:
        cfg = TrainingConfig(dataset_id=registered.id, models=["logistic_regression"], max_samples=80)
        req = MultiSeedStudyRequest(config=cfg, seeds=[111, 222])
        study, runs = create_study(session, req)
        study_id = study.id

    # Execute seed 111 successfully, and artificially fail seed 222
    with session_scope() as session:
        st = require(session, MultiSeedStudy, study_id)
        st.status = "partial"
        st.completed_seeds = [111]
        st.failed_seeds = [222]
        r1 = require(session, StudyRun, runs[0].id)
        r1.status = "completed"
        r2 = require(session, StudyRun, runs[1].id)
        r2.status = "failed"
        r2.failure = {"code": "mock_failure", "message": "Simulated hardware error"}

    detail_res = client.get(f"/api/studies/multi-seed/{study_id}")
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["study"]["status"] == "partial"
    assert data["study"]["completed_seeds"] == [111]
    assert data["study"]["failed_seeds"] == [222]
    assert data["runs"][1]["failure"]["code"] == "mock_failure"


# ---------------------------------------------------------------------------
# 18. Failed study handling
# ---------------------------------------------------------------------------
def test_failed_study_handling(client, registered):
    with session_scope() as session:
        cfg = TrainingConfig(dataset_id=registered.id, models=["logistic_regression"], max_samples=80)
        req = MultiSeedStudyRequest(config=cfg, seeds=[501, 502])
        study, runs = create_study(session, req)
        study_id = study.id
        study.status = "failed"
        study.completed_seeds = []
        study.failed_seeds = [501, 502]
        study.aggregate_summary = {}
        for r in runs:
            sr = require(session, StudyRun, r.id)
            sr.status = "failed"
            sr.failure = {"code": "execution_failed", "message": "Failed"}

    detail = client.get(f"/api/studies/multi-seed/{study_id}").json()
    assert detail["study"]["status"] == "failed"
    assert detail["study"]["completed_seeds"] == []
    assert len(detail["study"]["failed_seeds"]) == 2

    # Summary endpoint returns 409
    sum_res = client.get(f"/api/studies/multi-seed/{study_id}/summary")
    assert sum_res.status_code == 409


# ---------------------------------------------------------------------------
# 19. Idempotency behavior
# ---------------------------------------------------------------------------
def test_idempotency_behavior(client, registered):
    cfg = TrainingConfig(dataset_id=registered.id, models=["logistic_regression"], max_samples=80)
    key = f"study-idem-{uuid4()}"
    payload = {"config": cfg.model_dump(mode="json"), "seeds": [88, 99]}

    res1 = client.post("/api/studies/multi-seed", json=payload, headers={"Idempotency-Key": key})
    assert res1.status_code == 202
    study_id1 = res1.json()["study"]["id"]

    # Repeat exact same request with same key
    res2 = client.post("/api/studies/multi-seed", json=payload, headers={"Idempotency-Key": key})
    assert res2.status_code == 202
    assert res2.json()["study"]["id"] == study_id1

    # Conflict: same key with different seeds
    payload_diff = {"config": cfg.model_dump(mode="json"), "seeds": [77, 88]}
    res_conflict = client.post("/api/studies/multi-seed", json=payload_diff, headers={"Idempotency-Key": key})
    assert res_conflict.status_code == 409


# ---------------------------------------------------------------------------
# 20. Study artifact persistence
# ---------------------------------------------------------------------------
def test_study_artifact_persistence(client, registered):
    cfg = TrainingConfig(dataset_id=registered.id, models=["logistic_regression"], max_samples=80)
    res = client.post(
        "/api/studies/multi-seed",
        json={"config": cfg.model_dump(mode="json"), "seeds": [3, 9]},
    )
    study_id = res.json()["study"]["id"]
    poll_study(client, study_id)

    with session_scope() as session:
        study = require(session, MultiSeedStudy, study_id)
        assert study.study_artifact_id is not None
        artifact = require(session, Artifact, study.study_artifact_id)
        assert artifact.artifact_type == "multi_seed_study_summary"
        assert artifact.details["study_id"] == study_id
        assert "aggregates" in artifact.details


# ---------------------------------------------------------------------------
# 21. Artifact integrity / hash behavior
# ---------------------------------------------------------------------------
def test_artifact_integrity_hash_behavior(client, registered):
    cfg = TrainingConfig(dataset_id=registered.id, models=["logistic_regression"], max_samples=80)
    res = client.post(
        "/api/studies/multi-seed",
        json={"config": cfg.model_dump(mode="json"), "seeds": [4, 8]},
    )
    study_id = res.json()["study"]["id"]
    poll_study(client, study_id)

    with session_scope() as session:
        study = require(session, MultiSeedStudy, study_id)
        artifact = require(session, Artifact, study.study_artifact_id)
        expected_hash = fingerprint(artifact.details)
        assert artifact.integrity_hash == expected_hash


# ---------------------------------------------------------------------------
# 22. Reproducibility metadata
# ---------------------------------------------------------------------------
def test_reproducibility_metadata(client, registered):
    cfg = TrainingConfig(dataset_id=registered.id, models=["logistic_regression"], max_samples=80)
    res = client.post(
        "/api/studies/multi-seed",
        json={"config": cfg.model_dump(mode="json"), "seeds": [15, 25]},
    )
    study_id = res.json()["study"]["id"]
    poll_study(client, study_id)

    detail = client.get(f"/api/studies/multi-seed/{study_id}").json()
    repro = detail["reproducibility"]
    assert repro["requested_seeds"] == [15, 25]
    assert "configuration_fingerprint" in repro
    assert "statistical_aggregation_protocol" in repro
    assert repro["statistical_aggregation_protocol"]["bootstrap_interval"]["method"] == "bootstrap_percentile"
    assert repro["statistical_aggregation_protocol"]["bootstrap_interval"]["resamples"] == 2000
    assert len(repro["limitations"]) == len(MULTI_SEED_LIMITATIONS)


# ---------------------------------------------------------------------------
# 23. API schema validation
# ---------------------------------------------------------------------------
def test_api_schema_validation(client, registered):
    # Extra field forbidden
    res = client.post("/api/studies/multi-seed", json={"seeds": [1, 2], "unknown_field": "disallowed"})
    assert res.status_code == 422

    # Neither base_experiment_id nor config
    res_empty = client.post("/api/studies/multi-seed", json={"seeds": [1, 2]})
    assert res_empty.status_code == 422


# ---------------------------------------------------------------------------
# 24. Legacy experiment endpoint regression
# ---------------------------------------------------------------------------
def test_legacy_experiment_endpoint_regression(client):
    res = client.get("/api/experiments")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# ---------------------------------------------------------------------------
# 25. Legacy run endpoint regression
# ---------------------------------------------------------------------------
def test_legacy_run_endpoint_regression(client):
    res = client.get("/api/runs")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# ---------------------------------------------------------------------------
# 26. Existing model-training tests still pass
# ---------------------------------------------------------------------------
def test_existing_training_jobs_endpoint(client, registered):
    cfg = TrainingConfig(dataset_id=registered.id, models=["logistic_regression"], max_samples=80)
    res = client.post("/api/training/jobs", json=cfg.model_dump(mode="json"))
    assert res.status_code == 202
    assert "job" in res.json()
    assert "experiment" in res.json()


# ---------------------------------------------------------------------------
# 27. Create study from existing base_experiment_id
# ---------------------------------------------------------------------------
def test_create_study_from_existing_base_experiment(client, registered):
    cfg = TrainingConfig(dataset_id=registered.id, models=["logistic_regression"], max_samples=80)
    train_res = client.post("/api/training/jobs", json=cfg.model_dump(mode="json"))
    assert train_res.status_code == 202
    base_exp_id = train_res.json()["experiment"]["id"]

    study_res = client.post(
        "/api/studies/multi-seed",
        json={"base_experiment_id": base_exp_id, "seeds": [31, 32]},
    )
    assert study_res.status_code == 202
    study_id = study_res.json()["study"]["id"]
    detail = poll_study(client, study_id)
    assert detail["study"]["status"] == "completed"
    assert detail["study"]["base_experiment_id"] == base_exp_id


# ---------------------------------------------------------------------------
# 28. Cancel study endpoint
# ---------------------------------------------------------------------------
def test_cancel_study_endpoint(client, registered):
    with session_scope() as session:
        cfg = TrainingConfig(dataset_id=registered.id, models=["logistic_regression"])
        req = MultiSeedStudyRequest(config=cfg, seeds=[61, 62])
        study, runs = create_study(session, req)
        study_id = study.id

    cancel_res = client.post(f"/api/studies/multi-seed/{study_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] in {"cancel_requested", "cancelled"}


# ---------------------------------------------------------------------------
# 29. Deterministic fixture: 3-seed aggregation produces identical summary
# ---------------------------------------------------------------------------
def test_deterministic_3_seed_aggregation_fixture():
    study_id = "test-deterministic-study-12345"
    seeds = [10, 20, 30]
    models = ["logistic_regression", "random_forest"]

    seed_model_metrics = {
        10: {
            "logistic_regression": {"test": {"accuracy": 0.85, "sensitivity": 0.80, "f1": 0.82}, "timing": {"final_training_seconds": 0.12}},
            "random_forest": {"test": {"accuracy": 0.88, "sensitivity": 0.85, "f1": 0.86}, "timing": {"final_training_seconds": 0.45}},
        },
        20: {
            "logistic_regression": {"test": {"accuracy": 0.82, "sensitivity": 0.78, "f1": 0.80}, "timing": {"final_training_seconds": 0.11}},
            "random_forest": {"test": {"accuracy": 0.86, "sensitivity": 0.82, "f1": 0.84}, "timing": {"final_training_seconds": 0.42}},
        },
        30: {
            "logistic_regression": {"test": {"accuracy": 0.87, "sensitivity": 0.83, "f1": 0.85}, "timing": {"final_training_seconds": 0.13}},
            "random_forest": {"test": {"accuracy": 0.89, "sensitivity": 0.86, "f1": 0.87}, "timing": {"final_training_seconds": 0.48}},
        },
    }

    agg1, paired1 = aggregate_study_results(study_id, seeds, models, seed_model_metrics)
    agg2, paired2 = aggregate_study_results(study_id, seeds, models, seed_model_metrics)

    # Assert exact bitwise reproducibility
    bytes1 = canonical_json_bytes({"aggregates": agg1, "paired": paired1})
    bytes2 = canonical_json_bytes({"aggregates": agg2, "paired": paired2})
    assert bytes1 == bytes2
    assert fingerprint(agg1) == fingerprint(agg2)
    assert fingerprint(paired1) == fingerprint(paired2)
