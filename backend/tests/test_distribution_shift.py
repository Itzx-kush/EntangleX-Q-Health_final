"""Comprehensive tests for Distribution-Shift / Dataset-Shift Engine (Master Prompt 3)."""

from datetime import datetime
import hashlib
import time
from uuid import uuid4
import numpy as np
import pandas as pd
import pytest
from sqlalchemy import select

from app.api.schemas import (
    DatasetUploadMetadata,
    DistributionShiftConfig,
    DistributionShiftRequest,
    ExternalValidationRequest,
    TrainingConfig,
)
from app.database import session_scope
from app.data.service import register_csv
from app.storage.entities import (
    Artifact,
    Dataset,
    DatasetVersion,
    DistributionShiftAnalysis,
    Experiment,
    ExternalValidation,
    ModelRecord,
    MultiSeedStudy,
)
from app.storage.files import safe_path
from app.shift.constants import (
    DISTRIBUTION_SHIFT_POLICY_VERSION,
    SHIFT_DIRECTION_CONVENTION,
    SHIFT_LIMITATIONS,
)
from app.shift.service import (
    execute_shift_analysis,
    resolve_shift_preflight,
)


def poll_job(client, identity, timeout=90):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        response = client.get(f"/api/training/jobs/{identity}")
        assert response.status_code == 200
        value = response.json()
        if value["status"] not in ("queued", "running", "cancel_requested"):
            return value
        time.sleep(0.1)
    pytest.fail("Training job did not finish within the test timeout.")


@pytest.fixture
def trained_model_id(client, registered):
    cfg = TrainingConfig(
        dataset_id=registered.id,
        models=["logistic_regression"],
        max_samples=100,
        seed=42,
    )
    res = client.post("/api/training/jobs", json=cfg.model_dump(mode="json"))
    assert res.status_code == 202
    job_id = res.json()["job"]["id"]
    poll_job(client, job_id)
    with session_scope() as session:
        model = session.scalar(
            select(ModelRecord).where(
                ModelRecord.dataset_id == registered.id,
                ModelRecord.model_type == "logistic_regression",
                ModelRecord.status == "ready",
            )
        )
        assert model is not None
        return model.id


@pytest.fixture
def comp_dataset_clean():
    rng = np.random.default_rng(2026)
    frame = pd.DataFrame(rng.normal(size=(100, 6)), columns=[f"biomarker_{i}" for i in range(6)])
    latent = frame["biomarker_0"] + 0.5 * frame["biomarker_1"] + rng.normal(size=len(frame))
    frame["observed_class"] = np.where(latent > np.median(latent), "positive", "negative")
    meta = DatasetUploadMetadata(
        name="External Clean Cohort",
        target="observed_class",
        positive_label="positive",
        deidentified=True,
    )
    return register_csv(frame.to_csv(index=False).encode(), "ext_clean.csv", meta)


@pytest.fixture
def comp_dataset_shifted():
    rng = np.random.default_rng(999)
    # Significant shift: biomarker_0 shifted by +2.5 standard deviations
    frame = pd.DataFrame(rng.normal(size=(100, 6)), columns=[f"biomarker_{i}" for i in range(6)])
    frame["biomarker_0"] += 2.5
    # High missingness in biomarker_1
    frame.loc[0:25, "biomarker_1"] = np.nan
    # Extra column
    frame["unrelated_clinical_note_id"] = [f"note_{i}" for i in range(100)]
    latent = frame["biomarker_0"] + 0.5 * frame["biomarker_1"].fillna(0) + rng.normal(size=len(frame))
    frame["observed_class"] = np.where(latent > np.median(latent), "positive", "negative")
    meta = DatasetUploadMetadata(
        name="External Shifted Cohort",
        target="observed_class",
        positive_label="positive",
        deidentified=True,
    )
    return register_csv(frame.to_csv(index=False).encode(), "ext_shifted.csv", meta)


@pytest.fixture
def external_val_id(client, trained_model_id, comp_dataset_clean):
    payload = {
        "model_id": trained_model_id,
        "external_dataset_id": comp_dataset_clean.id,
    }
    res = client.post("/api/validation/external", json=payload)
    assert res.status_code == 201
    return res.json()["id"]


# ---------------------------------------------------------------------------
# Test 1: Valid dataset-vs-dataset shift analysis (CRUD + detail endpoints)
# ---------------------------------------------------------------------------
def test_valid_dataset_vs_dataset_analysis(client, registered, comp_dataset_clean):
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_clean.id,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["status"] == "completed"
    assert data["reference_dataset_id"] == registered.id
    assert data["comparison_dataset_id"] == comp_dataset_clean.id
    assert data["policy_version"] == DISTRIBUTION_SHIFT_POLICY_VERSION
    assert len(data["limitations"]) == len(SHIFT_LIMITATIONS)
    assert data["artifact_id"] is not None

    analysis_id = data["id"]

    # Detail endpoint
    detail_res = client.get(f"/api/shift-analysis/{analysis_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == analysis_id

    # List endpoint
    list_res = client.get("/api/shift-analysis")
    assert list_res.status_code == 200
    assert any(item["id"] == analysis_id for item in list_res.json())

    # Filtered list endpoint
    filt_res = client.get(f"/api/shift-analysis?reference_dataset_id={registered.id}")
    assert filt_res.status_code == 200
    assert all(item["reference_dataset_id"] == registered.id for item in filt_res.json())


# ---------------------------------------------------------------------------
# Test 2: Same dataset comparison handled cleanly with explicit baseline warning
# ---------------------------------------------------------------------------
def test_same_dataset_comparison_produces_zero_shift_baseline(client, registered):
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": registered.id,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "completed"
    assert any("identical" in w.lower() for w in data["warnings"])
    assert data["summary"]["shifted_features_count"] == 0
    assert data["summary"]["missingness_shifted_count"] == 0
    assert data["summary"]["target_shift_detected"] is False


# ---------------------------------------------------------------------------
# Test 3: Dataset version handling (explicit version ID)
# ---------------------------------------------------------------------------
def test_dataset_version_explicit_resolution(client, registered, comp_dataset_clean):
    with session_scope() as session:
        ref_v = session.scalar(select(DatasetVersion).where(DatasetVersion.dataset_id == registered.id))
        comp_v = session.scalar(select(DatasetVersion).where(DatasetVersion.dataset_id == comp_dataset_clean.id))
        ref_ver_id = ref_v.id if ref_v else None
        comp_ver_id = comp_v.id if comp_v else None

    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_clean.id,
        "reference_dataset_version_id": ref_ver_id,
        "comparison_dataset_version_id": comp_ver_id,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["reference_dataset_version_id"] == ref_ver_id
    assert data["comparison_dataset_version_id"] == comp_ver_id


# ---------------------------------------------------------------------------
# Test 4: Missing dataset rejected (404)
# ---------------------------------------------------------------------------
def test_missing_dataset_rejected(client, registered):
    fake_id = str(uuid4())
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": fake_id,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "dataset_not_found"


# ---------------------------------------------------------------------------
# Test 5: Missing dataset version rejected (404)
# ---------------------------------------------------------------------------
def test_missing_version_rejected(client, registered, comp_dataset_clean):
    fake_ver = str(uuid4())
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_clean.id,
        "reference_dataset_version_id": fake_ver,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "dataset_version_not_found"


# ---------------------------------------------------------------------------
# Test 6 & 7 & 8: Schema comparison: shared, missing, and extra columns
# ---------------------------------------------------------------------------
def test_schema_comparison_and_extra_columns(client, registered, comp_dataset_shifted):
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_shifted.id,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 201
    data = res.json()
    schema = data["schema_analysis"]

    assert "unrelated_clinical_note_id" in schema["extra_in_comparison"]
    assert "biomarker_0" in schema["shared_columns"]
    assert any("extra column" in w.lower() for w in data["warnings"])


# ---------------------------------------------------------------------------
# Test 9: Data type mismatch detection (numeric vs string)
# ---------------------------------------------------------------------------
def test_type_mismatch_detection(client, registered):
    rng = np.random.default_rng(77)
    frame = pd.DataFrame(rng.normal(size=(60, 6)), columns=[f"biomarker_{i}" for i in range(6)])
    # Convert biomarker_0 to strings
    frame["biomarker_0"] = [f"cat_value_{i % 3}" for i in range(60)]
    frame["observed_class"] = ["positive" if i % 2 == 0 else "negative" for i in range(60)]
    meta = DatasetUploadMetadata(
        name="Type Mismatched Cohort",
        target="observed_class",
        positive_label="positive",
        deidentified=True,
    )
    mismatch_ds = register_csv(frame.to_csv(index=False).encode(), "type_mismatch.csv", meta)

    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": mismatch_ds.id,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 201
    data = res.json()

    type_mismatches = data["schema_analysis"]["type_mismatches"]
    assert len(type_mismatches) >= 1
    assert any(m["feature"] == "biomarker_0" for m in type_mismatches)
    b0_record = next(f for f in data["feature_shifts"] if f["feature"] == "biomarker_0")
    assert b0_record["feature_type"] == "type_mismatch"
    assert b0_record["flagged"] is True


# ---------------------------------------------------------------------------
# Test 10 & 11 & 12: Target presence, target class comparison & prevalence delta
# ---------------------------------------------------------------------------
def test_target_shift_and_prevalence_delta(client, registered):
    rng = np.random.default_rng(88)
    frame = pd.DataFrame(rng.normal(size=(100, 6)), columns=[f"biomarker_{i}" for i in range(6)])
    # Set positive class to 80% instead of 50%
    frame["observed_class"] = ["positive" if i < 80 else "negative" for i in range(100)]
    meta = DatasetUploadMetadata(
        name="High Prevalence Cohort",
        target="observed_class",
        positive_label="positive",
        deidentified=True,
    )
    high_prev_ds = register_csv(frame.to_csv(index=False).encode(), "high_prev.csv", meta)

    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": high_prev_ds.id,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 201
    data = res.json()

    target_info = data["target_analysis"]
    assert target_info["target_evaluated"] is True
    assert target_info["compatible"] is True
    assert target_info["comparison_positive_prevalence"] == 0.80
    assert target_info["prevalence_delta"] is not None
    assert target_info["prevalence_delta"] > 0.20
    assert "Observed positive-class prevalence differs by" in target_info["interpretation"]


# ---------------------------------------------------------------------------
# Test 13: Missingness shift calculation & flagging
# ---------------------------------------------------------------------------
def test_missingness_shift_calculation(client, registered, comp_dataset_shifted):
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_shifted.id,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 201
    data = res.json()

    b1_shift = next(f for f in data["feature_shifts"] if f["feature"] == "biomarker_1")
    assert b1_shift["missingness"]["comparison_missing_count"] >= 25
    assert b1_shift["missingness"]["delta"] > 0.20
    assert b1_shift["missingness"]["flagged"] is True


# ---------------------------------------------------------------------------
# Test 14 & 15: Numeric descriptive stats, KS-test, and Wasserstein distance
# ---------------------------------------------------------------------------
def test_numeric_shift_descriptive_and_statistical(client, registered, comp_dataset_shifted):
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_shifted.id,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 201
    data = res.json()

    b0_shift = next(f for f in data["feature_shifts"] if f["feature"] == "biomarker_0")
    num = b0_shift["numeric"]
    assert num is not None
    assert num["mean_difference"] > 1.5
    assert num["statistic"] is not None
    assert num["statistic"] > 0.40  # Massive KS shift
    assert num["raw_p_value"] < 0.001
    assert num["distance_value"] > 1.0  # Wasserstein distance
    assert num["standardized_mean_difference"] is not None
    assert "large (heuristic)" in num["effect_size_label"]
    assert b0_shift["flagged"] is True


# ---------------------------------------------------------------------------
# Test 16 & 17: Categorical distribution shift & Total Variation Distance
# ---------------------------------------------------------------------------
def test_categorical_distribution_shift_and_tvd(client):
    rng = np.random.default_rng(55)
    # Ref: binary category 50/50
    ref_f = pd.DataFrame({
        "blood_group": ["A" if i % 2 == 0 else "B" for i in range(80)],
        "observed_class": ["positive" if i % 2 == 0 else "negative" for i in range(80)],
    })
    meta_ref = DatasetUploadMetadata(name="Ref Cat DS", target="observed_class", positive_label="positive", deidentified=True)
    ref_ds = register_csv(ref_f.to_csv(index=False).encode(), "ref_cat.csv", meta_ref)

    # Comp: blood group 90% A, 10% B, plus tiny sparse category O
    comp_f = pd.DataFrame({
        "blood_group": ["A" if i < 70 else ("B" if i < 78 else "O") for i in range(80)],
        "observed_class": ["positive" if i % 2 == 0 else "negative" for i in range(80)],
    })
    meta_comp = DatasetUploadMetadata(name="Comp Cat DS", target="observed_class", positive_label="positive", deidentified=True)
    comp_ds = register_csv(comp_f.to_csv(index=False).encode(), "comp_cat.csv", meta_comp)

    payload = {
        "reference_dataset_id": ref_ds.id,
        "comparison_dataset_id": comp_ds.id,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 201
    data = res.json()

    cat_shift = next(f for f in data["feature_shifts"] if f["feature"] == "blood_group")
    cat = cat_shift["categorical"]
    assert cat is not None
    assert cat["distance_metric"] == "total_variation_distance"
    assert cat["distance_value"] > 0.30
    assert cat_shift["flagged"] is True


# ---------------------------------------------------------------------------
# Test 18: Multiple-testing correction (Benjamini-Hochberg FDR)
# ---------------------------------------------------------------------------
def test_multiple_testing_benjamini_hochberg(client, registered, comp_dataset_shifted):
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_shifted.id,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 201
    data = res.json()

    tested_records = [f for f in data["feature_shifts"] if f["raw_p_value"] is not None]
    assert len(tested_records) >= 2
    for r in tested_records:
        assert r["adjusted_p_value"] is not None
        # Monotonicity property: adjusted_p_value >= raw_p_value
        assert r["adjusted_p_value"] >= (r["raw_p_value"] - 1e-9)


# ---------------------------------------------------------------------------
# Test 19: Deterministic feature flagging
# ---------------------------------------------------------------------------
def test_deterministic_feature_flagging(client, registered, comp_dataset_shifted):
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_shifted.id,
    }
    res1 = client.post("/api/shift-analysis", json=payload)
    assert res1.status_code == 201
    flags1 = res1.json()["flagged_features"]

    res2 = client.post("/api/shift-analysis", json=payload)
    assert res2.status_code == 201
    flags2 = res2.json()["flagged_features"]

    assert flags1 == flags2
    assert "biomarker_0" in flags1  # shifted mean
    assert "biomarker_1" in flags1  # shifted missingness


# ---------------------------------------------------------------------------
# Test 20: Threshold configuration validation (bounds check)
# ---------------------------------------------------------------------------
def test_threshold_configuration_validation(client, registered, comp_dataset_clean):
    # Invalid missingness threshold (exceeds max 0.50)
    invalid_payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_clean.id,
        "config": {
            "missingness_delta_threshold": 0.99,
        },
    }
    res = client.post("/api/shift-analysis", json=invalid_payload)
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Test 21: Model-relevant feature filtering (model_id provided)
# ---------------------------------------------------------------------------
def test_model_relevant_feature_filtering(client, registered, comp_dataset_shifted, trained_model_id):
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_shifted.id,
        "model_id": trained_model_id,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["model_id"] == trained_model_id
    assert data["summary"]["model_features_count"] == 6

    # Features endpoint with model_input_only=True
    feat_res = client.get(f"/api/shift-analysis/{data['id']}/features?model_input_only=true")
    assert feat_res.status_code == 200
    features = feat_res.json()["features"]
    assert all(f["is_model_input"] is True for f in features)


# ---------------------------------------------------------------------------
# Test 22: Corrupted model artifact rejected (409)
# ---------------------------------------------------------------------------
def test_corrupted_model_artifact_blocked(client, registered, comp_dataset_clean):
    with session_scope() as session:
        exp = Experiment(id=str(uuid4()), dataset_id=registered.id, config={})
        session.add(exp)
        corrupted = ModelRecord(
            id=str(uuid4()),
            experiment_id=exp.id,
            dataset_id=registered.id,
            model_type="logistic_regression",
            status="ready",
            artifact_sha256="bad" * 16,
        )
        session.add(corrupted)
        session.flush()
        c_id = corrupted.id

    p = safe_path("models", c_id, ".dill")
    p.write_bytes(b"corrupted bytes")

    try:
        payload = {
            "reference_dataset_id": registered.id,
            "comparison_dataset_id": comp_dataset_clean.id,
            "model_id": c_id,
        }
        res = client.post("/api/shift-analysis", json=payload)
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "integrity_error"
    finally:
        p.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test 23: External-validation integration (linking external_validation_id)
# ---------------------------------------------------------------------------
def test_external_validation_integration(client, registered, comp_dataset_clean, trained_model_id, external_val_id):
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_clean.id,
        "model_id": trained_model_id,
        "external_validation_id": external_val_id,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["external_validation_id"] == external_val_id


# ---------------------------------------------------------------------------
# Test 24 & 25: Shift artifact persistence & integrity verification
# ---------------------------------------------------------------------------
def test_shift_artifact_persistence_and_integrity(client, registered, comp_dataset_clean):
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_clean.id,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 201
    art_id = res.json()["artifact_id"]
    assert art_id is not None

    with session_scope() as session:
        art = session.scalar(select(Artifact).where(Artifact.id == art_id))
        assert art is not None
        assert art.artifact_type == "distribution_shift_report"
        assert art.details.get("analysis_id") == res.json()["id"]
        assert art.immutable is True


# ---------------------------------------------------------------------------
# Test 26 & 27: Reproducibility metadata & policy version persistence
# ---------------------------------------------------------------------------
def test_reproducibility_and_policy_version(client, registered, comp_dataset_clean):
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_clean.id,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 201
    data = res.json()

    prov = data["provenance"]
    assert prov["policy_version"] == DISTRIBUTION_SHIFT_POLICY_VERSION
    assert prov["direction"] == SHIFT_DIRECTION_CONVENTION
    assert prov["reference"]["dataset_id"] == registered.id
    assert prov["comparison"]["dataset_id"] == comp_dataset_clean.id
    assert "software_versions" in prov


# ---------------------------------------------------------------------------
# Test 28: No raw biomedical values stored in record or logs
# ---------------------------------------------------------------------------
def test_no_raw_data_in_shift_record(client, registered, comp_dataset_shifted):
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_shifted.id,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 201
    data = res.json()

    # Raw patient row values should never be stored in the top-level entity
    assert "data" not in data
    assert "rows" not in data
    assert "raw_samples" not in data


# ---------------------------------------------------------------------------
# Test 29: API request validation (rejects extra forbidden fields)
# ---------------------------------------------------------------------------
def test_api_schema_forbids_extra_fields(client, registered, comp_dataset_clean):
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_clean.id,
        "malicious_extra_field": "injected",
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Test 30: Authorization dependency respected
# ---------------------------------------------------------------------------
def test_authorization_respected(client, registered, comp_dataset_clean, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "api_token", "secret_research_token")

    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_clean.id,
    }
    # No auth header -> 401
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 401

    # Valid auth header -> 201
    res_auth = client.post(
        "/api/shift-analysis",
        json=payload,
        headers={"Authorization": "Bearer secret_research_token"},
    )
    assert res_auth.status_code == 201


# ---------------------------------------------------------------------------
# Test 31: Prompt 1 regression (Multi-seed studies unaffected)
# ---------------------------------------------------------------------------
def test_multi_seed_study_regression(client):
    res = client.get("/api/studies/multi-seed")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# ---------------------------------------------------------------------------
# Test 32: Prompt 2 regression (External validation unaffected)
# ---------------------------------------------------------------------------
def test_external_validation_regression(client):
    res = client.get("/api/validation/external")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# ---------------------------------------------------------------------------
# Test 33: Legacy dataset endpoint regression & dataset-related shift analyses
# ---------------------------------------------------------------------------
def test_legacy_dataset_endpoint_and_shift_link(client, registered, comp_dataset_clean):
    # Standard dataset endpoint works
    res_ds = client.get(f"/api/datasets/{registered.id}")
    assert res_ds.status_code == 200

    # Dataset shift analysis route
    res_shift = client.get(f"/api/datasets/{registered.id}/shift-analysis")
    assert res_shift.status_code == 200
    assert isinstance(res_shift.json(), list)


# ---------------------------------------------------------------------------
# Test 34: Deterministic repeated analysis produces identical results
# ---------------------------------------------------------------------------
def test_deterministic_repeated_analysis(client, registered, comp_dataset_clean):
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_clean.id,
    }
    res1 = client.post("/api/shift-analysis", json=payload)
    assert res1.status_code == 201
    summary1 = res1.json()["summary"]

    res2 = client.post("/api/shift-analysis", json=payload)
    assert res2.status_code == 201
    summary2 = res2.json()["summary"]

    assert summary1 == summary2


# ---------------------------------------------------------------------------
# Test 35: Non-mutating preflight endpoint
# ---------------------------------------------------------------------------
def test_shift_preflight_endpoint(client, registered, comp_dataset_clean):
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_clean.id,
    }
    res = client.post("/api/shift-analysis/preflight", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ready"] is True
    assert "schema_preview" in data
    assert "target_preview" in data


# ---------------------------------------------------------------------------
# Test 36: Provenance detail endpoint
# ---------------------------------------------------------------------------
def test_shift_provenance_endpoint(client, registered, comp_dataset_clean):
    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_clean.id,
    }
    create_res = client.post("/api/shift-analysis", json=payload)
    assert create_res.status_code == 201
    analysis_id = create_res.json()["id"]

    prov_res = client.get(f"/api/shift-analysis/{analysis_id}/provenance")
    assert prov_res.status_code == 200
    prov_data = prov_res.json()
    assert prov_data["analysis_id"] == analysis_id
    assert "provenance" in prov_data
    assert len(prov_data["limitations"]) == len(SHIFT_LIMITATIONS)


# ---------------------------------------------------------------------------
# Test 37: Performance/bounds test: no model training side effects
# ---------------------------------------------------------------------------
def test_shift_analysis_causes_zero_model_training(client, registered, comp_dataset_clean):
    with session_scope() as session:
        initial_model_count = session.scalar(select(Dataset).where(Dataset.id == registered.id))
        initial_models = len(list(session.scalars(select(ModelRecord))))

    payload = {
        "reference_dataset_id": registered.id,
        "comparison_dataset_id": comp_dataset_clean.id,
    }
    res = client.post("/api/shift-analysis", json=payload)
    assert res.status_code == 201

    with session_scope() as session:
        final_models = len(list(session.scalars(select(ModelRecord))))
        assert final_models == initial_models, "Shift analysis must not train models or create ModelRecord rows."
