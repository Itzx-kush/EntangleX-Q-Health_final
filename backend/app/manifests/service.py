from __future__ import annotations

import hashlib
import os
import platform
from copy import deepcopy
from uuid import uuid4

from sqlalchemy import select

from .. import __version__
from ..api.schemas import TrainingConfig
from ..data.splitting import PreparedData
from ..database import session_scope
from ..evaluation.metrics import METRIC_NAMES
from ..storage.entities import Artifact, Dataset, DatasetVersion, Experiment, Job, ModelRecord, Run
from ..storage.repository import require
from ..utils.errors import AppError
from ..utils.serialization import canonical_json_bytes, fingerprint, software_versions, utcnow
from .schemas import ManifestIntegrityResult, RunManifest


MANIFEST_SCHEMA_VERSION = "1.0.0"
REPRODUCIBLE = "CONFIGURATIONALLY_REPRODUCIBLE"
INCOMPLETE = "INCOMPLETE_PROVENANCE"


def _manifest_hash(payload: dict) -> str:
    canonical = deepcopy(payload)
    canonical["identity"]["manifest_hash"] = ""
    return hashlib.sha256(canonical_json_bytes(canonical)).hexdigest()


def _scientific_configuration(payload: dict) -> dict:
    return {
        key: payload[key]
        for key in [
            "dataset", "sampling", "split", "cross_validation", "preprocessing",
            "feature_engineering", "feature_selection", "dimensionality_reduction",
            "models", "threshold_protocol", "evaluation_protocol",
        ]
    }


def configuration_fingerprint(payload: dict) -> str:
    """Hash scientific conditions only; identity, time and runtime are excluded."""
    return fingerprint(_scientific_configuration(payload))


def _model_configuration(kind: str, config: TrainingConfig) -> dict:
    parameters = config.parameters.model_dump(mode="json")
    common = {
        "model_identifier": kind,
        "deterministic_seed": config.seed,
        "class_weight": parameters["class_weight"],
        "calibration": {"method": config.calibration, "folds": config.calibration_folds},
    }
    if kind == "logistic_regression":
        return {**common, "model_family": "classical", "estimator_type": "LogisticRegression",
                "hyperparameters": {"C": parameters["logistic_c"], "max_iter": 2000},
                "training_parameters": {}, "quantum": None}
    if kind == "svm":
        return {**common, "model_family": "classical", "estimator_type": "SVC",
                "hyperparameters": {"C": parameters["svm_c"], "kernel": parameters["svm_kernel"], "probability": False},
                "training_parameters": {}, "quantum": None}
    if kind == "random_forest":
        return {**common, "model_family": "classical", "estimator_type": "RandomForestClassifier",
                "hyperparameters": {"n_estimators": parameters["forest_trees"], "max_depth": parameters["forest_max_depth"], "n_jobs": 1},
                "training_parameters": {}, "quantum": None}
    if kind in {"vqc", "qsvc", "qnn"}:
        q = config.quantum
        estimator = {"vqc": "VQC", "qsvc": "QSVC", "qnn": "NeuralNetworkClassifier(SamplerQNN)"}[kind]
        quantum = {
            "framework": "Qiskit", "classical_framework": None, "model_type": kind,
            "backend": q.backend,
            "execution_kind": "exact local quantum simulation" if q.backend == "statevector" else "finite-shot local Aer simulation",
            "real_hardware": False, "qubits": q.qubits, "feature_map": "ZZFeatureMap",
            "ansatz": None if kind == "qsvc" else "RealAmplitudes",
            "circuit_layers": None if kind == "qsvc" else q.ansatz_reps,
            "shots": None if q.backend == "statevector" else q.shots,
            "noise_configuration": {
                "probability": q.noise_probability,
                "interpretation": "Illustrative depolarizing simulator channel; not a characterized device." if q.noise_probability else "none",
            },
            "optimizer": q.optimizer if kind != "qsvc" else "SVC dual optimization",
            "learning_rate": None, "epochs_or_iterations": q.maxiter if kind != "qsvc" else 1,
            "batch_size": None, "seed": config.seed,
            "circuit_resource_evidence": "Run quantum_metadata Artifact created from the fitted estimator.",
        }
        return {**common, "model_family": "qiskit_quantum", "estimator_type": estimator,
                "hyperparameters": q.model_dump(mode="json"),
                "training_parameters": {"max_samples": config.max_samples}, "quantum": quantum}
    h = config.hybrid
    quantum = {
        "framework": "PennyLane", "classical_framework": "PyTorch", "model_type": kind,
        "backend": h.backend, "execution_kind": "local PennyLane quantum simulation",
        "real_hardware": False, "qubits": h.qubits, "feature_map": "AngleEmbedding(Y)",
        "ansatz": "StronglyEntanglingLayers", "circuit_layers": h.quantum_layers,
        "shots": None, "noise_configuration": {"probability": 0.0, "interpretation": "none"},
        "optimizer": h.optimizer, "learning_rate": h.learning_rate,
        "epochs_or_iterations": h.epochs, "batch_size": h.batch_size,
        "seed": h.deterministic_seed,
        "circuit_resource_evidence": "Run quantum_metadata Artifact created from the fitted estimator.",
    }
    return {**common, "model_family": "pennylane_hybrid", "estimator_type": "PennyLaneTorchClassifier",
            "hyperparameters": h.model_dump(mode="json"),
            "training_parameters": {"sample_cap": h.sample_cap}, "quantum": quantum}


def build_manifest(
    *,
    run: Run,
    experiment: Experiment,
    data: PreparedData,
    config: TrainingConfig,
    job_id: str,
    locked_at,
    manifest_id: str,
) -> dict:
    split = data.split_metadata()
    provenance = data.dataset_version.provenance if data.dataset_version else data.dataset.provenance
    pipeline = config.pipeline
    packages = software_versions()
    schema_fingerprint = fingerprint({
        "features": data.features,
        "numeric": data.numeric,
        "target": provenance["target"],
        "positive_label": provenance["positive_label"],
        "negative_label": provenance["negative_label"],
    })
    feature_engineering_fingerprint = fingerprint({
        "source_features": data.features,
        "log_features": pipeline.log_features,
        "ratios": [ratio.model_dump(mode="json") for ratio in pipeline.ratios],
    })
    payload = {
        "identity": {
            "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
            "manifest_id": manifest_id,
            "experiment_id": experiment.id,
            "run_id": run.id,
            "created_at": locked_at.isoformat(),
            "immutable_at": locked_at.isoformat(),
            "manifest_hash": "",
            "configuration_fingerprint": "",
            "parent_run_id": None,
            "parent_experiment_id": experiment.parent_id,
        },
        "dataset": {
            "dataset_id": data.dataset.id,
            "dataset_version_id": data.dataset_version.id if data.dataset_version else None,
            "dataset_version": data.dataset_version.version_label if data.dataset_version else None,
            "name": data.dataset.name,
            "source": provenance.get("source", "unspecified"),
            "source_reference": provenance.get("source_url"),
            "source_version": provenance.get("version", "unspecified"),
            "sha256": data.dataset_version.content_sha256 if data.dataset_version else data.dataset.sha256,
            "hash_scope": provenance.get("hash_scope", "exact stored CSV bytes"),
            "row_count": int(provenance.get("row_count", len(data.frame))),
            "feature_count": len(data.features),
            "target_column": provenance["target"],
            "positive_class": provenance["positive_label"],
            "negative_class": provenance["negative_label"],
            "class_distribution": {str(k): int(v) for k, v in provenance["class_distribution"].items()},
            "input_filename": provenance.get("original_filename", data.dataset.filename),
            "storage_identity": data.dataset_version.storage_reference if data.dataset_version else f"data/datasets/{data.dataset.id}.csv",
            "schema_fingerprint": data.dataset_version.schema_fingerprint if data.dataset_version else schema_fingerprint,
            "feature_names": list(data.features),
        },
        "sampling": {
            "strategy": "seeded stratified bounded sampling before split" if data.excluded_by_sampling else "all eligible rows after duplicate policy",
            "requested_sample_count": config.max_samples,
            "actual_sample_count": split["evaluated_sample_count"],
            "sampling_seed": config.seed,
            "selected_row_fingerprint": split["sample_pool_hash"],
            "class_balancing": "stratification preserves observed class proportions; no resampling or synthetic balancing",
            "restrictions": ["independent samples only", "common sample pool shared by every model in the Run"],
            "dropped_duplicate_count": split["dropped_duplicate_count"],
            "excluded_by_sampling": split["excluded_by_sampling"],
        },
        "split": {
            "strategy": "stratified random holdout",
            "test_size": config.test_size, "split_seed": config.seed,
            "train_row_count": split["train_count"], "test_row_count": split["test_count"],
            "train_index_fingerprint": fingerprint(split["train_indices"]),
            "test_index_fingerprint": fingerprint(split["test_indices"]),
            "split_fingerprint": split["split_hash"],
            "stratification": "binary encoded target", "grouping": "not_supported", "time_based": "not_supported",
        },
        "cross_validation": {
            "strategy": "StratifiedKFold", "folds": config.cv_folds, "shuffle": True, "seed": config.seed,
            "fold_structure_fingerprint": fingerprint([(a.tolist(), b.tolist()) for a, b in data.cv]),
            "training_only_fitting": True, "fold_local_preprocessing": True,
        },
        "preprocessing": {
            "missing_value_strategy": pipeline.imputer,
            "numeric_imputation": pipeline.imputer, "categorical_imputation": "most_frequent",
            "scaling": pipeline.scaler, "outlier_strategy": pipeline.outlier_strategy,
            "clipping_quantiles": {"lower": pipeline.lower_quantile, "upper": pipeline.upper_quantile} if pipeline.outlier_strategy == "clip_quantiles" else None,
            "duplicate_policy": config.duplicate_policy,
            "infinite_value_handling": "blocked by source quality validation",
            "categorical_encoding": "OneHotEncoder(handle_unknown=ignore, max_categories=32)",
            "angle_scaling": pipeline.angle_scaling,
            "angle_range": [0.0, 3.141592653589793] if pipeline.angle_scaling else None,
        },
        "feature_engineering": {
            "log_transforms": list(pipeline.log_features),
            "ratio_transforms": [ratio.model_dump(mode="json") for ratio in pipeline.ratios],
            "source_features": list(data.features),
            "resulting_schema_fingerprint": feature_engineering_fingerprint,
        },
        "feature_selection": {
            "method": pipeline.selection, "requested_feature_count": pipeline.k_features,
            "variance_threshold": pipeline.variance_threshold,
            "scoring_parameters": {"mutual_info_random_state": config.seed if pipeline.selection == "mutual_info" else None},
            "seed": config.seed, "retained_feature_identifiers": None,
            "retained_features_evidence": "Model evaluation Artifact -> fitted preprocessing metadata after training.",
        },
        "dimensionality_reduction": {
            "enabled": pipeline.pca_components is not None,
            "method": "PCA" if pipeline.pca_components is not None else None,
            "component_count": pipeline.pca_components,
            "solver": "full" if pipeline.pca_components is not None else None,
            "whiten": pipeline.pca_whiten, "fitted_input_dimensions": None,
            "explained_variance": None,
            "output_dimensionality": pipeline.pca_components,
            "fitted_evidence": "Model evaluation Artifact -> fitted preprocessing metadata after training.",
            "angle_scaling": pipeline.angle_scaling,
            "angle_range": [0.0, 3.141592653589793] if pipeline.angle_scaling else None,
        },
        "models": [_model_configuration(kind, config) for kind in config.models],
        "threshold_protocol": {
            "selection_method": config.threshold_strategy,
            "target_sensitivity": config.target_sensitivity if config.threshold_strategy == "target_sensitivity" else None,
            "configured_fixed_threshold": config.probability_threshold,
            "calibration_status": config.calibration,
            "actual_decision_threshold": config.probability_threshold if config.threshold_strategy == "fixed" else None,
            "actual_threshold_evidence": "Model evaluation Artifact -> operating_point; unknown until OOF fitting completes." if config.threshold_strategy != "fixed" else "Validated fixed configuration.",
            "selected_from_out_of_fold_data": config.threshold_strategy == "target_sensitivity",
            "untouched_holdout_not_used_for_selection": True,
            "infeasible_policy": "configured fixed fallback after explicitly infeasible OOF validation",
        },
        "evaluation_protocol": {
            "evaluated_metrics": list(METRIC_NAMES) + ["confusion_matrix"],
            "positive_class": provenance["positive_label"], "primary_metric": None,
            "secondary_metrics": list(METRIC_NAMES),
            "held_out_evaluation": "one untouched stratified test partition evaluated after final training",
            "cross_validation_evaluation": "out-of-fold metrics on training partition with fresh fold-local pipelines",
            "confusion_matrix_convention": "[[true_negative,false_positive],[false_negative,true_positive]] for configured positive class",
            "timing_categories": ["cv_total_seconds", "cv_fold_seconds", "final_training_seconds", "test_inference_seconds"],
            "evaluation_sample_count": split["test_count"],
        },
        "software_environment": {
            "application_version": __version__,
            "packages": packages,
        },
        "runtime_environment": {
            "operating_system": platform.system(),
            "platform": platform.platform(),
            "machine_architecture": platform.machine(),
            "python_architecture": platform.architecture()[0],
            "logical_cpu_count": os.cpu_count(),
            "worker_mode": "single_process_thread_pool", "worker_count": 1,
            "simulator_runtime": {
                "qiskit_backend": config.quantum.backend if {"vqc", "qsvc", "qnn"}.intersection(config.models) else None,
                "pennylane_backend": config.hybrid.backend if "hybrid_pennylane_torch" in config.models else None,
                "real_hardware": False,
            },
        },
        "execution_at_lock": {
            "job_id": job_id, "state_at_lock": "created",
            "run_created_at": run.created_at.isoformat(),
            "manifest_locked_at": locked_at.isoformat(),
            "started_at": None, "completed_at": None,
            "volatile_execution_metadata_location": "Run lifecycle timestamps/result_summary/failure and associated Job state.",
        },
        "reproducibility": {
            "status": REPRODUCIBLE, "bitwise_reproducible": False,
            "evidence": [
                "dataset SHA-256 and safe schema fingerprint",
                "sample/split/fold fingerprints and deterministic seeds",
                "validated resolved pipeline/model/threshold/evaluation configuration",
                "software and safe runtime metadata",
            ],
            "limitations": [
                "Configurationally reproducible does not claim bit-for-bit cross-platform determinism.",
                "Fitted parameters and post-fit operating points remain in integrity-registered model/evaluation artifacts.",
                "No clinical reproducibility or external validation is claimed.",
            ],
        },
    }
    payload["identity"]["configuration_fingerprint"] = configuration_fingerprint(payload)
    payload["identity"]["manifest_hash"] = _manifest_hash(payload)
    return RunManifest.model_validate(payload).model_dump(mode="json")


def create_locked_manifest(session, *, run: Run, experiment: Experiment, data: PreparedData, config: TrainingConfig, job_id: str) -> Artifact:
    existing = session.scalar(select(Artifact).where(Artifact.operation_key == f"run-manifest:{run.id}"))
    if existing is not None:
        if run.manifest_artifact_id != existing.id:
            raise AppError("manifest_lineage_conflict", "The Run manifest relationship is inconsistent.", 409)
        return existing
    if run.status != "created" or run.manifest_locked_at is not None:
        raise AppError("manifest_lock_invalid", "A manifest can be created only before scientific execution begins.", 409)
    resolved_version_id = data.dataset_version.id if data.dataset_version else None
    if run.dataset_version_id is None:
        run.dataset_version_id = resolved_version_id
    elif run.dataset_version_id != resolved_version_id:
        raise AppError(
            "dataset_version_mismatch",
            "The Run and resolved training data must use the same Dataset Version.",
            409,
        )
    locked_at = utcnow()
    manifest_id = str(uuid4())
    payload = build_manifest(
        run=run, experiment=experiment, data=data, config=config,
        job_id=job_id, locked_at=locked_at, manifest_id=manifest_id,
    )
    artifact = Artifact(
        id=str(uuid4()), experiment_id=experiment.id, run_id=run.id, model_id=None,
        artifact_type="experiment_manifest", name="Immutable Run provenance manifest",
        description="Canonical scientific configuration and provenance locked before execution.",
        storage_reference=None, integrity_hash=payload["identity"]["manifest_hash"],
        hash_algorithm="sha256", size_bytes=len(canonical_json_bytes(payload)),
        content_type="application/json", details=payload, immutable=True,
        operation_key=f"run-manifest:{run.id}",
    )
    session.add(artifact)
    session.flush()
    run.manifest_artifact_id = artifact.id
    run.configuration_fingerprint = payload["identity"]["configuration_fingerprint"]
    run.reproducibility_status = payload["reproducibility"]["status"]
    run.manifest_locked_at = locked_at
    session.flush()
    return artifact


def validate_manifest_consistency(run: Run, artifact: Artifact, payload: dict) -> list[str]:
    errors: list[str] = []
    try:
        manifest = RunManifest.model_validate(payload)
    except Exception:
        return ["manifest_schema_invalid"]
    if manifest.identity.run_id != run.id:
        errors.append("run_id_mismatch")
    if manifest.identity.experiment_id != run.experiment_id or artifact.experiment_id != run.experiment_id:
        errors.append("experiment_id_mismatch")
    if manifest.dataset.dataset_id != run.dataset_id:
        errors.append("dataset_id_mismatch")
    if artifact.run_id != run.id or run.manifest_artifact_id != artifact.id:
        errors.append("manifest_lineage_mismatch")
    if artifact.artifact_type != "experiment_manifest" or not artifact.immutable:
        errors.append("manifest_artifact_contract_invalid")
    if configuration_fingerprint(payload) != manifest.identity.configuration_fingerprint:
        errors.append("configuration_fingerprint_mismatch")
    with session_scope() as session:
        dataset = require(session, Dataset, run.dataset_id)
        version = session.get(DatasetVersion, run.dataset_version_id) if run.dataset_version_id else None
    if manifest.dataset.dataset_version_id != run.dataset_version_id:
        errors.append("dataset_version_id_mismatch")
    expected_hash = version.content_sha256 if version else dataset.sha256
    if expected_hash != manifest.dataset.sha256:
        errors.append("dataset_hash_mismatch")
    if version and version.schema_fingerprint != manifest.dataset.schema_fingerprint:
        errors.append("dataset_schema_fingerprint_mismatch")
    qiskit_models = {"vqc", "qsvc", "qnn"}
    for model in manifest.models:
        if model.model_identifier in qiskit_models and (model.quantum is None or model.quantum.framework != "Qiskit"):
            errors.append("quantum_configuration_mismatch")
        if model.model_identifier == "hybrid_pennylane_torch" and (model.quantum is None or model.quantum.framework != "PennyLane"):
            errors.append("quantum_configuration_mismatch")
        if model.model_identifier not in qiskit_models | {"hybrid_pennylane_torch"} and model.quantum is not None:
            errors.append("quantum_configuration_mismatch")
    return sorted(set(errors))


def verify_manifest_integrity(run_id: str) -> ManifestIntegrityResult:
    with session_scope() as session:
        run = require(session, Run, run_id)
        if not run.manifest_artifact_id:
            return ManifestIntegrityResult(
                valid=False, run_id=run.id, artifact_id=None, manifest_hash=None,
                configuration_fingerprint=run.configuration_fingerprint,
                errors=["manifest_unavailable"],
            )
        artifact = require(session, Artifact, run.manifest_artifact_id)
        payload = deepcopy(artifact.details)
    errors = validate_manifest_consistency(run, artifact, payload)
    computed = _manifest_hash(payload) if isinstance(payload, dict) and "identity" in payload else None
    stored = payload.get("identity", {}).get("manifest_hash") if isinstance(payload, dict) else None
    if computed != stored or computed != artifact.integrity_hash:
        errors.append("manifest_hash_mismatch")
    return ManifestIntegrityResult(
        valid=not errors, run_id=run.id, artifact_id=artifact.id,
        manifest_hash=stored, configuration_fingerprint=run.configuration_fingerprint,
        errors=sorted(set(errors)),
    )


def get_manifest(run_id: str) -> tuple[Run, Artifact, dict]:
    with session_scope() as session:
        run = require(session, Run, run_id)
        if not run.manifest_artifact_id:
            raise AppError("manifest_unavailable", "This legacy Run has no authoritative provenance manifest.", 404)
        artifact = require(session, Artifact, run.manifest_artifact_id)
        return run, artifact, RunManifest.model_validate(artifact.details).model_dump(mode="json")


def provenance_graph(run_id: str) -> dict:
    with session_scope() as session:
        run = require(session, Run, run_id)
        artifacts = list(session.scalars(select(Artifact).where(Artifact.run_id == run.id).order_by(Artifact.created_at)))
        models = list(session.scalars(select(ModelRecord).where(ModelRecord.run_id == run.id)))
        job = session.scalar(select(Job).where(Job.run_id == run.id))
    return {
        "run_id": run.id, "experiment_id": run.experiment_id, "dataset_id": run.dataset_id,
        "dataset_version_id": run.dataset_version_id,
        "manifest_artifact_id": run.manifest_artifact_id,
        "configuration_fingerprint": run.configuration_fingerprint,
        "reproducibility_status": run.reproducibility_status or INCOMPLETE,
        "job_id": job.id if job else None,
        "model_ids": [model.id for model in models],
        "artifacts": [
            {"artifact_id": item.id, "artifact_type": item.artifact_type, "model_id": item.model_id,
             "integrity_hash": item.integrity_hash, "immutable": item.immutable}
            for item in artifacts
        ],
        "legacy_limitations": [] if run.manifest_artifact_id else [
            "No manifest was recorded when this Run was created; missing provenance is not reconstructed."
        ],
    }