"""Reproducibility verification.

Reproducibility manifests are verified at the metadata level: schema sections,
deterministic configuration fingerprints, and structured integrity reporting.
Large models are never retrained to prove reproducibility during a PR.
"""

from __future__ import annotations

from ..fixtures import ALTERNATE_SEED, canonical_manifest_payload, persist_chain
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check
from ._support import expect_app_error, require_fingerprint

REQUIRED_MANIFEST_SECTIONS = (
    "identity",
    "dataset",
    "sampling",
    "split",
    "cross_validation",
    "preprocessing",
    "feature_engineering",
    "feature_selection",
    "dimensionality_reduction",
    "models",
    "threshold_protocol",
    "evaluation_protocol",
    "software_environment",
    "runtime_environment",
    "execution_at_lock",
    "reproducibility",
)


@check(
    check_id="reproducibility_manifest_contract",
    name="Reproducibility manifest contract",
    category=CheckCategory.REPRODUCIBILITY,
    description="Verifies the manifest schema sections, deterministic configuration fingerprints and structured integrity reporting.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=120.0,
)
def reproducibility_manifest_contract() -> CheckResult:
    from app.manifests.schemas import RunManifest
    from app.manifests.service import MANIFEST_SCHEMA_VERSION, configuration_fingerprint, verify_manifest_integrity

    missing_sections = sorted(set(REQUIRED_MANIFEST_SECTIONS) - set(RunManifest.model_fields))
    if missing_sections:
        return CheckResult(
            check_id="reproducibility_manifest_contract",
            category=CheckCategory.REPRODUCIBILITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message=f"The run manifest schema no longer exposes required provenance sections: {missing_sections}.",
            evidence={"missing_sections": missing_sections, "manifest_schema_version": MANIFEST_SCHEMA_VERSION},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="every required provenance section remains in RunManifest",
            observed=f"missing: {missing_sections}",
        )

    payload = canonical_manifest_payload()
    first = require_fingerprint(configuration_fingerprint(payload), label="configuration fingerprint")
    second = require_fingerprint(configuration_fingerprint(payload), label="configuration fingerprint")

    identity_only = canonical_manifest_payload()
    identity_only["identity"]["run_id"] = "00000000-0000-4000-8000-000000000099"
    identity_fingerprint = configuration_fingerprint(identity_only)

    changed = canonical_manifest_payload()
    changed["split"]["seed"] = ALTERNATE_SEED
    changed_fingerprint = configuration_fingerprint(changed)

    problems: list[str] = []
    if first != second:
        problems.append("configuration fingerprint is not deterministic for identical input")
    if identity_fingerprint != first:
        problems.append("configuration fingerprint changed when only run identity changed")
    if changed_fingerprint == first:
        problems.append("configuration fingerprint did not change when scientific conditions changed")

    chain = persist_chain()
    integrity = verify_manifest_integrity(chain.run_id)
    if integrity.valid or "manifest_unavailable" not in integrity.errors:
        problems.append(
            "a run without a locked manifest did not report a structured 'manifest_unavailable' integrity result"
        )

    with expect_app_error():
        from app.manifests.service import get_manifest

        get_manifest(chain.run_id)

    if problems:
        return CheckResult(
            check_id="reproducibility_manifest_contract",
            category=CheckCategory.REPRODUCIBILITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="deterministic, identity-independent configuration fingerprints and structured integrity reporting",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="reproducibility_manifest_contract",
        category=CheckCategory.REPRODUCIBILITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Reproducibility manifest schema, deterministic configuration fingerprint and integrity reporting are consistent.",
        evidence={
            "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
            "section_count": len(REQUIRED_MANIFEST_SECTIONS),
            "configuration_fingerprint": first,
            "identity_independent": True,
            "scientific_change_detected": True,
            "legacy_manifest_integrity_errors": list(integrity.errors),
        },
    )

