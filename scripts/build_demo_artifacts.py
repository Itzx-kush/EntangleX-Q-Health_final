#!/usr/bin/env python3
"""Regenerate and transactionally publish genuine verified-demo packages."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = {
    "wdbc": {"duplicate_policy": "reject"},
    "early-stage-diabetes": {"duplicate_policy": "drop_exact"},
}
# Stable package slots avoid filename churn; manifest identity remains the model record ID.
ARTIFACT_FILENAMES = {
    ("early-stage-diabetes", "logistic_regression"): "d025c91a-d637-46ee-bd29-8bbce2d1bf69.dill.b64",
    ("early-stage-diabetes", "random_forest"): "baa94644-b5ff-4f31-8375-ade8b7dc54eb.dill.b64",
    ("wdbc", "logistic_regression"): "f2afdeb1-f61c-40d7-800f-52d6fc80d2e2.dill.b64",
    ("wdbc", "random_forest"): "e088bd64-7e1b-4a81-b883-48311dde3eb8.dill.b64",
}


def serialise_dataset(row) -> dict:
    return {"id": row.id, "name": row.name, "filename": row.filename, "sha256": row.sha256,
            "provenance": row.provenance, "quality": row.quality, "created_at": row.created_at.isoformat()}


def serialise_experiment(row) -> dict:
    return {"id": row.id, "dataset_id": row.dataset_id, "parent_id": row.parent_id, "status": row.status,
            "config": row.config, "summary": row.summary, "created_at": row.created_at.isoformat()}


def serialise_job(row) -> dict:
    return {"id": row.id, "experiment_id": row.experiment_id, "status": row.status,
            "progress": row.progress, "state": row.state, "errors": row.errors,
            "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat()}


def serialise_model(row, filename: str, sha256: str, hash_algorithm: str, hash_scope: str) -> dict:
    return {"id": row.id, "experiment_id": row.experiment_id, "dataset_id": row.dataset_id,
            "model_type": row.model_type, "status": row.status, "artifact_sha256": sha256,
            "details": row.details, "metrics": row.metrics, "created_at": row.created_at.isoformat(),
            "artifact": {"filename": filename, "sha256": sha256,
                         "hash_algorithm": hash_algorithm, "hash_scope": hash_scope}}


def wait(job_id: str, Job, session_scope, timeout: float = 180) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with session_scope() as session:
            job = session.get(Job, job_id)
            if job.status not in {"queued", "running", "cancel_requested"}:
                if job.status != "succeeded":
                    raise RuntimeError(f"training failed: {job.status} {job.errors}")
                return
        time.sleep(0.1)
    raise TimeoutError(job_id)


def transactional_replace_tree(
    staged: Path,
    published: Path,
    *,
    after_backup: Callable[[], None] | None = None,
) -> None:
    """Replace a complete package tree; restore the previous tree on any swap failure."""
    staged, published = staged.resolve(), published.resolve()
    if staged.parent != published.parent or not staged.is_dir() or not published.is_dir():
        raise ValueError("Staged and published package trees must be existing siblings.")
    backup = published.parent / f".{published.name}.backup-{uuid4().hex}"
    os.replace(published, backup)
    try:
        if after_backup is not None:
            after_backup()
        os.replace(staged, published)
    except BaseException:
        if published.exists():
            shutil.rmtree(published)
        os.replace(backup, published)
        raise
    else:
        shutil.rmtree(backup)


def _assert_staged_shape(entries: dict, ready_slugs: set[str] | frozenset[str], staged: Path) -> None:
    if set(entries) != set(ready_slugs):
        raise RuntimeError("Staged manifest does not contain exactly the configured ready datasets.")
    models = [model for entry in entries.values() for model in entry["models"]]
    expected_names = set(ARTIFACT_FILENAMES.values())
    actual_names = {model["artifact"]["filename"] for model in models}
    if len(models) != len(expected_names) or actual_names != expected_names:
        raise RuntimeError("Staged model count or filenames do not match the package contract.")
    if any(not (staged / "models" / filename).is_file() for filename in expected_names):
        raise RuntimeError("A staged manifest-referenced model artifact is missing.")


def main() -> None:
    package = ROOT / "backend" / "app" / "demo_artifacts"
    with tempfile.TemporaryDirectory(prefix="qhealth-demo-build-") as build_name:
        build_root = Path(build_name)
        os.environ["QHEALTH_STORAGE_ROOT"] = str(build_root)
        sys.path.insert(0, str(ROOT / "backend"))

        # Application imports happen only after isolated build storage is configured.
        from sqlalchemy import select
        from app.api.schemas import ModelParameters, PipelineConfig, TrainingConfig
        from app.data.service import register_builtin
        from app.database import init_db, session_scope
        from app.demo_readiness import (
            ARTIFACT_SCHEMA_VERSION, ARTIFACT_VERSION, PACKAGED_ARTIFACT_HASH_ALGORITHM,
            PACKAGED_ARTIFACT_HASH_SCOPE, READY_DEMO_DATASETS, packaged_artifact_sha256,
            validate_package_tree,
        )
        from app.jobs.manager import manager
        from app.storage.entities import Dataset, Experiment, Job, ModelRecord

        if set(CONFIGS) != set(READY_DEMO_DATASETS):
            raise RuntimeError("Generator configuration must match READY_DEMO_DATASETS exactly")

        # The complete replacement is built in a temporary sibling, on the same filesystem.
        with tempfile.TemporaryDirectory(prefix=".demo_artifacts-stage-", dir=package.parent) as staged_name:
            staged = Path(staged_name)
            staged_models = staged / "models"
            staged_models.mkdir()
            shutil.copy2(package / "__init__.py", staged / "__init__.py")

            init_db()
            manager.start()
            entries = {}
            try:
                for slug in sorted(READY_DEMO_DATASETS):
                    dataset = register_builtin(slug)
                    config = TrainingConfig(
                        dataset_id=dataset.id,
                        models=["logistic_regression", "random_forest"],
                        pipeline=PipelineConfig(imputer="median", scaler="standard", selection="anova", k_features=12,
                                                pca_components=4, pca_whiten=False, angle_scaling=True),
                        parameters=ModelParameters(forest_trees=80, forest_max_depth=8),
                        seed=2026, test_size=0.2, cv_folds=3, max_samples=160,
                        duplicate_policy=CONFIGS[slug]["duplicate_policy"], probability_threshold=0.5,
                        calibration="none", calibration_folds=3,
                    )
                    job, experiment = manager.enqueue(config)
                    wait(job.id, Job, session_scope)
                    with session_scope() as session:
                        exp = session.get(Experiment, experiment.id)
                        exp.summary = {**exp.summary, "experiment_kind": "precomputed_verified_demo",
                                       "artifact_version": ARTIFACT_VERSION,
                                       "description": "Controlled benchmark experiment; precomputed research result."}
                        models = list(session.scalars(select(ModelRecord).where(
                            ModelRecord.experiment_id == exp.id).order_by(ModelRecord.model_type)))
                        if len(models) != 2 or any(model.status != "ready" for model in models):
                            raise RuntimeError(f"expected two ready models for {slug}")
                        for model in models:
                            model.details = {**model.details, "experiment_kind": "precomputed_verified_demo",
                                             "artifact_version": ARTIFACT_VERSION}
                        dataset_data = serialise_dataset(session.get(Dataset, dataset.id))
                        experiment_data = serialise_experiment(exp)
                        job_data = serialise_job(session.get(Job, job.id))
                    model_data = []
                    for model in models:
                        payload = (build_root / "models" / f"{model.id}.dill").read_bytes()
                        sha = packaged_artifact_sha256(payload)
                        filename = ARTIFACT_FILENAMES[(slug, model.model_type)]
                        (staged_models / filename).write_bytes(base64.b64encode(payload))
                        with session_scope() as session:
                            stored = session.get(ModelRecord, model.id)
                            stored.artifact_sha256 = sha
                            stored.details = {**stored.details, "experiment_kind": "precomputed_verified_demo",
                                              "artifact_version": ARTIFACT_VERSION,
                                              "artifact_integrity": {"scheme": "packaged_sha256",
                                                                     "algorithm": PACKAGED_ARTIFACT_HASH_ALGORITHM,
                                                                     "scope": PACKAGED_ARTIFACT_HASH_SCOPE}}
                            model_data.append(serialise_model(
                                stored, filename, sha, PACKAGED_ARTIFACT_HASH_ALGORITHM,
                                PACKAGED_ARTIFACT_HASH_SCOPE))
                    entries[slug] = {
                        "slug": slug, "dataset_sha256": dataset.sha256, "dataset": dataset_data,
                        "experiment": experiment_data, "job": job_data, "models": model_data,
                        "prediction_sample": {"source": "withheld row from packaged public benchmark", "target_withheld": True},
                        "explanations": {"mode": "on_demand_after_integrity_validation"},
                        "report": {"mode": "generated_on_demand_from_verified_registry_records"},
                    }
            finally:
                manager.stop()

            manifest = {"schema_version": ARTIFACT_SCHEMA_VERSION, "artifact_version": ARTIFACT_VERSION,
                        "generated_by": "scripts/build_demo_artifacts.py", "datasets": entries}
            canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            manifest["manifest_sha256"] = hashlib.sha256(canonical).hexdigest()
            (staged / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            _assert_staged_shape(entries, READY_DEMO_DATASETS, staged)
            validate_package_tree(staged)  # Full hashes, safe bundles, and all relationships.
            transactional_replace_tree(staged, package)

            print(json.dumps({"manifest_sha256": manifest["manifest_sha256"],
                              "datasets": {slug: {"experiment_id": value["experiment"]["id"],
                                                   "model_ids": [model["id"] for model in value["models"]]}
                                           for slug, value in entries.items()}}, indent=2))


if __name__ == "__main__":
    main()
