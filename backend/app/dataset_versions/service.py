from __future__ import annotations

import hashlib
from pathlib import Path
from threading import Lock
from uuid import uuid4

import pandas as pd
from sqlalchemy import func, select

from ..api.schemas import DatasetUploadMetadata
from ..config import get_settings
from ..database import session_scope
from ..storage.entities import Dataset, DatasetVersion, Run
from ..storage.files import atomic_bytes, sanitize_filename
from ..storage.repository import require
from ..utils.errors import AppError
from ..utils.serialization import fingerprint, utcnow

_version_lock = Lock()


def schema_descriptor(frame: pd.DataFrame, target: str, positive_label: str) -> dict:
    return {
        "columns": [
            {"name": str(name), "position": index, "dtype": str(frame[name].dtype)}
            for index, name in enumerate(frame.columns)
        ],
        "target": target,
        "positive_label": str(positive_label),
        "features": [str(name) for name in frame.columns if name != target],
    }


def schema_fingerprint(frame: pd.DataFrame, target: str, positive_label: str) -> str:
    return fingerprint(schema_descriptor(frame, target, positive_label))


def version_signature(content_sha256: str, schema_hash: str, target: str, positive_label: str, negative_label: str) -> str:
    return fingerprint({
        "content_sha256": content_sha256,
        "schema_fingerprint": schema_hash,
        "target": target,
        "positive_label": str(positive_label),
        "negative_label": str(negative_label),
    })


def _storage_path(reference: str) -> Path:
    root = get_settings().root.resolve()
    path = (root / reference).resolve()
    dataset_root = (root / "data" / "datasets").resolve()
    if path.parent != dataset_root or path.suffix != ".csv":
        raise AppError("storage_reference_invalid", "Dataset Version storage metadata is invalid.", 409)
    return path


def _summary_provenance(provenance: dict) -> dict:
    allowed = {
        "domain", "source", "source_url", "version", "license", "license_url",
        "attribution", "origin", "library_slug", "is_demo", "dataset_status",
        "target_type", "deidentification_asserted_by_uploader", "normalization",
        "recommended_duplicate_policy", "sampling_unit", "original_filename",
    }
    return {key: provenance.get(key) for key in allowed if key in provenance}


def _set_current(dataset: Dataset, version: DatasetVersion) -> None:
    dataset.current_version_id = version.id
    dataset.sha256 = version.content_sha256
    dataset.provenance = version.provenance
    dataset.quality = version.quality_summary


def _create_record(session, *, dataset: Dataset, frame: pd.DataFrame, content: bytes, storage_reference: str,
                   provenance: dict, quality: dict, created_at=None) -> tuple[DatasetVersion, bool]:
    provenance = dict(provenance)
    provenance.setdefault("original_filename", dataset.filename)
    sha = hashlib.sha256(content).hexdigest()
    target = provenance["target"]
    positive = str(provenance["positive_label"])
    classes = [str(item) for item in provenance.get("target_classes", quality.get("target_classes", []))]
    negative = str(provenance.get("negative_label") or next((item for item in classes if item != positive), ""))
    schema_hash = schema_fingerprint(frame, target, positive)
    signature = version_signature(sha, schema_hash, target, positive, negative)
    existing = session.scalar(select(DatasetVersion).where(
        DatasetVersion.dataset_id == dataset.id,
        DatasetVersion.version_signature == signature,
    ))
    if existing is not None:
        _set_current(dataset, existing)
        return existing, False
    next_number = int(session.scalar(select(func.coalesce(func.max(DatasetVersion.version_number), 0)).where(
        DatasetVersion.dataset_id == dataset.id
    )) or 0) + 1
    record = DatasetVersion(
        id=str(uuid4()), dataset_id=dataset.id, version_number=next_number,
        version_label=f"v{next_number}", content_sha256=sha,
        schema_fingerprint=schema_hash, version_signature=signature,
        row_count=len(frame), feature_count=max(0, len(frame.columns) - 1),
        target=target, positive_label=positive, negative_label=negative,
        target_type=provenance.get("target_type", "binary_classification"),
        class_distribution={str(k): int(v) for k, v in provenance.get("class_distribution", quality.get("class_distribution", {})).items()},
        source_metadata=_summary_provenance(provenance), provenance=provenance,
        quality_summary=quality, storage_reference=storage_reference,
        status="ready", immutable=True, created_at=created_at or utcnow(),
    )
    session.add(record)
    session.flush()
    dataset.current_version_id = record.id
    return record, True


def register_initial_version(session, *, dataset: Dataset, frame: pd.DataFrame, content: bytes,
                             storage_reference: str, provenance: dict, quality: dict) -> DatasetVersion:
    record, _ = _create_record(
        session, dataset=dataset, frame=frame, content=content,
        storage_reference=storage_reference, provenance=provenance, quality=quality,
        created_at=dataset.created_at,
    )
    return record


def ensure_legacy_versions() -> None:
    """Backfill only verifiable historical snapshots; unverifiable rows remain legacy."""
    from ..data.service import parse_csv
    with _version_lock:
        with session_scope() as session:
            datasets = list(session.scalars(select(Dataset).where(Dataset.current_version_id.is_(None))))
            for dataset in datasets:
                reference = f"data/datasets/{dataset.id}.csv"
                path = _storage_path(reference)
                if not path.is_file():
                    continue
                content = path.read_bytes()
                if hashlib.sha256(content).hexdigest() != dataset.sha256:
                    continue
                try:
                    frame = parse_csv(content, dataset.provenance["target"], dataset.provenance["positive_label"])
                    register_initial_version(
                        session, dataset=dataset, frame=frame, content=content,
                        storage_reference=reference, provenance=dataset.provenance, quality=dataset.quality,
                    )
                except (KeyError, AppError, ValueError):
                    continue


def create_version(dataset_id: str, content: bytes, filename: str, metadata: DatasetUploadMetadata) -> tuple[DatasetVersion, bool]:
    from ..data.service import parse_csv
    from ..data.quality import quality_report
    from ..data.target_detection import detect_target
    if not filename.lower().endswith(".csv"):
        raise AppError("extension_not_allowed", "Only UTF-8 .csv uploads are accepted.")
    frame = parse_csv(content, metadata.target, metadata.positive_label)
    quality = quality_report(frame, metadata.target, metadata.positive_label)
    detection = detect_target(frame, metadata.target, metadata.positive_label)
    with _version_lock:
        with session_scope() as session:
            dataset = require(session, Dataset, dataset_id)
            if metadata.name != dataset.name:
                raise AppError("dataset_identity_mismatch", "A new version must retain the logical Dataset name.", 409)
            sha = hashlib.sha256(content).hexdigest()
            provenance = {
                **metadata.model_dump(exclude={"deidentified"}),
                "task": "binary_classification", "dataset_hash": sha,
                "hash_algorithm": "sha256", "hash_scope": "exact stored CSV bytes",
                "uploaded_at": utcnow().isoformat(), "row_count": len(frame),
                "feature_count": len(frame.columns) - 1,
                "features": [str(c) for c in frame if c != metadata.target],
                "numeric_features": quality["numeric_features"], "categorical_features": quality["categorical_features"],
                "target_classes": quality["target_classes"], "class_distribution": quality["class_distribution"],
                "negative_label": next(str(c) for c in quality["target_classes"] if str(c) != metadata.positive_label),
                "license": None, "is_demo": False, "deidentification_asserted_by_uploader": True,
                "origin": "uploaded", "dataset_status": "registered",
                "target_type": "binary_classification", "target_detection": detection,
                "preprocessing_configuration": "Stored per experiment; source dataset version is immutable.",
                "original_filename": sanitize_filename(filename),
            }
            schema_hash = schema_fingerprint(frame, metadata.target, metadata.positive_label)
            negative = provenance["negative_label"]
            signature = version_signature(sha, schema_hash, metadata.target, metadata.positive_label, negative)
            existing = session.scalar(select(DatasetVersion).where(
                DatasetVersion.dataset_id == dataset.id, DatasetVersion.version_signature == signature
            ))
            if existing is not None:
                _set_current(dataset, existing)
                return existing, False
            content_match = session.scalar(select(DatasetVersion).where(
                DatasetVersion.dataset_id == dataset.id,
                DatasetVersion.content_sha256 == sha,
            ).order_by(DatasetVersion.version_number))
            identity = str(uuid4())
            reference = content_match.storage_reference if content_match else f"data/datasets/{identity}.csv"
            path = _storage_path(reference)
            storage_created = content_match is None
            if storage_created:
                atomic_bytes(path, content)
            try:
                record, created = _create_record(
                    session, dataset=dataset, frame=frame, content=content,
                    storage_reference=reference, provenance=provenance, quality=quality,
                )
                dataset.filename = filename
                dataset.sha256 = sha
                dataset.provenance = provenance
                dataset.quality = quality
                return record, created
            except Exception:
                if storage_created:
                    path.unlink(missing_ok=True)
                raise


def list_versions(dataset_id: str) -> list[DatasetVersion]:
    with session_scope() as session:
        require(session, Dataset, dataset_id)
        return list(session.scalars(select(DatasetVersion).where(
            DatasetVersion.dataset_id == dataset_id
        ).order_by(DatasetVersion.version_number.desc())))


def get_version(dataset_id: str, version_id: str) -> DatasetVersion:
    with session_scope() as session:
        version = require(session, DatasetVersion, version_id)
        if version.dataset_id != dataset_id:
            raise AppError("dataset_version_mismatch", "Dataset Version does not belong to this Dataset.", 404)
        return version


def resolve_version(session, dataset: Dataset, *, version_id: str | None = None, expected_hash: str | None = None) -> DatasetVersion | None:
    if version_id:
        version = require(session, DatasetVersion, version_id)
        if version.dataset_id != dataset.id:
            raise AppError("dataset_version_mismatch", "Dataset Version does not belong to this Dataset.", 409)
        return version
    if expected_hash:
        version = session.scalar(select(DatasetVersion).where(
            DatasetVersion.dataset_id == dataset.id, DatasetVersion.content_sha256 == expected_hash
        ).order_by(DatasetVersion.version_number.desc()))
        if version is not None:
            return version
    return session.get(DatasetVersion, dataset.current_version_id) if dataset.current_version_id else None


def read_version_bytes(version: DatasetVersion) -> bytes:
    path = _storage_path(version.storage_reference)
    if not path.is_file():
        raise AppError("integrity_error", "Stored Dataset Version is missing.", 409)
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != version.content_sha256:
        raise AppError("integrity_error", "Stored Dataset Version integrity has changed.", 409)
    return content


def verify_version(dataset_id: str, version_id: str) -> dict:
    version = get_version(dataset_id, version_id)
    actual = None
    errors = []
    try:
        path = _storage_path(version.storage_reference)
        if not path.is_file():
            errors.append("dataset_version_file_missing")
        else:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != version.content_sha256:
                errors.append("dataset_version_hash_mismatch")
    except (OSError, AppError):
        errors.append("dataset_version_storage_unavailable")
    return {"valid": not errors, "dataset_id": dataset_id, "dataset_version_id": version_id,
            "expected_sha256": version.content_sha256, "actual_sha256": actual, "errors": errors}


def dataset_card(dataset_id: str, version_id: str) -> dict:
    version = get_version(dataset_id, version_id)
    with session_scope() as session:
        dataset = require(session, Dataset, dataset_id)
    q = version.quality_summary or {}
    p = version.provenance or {}
    known_limitations = list(q.get("warnings", []))
    if not p.get("source_url"):
        known_limitations.append("No source URL was recorded for this version.")
    known_limitations.extend([
        "This card documents a research dataset snapshot; it is not clinical validation.",
        "Population representativeness and external validity are not established unless explicitly documented by the source.",
    ])
    return {
        "identity": {"dataset_id": dataset.id, "dataset_name": dataset.name, "dataset_version_id": version.id,
                     "version": version.version_label, "domain": p.get("domain", "biomedical"),
                     "task_type": version.target_type, "source": p.get("source", "unspecified"),
                     "source_reference": p.get("source_url")},
        "data": {"rows": version.row_count, "features": version.feature_count,
                 "feature_types": {"numeric": len(p.get("numeric_features", [])), "categorical": len(p.get("categorical_features", []))},
                 "target": version.target, "positive_class": version.positive_label,
                 "negative_class": version.negative_label, "class_distribution": version.class_distribution},
        "quality": {"missingness_summary": q.get("missingness", q.get("missing_values", {})),
                    "duplicate_summary": {
                        "exact_rows": q.get("duplicate_rows", 0),
                        "feature_rows": q.get("duplicate_feature_rows", 0),
                    },
                    "constant_features": q.get("constant_features", []),
                    "identifier_or_proxy_indicators": {
                        "identifier_features": q.get("identifier_features", []),
                        "suspiciously_predictive_features": q.get("suspiciously_predictive_features", []),
                    },
                    "validation_status": version.status},
        "provenance": {"source": p.get("source"), "source_version": p.get("version"),
                       "content_sha256": version.content_sha256, "schema_fingerprint": version.schema_fingerprint,
                       "registered_at": version.created_at.isoformat(), "origin": p.get("origin", "uploaded")},
        "limitations": list(dict.fromkeys(known_limitations)),
        "usage": {"supported_task": "binary_classification", "public_demo_samples_allowed": bool(p.get("is_demo")),
                  "private_upload_restrictions_apply": p.get("origin") != "built_in"},
    }


def compare_versions(dataset_id: str, left_id: str, right_id: str) -> dict:
    left, right = get_version(dataset_id, left_id), get_version(dataset_id, right_id)
    if left.content_sha256 == right.content_sha256:
        classification = "IDENTICAL_CONTENT"
    elif left.schema_fingerprint == right.schema_fingerprint:
        classification = "SAME_SCHEMA_DIFFERENT_DATA"
    else:
        classification = "SCHEMA_CHANGED"
    def summary(item):
        return {"dataset_version_id": item.id, "version": item.version_label, "content_sha256": item.content_sha256,
                "schema_fingerprint": item.schema_fingerprint, "row_count": item.row_count,
                "feature_count": item.feature_count, "target": item.target,
                "class_distribution": item.class_distribution, "source_metadata": item.source_metadata}
    return {"classification": classification, "left": summary(left), "right": summary(right),
            "differences": {"content_changed": left.content_sha256 != right.content_sha256,
                            "schema_changed": left.schema_fingerprint != right.schema_fingerprint,
                            "target_changed": (left.target, left.positive_label, left.negative_label) != (right.target, right.positive_label, right.negative_label),
                            "row_count_delta": right.row_count - left.row_count,
                            "feature_count_delta": right.feature_count - left.feature_count,
                            "class_distribution_changed": left.class_distribution != right.class_distribution}}


def assert_version_not_referenced(version_id: str) -> None:
    with session_scope() as session:
        if session.scalar(select(Run.id).where(Run.dataset_version_id == version_id).limit(1)):
            raise AppError("dataset_version_in_use", "This Dataset Version is referenced by a Run and is retained for reproducibility.", 409)
