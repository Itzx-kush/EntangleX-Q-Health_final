"""Advanced Dataset Quality Scorecard verification (Prompt 19).

Representative deterministic fixtures cover schema integrity, missingness,
duplicates, target integrity, non-finite values, class distribution, constant
features and context compatibility, together with the PASS / WARN / FAIL /
NOT_APPLICABLE / UNVERIFIABLE status vocabulary.
"""

from __future__ import annotations

from ..fixtures import quality_defect_frame, synthetic_biomedical_frame
from ..isolation import initialize_database, session
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check
from ._support import require_fingerprint

STATUSES = {"PASS", "WARN", "FAIL", "NOT_APPLICABLE", "UNVERIFIABLE"}


def _flatten_checks(domains: dict) -> list[dict]:
    checks: list[dict] = []
    for domain in domains.values():
        if isinstance(domain, dict):
            checks.extend(domain.get("checks") or [])
    return checks


@check(
    check_id="dataset_quality_contract",
    name="Dataset quality scorecard contract",
    category=CheckCategory.DATA_SCHEMA,
    description="Assesses a clean and a deliberately defective synthetic dataset and verifies statuses, determinism, idempotency and artifacts.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=300.0,
)
def dataset_quality_contract() -> CheckResult:
    from app.data_quality.schemas import DatasetQualityRequest
    from app.data_quality.service import assess_dataset_quality, get_latest_scorecard
    from app.storage.entities import Artifact

    initialize_database()
    problems: list[str] = []

    clean = register_clean()
    with session() as scope:
        clean_card = assess_dataset_quality(
            scope,
            clean.id,
            DatasetQualityRequest(target_column="observed_class", positive_label="positive"),
        )
        clean_summary = dict(clean_card.summary or {})
        clean_domains = dict(clean_card.domains or {})
        clean_fingerprint = require_fingerprint(clean_card.assessment_fingerprint, label="assessment fingerprint")
        clean_id = clean_card.id
        artifact_id = clean_card.artifact_id

    with session() as scope:
        repeated = assess_dataset_quality(
            scope,
            clean.id,
            DatasetQualityRequest(target_column="observed_class", positive_label="positive"),
        )
        latest = get_latest_scorecard(scope, clean.id)
        artifact = scope.get(Artifact, artifact_id) if artifact_id else None
    if repeated.id != clean_id or repeated.assessment_fingerprint != clean_fingerprint:
        problems.append("re-assessing unchanged data did not reuse the existing scorecard identity")
    if latest is None or latest.id != clean_id:
        problems.append("the latest scorecard lookup did not return the persisted assessment")
    if artifact is None or not artifact.immutable:
        problems.append("the scorecard did not register an immutable evidence artifact")
    if clean_summary.get("failed"):
        problems.append(f"a clean synthetic dataset reported {clean_summary.get('failed')} failed quality checks")
    if clean_summary.get("overall_status") not in STATUSES:
        problems.append(f"unknown overall scorecard status {clean_summary.get('overall_status')!r}")

    for entry in _flatten_checks(clean_domains):
        if entry.get("status") not in STATUSES:
            problems.append(f"quality check {entry.get('name')} reported unknown status {entry.get('status')!r}")
    if not _flatten_checks(clean_domains):
        problems.append("the scorecard did not emit any domain checks")

    defect = register_defect()
    with session() as scope:
        defect_card = assess_dataset_quality(
            scope,
            defect.id,
            DatasetQualityRequest(target_column="target", positive_label="positive"),
        )
        defect_summary = dict(defect_card.summary or {})
        defect_domains = dict(defect_card.domains or {})
    defect_checks = _flatten_checks(defect_domains)
    flagged = {entry.get("name") for entry in defect_checks if entry.get("status") in {"WARN", "FAIL"}}
    if defect_summary.get("overall_status") not in {"WARN", "FAIL"}:
        problems.append(
            f"a dataset with missing values, duplicates, imbalance, a constant feature and non-finite values reported "
            f"{defect_summary.get('overall_status')!r}"
        )
    if len(flagged) < 3:
        problems.append(f"only {len(flagged)} defect-bearing checks were flagged: {sorted(flagged)}")
    for entry in defect_checks:
        if entry.get("status") not in STATUSES:
            problems.append(f"quality check {entry.get('name')} reported unknown status {entry.get('status')!r}")
    unverifiable = [entry for entry in defect_checks if entry.get("status") == "UNVERIFIABLE"]
    passed = [entry for entry in defect_checks if entry.get("status") == "PASS"]
    if set(entry.get("name") for entry in unverifiable) & set(entry.get("name") for entry in passed):
        problems.append("a check is reported as both UNVERIFIABLE and PASS")

    with session() as scope:
        other_target = assess_dataset_quality(
            scope,
            clean.id,
            DatasetQualityRequest(target_column="biomarker_0", positive_label="positive", operation_key="scientific-ci:alternate-target"),
        )
    if other_target.assessment_fingerprint == clean_fingerprint:
        problems.append("changing the assessment configuration did not change the assessment fingerprint")

    if problems:
        return CheckResult(
            check_id="dataset_quality_contract",
            category=CheckCategory.DATA_SCHEMA.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="deterministic, status-accurate dataset quality assessments",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="dataset_quality_contract",
        category=CheckCategory.DATA_SCHEMA.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Dataset quality assessments are deterministic, idempotent, artifact-backed and status-accurate.",
        evidence={
            "clean_overall_status": clean_summary.get("overall_status"),
            "clean_check_count": len(_flatten_checks(clean_domains)),
            "assessment_fingerprint": clean_fingerprint,
            "defect_overall_status": defect_summary.get("overall_status"),
            "defect_flagged_checks": sorted(flagged),
            "domain_count": len(clean_domains),
        },
    )


def register_clean():
    from ..fixtures import register_fixture_dataset

    return register_fixture_dataset(synthetic_biomedical_frame(), name="Synthetic clean quality fixture")


def register_defect():
    from ..fixtures import register_fixture_dataset

    return register_fixture_dataset(
        quality_defect_frame(),
        name="Synthetic defective quality fixture",
        target="target",
    )
