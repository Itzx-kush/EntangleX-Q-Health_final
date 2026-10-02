import hashlib
from time import perf_counter
from uuid import uuid4
import numpy as np
import pandas as pd
from sqlalchemy import select

from ..artifacts.service import register_metadata
from ..data.service import load_versioned_frame
from ..dataset_versions.service import resolve_version
from ..demo_readiness import verify_installed_model
from ..evaluation.metrics import classification_metrics, score_outputs
from ..evaluation.thresholds import predictions_at_threshold
from ..models.prediction import get_bundle
from ..storage.entities import Dataset, ExternalValidation, ModelRecord, StudyRun
from ..storage.files import load_model, safe_path
from ..utils.errors import AppError
from ..utils.serialization import clean_json, software_versions, utcnow
from .constants import EVALUATED_METRIC_NAMES, SIGN_CONVENTION, VALIDATION_LIMITATIONS


def make_validation_operation_key(
    model_id: str,
    external_dataset_id: str,
    external_version_id: str | None,
    idempotency_key: str | None = None,
) -> str:
    if idempotency_key:
        return f"idemp:{idempotency_key}"
    parts = [model_id, external_dataset_id, external_version_id or "none"]
    return f"val:{hashlib.sha256(':'.join(parts).encode()).hexdigest()[:32]}"


def resolve_preflight(
    session,
    *,
    model_id: str,
    external_dataset_id: str,
    external_dataset_version_id: str | None = None,
    label_mapping: dict[str, str] | None = None,
) -> dict:
    """Perform comprehensive 16-step preflight compatibility checks before validation."""
    model = session.scalar(select(ModelRecord).where(ModelRecord.id == model_id))
    if model is None:
        raise AppError("model_not_found", f"Model {model_id} does not exist.", 404)

    if model.status != "ready" or not model.artifact_sha256:
        raise AppError("model_not_ready", f"Model {model_id} is in status '{model.status}' and cannot be validated.", 409)

    artifact_path = safe_path("models", model_id, ".dill")
    if not artifact_path.is_file():
        raise AppError("model_artifact_missing", "Model artifact file is missing from disk.", 409)

    try:
        verify_installed_model(model)
        bundle = load_model(model_id, model.artifact_sha256)
    except AppError:
        raise
    except Exception as exc:
        raise AppError("integrity_error", "Model artifact is corrupted or failed integrity verification.", 409) from exc

    train_dataset = session.scalar(select(Dataset).where(Dataset.id == model.dataset_id))
    if train_dataset is None:
        raise AppError("dataset_not_found", f"Training dataset {model.dataset_id} not found.", 404)
    train_version_id = bundle.get("dataset_version_id")
    train_dataset_hash = bundle.get("dataset_hash", train_dataset.sha256)

    ext_dataset = session.scalar(select(Dataset).where(Dataset.id == external_dataset_id))
    if ext_dataset is None:
        raise AppError("dataset_not_found", f"External dataset {external_dataset_id} does not exist.", 404)

    ext_version = resolve_version(session, ext_dataset, version_id=external_dataset_version_id)
    if external_dataset_version_id is not None and ext_version is None:
        raise AppError("dataset_version_not_found", f"External dataset version {external_dataset_version_id} not found.", 404)

    ext_dataset_hash = ext_version.content_sha256 if ext_version else ext_dataset.sha256

    # Distinctness and Independence checks
    if external_dataset_id == model.dataset_id:
        if ext_version is None and train_version_id is None:
            raise AppError("same_dataset_version", "Cannot validate a model against the exact same training dataset.", 409)
        if ext_version is not None and train_version_id is not None and ext_version.id == train_version_id:
            raise AppError("same_dataset_version", "Cannot validate a model against the exact same training dataset version.", 409)

    if ext_dataset_hash == train_dataset_hash:
        raise AppError(
            "same_dataset_content_hash",
            "External dataset has identical content hash to the training dataset. External validation requires an independent dataset.",
            409,
        )

    content_hash_distinct = bool(ext_dataset_hash != train_dataset_hash)
    dataset_identity_distinct = bool(external_dataset_id != model.dataset_id)
    version_distinct = bool(ext_version.id != train_version_id) if (ext_version and train_version_id) else dataset_identity_distinct
    declared_source = ext_dataset.provenance.get("source") if ext_dataset.provenance else None
    train_source = train_dataset.provenance.get("source") if train_dataset.provenance else None

    if not content_hash_distinct or (not dataset_identity_distinct and not version_distinct):
        independence_status = "not_external"
    elif declared_source and declared_source != train_source:
        independence_status = "declared_external"
    else:
        independence_status = "uncertain"

    # Load external tabular frame
    ext_record, ext_ver, ext_frame = load_versioned_frame(
        external_dataset_id,
        ext_version.id if ext_version else None,
        ext_dataset_hash,
    )

    block_reasons: list[str] = []
    warnings: list[str] = []

    model_features = list(bundle.get("features", []))
    numeric_features = set(bundle.get("numeric", []))
    ext_target = ext_ver.target if ext_ver else ext_dataset.provenance.get("target")

    if not ext_target or ext_target not in ext_frame.columns:
        block_reasons.append(f"Target column '{ext_target}' not found in external dataset.")

    if ext_target and ext_target in model_features:
        block_reasons.append(f"Target column '{ext_target}' cannot be included in model input features.")

    observed_classes: list[str] = []
    if ext_target and ext_target in ext_frame.columns:
        target_series = ext_frame[ext_target].dropna()
        observed_classes = [str(c) for c in sorted(target_series.unique().tolist(), key=str)]
        if len(observed_classes) != 2:
            block_reasons.append(
                f"External validation requires a binary target with exactly 2 observed classes; found {len(observed_classes)}: {observed_classes[:5]}."
            )

    present_features = [f for f in model_features if f in ext_frame.columns]
    missing_features = [f for f in model_features if f not in ext_frame.columns]
    extra_features = [c for c in ext_frame.columns if c not in model_features and c != ext_target]

    if missing_features:
        block_reasons.append(f"External dataset is missing {len(missing_features)} required model features: {missing_features[:10]}.")

    type_mismatches: list[dict] = []
    for f in present_features:
        if f in numeric_features:
            s = pd.to_numeric(ext_frame[f], errors="coerce")
            nan_orig = ext_frame[f].isna().sum()
            nan_parsed = s.isna().sum()
            if nan_parsed > nan_orig:
                type_mismatches.append({"feature": f, "reason": "Non-numeric values found in expected numeric feature."})
            elif np.isinf(s.dropna().to_numpy()).any():
                type_mismatches.append({"feature": f, "reason": "Infinite values found in numeric feature."})

    if type_mismatches:
        block_reasons.append(f"External dataset has {len(type_mismatches)} feature type mismatches: {[t['feature'] for t in type_mismatches[:5]]}.")

    feature_compat = {
        "compatible": len(missing_features) == 0 and len(type_mismatches) == 0,
        "required_features": model_features,
        "present_features": present_features,
        "missing_features": missing_features,
        "extra_features": extra_features,
        "type_mismatches": type_mismatches,
    }

    if extra_features:
        warnings.append(f"External dataset contains {len(extra_features)} extra features that will be ignored safely.")

    # Label compatibility
    model_pos = str(bundle.get("positive_label", "1"))
    model_neg = str(bundle.get("negative_label", "0"))
    ext_pos = str(ext_ver.positive_label if ext_ver else ext_dataset.provenance.get("positive_label", ""))
    ext_neg = str(ext_ver.negative_label if ext_ver else ext_dataset.provenance.get("negative_label", ""))

    label_compat_reasons: list[str] = []
    mapping_strategy = "unknown"
    mapped_positive = None
    mapped_negative = None

    if len(observed_classes) == 2:
        if label_mapping:
            user_pos = label_mapping.get("positive")
            user_neg = label_mapping.get("negative")
            if user_pos and user_neg and set([str(user_pos), str(user_neg)]) == set(observed_classes):
                mapped_positive = str(user_pos)
                mapped_negative = str(user_neg)
                mapping_strategy = "explicit_user_mapping"
            else:
                label_compat_reasons.append(f"User label mapping {label_mapping} does not match observed classes {observed_classes}.")
        elif set(observed_classes) == {model_pos, model_neg}:
            mapped_positive = model_pos
            mapped_negative = model_neg
            mapping_strategy = "exact_literal_match"
        elif ext_pos in observed_classes:
            mapped_positive = ext_pos
            mapped_negative = [c for c in observed_classes if c != ext_pos][0]
            mapping_strategy = "declared_dataset_metadata_mapping"
        else:
            label_compat_reasons.append(
                f"Observed classes {observed_classes} do not match model labels ({model_pos}, {model_neg}) or external declared positive label '{ext_pos}'."
            )

    if label_compat_reasons:
        block_reasons.extend(label_compat_reasons)

    label_compat = {
        "compatible": len(label_compat_reasons) == 0 and mapped_positive is not None,
        "model_positive_label": model_pos,
        "model_negative_label": model_neg,
        "external_target": ext_target or "unknown",
        "external_positive_label": ext_pos or None,
        "external_negative_label": ext_neg or None,
        "observed_classes": observed_classes,
        "mapping_strategy": mapping_strategy,
        "mapped_positive_value": mapped_positive,
        "mapped_negative_value": mapped_negative,
        "reasons": label_compat_reasons,
    }

    operating_threshold = float(bundle.get("operating_threshold", 0.5))
    threshold_source = bundle.get("threshold_source", "locked_internal_operating_point")
    threshold_units = bundle.get("threshold_units", "positive_class_probability")

    threshold_lock = {
        "threshold_used": operating_threshold,
        "threshold_source": threshold_source,
        "threshold_units": threshold_units,
        "external_threshold_tuning": False,
    }

    if len(ext_frame) < 30:
        warnings.append(f"External dataset sample count is small (N={len(ext_frame)}); metric uncertainty will be high.")

    ready = bool(len(block_reasons) == 0 and feature_compat["compatible"] and label_compat["compatible"])

    return {
        "ready": ready,
        "model": model,
        "bundle": bundle,
        "training_dataset": {
            "id": train_dataset.id,
            "name": train_dataset.name,
            "version_id": train_version_id,
            "content_sha256": train_dataset_hash,
        },
        "external_dataset": {
            "id": ext_dataset.id,
            "name": ext_dataset.name,
            "version_id": ext_version.id if ext_version else None,
            "content_sha256": ext_dataset_hash,
        },
        "external_frame": ext_frame,
        "feature_compatibility": feature_compat,
        "label_compatibility": label_compat,
        "threshold_lock": threshold_lock,
        "artifact_integrity": {
            "verified": True,
            "model_artifact_sha256": model.artifact_sha256,
            "model_status": model.status,
        },
        "independence": {
            "content_hash_distinct": content_hash_distinct,
            "dataset_identity_distinct": dataset_identity_distinct,
            "version_distinct": version_distinct,
            "declared_source": declared_source,
            "independence_status": independence_status,
        },
        "warnings": warnings,
        "block_reasons": block_reasons,
    }


def execute_validation(
    session,
    *,
    model_id: str,
    external_dataset_id: str,
    external_dataset_version_id: str | None = None,
    label_mapping: dict[str, str] | None = None,
    idempotency_key: str | None = None,
    notes: str | None = None,
) -> ExternalValidation:
    """Execute external validation on an explicitly locked model against an external dataset."""
    operation_key = make_validation_operation_key(
        model_id=model_id,
        external_dataset_id=external_dataset_id,
        external_version_id=external_dataset_version_id,
        idempotency_key=idempotency_key,
    )

    existing = session.scalar(select(ExternalValidation).where(ExternalValidation.operation_key == operation_key))
    if existing is not None:
        if idempotency_key:
            if existing.model_id != model_id or existing.external_dataset_id != external_dataset_id:
                raise AppError("idempotency_conflict", "Idempotency key was previously used with different parameters.", 409)
        return existing

    preflight = resolve_preflight(
        session,
        model_id=model_id,
        external_dataset_id=external_dataset_id,
        external_dataset_version_id=external_dataset_version_id,
        label_mapping=label_mapping,
    )

    model = preflight["model"]
    bundle = preflight["bundle"]
    ext_frame = preflight["external_frame"]

    # Check for blocking conditions
    if not preflight["ready"]:
        block_reasons = preflight["block_reasons"]
        if preflight["feature_compatibility"]["missing_features"]:
            raise AppError("missing_required_features", f"Validation blocked: {'; '.join(block_reasons)}", 422)
        if len(preflight["label_compatibility"]["observed_classes"]) != 2:
            raise AppError("non_binary_target", f"Validation blocked: {'; '.join(block_reasons)}", 422)
        raise AppError("schema_incompatible", f"Validation blocked: {'; '.join(block_reasons)}", 422)

    # Multi-seed study linking if model was generated in a study run
    study_id = None
    study_seed = None
    if model.run_id:
        study_run = session.scalar(select(StudyRun).where(StudyRun.run_id == model.run_id))
        if study_run:
            study_id = study_run.study_id
            study_seed = study_run.seed

    val_id = str(uuid4())
    val_record = ExternalValidation(
        id=val_id,
        model_id=model_id,
        run_id=model.run_id,
        experiment_id=model.experiment_id,
        training_dataset_id=preflight["training_dataset"]["id"],
        training_dataset_version_id=preflight["training_dataset"]["version_id"],
        external_dataset_id=external_dataset_id,
        external_dataset_version_id=preflight["external_dataset"]["version_id"],
        study_id=study_id,
        study_seed=study_seed,
        status="validating",
        operation_key=operation_key,
        compatibility=preflight["feature_compatibility"],
        label_mapping=preflight["label_compatibility"],
        threshold_metadata=preflight["threshold_lock"],
        limitations=VALIDATION_LIMITATIONS,
        warnings=preflight["warnings"],
    )
    session.add(val_record)
    session.flush()

    try:
        # Prepare evaluation frame (strictly reusing model features without refitting anything)
        features = bundle["features"]
        numeric = bundle["numeric"]
        X_df = ext_frame[features].copy()

        for col in features:
            if col in numeric:
                X_df[col] = pd.to_numeric(X_df[col], errors="coerce").astype(float)
            else:
                X_df[col] = X_df[col].map(lambda v: str(v) if v is not None and pd.notna(v) else np.nan).astype(object)

        ext_target = preflight["label_compatibility"]["external_target"]
        mapped_pos = preflight["label_compatibility"]["mapped_positive_value"]
        y_true = np.where(ext_frame[ext_target].astype(str).str.strip() == mapped_pos, 1, 0)

        estimator = bundle["estimator"]
        threshold = preflight["threshold_lock"]["threshold_used"]

        # Run inference (estimator is locked; NOT refit!)
        start_t = perf_counter()
        _, scores, probabilities = score_outputs(estimator, X_df, threshold)
        predicted = predictions_at_threshold(scores, threshold)
        infer_time = perf_counter() - start_t

        metrics = classification_metrics(y_true, predicted, scores)
        pos_support = int(np.sum(y_true == 1))
        neg_support = int(np.sum(y_true == 0))
        metrics["positive_support"] = pos_support
        metrics["negative_support"] = neg_support
        metrics["inference_seconds"] = infer_time
        metrics["inference_seconds_per_sample"] = infer_time / len(X_df) if len(X_df) else 0.0

        warnings = list(preflight["warnings"])
        if pos_support < 10:
            warnings.append(f"External positive class support is small ({pos_support} samples); sensitivity and positive predictive metrics have high statistical uncertainty.")
        if neg_support < 10:
            warnings.append(f"External negative class support is small ({neg_support} samples); specificity and negative predictive metrics have high statistical uncertainty.")

        # Comparison with model's internal held-out test evidence
        internal_test = model.metrics.get("test", {}) if model.metrics else {}
        comparison = {}
        generalization_gap = {}
        for m in EVALUATED_METRIC_NAMES:
            int_v = internal_test.get(m)
            ext_v = metrics.get(m)
            if int_v is not None and ext_v is not None:
                delta = float(ext_v - int_v)
                rel = float(delta / int_v) if int_v != 0 else None
                comparison[m] = {
                    "metric": m,
                    "internal_value": int_v,
                    "external_value": ext_v,
                    "delta": delta,
                    "relative_change": rel,
                    "interpretation": "Observed external-to-internal difference.",
                }
                generalization_gap[m] = delta
            else:
                generalization_gap[m] = None

        provenance = {
            "validation_id": val_id,
            "model_id": model_id,
            "model_type": model.model_type,
            "model_artifact_sha256": model.artifact_sha256,
            "training_dataset_id": preflight["training_dataset"]["id"],
            "training_dataset_version_id": preflight["training_dataset"]["version_id"],
            "training_dataset_hash": preflight["training_dataset"]["content_sha256"],
            "external_dataset_id": preflight["external_dataset"]["id"],
            "external_dataset_version_id": preflight["external_dataset"]["version_id"],
            "external_dataset_hash": preflight["external_dataset"]["content_sha256"],
            "independence": preflight["independence"],
            "threshold_lock": preflight["threshold_lock"],
            "label_mapping": preflight["label_compatibility"],
            "parent_study_id": study_id,
            "study_seed": study_seed,
            "sign_convention": SIGN_CONVENTION,
            "notes": notes,
            "protocol": "locked_model_external_validation_v1",
            "software_versions": software_versions(),
        }

        # Register immutable validation artifact
        artifact_payload = {
            "validation_id": val_id,
            "model_id": model_id,
            "model_type": model.model_type,
            "model_artifact_sha256": model.artifact_sha256,
            "training_dataset_hash": preflight["training_dataset"]["content_sha256"],
            "external_dataset_hash": preflight["external_dataset"]["content_sha256"],
            "metrics": metrics,
            "internal_metrics": internal_test,
            "comparison": comparison,
            "generalization_gap": generalization_gap,
            "sample_counts": {
                "total": len(X_df),
                "positive": pos_support,
                "negative": neg_support,
            },
            "sample_fingerprint": hashlib.sha256(X_df.to_csv(index=False).encode()).hexdigest(),
            "threshold_metadata": preflight["threshold_lock"],
            "provenance": provenance,
            "limitations": VALIDATION_LIMITATIONS,
            "warnings": warnings,
            "created_at": utcnow().isoformat(),
        }

        artifact = register_metadata(
            session,
            experiment_id=model.experiment_id,
            run_id=model.run_id,
            model_id=model.id,
            artifact_type="external_validation",
            name=f"External Validation {val_id[:8]}",
            description="Immutable external validation evaluation artifact and comparison evidence.",
            payload=artifact_payload,
            operation_key=f"extval_artifact:{val_id}",
        )

        val_record.status = "completed"
        val_record.metrics = metrics
        val_record.internal_metrics = internal_test
        val_record.comparison = comparison
        val_record.generalization_gap = generalization_gap
        val_record.provenance = provenance
        val_record.artifact_id = artifact.id
        val_record.warnings = warnings
        val_record.completed_at = utcnow()
        session.flush()
        return val_record

    except Exception as exc:
        val_record.status = "failed"
        val_record.failure = {
            "code": type(exc).__name__,
            "message": str(exc),
        }
        val_record.completed_at = utcnow()
        session.flush()
        raise


def get_validation(session, validation_id: str) -> ExternalValidation:
    val = session.scalar(select(ExternalValidation).where(ExternalValidation.id == validation_id))
    if val is None:
        raise AppError("validation_not_found", f"External validation {validation_id} does not exist.", 404)
    return val


def list_validations(
    session,
    *,
    limit: int = 100,
    offset: int = 0,
    model_id: str | None = None,
    status: str | None = None,
) -> list[ExternalValidation]:
    stmt = select(ExternalValidation).order_by(ExternalValidation.created_at.desc())
    if model_id:
        stmt = stmt.where(ExternalValidation.model_id == model_id)
    if status:
        stmt = stmt.where(ExternalValidation.status == status)
    stmt = stmt.offset(offset).limit(limit)
    return list(session.scalars(stmt).all())
