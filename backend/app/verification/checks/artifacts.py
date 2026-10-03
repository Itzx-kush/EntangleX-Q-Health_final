"""Artifact Registry verification (Prompt 28 / artifact integrity).

File-backed and metadata artifacts must be content-addressed, reference-resolving
and immutable.  Only tiny synthetic fixtures are used.
"""

from __future__ import annotations

import hashlib
from uuid import uuid4

from ..fixtures import persist_chain
from ..isolation import initialize_database, isolated_root, session
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check
from ._support import expect_app_error


@check(
    check_id="artifact_registry_contract",
    name="Artifact registry contract",
    category=CheckCategory.ARTIFACT_INTEGRITY,
    description="Content addressing, idempotency, conflicting-write rejection and reference resolution for registered artifacts.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=180.0,
)
def artifact_registry_contract() -> CheckResult:
    from app.artifacts.service import digest, register_file, register_metadata
    from app.storage.entities import Dataset, Experiment, ModelRecord, Run

    initialize_database()
    chain = persist_chain(with_pipeline=True, with_protocol=True)
    problems: list[str] = []

    payload_bytes = b"synthetic scientific ci artifact payload\n"
    path = isolated_root() / "artifacts" / "synthetic-fixture.bin"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload_bytes)
    expected_hash = hashlib.sha256(payload_bytes).hexdigest()
    operation_key = f"scientific-ci:file:{uuid4()}"

    with session() as scope:
        artifact = register_file(
            scope,
            experiment_id=chain.experiment_id,
            run_id=chain.run_id,
            model_id=chain.model_id,
            artifact_type="scientific_ci_fixture",
            name="Synthetic artifact file",
            description="Synthetic Scientific CI artifact.",
            path=path,
            storage_reference=str(path),
            content_type="application/octet-stream",
            operation_key=operation_key,
        )
        artifact_id = artifact.id
        if artifact.integrity_hash != expected_hash or digest(path) != expected_hash:
            problems.append("the file artifact integrity hash is not the SHA-256 of the stored bytes")
        if artifact.size_bytes != len(payload_bytes):
            problems.append("the file artifact size does not match the stored bytes")
        if not artifact.immutable:
            problems.append("the file artifact is not marked immutable")
        if scope.get(Experiment, artifact.experiment_id) is None:
            problems.append("the artifact experiment reference does not resolve")
        if scope.get(Run, artifact.run_id) is None or scope.get(ModelRecord, artifact.model_id) is None:
            problems.append("the artifact run or model reference does not resolve")

    with session() as scope:
        reused = register_file(
            scope,
            experiment_id=chain.experiment_id,
            run_id=chain.run_id,
            model_id=chain.model_id,
            artifact_type="scientific_ci_fixture",
            name="Synthetic artifact file",
            description="Synthetic Scientific CI artifact.",
            path=path,
            storage_reference=str(path),
            content_type="application/octet-stream",
            operation_key=operation_key,
        )
    if reused.id != artifact_id:
        problems.append("registering the identical immutable artifact twice created a second record")

    conflicting = path.with_name("synthetic-fixture-other.bin")
    conflicting.write_bytes(b"different synthetic payload\n")
    with expect_app_error("artifact_conflict"):
        with session() as scope:
            register_file(
                scope,
                experiment_id=chain.experiment_id,
                run_id=chain.run_id,
                model_id=chain.model_id,
                artifact_type="scientific_ci_fixture",
                name="Synthetic artifact file",
                description="Synthetic Scientific CI artifact.",
                path=conflicting,
                storage_reference=str(conflicting),
                content_type="application/octet-stream",
                operation_key=operation_key,
            )

    metadata_payload = {"kind": "synthetic", "rows": 3}
    from app.utils.serialization import fingerprint

    with session() as scope:
        metadata_artifact = register_metadata(
            scope,
            experiment_id=chain.experiment_id,
            artifact_type="scientific_ci_metadata_fixture",
            name="Synthetic metadata artifact",
            description="Synthetic Scientific CI metadata artifact.",
            payload=metadata_payload,
            operation_key=f"scientific-ci:metadata:{uuid4()}",
        )
        if metadata_artifact.integrity_hash != fingerprint(metadata_payload):
            problems.append("the metadata artifact integrity hash is not the canonical payload fingerprint")
        if scope.get(Dataset, chain.dataset_id) is None:
            problems.append("the synthetic dataset reference does not resolve")

    if problems:
        return CheckResult(
            check_id="artifact_registry_contract",
            category=CheckCategory.ARTIFACT_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="content-addressed, immutable, reference-resolving artifacts",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="artifact_registry_contract",
        category=CheckCategory.ARTIFACT_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Artifacts are content-addressed, idempotent, reference-resolving and reject conflicting writes.",
        evidence={
            "artifact_id": artifact_id,
            "integrity_hash": expected_hash,
            "hash_algorithm": "sha256",
            "immutable": True,
            "conflicting_write": "rejected",
        },
    )
