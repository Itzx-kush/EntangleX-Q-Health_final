#!/usr/bin/env python3
"""Regenerate the two genuine verified-demo packages through the production training manager."""
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

ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = Path(tempfile.mkdtemp(prefix="qhealth-demo-build-"))
os.environ["QHEALTH_STORAGE_ROOT"] = str(BUILD_ROOT)
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select
from app.api.schemas import ModelParameters, PipelineConfig, TrainingConfig
from app.data.service import register_builtin
from app.database import init_db, session_scope
from app.demo_readiness import (ARTIFACT_SCHEMA_VERSION, ARTIFACT_VERSION, PACKAGED_ARTIFACT_HASH_ALGORITHM,
    PACKAGED_ARTIFACT_HASH_SCOPE, READY_DEMO_DATASETS, packaged_artifact_sha256)
from app.jobs.manager import manager
from app.storage.entities import Dataset, Experiment, Job, ModelRecord

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


def serialise_dataset(row: Dataset) -> dict:
    return {"id": row.id, "name": row.name, "filename": row.filename, "sha256": row.sha256,
            "provenance": row.provenance, "quality": row.quality, "created_at": row.created_at.isoformat()}


def serialise_experiment(row: Experiment) -> dict:
    return {"id": row.id, "dataset_id": row.dataset_id, "parent_id": row.parent_id, "status": row.status,
            "config": row.config, "summary": row.summary, "created_at": row.created_at.isoformat()}


def serialise_job(row: Job) -> dict:
    return {"id": row.id, "experiment_id": row.experiment_id, "status": row.status,
            "progress": row.progress, "state": row.state, "errors": row.errors,
            "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat()}


def serialise_model(row: ModelRecord, filename: str, sha256: str) -> dict:
    return {"id": row.id, "experiment_id": row.experiment_id, "dataset_id": row.dataset_id,
            "model_type": row.model_type, "status": row.status, "artifact_sha256": sha256,
            "details": row.details, "metrics": row.metrics, "created_at": row.created_at.isoformat(),
            "artifact": {"filename": filename, "sha256": sha256,
                         "hash_algorithm": PACKAGED_ARTIFACT_HASH_ALGORITHM,
                         "hash_scope": PACKAGED_ARTIFACT_HASH_SCOPE}}


def wait(job_id: str, timeout: float = 180) -> None:
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


def main() -> None:
    if set(CONFIGS) != set(READY_DEMO_DATASETS):
        raise RuntimeError("Generator configuration must match READY_DEMO_DATASETS exactly")
    package = ROOT / "backend" / "app" / "demo_artifacts"
    model_package = package / "models"
    model_package.mkdir(parents=True, exist_ok=True)
    for filename in ARTIFACT_FILENAMES.values():
        (model_package / filename).unlink(missing_ok=True)
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
            wait(job.id)
            with session_scope() as session:
                exp = session.get(Experiment, experiment.id)
                exp.summary = {**exp.summary, "experiment_kind": "precomputed_verified_demo",
                               "artifact_version": ARTIFACT_VERSION,
                               "description": "Controlled benchmark experiment; precomputed research result."}
                models = list(session.scalars(select(ModelRecord).where(ModelRecord.experiment_id == exp.id).order_by(ModelRecord.model_type)))
                if not models or any(model.status != "ready" for model in models):
                    raise RuntimeError(f"not all models ready for {slug}")
                for model in models:
                    model.details = {**model.details, "experiment_kind": "precomputed_verified_demo", "artifact_version": ARTIFACT_VERSION}
                dataset_data = serialise_dataset(session.get(Dataset, dataset.id))
                experiment_data = serialise_experiment(exp)
                job_data = serialise_job(session.get(Job, job.id))
            model_data = []
            for model in models:
                source = BUILD_ROOT / "models" / f"{model.id}.dill"
                payload = source.read_bytes()
                sha = packaged_artifact_sha256(payload)
                filename = ARTIFACT_FILENAMES[(slug, model.model_type)]
                (model_package / filename).write_bytes(base64.b64encode(payload))
                with session_scope() as session:
                    stored = session.get(ModelRecord, model.id)
                    stored.artifact_sha256 = sha
                    stored.details = {**stored.details, "experiment_kind": "precomputed_verified_demo", "artifact_version": ARTIFACT_VERSION,
                                      "artifact_integrity": {"scheme": "packaged_sha256", "algorithm": PACKAGED_ARTIFACT_HASH_ALGORITHM,
                                                             "scope": PACKAGED_ARTIFACT_HASH_SCOPE}}
                    model_data.append(serialise_model(stored, filename, sha))
            entries[slug] = {"slug": slug, "dataset_sha256": dataset.sha256, "dataset": dataset_data,
                             "experiment": experiment_data, "job": job_data, "models": model_data,
                             "prediction_sample": {"source": "withheld row from packaged public benchmark", "target_withheld": True},
                             "explanations": {"mode": "on_demand_after_integrity_validation"},
                             "report": {"mode": "generated_on_demand_from_verified_registry_records"}}
    finally:
        manager.stop()
    manifest = {"schema_version": ARTIFACT_SCHEMA_VERSION, "artifact_version": ARTIFACT_VERSION,
                "generated_by": "scripts/build_demo_artifacts.py", "datasets": entries}
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    manifest["manifest_sha256"] = hashlib.sha256(canonical).hexdigest()
    (package / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"manifest_sha256": manifest["manifest_sha256"],
                      "datasets": {slug: {"experiment_id": value["experiment"]["id"],
                                           "model_ids": [model["id"] for model in value["models"]]}
                                   for slug, value in entries.items()}}, indent=2))
    shutil.rmtree(BUILD_ROOT, ignore_errors=True)


if __name__ == "__main__":
    main()
