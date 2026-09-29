import hashlib
import json
import os
import time

import pandas as pd
import pytest

from app.api.schemas import PipelineConfig, QuantumConfig, TrainingConfig
from app.data.catalog import builtin_bytes, list_builtin_datasets
from app.data.service import inspect_csv, load_frame, register_builtin
from app.data.splitting import prepare_data
from app.feature_engineering.pipeline import preview


EXPECTED = {
    "wdbc": ("diagnosis", {"benign", "malignant"}, 569, 30),
    "early-stage-diabetes": ("diabetes_status", {"negative", "positive"}, 520, 16),
    "cleveland-heart-disease": ("heart_disease", {"absent", "present"}, 303, 13),
    "chronic-kidney-disease": ("ckd_status", {"ckd", "not_ckd"}, 400, 24),
    "ilpd-liver": ("liver_disease", {"absent", "present"}, 583, 10),
}


def test_five_deployment_safe_resources_have_verified_metadata_and_hashes():
    library = list_builtin_datasets()
    assert {item["slug"] for item in library} == set(EXPECTED)
    for item in library:
        target, labels, rows, features = EXPECTED[item["slug"]]
        entry, content = builtin_bytes(item["slug"])
        assert hashlib.sha256(content).hexdigest() == entry["sha256"]
        assert entry["target"] == target
        assert set(entry["class_labels"]) == labels
        assert entry["row_count"] == rows
        assert entry["feature_count"] == features
        assert entry["license"] == "CC BY 4.0"
        assert entry["source_url"].startswith("https://doi.org/")
        inspection = inspect_csv(content, entry["filename"], entry["target"], entry["positive_label"])
        assert inspection["row_count"] == rows
        assert inspection["column_count"] == features + 1
        assert inspection["detected_target"] == target


@pytest.mark.parametrize("slug", list(EXPECTED))
def test_each_builtin_registers_with_central_provenance_and_valid_schema(slug):
    record = register_builtin(slug)
    entry = next(item for item in list_builtin_datasets() if item["slug"] == slug)
    loaded, frame = load_frame(record.id)
    assert loaded.id == record.id
    assert len(frame) == entry["row_count"]
    assert len(frame.columns) == entry["feature_count"] + 1
    assert record.provenance["origin"] == "built_in"
    assert record.provenance["library_slug"] == slug
    assert record.provenance["target"] == entry["target"]
    assert record.provenance["positive_label"] == entry["positive_label"]
    assert set(record.provenance["target_classes"]) == set(entry["class_labels"])
    assert record.provenance["target_detection"]["selection_method"] == "verified_manifest"
    assert record.provenance["is_demo"] is False
    assert record.provenance["normalization"] == entry["normalization"]
    assert record.provenance["negative_label"] == entry["negative_label"]
    assert frame[entry["target"]].nunique() == 2
    assert entry["positive_label"] in set(frame[entry["target"]].astype(str))
    assert entry["negative_label"] in set(frame[entry["target"]].astype(str))
    assert register_builtin(slug).id == record.id


@pytest.mark.parametrize("slug", list(EXPECTED))
def test_each_builtin_enters_existing_quality_and_pipeline_preview(slug):
    entry = next(item for item in list_builtin_datasets() if item["slug"] == slug)
    record = register_builtin(slug)
    config = TrainingConfig(
        dataset_id=record.id,
        models=["logistic_regression"],
        max_samples=120,
        duplicate_policy=entry["recommended_duplicate_policy"],
    )
    result = preview(config)
    assert result["train_count"] > 0
    assert result["test_count"] > 0
    assert entry["target"] not in result["input_features"]
    assert result["output_features"]


def _poll_job(client, identity, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/training/jobs/{identity}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] not in {"queued", "running", "cancel_requested"}:
            return job
        time.sleep(0.05)
    pytest.fail(f"Training job {identity} did not finish in {timeout} seconds.")


def _json_sample(frame, features):
    values = frame[features].iloc[0].to_dict()
    return {
        key: None if pd.isna(value) else value.item() if hasattr(value, "item") else value
        for key, value in values.items()
    }


@pytest.mark.integration
@pytest.mark.parametrize("slug", list(EXPECTED))
def test_each_builtin_completes_bounded_classical_end_to_end_workflow(client, slug):
    library = client.get("/api/datasets/library")
    assert library.status_code == 200
    entry = next(item for item in library.json() if item["slug"] == slug)

    registered_response = client.post(f"/api/datasets/library/{slug}", json={})
    assert registered_response.status_code == 201, registered_response.text
    registered = registered_response.json()
    dataset_id = registered["id"]
    assert dataset_id
    assert registered["provenance"]["target"] == entry["target"]
    assert registered["provenance"]["positive_label"] == entry["positive_label"]
    assert registered["provenance"]["negative_label"] == entry["negative_label"]

    stored = client.get(f"/api/datasets/{dataset_id}")
    provenance = client.get(f"/api/datasets/{dataset_id}/provenance")
    assert stored.status_code == 200
    assert provenance.status_code == 200
    assert provenance.json()["library_slug"] == slug
    assert provenance.json()["packaged_resource_sha256"] == entry["sha256"]

    validation = client.post(f"/api/datasets/{dataset_id}/validate", json={"features": None})
    assert validation.status_code == 200, validation.text
    assert validation.json()["target"] == entry["target"]

    config = TrainingConfig(
        dataset_id=dataset_id,
        models=["logistic_regression"],
        seed=17,
        cv_folds=2,
        max_samples=80,
        duplicate_policy=entry["recommended_duplicate_policy"],
    )
    payload = config.model_dump(mode="json")
    for endpoint in ("preprocessing", "feature-selection", "pca"):
        response = client.post(f"/api/{endpoint}/preview", json=payload)
        assert response.status_code == 200, f"{endpoint}: {response.text}"
        assert response.json()["input_features"]
        assert entry["target"] not in response.json()["input_features"]

    created = client.post("/api/training/jobs", json=payload)
    assert created.status_code == 202, created.text
    experiment_id = created.json()["experiment"]["id"]
    assert created.json()["experiment"]["dataset_id"] == dataset_id
    job = _poll_job(client, created.json()["job"]["id"])
    assert job["status"] == "succeeded", job["errors"]

    detail = client.get(f"/api/experiments/{experiment_id}")
    assert detail.status_code == 200
    assert detail.json()["experiment"]["dataset_id"] == dataset_id
    model = next(record for record in detail.json()["models"] if record["status"] == "ready")
    assert model["dataset_id"] == dataset_id
    assert model["details"]["dataset_provenance"]["library_slug"] == slug
    assert client.get(f"/api/models/{model['id']}/demo-sample").status_code == 403

    comparison = client.get(f"/api/experiments/{experiment_id}/comparison")
    assert comparison.status_code == 200
    assert comparison.json()["experiment_id"] == experiment_id
    assert any(record["id"] == model["id"] for record in comparison.json()["models"])

    _, frame = load_frame(dataset_id)
    features = model["details"]["input_features"]
    prediction = client.post(
        f"/api/models/{model['id']}/predict",
        json={"samples": [_json_sample(frame, features)], "include_influence": False},
    )
    assert prediction.status_code == 200, prediction.text
    assert prediction.json()["predictions"][0]["predicted_class"] in entry["class_labels"]

    explanation = client.post(
        f"/api/models/{model['id']}/explain",
        json={"method": "perturbation", "max_samples": 4, "repeats": 1, "max_features": min(5, len(features))},
    )
    assert explanation.status_code == 201, explanation.text
    assert explanation.json()["result"]["influence"]

    report = client.get(f"/api/experiments/{experiment_id}/report?format=json")
    assert report.status_code == 200
    assert report.json()["dataset"]["library_slug"] == slug
    assert report.json()["experiment"]["dataset_id"] == dataset_id


@pytest.mark.parametrize("slug", list(EXPECTED))
def test_each_builtin_is_quantum_configuration_compatible_without_claiming_execution(slug):
    entry = next(item for item in list_builtin_datasets() if item["slug"] == slug)
    record = register_builtin(slug)
    config = TrainingConfig(
        dataset_id=record.id,
        models=["qsvc"],
        max_samples=40,
        cv_folds=2,
        duplicate_policy=entry["recommended_duplicate_policy"],
    )
    assert str(config.dataset_id) == record.id
    assert config.pipeline.pca_components == config.quantum.qubits == 4
    assert config.pipeline.angle_scaling is True
    prepared = prepare_data(config)
    assert prepared.dataset.id == record.id
    assert prepared.X.shape[0] == entry["row_count"]


@pytest.mark.quantum
@pytest.mark.skipif(
    os.getenv("RUN_QUANTUM_TESTS") != "1",
    reason="Set RUN_QUANTUM_TESTS=1 to execute the bounded quantum integration test.",
)
def test_wdbc_executes_one_bounded_real_qsvc_experiment(client):
    """Execute one real simulator-backed quantum job; the other datasets receive config validation."""
    pytest.importorskip("qiskit_machine_learning")
    registered = client.post("/api/datasets/library/wdbc", json={})
    assert registered.status_code == 201, registered.text
    dataset_id = registered.json()["id"]
    config = TrainingConfig(
        dataset_id=dataset_id,
        models=["qsvc"],
        pipeline=PipelineConfig(k_features=4, pca_components=2, angle_scaling=True),
        quantum=QuantumConfig(qubits=2, maxiter=5, shots=128),
        seed=17,
        cv_folds=2,
        max_samples=30,
        duplicate_policy="reject",
    )
    created = client.post("/api/training/jobs", json=config.model_dump(mode="json"))
    assert created.status_code == 202, created.text
    job = _poll_job(client, created.json()["job"]["id"], timeout=120)
    assert job["status"] == "succeeded", job
    experiment = client.get(f"/api/experiments/{created.json()['experiment']['id']}")
    assert experiment.status_code == 200
    assert experiment.json()["experiment"]["dataset_id"] == dataset_id
    model = next(item for item in experiment.json()["models"] if item["status"] == "ready")
    assert model["dataset_id"] == dataset_id
    assert model["model_type"] == "qsvc"
    assert model["details"]["quantum"]["circuit"]["qubits"] == 2


def test_library_inspection_and_registration_api_are_backwards_compatible(client):
    response = client.get("/api/datasets/library")
    assert response.status_code == 200
    assert len(response.json()) == 5
    registered = client.post("/api/datasets/library/wdbc", json={})
    assert registered.status_code == 201
    assert registered.json()["provenance"]["target"] == "diagnosis"
    assert client.get("/api/datasets").status_code == 200
    assert client.post("/api/datasets/demo").status_code == 201


def test_inspect_upload_auto_detection_and_manual_override(client):
    rows = ["patient_id,diagnosis,review_result,value"]
    for index in range(20):
        rows.append(f"{index},{'malignant' if index % 2 else 'benign'},{'remove' if index % 2 else 'keep'},{index / 10}")
    content = ("\n".join(rows) + "\n").encode()
    automatic = client.post("/api/datasets/inspect", files={"file": ("medical.csv", content, "text/csv")})
    assert automatic.status_code == 200, automatic.text
    assert automatic.json()["detected_target"] == "diagnosis"
    manual = client.post(
        "/api/datasets/inspect",
        data={"target": "review_result", "positive_label": "remove"},
        files={"file": ("medical.csv", content, "text/csv")},
    )
    assert manual.status_code == 200, manual.text
    assert manual.json()["detected_target"] == "review_result"
    assert manual.json()["positive_label"] == "remove"
    assert manual.json()["selection_method"] == "manual_override"


def test_existing_upload_route_registers_resolved_target_metadata(client):
    content = b"feature,diagnosis\n" + b"\n".join(
        f"{index},{'malignant' if index % 2 else 'benign'}".encode() for index in range(20)
    ) + b"\n"
    metadata = {
        "name": "Upload compatibility",
        "target": "diagnosis",
        "positive_label": "malignant",
        "deidentified": True,
    }
    response = client.post(
        "/api/datasets/upload",
        data={"metadata_json": json.dumps(metadata)},
        files={"file": ("upload.csv", content, "text/csv")},
    )
    assert response.status_code == 201, response.text
    provenance = response.json()["provenance"]
    assert provenance["origin"] == "uploaded"
    assert provenance["target"] == "diagnosis"
    assert provenance["target_detection"]["selection_method"] == "manual_override"


@pytest.mark.integration
def test_custom_upload_inspection_override_registration_and_pipeline_are_consistent(client):
    rows = ["age,outcome,review_result,blood_pressure_measurement"]
    for index in range(80):
        rows.append(
            f"{25 + index},{'yes' if index % 2 else 'no'},"
            f"{'refer' if index % 3 else 'observe'},{105 + (index % 25)}"
        )
    content = ("\n".join(rows) + "\n").encode()

    automatic = client.post("/api/datasets/inspect", files={"file": ("custom.csv", content, "text/csv")})
    assert automatic.status_code == 200
    assert automatic.json()["detected_target"] == "outcome"

    manual = client.post(
        "/api/datasets/inspect",
        data={"target": "review_result", "positive_label": "refer"},
        files={"file": ("custom.csv", content, "text/csv")},
    )
    assert manual.status_code == 200
    assert manual.json()["detected_target"] == "review_result"
    assert manual.json()["positive_label"] == "refer"
    assert manual.json()["selection_method"] == "manual_override"

    metadata = {
        "name": "Custom inspection integration",
        "target": manual.json()["detected_target"],
        "positive_label": manual.json()["positive_label"],
        "deidentified": True,
    }
    registered = client.post(
        "/api/datasets/upload",
        data={"metadata_json": json.dumps(metadata)},
        files={"file": ("custom.csv", content, "text/csv")},
    )
    assert registered.status_code == 201, registered.text
    dataset = registered.json()
    assert dataset["provenance"]["target"] == "review_result"
    assert dataset["provenance"]["positive_label"] == "refer"
    assert dataset["provenance"]["target_detection"]["selection_method"] == "manual_override"

    quality = client.post(f"/api/datasets/{dataset['id']}/validate", json={"features": None})
    assert quality.status_code == 200
    config = TrainingConfig(
        dataset_id=dataset["id"],
        models=["logistic_regression"],
        max_samples=60,
        cv_folds=2,
    )
    pipeline = client.post("/api/preprocessing/preview", json=config.model_dump(mode="json"))
    assert pipeline.status_code == 200, pipeline.text
    assert "review_result" not in pipeline.json()["input_features"]


@pytest.mark.integration
def test_legacy_demo_remains_distinct_and_is_the_only_approved_demo_sample_path(client):
    builtin = client.post("/api/datasets/library/wdbc", json={})
    legacy = client.post("/api/datasets/demo")
    assert builtin.status_code == legacy.status_code == 201
    assert builtin.json()["id"] != legacy.json()["id"]
    assert builtin.json()["provenance"]["is_demo"] is False
    assert legacy.json()["provenance"]["is_demo"] is True

    config = TrainingConfig(
        dataset_id=legacy.json()["id"],
        models=["logistic_regression"],
        seed=23,
        cv_folds=2,
        max_samples=40,
    )
    created = client.post("/api/training/jobs", json=config.model_dump(mode="json"))
    assert created.status_code == 202
    job = _poll_job(client, created.json()["job"]["id"])
    assert job["status"] == "succeeded", job["errors"]
    detail = client.get(f"/api/experiments/{created.json()['experiment']['id']}").json()
    model = next(record for record in detail["models"] if record["status"] == "ready")
    sample = client.get(f"/api/models/{model['id']}/demo-sample")
    assert sample.status_code == 200
    assert sample.json()["target_withheld"] is True
