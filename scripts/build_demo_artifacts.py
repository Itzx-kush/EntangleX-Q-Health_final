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
CONFIGS = {"early-stage-diabetes": {"duplicate_policy": "drop_exact"}}
# Stable package slots avoid filename churn; manifest identity remains the model record ID.
ARTIFACT_FILENAMES = {
    ("early-stage-diabetes", kind): f"early-stage-diabetes-{kind}.dill.b64"
    for kind in (
        "logistic_regression", "svm", "random_forest",
        "vqc", "qsvc", "qnn", "hybrid_pennylane_torch",
    )
}
EVIDENCE_FILENAMES = {
    kind: f"early-stage-diabetes-{kind}.json"
    for kind in ("benchmark", "robustness", "explainability", "predictions", "preprocessing", "provenance")
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


def wait(job_id: str, Job, session_scope, timeout: float = 3600) -> None:
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
    if any(not (staged / "evidence" / filename).is_file() for filename in EVIDENCE_FILENAMES.values()):
        raise RuntimeError("A staged manifest-referenced evidence artifact is missing.")


def main() -> None:
    package = ROOT / "backend" / "app" / "demo_artifacts"
    with tempfile.TemporaryDirectory(prefix="qhealth-demo-build-") as build_name:
        build_root = Path(build_name)
        os.environ["QHEALTH_STORAGE_ROOT"] = str(build_root)
        sys.path.insert(0, str(ROOT / "backend"))

        # Application imports happen only after isolated build storage is configured.
        from sqlalchemy import select
        import dill
        import numpy as np
        from app.api.schemas import (
            HybridModelConfig, ModelParameters, PipelineConfig, QuantumConfig,
            RobustnessScenario, TrainingConfig,
        )
        from app.data.service import load_frame, register_builtin
        from app.database import init_db, session_scope
        from app.demo_readiness import (
            ARTIFACT_SCHEMA_VERSION, ARTIFACT_VERSION, PACKAGED_ARTIFACT_HASH_ALGORITHM,
            PACKAGED_ARTIFACT_HASH_SCOPE, READY_DEMO_DATASETS, packaged_artifact_sha256,
            validate_package_tree,
        )
        from app.evaluation.metrics import score_outputs
        from app.evaluation.robustness import _changes, _measure, perturb_frame
        from app.explainability.hybrid_shap import HybridShapAdapter, local_contract
        from app.jobs.manager import manager
        from app.storage.entities import Dataset, Experiment, Job, ModelRecord
        from app.utils.serialization import clean_json

        if set(CONFIGS) != set(READY_DEMO_DATASETS):
            raise RuntimeError("Generator configuration must match READY_DEMO_DATASETS exactly")

        # The complete replacement is built in a temporary sibling, on the same filesystem.
        with tempfile.TemporaryDirectory(prefix=".demo_artifacts-stage-", dir=package.parent) as staged_name:
            staged = Path(staged_name)
            staged_models = staged / "models"
            staged_evidence = staged / "evidence"
            staged_models.mkdir()
            staged_evidence.mkdir()
            shutil.copy2(package / "__init__.py", staged / "__init__.py")

            init_db()
            manager.start()
            entries = {}
            try:
                for slug in sorted(READY_DEMO_DATASETS):
                    dataset = register_builtin(slug)
                    config = TrainingConfig(
                        dataset_id=dataset.id,
                        models=[
                            "logistic_regression", "svm", "random_forest",
                            "vqc", "qsvc", "qnn", "hybrid_pennylane_torch",
                        ],
                        pipeline=PipelineConfig(imputer="median", scaler="standard", selection="anova", k_features=12,
                                                pca_components=4, pca_whiten=False, angle_scaling=True),
                        parameters=ModelParameters(forest_trees=80, forest_max_depth=8),
                        quantum=QuantumConfig(
                            backend="statevector", qubits=4, feature_map_reps=1,
                            ansatz_reps=1, optimizer="COBYLA", maxiter=5,
                        ),
                        hybrid=HybridModelConfig(
                            qubits=4, quantum_layers=1, classical_hidden_dimensions=[8],
                            learning_rate=0.01, epochs=5, batch_size=16,
                            deterministic_seed=2026, sample_cap=60,
                        ),
                        seed=2026, test_size=0.2, cv_folds=2, max_samples=60,
                        duplicate_policy=CONFIGS[slug]["duplicate_policy"],
                        probability_threshold=0.5, threshold_strategy="target_sensitivity",
                        target_sensitivity=0.90,
                        calibration="none", calibration_folds=3,
                    )
                    job, experiment = manager.enqueue(config)
                    wait(job.id, Job, session_scope)
                    with session_scope() as session:
                        exp = session.get(Experiment, experiment.id)
                        exp.summary = {**exp.summary, "experiment_kind": "precomputed_verified_demo",
                                       "artifact_version": ARTIFACT_VERSION,
                                       "description": "One controlled seven-model diabetes benchmark; precomputed research evidence.",
                                       "scientific_scope": "Research benchmark only; not diagnosis, clinical validation, treatment guidance, or medical advice."}
                        models = list(session.scalars(select(ModelRecord).where(
                            ModelRecord.experiment_id == exp.id).order_by(ModelRecord.model_type)))
                        if len(models) != 7 or any(model.status != "ready" for model in models):
                            failures = {model.model_type: model.details for model in models if model.status != "ready"}
                            raise RuntimeError(f"expected seven ready models for {slug}; failures={failures}")
                        for model in models:
                            model.details = {**model.details, "experiment_kind": "precomputed_verified_demo",
                                             "artifact_version": ARTIFACT_VERSION}
                        dataset_data = serialise_dataset(session.get(Dataset, dataset.id))
                        experiment_data = serialise_experiment(exp)
                        job_data = serialise_job(session.get(Job, job.id))
                    model_data = []
                    bundles = {}
                    for model in models:
                        payload = (build_root / "models" / f"{model.id}.dill").read_bytes()
                        bundles[model.model_type] = dill.loads(payload)
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
                    model_data.sort(key=lambda value: value["model_type"])

                    dataset_row, source = load_frame(dataset.id)
                    hybrid_model = next(model for model in model_data if model["model_type"] == "hybrid_pennylane_torch")
                    hybrid_bundle = bundles["hybrid_pennylane_torch"]
                    features, numeric = hybrid_bundle["features"], hybrid_bundle["numeric"]
                    target, positive = dataset_row.provenance["target"], dataset_row.provenance["positive_label"]
                    negative = dataset_row.provenance["negative_label"]
                    labels = (source[target].astype(str) == positive).astype(int).to_numpy()
                    test_indices = np.asarray(hybrid_bundle["test_indices"], dtype=int)
                    train_indices = np.asarray(hybrid_bundle["train_indices"], dtype=int)
                    holdout = source[features].iloc[test_indices].copy()
                    background = source[features].iloc[train_indices].copy()
                    threshold = float(hybrid_bundle["operating_threshold"])
                    _, hybrid_scores, _ = score_outputs(hybrid_bundle["estimator"], holdout, threshold)
                    _, all_hybrid_scores, _ = score_outputs(
                        hybrid_bundle["estimator"], source[features], threshold
                    )
                    high_position = int(np.argmax(hybrid_scores))
                    positive_row_index = int(test_indices[high_position])
                    negative_row_index = int(np.argmin(all_hybrid_scores))
                    if all_hybrid_scores[negative_row_index] >= threshold:
                        raise RuntimeError("The genuine hybrid artifact produced no deterministic not-flagged representative case.")

                    base = {
                        "dataset_id": dataset.id,
                        "dataset_hash": dataset.sha256,
                        "experiment_id": experiment.id,
                        "artifact_version": ARTIFACT_VERSION,
                        "scientific_scope": "Research benchmark demonstration; not clinical validation or medical advice.",
                    }
                    all_model_ids = [model["id"] for model in model_data]
                    benchmark = {
                        **base, "evidence_type": "benchmark", "model_ids": all_model_ids,
                        "comparison_contract": model_data[0]["details"]["comparison_conditions"],
                        "models": [{
                            "model_id": model["id"], "model_type": model["model_type"],
                            "metrics": model["metrics"], "execution": model["details"].get("quantum"),
                            "operating_point": model["details"].get("operating_point"),
                            "runtime": model["metrics"].get("timing"),
                        } for model in model_data],
                        "claims": {"quantum_advantage": False, "real_quantum_hardware": False},
                    }

                    scenarios = [
                        RobustnessScenario(perturbation_type="missingness", level=0.05),
                        RobustnessScenario(perturbation_type="categorical", level=0.05),
                    ]
                    perturbations = [
                        (scenario, perturb_frame(holdout, background, numeric, scenario, config.seed + number))
                        for number, scenario in enumerate(scenarios)
                    ]
                    robustness_results = []
                    for model in model_data:
                        bundle = bundles[model["model_type"]]
                        model_threshold = float(bundle["operating_threshold"])
                        baseline_metrics, baseline_seconds = _measure(
                            bundle["estimator"], holdout, labels[test_indices], model_threshold
                        )
                        for scenario, perturbation in perturbations:
                            changed, changed_seconds = _measure(
                                bundle["estimator"], perturbation["frame"], labels[test_indices], model_threshold
                            )
                            delta, relative, undefined = _changes(baseline_metrics, changed)
                            robustness_results.append({
                                "model_id": model["id"], "model_type": model["model_type"],
                                "condition": scenario.perturbation_type,
                                "configuration": scenario.model_dump(mode="json"),
                                "perturbation": perturbation["metadata"],
                                "baseline": baseline_metrics, "degraded": changed,
                                "delta": delta, "relative_delta": relative,
                                "undefined_metrics": undefined,
                                "timing_seconds": {"baseline": baseline_seconds, "perturbed": changed_seconds},
                                "evaluation_indices": test_indices.tolist(),
                            })
                    robustness = {
                        **base, "evidence_type": "robustness", "model_ids": all_model_ids,
                        "method": "controlled-perturbation-v1", "results": robustness_results,
                    }

                    cases = []
                    for label, row_index, probability in (
                        ("flagged", positive_row_index, float(all_hybrid_scores[positive_row_index])),
                        ("not_flagged", negative_row_index, float(all_hybrid_scores[negative_row_index])),
                    ):
                        cases.append({
                            "case_id": f"heldout-row-{row_index}", "case_label": label,
                            "model_id": hybrid_model["id"], "model_type": hybrid_model["model_type"],
                            "row_index": row_index, "input": clean_json(source[features].iloc[row_index].to_dict()),
                            "probability_positive": probability, "threshold": threshold,
                            "threshold_source": hybrid_bundle["threshold_source"],
                            "predicted_class": positive if probability >= threshold else negative,
                        })
                    predictions = {
                        **base, "evidence_type": "predictions", "model_ids": [hybrid_model["id"]],
                        "model_id": hybrid_model["id"], "cases": cases,
                    }

                    adapter = HybridShapAdapter(
                        hybrid_bundle["estimator"], background, features, numeric, threshold, config.seed
                    )
                    local_result = adapter.explain(holdout.iloc[[high_position]], repeats=1)
                    local = local_contract(
                        local_result, threshold=threshold,
                        threshold_source=hybrid_bundle["threshold_source"],
                        predicted_class=cases[0]["predicted_class"],
                        positive_label=positive, negative_label=negative, risk_category="research_flagged",
                    )
                    local["case_id"] = cases[0]["case_id"]
                    global_frame = source[features].iloc[[positive_row_index, negative_row_index]].copy()
                    global_result = adapter.explain(global_frame, repeats=1)
                    explainability = {
                        **base, "evidence_type": "explainability", "model_ids": [hybrid_model["id"]],
                        "model_id": hybrid_model["id"], "method": "SHAP permutation explainer",
                        "output_path": "raw input → shared preprocessing → PennyLane expectation values → PyTorch output head → positive-class probability",
                        "local": local,
                        "global_summary": [{
                            "feature": feature,
                            "mean_absolute_shap": float(np.mean(np.abs(global_result.values[:, index]))),
                            "mean_signed_shap": float(np.mean(global_result.values[:, index])),
                        } for index, feature in enumerate(features)],
                    }
                    explainability["global_summary"].sort(
                        key=lambda value: value["mean_absolute_shap"], reverse=True
                    )
                    preprocessing = {
                        **base, "evidence_type": "preprocessing", "model_ids": all_model_ids,
                        "configuration": config.model_dump(mode="json"),
                        "fitted_preprocessing": hybrid_model["details"]["preprocessing"],
                        "representation": hybrid_model["details"]["common_representation"],
                        "split": hybrid_model["details"]["split"],
                    }
                    provenance = {
                        **base, "evidence_type": "provenance", "model_ids": all_model_ids,
                        "dataset": dataset_data["provenance"],
                    }
                    evidence_values = {
                        "benchmark": benchmark, "robustness": robustness,
                        "explainability": explainability, "predictions": predictions,
                        "preprocessing": preprocessing, "provenance": provenance,
                    }
                    evidence_refs = {}
                    for kind, value in evidence_values.items():
                        filename = EVIDENCE_FILENAMES[kind]
                        payload = (json.dumps(clean_json(value), indent=2, sort_keys=True) + "\n").encode("utf-8")
                        (staged_evidence / filename).write_bytes(payload)
                        evidence_refs[kind] = {
                            "filename": filename, "sha256": hashlib.sha256(payload).hexdigest(),
                            "hash_algorithm": "sha256", "hash_scope": "exact_json_bytes",
                        }
                    entries[slug] = {
                        "slug": slug, "dataset_sha256": dataset.sha256, "dataset": dataset_data,
                        "experiment": experiment_data, "job": job_data, "models": model_data,
                        "evidence": evidence_refs,
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
