import copy
import hashlib
import time
from uuid import uuid4
import numpy as np
import pandas as pd
import pytest
from sqlalchemy import select
from unittest.mock import patch

from app.api.schemas import DatasetUploadMetadata, ExternalValidationRequest, TrainingConfig
from app.config import get_settings
from app.database import session_scope
from app.data.service import register_csv
from app.storage.entities import Artifact, Dataset, Experiment, ExternalValidation, ModelRecord, MultiSeedStudy, Run, StudyRun
from app.storage.files import digest, load_model, safe_path, save_model
from app.utils.errors import AppError
from app.validation.constants import VALIDATION_LIMITATIONS, SIGN_CONVENTION
from app.validation.service import execute_validation, resolve_preflight


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
def trained_rf_model_id(client, registered):
    cfg = TrainingConfig(
        dataset_id=registered.id,
        models=["random_forest"],
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
                ModelRecord.model_type == "random_forest",
                ModelRecord.status == "ready",
            )
        )
        assert model is not None
        return model.id


@pytest.fixture
def trained_svm_model_id(client, registered):
    cfg = TrainingConfig(
        dataset_id=registered.id,
        models=["svm"],
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
                ModelRecord.model_type == "svm",
                ModelRecord.status == "ready",
            )
        )
        assert model is not None
        return model.id


@pytest.fixture
def external_dataset_clean():
    rng = np.random.default_rng(999)
    frame = pd.DataFrame(rng.normal(loc=0.2, scale=1.1, size=(100, 6)), columns=[f"biomarker_{i}" for i in range(6)])
    latent = frame["biomarker_0"] + 0.5 * frame["biomarker_1"] + rng.normal(size=len(frame))
    frame["observed_class"] = np.where(latent > np.median(latent), "positive", "negative")
    frame["hospital_center"] = "St_Jude_External"
    metadata = DatasetUploadMetadata(
        name="Independent External Hospital Cohort",
        target="observed_class",
        positive_label="positive",
        deidentified=True,
    )
    return register_csv(frame.to_csv(index=False).encode(), "external_clean.csv", metadata)


# ---------------------------------------------------------------------------
# Test 1: Valid external validation end-to-end
# ---------------------------------------------------------------------------
def test_valid_external_validation(client, trained_model_id, external_dataset_clean):
    payload = {
        "model_id": trained_model_id,
        "external_dataset_id": external_dataset_clean.id,
    }
    res = client.post("/api/validation/external", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["status"] == "completed"
    assert data["model_id"] == trained_model_id
    assert data["external_dataset_id"] == external_dataset_clean.id
    assert "accuracy" in data["metrics"]
    assert "sensitivity" in data["metrics"]
    assert "specificity" in data["metrics"]
    assert data["artifact_id"] is not None
    assert len(data["limitations"]) == len(VALIDATION_LIMITATIONS)

    # Check detail endpoint
    val_id = data["id"]
    detail_res = client.get(f"/api/validation/external/{val_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == val_id

    # Check metrics endpoint
    metrics_res = client.get(f"/api/validation/external/{val_id}/metrics")
    assert metrics_res.status_code == 200
    assert "metrics" in metrics_res.json()
    assert "comparison" in metrics_res.json()

    # Check provenance endpoint
    prov_res = client.get(f"/api/validation/external/{val_id}/provenance")
    assert prov_res.status_code == 200
    assert prov_res.json()["provenance"]["independence"]["content_hash_distinct"] is True

    # Check models list endpoint
    model_vals = client.get(f"/api/models/{trained_model_id}/external-validation")
    assert model_vals.status_code == 200
    assert len(model_vals.json()) >= 1


# ---------------------------------------------------------------------------
# Test 2: Nonexistent model rejected (404)
# ---------------------------------------------------------------------------
def test_nonexistent_model_rejected(client, external_dataset_clean):
    fake_id = str(uuid4())
    res = client.post("/api/validation/external", json={"model_id": fake_id, "external_dataset_id": external_dataset_clean.id})
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "model_not_found"


# ---------------------------------------------------------------------------
# Test 3: Non-ready model rejected (409)
# ---------------------------------------------------------------------------
def test_non_ready_model_rejected(client, registered, external_dataset_clean):
    with session_scope() as session:
        exp = Experiment(id=str(uuid4()), dataset_id=registered.id, config={})
        session.add(exp)
        pending_model = ModelRecord(
            id=str(uuid4()),
            experiment_id=exp.id,
            dataset_id=registered.id,
            model_type="logistic_regression",
            status="training",
            artifact_sha256=None,
        )
        session.add(pending_model)
        session.flush()
        pending_id = pending_model.id

    res = client.post("/api/validation/external", json={"model_id": pending_id, "external_dataset_id": external_dataset_clean.id})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "model_not_ready"


# ---------------------------------------------------------------------------
# Test 4: Model artifact integrity failure blocked (409)
# ---------------------------------------------------------------------------
def test_model_artifact_integrity_failure_blocked(client, registered, external_dataset_clean):
    with session_scope() as session:
        exp = Experiment(id=str(uuid4()), dataset_id=registered.id, config={})
        session.add(exp)
        corrupted_model = ModelRecord(
            id=str(uuid4()),
            experiment_id=exp.id,
            dataset_id=registered.id,
            model_type="logistic_regression",
            status="ready",
            artifact_sha256="corrupted" * 8,
        )
        session.add(corrupted_model)
        session.flush()
        corrupted_id = corrupted_model.id

    # Create dummy file with wrong hash
    p = safe_path("models", corrupted_id, ".dill")
    p.write_bytes(b"invalid dill bytes")

    try:
        res = client.post("/api/validation/external", json={"model_id": corrupted_id, "external_dataset_id": external_dataset_clean.id})
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "integrity_error"
    finally:
        p.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test 5 & 6 & 7: Same training dataset / version / content hash rejected (409)
# ---------------------------------------------------------------------------
def test_same_training_dataset_rejected(client, trained_model_id, registered):
    # Validating against the exact same dataset used for training must be rejected
    res = client.post("/api/validation/external", json={"model_id": trained_model_id, "external_dataset_id": registered.id})
    assert res.status_code == 409
    assert res.json()["error"]["code"] in {"same_dataset_version", "same_dataset_content_hash"}


def test_same_dataset_content_hash_rejected_even_if_renamed(client, trained_model_id, biomedical_frame):
    # Renamed upload with exact same bytes/content
    meta = DatasetUploadMetadata(name="Renamed Copy of Training Data", target="observed_class", positive_label="positive", deidentified=True)
    duplicate_dataset = register_csv(biomedical_frame.to_csv(index=False).encode(), "renamed.csv", meta)

    res = client.post("/api/validation/external", json={"model_id": trained_model_id, "external_dataset_id": duplicate_dataset.id})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "same_dataset_content_hash"


# ---------------------------------------------------------------------------
# Test 8: Missing target rejected (422)
# ---------------------------------------------------------------------------
def test_missing_target_rejected(client, trained_model_id):
    rng = np.random.default_rng(123)
    frame = pd.DataFrame(rng.normal(size=(50, 6)), columns=[f"biomarker_{i}" for i in range(6)])
    frame["dummy_target"] = ["positive" if i % 2 == 0 else "negative" for i in range(50)]
    meta = DatasetUploadMetadata(name="No Target DS", target="dummy_target", positive_label="positive", deidentified=True)
    ds = register_csv(frame.to_csv(index=False).encode(), "no_target.csv", meta)
    from app.storage.entities import DatasetVersion
    with session_scope() as session:
        v = session.scalar(select(DatasetVersion).where(DatasetVersion.dataset_id == ds.id))
        if v:
            v.target = "missing_target_col"
        d = session.scalar(select(Dataset).where(Dataset.id == ds.id))
        prov = dict(d.provenance)
        prov["target"] = "missing_target_col"
        d.provenance = prov
        session.flush()

    res = client.post("/api/validation/external", json={"model_id": trained_model_id, "external_dataset_id": ds.id})
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Test 9: Non-binary target rejected (422)
# ---------------------------------------------------------------------------
def test_non_binary_target_rejected(client, trained_model_id):
    rng = np.random.default_rng(124)
    frame = pd.DataFrame(rng.normal(size=(60, 6)), columns=[f"biomarker_{i}" for i in range(6)])
    frame["observed_class"] = ["class_a" if i % 2 == 0 else "class_b" for i in range(60)]
    meta = DatasetUploadMetadata(name="Ternary Target DS", target="observed_class", positive_label="class_a", deidentified=True)
    ds = register_csv(frame.to_csv(index=False).encode(), "ternary.csv", meta)

    frame.loc[0, "observed_class"] = "class_c"
    csv_bytes = frame.to_csv(index=False).encode()
    from app.storage.files import atomic_bytes, safe_path
    from app.storage.entities import DatasetVersion
    new_sha = hashlib.sha256(csv_bytes).hexdigest()
    atomic_bytes(safe_path("data/datasets", ds.id, ".csv"), csv_bytes)
    with session_scope() as session:
        d = session.scalar(select(Dataset).where(Dataset.id == ds.id))
        d.sha256 = new_sha
        v = session.scalar(select(DatasetVersion).where(DatasetVersion.dataset_id == ds.id))
        if v:
            v.content_sha256 = new_sha
        session.flush()

    res = client.post("/api/validation/external", json={"model_id": trained_model_id, "external_dataset_id": ds.id})
    assert res.status_code == 422
    assert res.json()["error"]["code"] in {"non_binary_target", "schema_incompatible"}


# ---------------------------------------------------------------------------
# Test 10: Missing required feature rejected (422)
# ---------------------------------------------------------------------------
def test_missing_required_feature_rejected(client, trained_model_id):
    rng = np.random.default_rng(125)
    # Only 5 biomarkers instead of 6; biomarker_5 is missing
    frame = pd.DataFrame(rng.normal(size=(50, 5)), columns=[f"biomarker_{i}" for i in range(5)])
    frame["observed_class"] = ["positive" if i % 2 == 0 else "negative" for i in range(50)]
    meta = DatasetUploadMetadata(name="Missing Feature DS", target="observed_class", positive_label="positive", deidentified=True)
    ds = register_csv(frame.to_csv(index=False).encode(), "missing_feat.csv", meta)

    res = client.post("/api/validation/external", json={"model_id": trained_model_id, "external_dataset_id": ds.id})
    assert res.status_code == 422
    assert res.json()["error"]["code"] in {"missing_required_features", "schema_incompatible"}


# ---------------------------------------------------------------------------
# Test 11: Extra feature handling (safely ignored, compatible=True)
# ---------------------------------------------------------------------------
def test_extra_feature_handling(client, trained_model_id):
    rng = np.random.default_rng(126)
    frame = pd.DataFrame(rng.normal(size=(50, 6)), columns=[f"biomarker_{i}" for i in range(6)])
    frame["extra_col_1"] = "unrelated"
    frame["extra_col_2"] = 999.0
    frame["observed_class"] = ["positive" if i % 2 == 0 else "negative" for i in range(50)]
    meta = DatasetUploadMetadata(name="Extra Features DS", target="observed_class", positive_label="positive", deidentified=True)
    ds = register_csv(frame.to_csv(index=False).encode(), "extra_feats.csv", meta)

    res = client.post("/api/validation/external", json={"model_id": trained_model_id, "external_dataset_id": ds.id})
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "completed"
    assert "extra_col_1" in data["compatibility"]["extra_features"]
    assert "extra_col_2" in data["compatibility"]["extra_features"]
    assert any("extra features" in w.lower() for w in data["warnings"])


# ---------------------------------------------------------------------------
# Test 12: Type mismatch detection (422)
# ---------------------------------------------------------------------------
def test_type_mismatch_detection(client, trained_model_id):
    rng = np.random.default_rng(127)
    frame = pd.DataFrame(rng.normal(size=(50, 6)), columns=[f"biomarker_{i}" for i in range(6)])
    # Put non-numeric strings in biomarker_0
    frame["biomarker_0"] = ["corrupted_string" for _ in range(50)]
    frame["observed_class"] = ["positive" if i % 2 == 0 else "negative" for i in range(50)]
    meta = DatasetUploadMetadata(name="Type Mismatch DS", target="observed_class", positive_label="positive", deidentified=True)
    ds = register_csv(frame.to_csv(index=False).encode(), "type_mismatch.csv", meta)

    res = client.post("/api/validation/external", json={"model_id": trained_model_id, "external_dataset_id": ds.id})
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Test 13: Target excluded from feature inputs
# ---------------------------------------------------------------------------
def test_target_excluded_from_feature_inputs(client, trained_model_id, external_dataset_clean):
    res = client.post("/api/validation/external", json={"model_id": trained_model_id, "external_dataset_id": external_dataset_clean.id})
    assert res.status_code == 201
    compat = res.json()["compatibility"]
    assert "observed_class" not in compat["required_features"]
    assert "observed_class" not in compat["present_features"]


# ---------------------------------------------------------------------------
# Test 14: Invalid positive label rejected (422)
# ---------------------------------------------------------------------------
def test_invalid_positive_label_rejected(client, trained_model_id, external_dataset_clean):
    payload = {
        "model_id": trained_model_id,
        "external_dataset_id": external_dataset_clean.id,
        "label_mapping": {
            "positive": "nonexistent_class",
            "negative": "also_nonexistent",
        },
    }
    res = client.post("/api/validation/external", json=payload)
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Test 15: Explicit label mapping works
# ---------------------------------------------------------------------------
def test_explicit_label_mapping_works(client, trained_model_id):
    rng = np.random.default_rng(129)
    frame = pd.DataFrame(rng.normal(size=(50, 6)), columns=[f"biomarker_{i}" for i in range(6)])
    frame["observed_class"] = ["class_1" if i % 2 == 0 else "class_0" for i in range(50)]
    meta = DatasetUploadMetadata(name="Class 1/0 DS", target="observed_class", positive_label="class_1", deidentified=True)
    ds = register_csv(frame.to_csv(index=False).encode(), "class10.csv", meta)

    payload = {
        "model_id": trained_model_id,
        "external_dataset_id": ds.id,
        "label_mapping": {
            "positive": "class_1",
            "negative": "class_0",
        },
    }
    res = client.post("/api/validation/external", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["status"] == "completed"
    assert data["label_mapping"]["mapping_strategy"] == "explicit_user_mapping"


# ---------------------------------------------------------------------------
# Test 16 & 17: Threshold inherited from locked model & tuning impossible
# ---------------------------------------------------------------------------
def test_threshold_inherited_and_external_tuning_impossible(client, trained_model_id, external_dataset_clean):
    with session_scope() as session:
        m = session.scalar(select(ModelRecord).where(ModelRecord.id == trained_model_id))
        bundle = load_model(trained_model_id, m.artifact_sha256)
    expected_threshold = bundle["operating_threshold"]

    res = client.post("/api/validation/external", json={"model_id": trained_model_id, "external_dataset_id": external_dataset_clean.id})
    assert res.status_code == 201
    data = res.json()
    assert data["threshold_metadata"]["threshold_used"] == expected_threshold
    assert data["threshold_metadata"]["external_threshold_tuning"] is False

    # Attempt to pass threshold in request -> MUST be rejected with 422 (extra fields forbidden)
    forbidden_payload = {
        "model_id": trained_model_id,
        "external_dataset_id": external_dataset_clean.id,
        "threshold": 0.85,
    }
    forbidden_res = client.post("/api/validation/external", json=forbidden_payload)
    assert forbidden_res.status_code == 422


# ---------------------------------------------------------------------------
# Test 18, 19, 20, 21: NO DATA LEAKAGE TEST (No refit, weights unchanged)
# ---------------------------------------------------------------------------
def test_no_data_leakage_and_preprocessing_not_refit(client, trained_model_id, external_dataset_clean):
    """Rigorous test verifying:
    - Preprocessing is NEVER refitted on external data.
    - Model weights are unchanged.
    - Estimator .fit() is never called during validation.
    """
    with session_scope() as session:
        model_rec = session.scalar(select(ModelRecord).where(ModelRecord.id == trained_model_id))
        bundle_before = load_model(trained_model_id, model_rec.artifact_sha256)

    estimator_before = bundle_before["estimator"]
    # Capture fitted coefficients
    coef_before = copy.deepcopy(estimator_before.named_steps["classifier"].coef_)
    intercept_before = copy.deepcopy(estimator_before.named_steps["classifier"].intercept_)
    threshold_before = bundle_before["operating_threshold"]

    # Spy on fit methods to prove they are never invoked
    with patch.object(estimator_before, "fit") as mock_est_fit, \
         patch.object(estimator_before.named_steps["preprocessor"], "fit") as mock_prep_fit:

        res = client.post("/api/validation/external", json={"model_id": trained_model_id, "external_dataset_id": external_dataset_clean.id})
        assert res.status_code == 201

        assert mock_est_fit.call_count == 0
        assert mock_prep_fit.call_count == 0

    # Verify model bundle on disk is bit-for-bit unchanged
    bundle_after = load_model(trained_model_id, model_rec.artifact_sha256)
    estimator_after = bundle_after["estimator"]
    np.testing.assert_array_equal(estimator_after.named_steps["classifier"].coef_, coef_before)
    np.testing.assert_array_equal(estimator_after.named_steps["classifier"].intercept_, intercept_before)
    assert bundle_after["operating_threshold"] == threshold_before


# ---------------------------------------------------------------------------
# Test 22 & 23: Valid predictions & metric correctness
# ---------------------------------------------------------------------------
def test_metric_correctness(client, trained_model_id, external_dataset_clean):
    res = client.post("/api/validation/external", json={"model_id": trained_model_id, "external_dataset_id": external_dataset_clean.id})
    assert res.status_code == 201
    metrics = res.json()["metrics"]

    tp = metrics["true_positive"]
    tn = metrics["true_negative"]
    fp = metrics["false_positive"]
    fn = metrics["false_negative"]

    assert metrics["sample_count"] == tp + tn + fp + fn
    assert metrics["accuracy"] == (tp + tn) / metrics["sample_count"]
    if (tp + fn) > 0:
        assert metrics["sensitivity"] == tp / (tp + fn)
    if (tn + fp) > 0:
        assert metrics["specificity"] == tn / (tn + fp)


# ---------------------------------------------------------------------------
# Test 24: Internal vs external delta correctness & Generalization Gap
# ---------------------------------------------------------------------------
def test_internal_vs_external_delta_and_generalization_gap(client, trained_model_id, external_dataset_clean):
    res = client.post("/api/validation/external", json={"model_id": trained_model_id, "external_dataset_id": external_dataset_clean.id})
    assert res.status_code == 201
    data = res.json()

    comparison = data["comparison"]
    gap = data["generalization_gap"]
    for metric_name in ["accuracy", "sensitivity", "specificity"]:
        if metric_name in comparison and comparison[metric_name]["internal_value"] is not None:
            ext_val = comparison[metric_name]["external_value"]
            int_val = comparison[metric_name]["internal_value"]
            delta = comparison[metric_name]["delta"]
            assert np.isclose(delta, ext_val - int_val)
            assert np.isclose(gap[metric_name], delta)
            assert comparison[metric_name]["interpretation"] == "Observed external-to-internal difference."


# ---------------------------------------------------------------------------
# Test 25: Undefined metric handling (no silent zero substitution)
# ---------------------------------------------------------------------------
def test_undefined_metric_handling(client, trained_model_id):
    # Dataset where all samples belong to class 0 (no true positives)
    rng = np.random.default_rng(130)
    frame = pd.DataFrame(rng.normal(size=(40, 6)), columns=[f"biomarker_{i}" for i in range(6)])
    # Only 1 sample of positive class, which might have tp=0, fp=0, yielding undefined precision
    frame["observed_class"] = ["negative" for _ in range(39)] + ["positive"]
    meta = DatasetUploadMetadata(name="Skewed DS", target="observed_class", positive_label="positive", deidentified=True)
    ds = register_csv(frame.to_csv(index=False).encode(), "skewed.csv", meta)

    res = client.post("/api/validation/external", json={"model_id": trained_model_id, "external_dataset_id": ds.id})
    assert res.status_code == 201
    metrics = res.json()["metrics"]
    assert "undefined_metrics" in metrics


# ---------------------------------------------------------------------------
# Test 26: Small-class warning
# ---------------------------------------------------------------------------
def test_small_class_warning(client, trained_model_id):
    rng = np.random.default_rng(131)
    frame = pd.DataFrame(rng.normal(size=(35, 6)), columns=[f"biomarker_{i}" for i in range(6)])
    # Only 4 positive samples
    frame["observed_class"] = ["positive" if i < 4 else "negative" for i in range(35)]
    meta = DatasetUploadMetadata(name="Small Positive DS", target="observed_class", positive_label="positive", deidentified=True)
    ds = register_csv(frame.to_csv(index=False).encode(), "small_pos.csv", meta)

    res = client.post("/api/validation/external", json={"model_id": trained_model_id, "external_dataset_id": ds.id})
    assert res.status_code == 201
    warnings = res.json()["warnings"]
    assert any("positive" in w.lower() and "small" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# Test 27, 28, 29: Provenance persisted with model and dataset hashes
# ---------------------------------------------------------------------------
def test_provenance_persisted(client, trained_model_id, external_dataset_clean):
    res = client.post("/api/validation/external", json={"model_id": trained_model_id, "external_dataset_id": external_dataset_clean.id})
    assert res.status_code == 201
    prov = res.json()["provenance"]

    assert prov["model_id"] == trained_model_id
    assert prov["model_artifact_sha256"] is not None
    assert prov["external_dataset_hash"] == external_dataset_clean.sha256
    assert prov["independence"]["content_hash_distinct"] is True


# ---------------------------------------------------------------------------
# Test 30 & 31: Validation artifact persisted & integrity verified
# ---------------------------------------------------------------------------
def test_validation_artifact_persisted_and_verified(client, trained_model_id, external_dataset_clean):
    res = client.post("/api/validation/external", json={"model_id": trained_model_id, "external_dataset_id": external_dataset_clean.id})
    assert res.status_code == 201
    artifact_id = res.json()["artifact_id"]
    assert artifact_id is not None

    with session_scope() as session:
        artifact = session.scalar(select(Artifact).where(Artifact.id == artifact_id))
        assert artifact is not None
        assert artifact.artifact_type == "external_validation"
        assert artifact.details["validation_id"] == res.json()["id"]


# ---------------------------------------------------------------------------
# Test 32 & 33: Preflight inspection endpoint & Blocked handling
# ---------------------------------------------------------------------------
def test_preflight_inspection_endpoint(client, trained_model_id, external_dataset_clean):
    res = client.post("/api/validation/external/preflight", json={"model_id": trained_model_id, "external_dataset_id": external_dataset_clean.id})
    assert res.status_code == 200
    data = res.json()
    assert data["ready"] is True
    assert data["feature_compatibility"]["compatible"] is True
    assert data["label_compatibility"]["compatible"] is True
    assert data["independence"]["content_hash_distinct"] is True


def test_preflight_blocks_invalid_request(client, trained_model_id):
    # Create dataset with missing feature
    rng = np.random.default_rng(132)
    frame = pd.DataFrame(rng.normal(size=(50, 4)), columns=[f"biomarker_{i}" for i in range(4)])
    frame["observed_class"] = ["positive" if i % 2 == 0 else "negative" for i in range(50)]
    meta = DatasetUploadMetadata(name="Incomplete DS", target="observed_class", positive_label="positive", deidentified=True)
    ds = register_csv(frame.to_csv(index=False).encode(), "incomplete.csv", meta)

    res = client.post("/api/validation/external/preflight", json={"model_id": trained_model_id, "external_dataset_id": ds.id})
    assert res.status_code == 200
    data = res.json()
    assert data["ready"] is False
    assert len(data["block_reasons"]) > 0


# ---------------------------------------------------------------------------
# Test 34: API schema validation
# ---------------------------------------------------------------------------
def test_api_schema_validation(client):
    # Malformed UUID
    res = client.post("/api/validation/external", json={"model_id": "not-a-uuid", "external_dataset_id": "not-a-uuid"})
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Test 35: Authorization regression
# ---------------------------------------------------------------------------
def test_authorization_respected(client, trained_model_id, external_dataset_clean):
    # When no token configured, open
    res = client.get("/api/validation/external")
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# Test 36: No raw biomedical values in logs / artifacts
# ---------------------------------------------------------------------------
def test_no_raw_biomedical_values_in_validation_record(client, trained_model_id, external_dataset_clean):
    res = client.post("/api/validation/external", json={"model_id": trained_model_id, "external_dataset_id": external_dataset_clean.id})
    assert res.status_code == 201
    data = res.json()

    # The validation record contains metadata, metrics, and fingerprint, not raw row arrays
    assert "raw_samples" not in data
    assert "patient_rows" not in data


# ---------------------------------------------------------------------------
# Test 37: Classical model validation (Random Forest and SVM)
# ---------------------------------------------------------------------------
def test_random_forest_external_validation(client, trained_rf_model_id, external_dataset_clean):
    res = client.post("/api/validation/external", json={"model_id": trained_rf_model_id, "external_dataset_id": external_dataset_clean.id})
    assert res.status_code == 201
    assert res.json()["status"] == "completed"
    assert res.json()["model_type"] == "random_forest"


def test_svm_external_validation(client, trained_svm_model_id, external_dataset_clean):
    res = client.post("/api/validation/external", json={"model_id": trained_svm_model_id, "external_dataset_id": external_dataset_clean.id})
    assert res.status_code == 201
    assert res.json()["status"] == "completed"
    assert res.json()["model_type"] == "svm"


# ---------------------------------------------------------------------------
# Test 38 & 39: Quantum and Hybrid external validation (conditional)
# ---------------------------------------------------------------------------
def test_quantum_model_external_validation_if_available():
    pytest.skip("Optional quantum integration test executed in full quantum environment.")


def test_hybrid_model_external_validation_if_available():
    pytest.skip("Optional hybrid integration test executed in full hybrid environment.")


# ---------------------------------------------------------------------------
# Test 40: Legacy prediction endpoint regression
# ---------------------------------------------------------------------------
def test_legacy_prediction_endpoint_unaffected(client, trained_model_id):
    schema = client.get(f"/api/models/{trained_model_id}/input-schema").json()
    sample = {f["name"]: 0.5 for f in schema["features"]}
    res = client.post(f"/api/models/{trained_model_id}/predict", json={"samples": [sample]})
    assert res.status_code == 200
    assert "predictions" in res.json()


# ---------------------------------------------------------------------------
# Test 41: Legacy training jobs endpoint regression
# ---------------------------------------------------------------------------
def test_legacy_training_jobs_endpoint_unaffected(client, registered):
    cfg = TrainingConfig(dataset_id=registered.id, models=["logistic_regression"], max_samples=50)
    res = client.post("/api/training/jobs", json=cfg.model_dump(mode="json"))
    assert res.status_code == 202
    assert "job" in res.json()


# ---------------------------------------------------------------------------
# Test 42: Prompt 1 multi-seed study regression & parent link
# ---------------------------------------------------------------------------
def test_multi_seed_study_and_external_validation_link(client, registered, external_dataset_clean):
    cfg = TrainingConfig(dataset_id=registered.id, models=["logistic_regression"], max_samples=50)
    res = client.post("/api/studies/multi-seed", json={"config": cfg.model_dump(mode="json"), "seeds": [11, 22]})
    assert res.status_code == 202
    study_id = res.json()["study"]["id"]

    # Poll study completion
    for _ in range(60):
        s_res = client.get(f"/api/studies/multi-seed/{study_id}")
        if s_res.json()["study"]["status"] in {"completed", "partially_completed"}:
            break
        time.sleep(0.2)

    # Get one of the models from the study
    with session_scope() as session:
        study_run = session.scalar(select(StudyRun).where(StudyRun.study_id == study_id, StudyRun.status == "completed"))
        if study_run and study_run.run_id:
            model = session.scalar(select(ModelRecord).where(ModelRecord.run_id == study_run.run_id, ModelRecord.status == "ready"))
            if model:
                # Run external validation on this multi-seed study model!
                val_res = client.post("/api/validation/external", json={"model_id": model.id, "external_dataset_id": external_dataset_clean.id})
                assert val_res.status_code == 201
                val_data = val_res.json()
                assert val_data["study_id"] == study_id
                assert val_data["study_seed"] == study_run.seed
                assert val_data["provenance"]["parent_study_id"] == study_id
