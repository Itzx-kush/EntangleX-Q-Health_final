from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from ..storage.entities import Artifact
from ..storage.files import digest
from ..utils.errors import AppError
from ..utils.serialization import fingerprint


def register_file(
    session,
    *,
    experiment_id: str,
    run_id: str | None,
    model_id: str | None,
    artifact_type: str,
    name: str,
    description: str,
    path: Path,
    storage_reference: str,
    content_type: str,
    operation_key: str,
    immutable: bool = True,
    details: dict | None = None,
) -> Artifact:
    if not path.is_file():
        raise AppError("artifact_missing", "The artifact file was not persisted.", 409)
    integrity_hash = digest(path)
    existing = session.scalar(select(Artifact).where(Artifact.operation_key == operation_key))
    if existing is not None:
        if existing.immutable:
            if existing.integrity_hash != integrity_hash or existing.storage_reference != storage_reference:
                raise AppError("artifact_conflict", "An immutable artifact operation produced different content.", 409)
            return existing
        existing.experiment_id = experiment_id
        existing.run_id = run_id
        existing.model_id = model_id
        existing.artifact_type = artifact_type
        existing.name = name
        existing.description = description
        existing.storage_reference = storage_reference
        existing.integrity_hash = integrity_hash
        existing.size_bytes = path.stat().st_size
        existing.content_type = content_type
        existing.details = details or {}
        return existing
    artifact = Artifact(
        id=str(uuid4()),
        experiment_id=experiment_id,
        run_id=run_id,
        model_id=model_id,
        artifact_type=artifact_type,
        name=name,
        description=description,
        storage_reference=storage_reference,
        integrity_hash=integrity_hash,
        hash_algorithm="sha256",
        size_bytes=path.stat().st_size,
        content_type=content_type,
        details=details or {},
        immutable=immutable,
        operation_key=operation_key,
    )
    session.add(artifact)
    session.flush()
    return artifact


def register_metadata(
    session,
    *,
    experiment_id: str,
    run_id: str | None,
    model_id: str | None,
    artifact_type: str,
    name: str,
    description: str,
    payload: dict,
    operation_key: str,
) -> Artifact:
    integrity_hash = fingerprint(payload)
    existing = session.scalar(select(Artifact).where(Artifact.operation_key == operation_key))
    if existing is not None:
        if existing.integrity_hash != integrity_hash:
            raise AppError("artifact_conflict", "An immutable metadata artifact operation produced different content.", 409)
        return existing
    artifact = Artifact(
        id=str(uuid4()),
        experiment_id=experiment_id,
        run_id=run_id,
        model_id=model_id,
        artifact_type=artifact_type,
        name=name,
        description=description,
        storage_reference=None,
        integrity_hash=integrity_hash,
        hash_algorithm="sha256",
        size_bytes=None,
        content_type="application/json",
        details=payload,
        immutable=True,
        operation_key=operation_key,
    )
    session.add(artifact)
    session.flush()
    return artifact