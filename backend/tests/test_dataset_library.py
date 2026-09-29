import hashlib
import json

import pytest

from app.api.schemas import TrainingConfig
from app.data.catalog import builtin_bytes, list_builtin_datasets
from app.data.service import inspect_csv, load_frame, register_builtin
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