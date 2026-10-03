"""Research Evidence Package verification (Prompt 12).

Verifies that package identity derives from persisted evidence, that creation is
idempotent, that new evidence produces a new immutable snapshot, that package
status follows the underlying evidence, and that prohibited raw payloads never
appear in the package manifest.
"""

from __future__ import annotations

from uuid import uuid4

from ..fixtures import persist_chain
from ..isolation import initialize_database, session
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check
from ._support import flatten_strings, sensitive_keys_present


@check(
    check_id="evidence_package_contract",
    name="Research evidence package contract",
    category=CheckCategory.EVIDENCE_INTEGRITY,
    description="Package identity, idempotency, immutability, evidence-derived status and payload privacy.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=240.0,
)
def evidence_package_contract() -> CheckResult:
    from app.evidence_packages.service import PACKAGE_SCHEMA_VERSION, create_package, package_payload, preflight_package
    from app.storage.entities import Artifact, ResearchEvidencePackage, RobustnessRecord

    initialize_database()
    chain = persist_chain()
    problems: list[str] = []

    with session() as scope:
        preflight = preflight_package(scope, chain.experiment_id)
        first, created = create_package(scope, chain.experiment_id)
        first_id, first_fingerprint = first.id, first.package_fingerprint
        first_manifest = dict(first.manifest)
        first_payload = package_payload(scope, first)

    if not created:
        problems.append("the first package creation reported reuse")
    if preflight["package_status"] not in {"COMPLETE", "PARTIAL", "INCOMPLETE"}:
        problems.append(f"preflight reported an unknown package status: {preflight['package_status']}")

    with session() as scope:
        second, created_again = create_package(scope, chain.experiment_id)
        package_count = scope.query(ResearchEvidencePackage).filter(
            ResearchEvidencePackage.experiment_id == chain.experiment_id
        ).count()
        artifact_count = scope.query(Artifact).filter(
            Artifact.experiment_id == chain.experiment_id,
            Artifact.artifact_type == "research_evidence_package",
        ).count()
    if created_again or second.id != first_id or second.package_fingerprint != first_fingerprint:
        problems.append("an unchanged evidence state produced a different package identity")
    if package_count != 1 or artifact_count != 1:
        problems.append(f"package creation is not idempotent (packages={package_count}, artifacts={artifact_count})")

    with session() as scope:
        scope.add(
            RobustnessRecord(
                id=str(uuid4()),
                experiment_id=chain.experiment_id,
                model_id=chain.model_id,
                perturbation_type="missingness",
                perturbation_level=0.1,
                random_seed=19,
                result={"aggregate_accuracy": 0.75},
            )
        )
    with session() as scope:
        third, created_third = create_package(scope, chain.experiment_id)
        stored_first = scope.get(ResearchEvidencePackage, first_id)
        new_count = scope.query(ResearchEvidencePackage).filter(
            ResearchEvidencePackage.experiment_id == chain.experiment_id
        ).count()
    if not created_third or third.id == first_id:
        problems.append("new evidence did not produce a new package identity")
    if third.package_fingerprint == first_fingerprint:
        problems.append("changed evidence references did not change the package fingerprint")
    if stored_first.manifest != first_manifest:
        problems.append("an existing immutable package manifest was rewritten in place")
    if new_count != 2:
        problems.append(f"expected two immutable package snapshots, found {new_count}")

    sensitive = sensitive_keys_present(first_payload)
    if sensitive:
        problems.append(f"package payload exposes prohibited keys: {sensitive}")
    text = flatten_strings(first_payload).lower()
    for forbidden in ("patient_id", "raw_patient_rows", "csv_content", "api_key"):
        if forbidden in text:
            problems.append(f"package payload contains the prohibited term {forbidden!r}")

    if problems:
        return CheckResult(
            check_id="evidence_package_contract",
            category=CheckCategory.EVIDENCE_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="evidence-derived, idempotent, immutable and privacy-safe packages",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="evidence_package_contract",
        category=CheckCategory.EVIDENCE_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Evidence packages are evidence-derived, idempotent, immutable and free of prohibited payloads.",
        evidence={
            "schema_version": PACKAGE_SCHEMA_VERSION,
            "package_status": preflight["package_status"],
            "package_fingerprint": first_fingerprint,
            "snapshot_count": new_count,
            "artifact_count": artifact_count,
        },
    )
