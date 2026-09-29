import base64
import copy
import hashlib
import json
from pathlib import Path

import pytest

from app.data.catalog import builtin_bytes, list_builtin_datasets
from app.demo_readiness import (
    READY_DEMO_DATASETS,
    _artifact_path,
    _load_manifest,
    _read_bundle,
    _validate_entry,
    readiness_summary,
    validate_packaged_dataset,
    validate_readiness_configuration,
)
from app.utils.errors import AppError

PROCESSING = {"cleveland-heart-disease", "chronic-kidney-disease", "ilpd-liver"}


def test_readiness_configuration_is_exact_and_invalid_selection_fails():
    library = list_builtin_datasets()
    assert len(library) == 5
    assert set(READY_DEMO_DATASETS) == {"wdbc", "early-stage-diabetes"}
    assert {item["slug"] for item in library if item["demo_readiness"]["status"] == "ready"} == set(READY_DEMO_DATASETS)
    assert {item["slug"] for item in library if item["demo_readiness"]["status"] == "requires_processing"} == PROCESSING
    with pytest.raises(AppError, match="exactly two"):
        validate_readiness_configuration({"wdbc"})
    with pytest.raises(AppError, match="exactly two"):
        validate_readiness_configuration({"wdbc", "unknown"})


def test_manifest_and_every_packaged_artifact_have_real_matching_hashes():
    manifest = _load_manifest(refresh=True)
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    assert hashlib.sha256(canonical).hexdigest() == manifest["manifest_sha256"]
    for slug in READY_DEMO_DATASETS:
        checked = validate_packaged_dataset(slug)
        _, content = builtin_bytes(slug)
        assert hashlib.sha256(content).hexdigest() == checked["catalog"]["sha256"]
        for model in checked["models"]:
            artifact = _artifact_path(model["artifact"]["filename"])
            assert hashlib.sha256(base64.b64decode(artifact.read_bytes(), validate=True)).hexdigest() == model["artifact_sha256"]
            bundle = _read_bundle(artifact, model["artifact_sha256"])
            assert bundle["dataset_id"] == checked["dataset"]["id"]
            assert bundle["dataset_hash"] == checked["catalog"]["sha256"]


def test_corrupted_artifact_and_cross_dataset_relationships_are_rejected(tmp_path):
    corrupted = tmp_path / "corrupted.dill"
    corrupted.write_bytes(b"not a trained artifact")
    with pytest.raises(AppError, match="invalid|integrity"):
        _read_bundle(corrupted, "0" * 64)
    manifest = _load_manifest()
    slug = "wdbc"
    entry = copy.deepcopy(manifest["datasets"][slug])
    other = manifest["datasets"]["early-stage-diabetes"]
    entry["models"][0]["dataset_id"] = other["dataset"]["id"]
    with pytest.raises(AppError, match="relationship"):
        _validate_entry(slug, entry, manifest)
    entry = copy.deepcopy(manifest["datasets"][slug])
    entry["experiment"]["dataset_id"] = other["dataset"]["id"]
    with pytest.raises(AppError, match="experiment identity"):
        _validate_entry(slug, entry, manifest)


def test_readiness_endpoint_and_seeded_records_are_genuine_and_dataset_specific(client):
    response = client.get("/api/datasets/readiness")
    assert response.status_code == 200
    body = response.json()
    assert (body["total"], body["verified_demo_ready"], body["requires_processing"]) == (5, 2, 3)
    for item in body["datasets"]:
        ready = item["demo_readiness"]
        if item["slug"] in READY_DEMO_DATASETS:
            assert ready["status"] == "ready"
            detail = client.get(f"/api/experiments/{ready['experiment_id']}")
            assert detail.status_code == 200
            experiment = detail.json()["experiment"]
            assert experiment["summary"]["experiment_kind"] == "precomputed_verified_demo"
            assert experiment["dataset_id"] == detail.json()["models"][0]["dataset_id"]
            model = detail.json()["models"][0]
            assert model["id"] in ready["model_ids"]
            assert client.get(f"/api/models/{model['id']}/demo-sample").status_code == 200
            assert client.get(f"/api/experiments/{experiment['id']}/report?format=json").json()["experiment_kind"] == "precomputed_verified_demo"
        else:
            assert ready["status"] == "requires_processing"
            assert ready["experiment_id"] is None and ready["model_ids"] == []


def test_processing_dataset_creates_no_fake_experiment_and_live_pipeline_remains_available(client):
    before = {item["id"] for item in client.get("/api/experiments").json()}
    registered = client.post("/api/datasets/library/cleveland-heart-disease", json={})
    assert registered.status_code == 201
    dataset_id = registered.json()["id"]
    after = client.get("/api/experiments").json()
    assert {item["id"] for item in after} == before
    payload = {
        "dataset_id": dataset_id, "models": ["logistic_regression"], "seed": 17, "test_size": .2,
        "cv_folds": 2, "max_samples": 60, "duplicate_policy": "reject",
    }
    assert client.post("/api/preprocessing/preview", json=payload).status_code == 200
    assert client.post("/api/training/jobs", json=payload).status_code == 202
