import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

import app.demo_readiness as demo_readiness
from app.data.catalog import builtin_bytes, list_builtin_datasets
from app.database import session_scope
from app.demo_readiness import (
    READY_DEMO_DATASETS,
    PACKAGED_ARTIFACT_HASH_ALGORITHM,
    PACKAGED_ARTIFACT_HASH_SCOPE,
    _artifact_path,
    _load_manifest,
    _read_bundle,
    _validate_entry,
    clear_verified_readiness_cache,
    install_verified_demo_artifacts,
    packaged_artifact_sha256,
    readiness_summary,
    validate_packaged_dataset,
    validate_readiness_configuration,
)
from app.storage.entities import Dataset, Experiment, Job, ModelRecord
from app.storage.files import safe_path
from app.utils.errors import AppError

PROCESSING = {"wdbc", "cleveland-heart-disease", "chronic-kidney-disease", "ilpd-liver"}
REQUIRED_MODELS = {
    "logistic_regression", "svm", "random_forest",
    "vqc", "qsvc", "qnn", "hybrid_pennylane_torch",
}


@pytest.fixture(autouse=True)
def reset_verified_cache():
    clear_verified_readiness_cache(clear_manifest=True)
    yield
    clear_verified_readiness_cache(clear_manifest=True)


def test_readiness_configuration_is_exact_and_invalid_selection_fails():
    library = list_builtin_datasets()
    assert len(library) == 5
    assert set(READY_DEMO_DATASETS) == {"early-stage-diabetes"}
    assert {item["slug"] for item in library if item["demo_readiness"]["status"] == "ready"} == set(READY_DEMO_DATASETS)
    assert {item["slug"] for item in library if item["demo_readiness"]["status"] == "requires_processing"} == PROCESSING
    with pytest.raises(AppError, match="exactly one"):
        validate_readiness_configuration({"wdbc", "early-stage-diabetes"})
    with pytest.raises(AppError, match="exactly one"):
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
            artifact_meta = model["artifact"]
            artifact = _artifact_path(artifact_meta["filename"])
            raw_dill = base64.b64decode(artifact.read_bytes(), validate=True)
            assert artifact_meta["hash_algorithm"] == PACKAGED_ARTIFACT_HASH_ALGORITHM == "sha256"
            assert artifact_meta["hash_scope"] == PACKAGED_ARTIFACT_HASH_SCOPE == "raw_dill_payload"
            assert packaged_artifact_sha256(raw_dill) == model["artifact_sha256"] == artifact_meta["sha256"]
            bundle = _read_bundle(artifact, model["artifact_sha256"])
            assert bundle["dataset_id"] == checked["dataset"]["id"]
            assert bundle["dataset_hash"] == checked["catalog"]["sha256"]


def test_diabetes_package_has_one_controlled_seven_model_experiment_and_all_evidence():
    checked = validate_packaged_dataset("early-stage-diabetes", refresh=True)
    assert len(checked["models"]) == 7
    assert {model["model_type"] for model in checked["models"]} == REQUIRED_MODELS
    assert {model["experiment_id"] for model in checked["models"]} == {checked["experiment"]["id"]}
    assert {model["dataset_id"] for model in checked["models"]} == {checked["dataset"]["id"]}
    assert set(checked["experiment"]["config"]["models"]) == REQUIRED_MODELS
    for model in checked["models"]:
        test_metrics = model["metrics"]["test"]
        assert {"accuracy", "precision", "recall", "f1", "roc_auc", "confusion_matrix"} <= set(test_metrics)
        assert model["metrics"]["operating_point"]["selection_strategy"] == "target_sensitivity"
        assert model["artifact_sha256"] == model["artifact"]["sha256"]

    hybrid = next(model for model in checked["models"] if model["model_type"] == "hybrid_pennylane_torch")
    quantum = hybrid["details"]["quantum"]
    assert quantum["framework"] == "PennyLane"
    assert quantum["classical_framework"] == "PyTorch"
    assert quantum["real_hardware"] is False
    assert quantum["quantum_parameters_changed"] is True

    evidence = checked["evidence"]
    assert set(evidence) == {
        "benchmark", "robustness", "explainability", "predictions",
        "preprocessing", "provenance",
    }
    model_ids = {model["id"] for model in checked["models"]}
    assert set(evidence["benchmark"]["model_ids"]) == model_ids
    assert {result["model_id"] for result in evidence["robustness"]["results"]} == model_ids
    assert evidence["explainability"]["model_id"] == hybrid["id"]
    assert evidence["explainability"]["local"]["contributions"]
    assert evidence["explainability"]["global_summary"]
    cases = evidence["predictions"]["cases"]
    assert {case["case_label"] for case in cases} == {"flagged", "not_flagged"}
    assert all(case["model_id"] == hybrid["id"] for case in cases)
    by_label = {case["case_label"]: case for case in cases}
    assert by_label["flagged"]["predicted_class"] == "positive"
    assert by_label["flagged"]["probability_positive"] >= by_label["flagged"]["threshold"]
    assert by_label["not_flagged"]["predicted_class"] == "negative"
    assert by_label["not_flagged"]["probability_positive"] < by_label["not_flagged"]["threshold"]
    assert evidence["preprocessing"]["split"]["split_hash"]
    assert evidence["provenance"]["dataset"]["source_url"]


def test_corrupted_artifact_and_cross_dataset_relationships_are_rejected(tmp_path):
    corrupted = tmp_path / "corrupted.dill.b64"
    corrupted.write_bytes(base64.b64encode(b"corrupted raw dill payload"))
    with pytest.raises(AppError, match="SHA-256 integrity"):
        _read_bundle(corrupted, "0" * 64)
    manifest = _load_manifest()
    slug = "early-stage-diabetes"
    entry = copy.deepcopy(manifest["datasets"][slug])
    entry["models"][0]["dataset_id"] = "00000000-0000-0000-0000-000000000000"
    with pytest.raises(AppError, match="relationship"):
        _validate_entry(slug, entry, manifest)
    entry = copy.deepcopy(manifest["datasets"][slug])
    entry["experiment"]["dataset_id"] = "00000000-0000-0000-0000-000000000000"
    with pytest.raises(AppError, match="experiment identity"):
        _validate_entry(slug, entry, manifest)
    entry = copy.deepcopy(manifest["datasets"][slug])
    entry["models"][0]["experiment_id"] = "00000000-0000-0000-0000-000000000000"
    with pytest.raises(AppError, match="relationship"):
        _validate_entry(slug, entry, manifest)


def test_readiness_endpoint_and_seeded_records_are_genuine_and_dataset_specific(client):
    response = client.get("/api/datasets/readiness")
    assert response.status_code == 200
    body = response.json()
    assert (body["total"], body["verified_demo_ready"], body["requires_processing"]) == (5, 1, 4)
    for item in body["datasets"]:
        ready = item["demo_readiness"]
        if item["slug"] in READY_DEMO_DATASETS:
            assert ready["status"] == "ready"
            detail = client.get(f"/api/experiments/{ready['experiment_id']}")
            assert detail.status_code == 200
            experiment = detail.json()["experiment"]
            assert experiment["summary"]["experiment_kind"] == "precomputed_verified_demo"
            assert experiment["dataset_id"] == detail.json()["models"][0]["dataset_id"]
            assert len(detail.json()["jobs"]) == 1
            completed_job = detail.json()["jobs"][0]
            assert completed_job["experiment_id"] == experiment["id"]
            assert completed_job["status"] == "succeeded"
            assert completed_job["progress"] == 100
            assert completed_job["errors"] == []
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


def test_repeated_readiness_calls_use_verified_cache_without_reopening_bundles(client, monkeypatch):
    clear_verified_readiness_cache(clear_manifest=True)
    calls = 0
    original = demo_readiness._read_bundle

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(demo_readiness, "_read_bundle", counted)
    first = client.get("/api/datasets/readiness")
    second = client.get("/api/datasets/readiness")
    library = client.get("/api/datasets/library")
    assert first.status_code == second.status_code == library.status_code == 200
    assert calls == 7  # all seven genuine diabetes models, verified once


def test_uploaded_dataset_is_excluded_at_registered_readiness_boundary(client, registered, config):
    stored = client.get(f"/api/datasets/{registered.id}")
    assert stored.status_code == 200
    assert stored.json()["provenance"]["origin"] == "uploaded"
    readiness = client.get(f"/api/datasets/{registered.id}/readiness")
    assert readiness.status_code == 200
    assert readiness.json() == {
        "status": "requires_processing", "instant_demo_available": False,
        "artifact_version": None, "experiment_id": None, "model_ids": [],
        "verified_dataset_hash": None, "verified_artifact_manifest_hash": None,
    }
    preview = client.post("/api/preprocessing/preview", json=config.model_dump(mode="json"))
    assert preview.status_code == 200


def test_installer_validates_all_registry_conflicts_before_any_file_write(client, monkeypatch):
    checked = validate_packaged_dataset("early-stage-diabetes")
    dataset_path = safe_path("data/datasets", checked["dataset"]["id"], ".csv")
    model_data = checked["models"][0]
    model_path = safe_path("models", model_data["id"], ".dill")
    original_dataset_bytes, original_model_bytes = dataset_path.read_bytes(), model_path.read_bytes()
    original_artifact_sha = model_data["artifact_sha256"]
    sentinel_dataset, sentinel_model = b"dataset-sentinel-before-conflict", b"model-sentinel-before-conflict"
    calls = []
    with session_scope() as session:
        model = session.get(ModelRecord, model_data["id"])
        model.artifact_sha256 = "0" * 64
        counts_before = tuple(
            len(list(session.query(entity)))
            for entity in (Dataset, Experiment, Job, ModelRecord)
        )
    dataset_path.write_bytes(sentinel_dataset)
    model_path.write_bytes(sentinel_model)

    def forbidden_write(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("filesystem hydration started before registry validation completed")

    monkeypatch.setattr(demo_readiness, "atomic_bytes", forbidden_write)
    try:
        with pytest.raises(AppError) as error:
            install_verified_demo_artifacts()
        assert error.value.code == "demo_model_mismatch"
        assert calls == []
        assert dataset_path.read_bytes() == sentinel_dataset
        assert model_path.read_bytes() == sentinel_model
        with session_scope() as session:
            counts_after = tuple(
                len(list(session.query(entity)))
                for entity in (Dataset, Experiment, Job, ModelRecord)
            )
            assert session.get(ModelRecord, model_data["id"]).artifact_sha256 == "0" * 64
        assert counts_after == counts_before
    finally:
        dataset_path.write_bytes(original_dataset_bytes)
        model_path.write_bytes(original_model_bytes)
        with session_scope() as session:
            session.get(ModelRecord, model_data["id"]).artifact_sha256 = original_artifact_sha
        clear_verified_readiness_cache(clear_manifest=True)


def _load_generator_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "build_demo_artifacts.py"
    spec = importlib.util.spec_from_file_location("build_demo_artifacts_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_fixture_package(root: Path, label: str) -> None:
    (root / "models").mkdir(parents=True)
    (root / "models" / "model.dill.b64").write_text(label, encoding="utf-8")
    (root / "manifest.json").write_text(
        json.dumps({"artifact": "models/model.dill.b64", "label": label}),
        encoding="utf-8",
    )


def _assert_fixture_package(root: Path, label: str) -> None:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["label"] == label
    referenced = root / manifest["artifact"]
    assert referenced.is_file()
    assert referenced.read_text(encoding="utf-8") == label


def test_transactional_publication_rolls_back_failure_and_publishes_complete_success(tmp_path):
    generator = _load_generator_module()
    published, failed_stage = tmp_path / "demo_artifacts", tmp_path / "failed-stage"
    _write_fixture_package(published, "old-complete-package")
    _write_fixture_package(failed_stage, "new-package-that-must-not-leak")

    def fail_after_backup():
        raise RuntimeError("simulated publication failure")

    with pytest.raises(RuntimeError, match="simulated publication failure"):
        generator.transactional_replace_tree(
            failed_stage,
            published,
            after_backup=fail_after_backup,
        )
    _assert_fixture_package(published, "old-complete-package")
    assert not (published / "models" / "partial.dill.b64").exists()

    successful_stage = tmp_path / "successful-stage"
    _write_fixture_package(successful_stage, "new-complete-package")
    generator.transactional_replace_tree(successful_stage, published)
    _assert_fixture_package(published, "new-complete-package")
