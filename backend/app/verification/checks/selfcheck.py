"""Meta-verification: the Scientific CI framework must itself be testable.

These checks protect the verification contract: registry loading, duplicate and
unknown check handling, malformed result rejection, deterministic summaries and
exit-code behaviour.  They never depend on the application's scientific modules.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..baseline import BASELINE_EXPECTATIONS, REQUIRED_CHECK_IDS, SCHEMA_VERSIONS
from ..models import (
    SCIENTIFIC_CI_SCHEMA_VERSION,
    CheckResult,
    CheckStatus,
    FailureCategory,
    MalformedCheckResult,
    Severity,
)
from ..registry import (
    CheckRegistry,
    DuplicateCheckError,
    UnknownCheckError,
    load_checks,
)
from ..service import (
    EXIT_INFRASTRUCTURE_ERROR,
    EXIT_REQUIRED_FAILURE,
    EXIT_SUCCESS,
    VerificationReport,
    render_report,
    run_verification,
)
from ..models import CheckCategory
from ..registry import FULL_PROFILE, FAST_PROFILE, check


@check(
    check_id="verification_registry_contract",
    name="Verification registry contract",
    category=CheckCategory.IMPORT_STARTUP,
    description="Registry loading, duplicate rejection, unknown-check handling, manifest shape and baseline consistency.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=60.0,
)
def verification_registry_contract() -> CheckResult:
    active = load_checks()
    problems: list[str] = []

    identifiers = [definition.check_id for definition in active.definitions(include_deprecated=True)]
    if len(identifiers) != len(set(identifiers)):
        problems.append("duplicate check identifiers are registered")
    if len(active) < 20:
        problems.append(f"only {len(active)} checks are registered; the registry looks incomplete")
    for definition in active.definitions(include_deprecated=True):
        if not definition.description:
            problems.append(f"check {definition.check_id} has no description")
        if definition.category not in CheckCategory._value2member_map_:
            problems.append(f"check {definition.check_id} declares unsupported category {definition.category!r}")
        if not definition.profiles:
            problems.append(f"check {definition.check_id} belongs to no profile")

    probe = CheckRegistry()

    def _runner() -> CheckResult:
        return CheckResult(
            check_id="duplicate_probe",
            category=CheckCategory.IMPORT_STARTUP.value,
            status=CheckStatus.PASS,
            severity=Severity.ADVISORY,
            message="probe",
        )

    from ..registry import CheckDefinition

    probe.register(
        CheckDefinition(
            check_id="duplicate_probe",
            name="probe",
            category=CheckCategory.IMPORT_STARTUP.value,
            description="probe",
            severity=Severity.ADVISORY,
            runner=_runner,
        )
    )
    try:
        probe.register(
            CheckDefinition(
                check_id="duplicate_probe",
                name="probe",
                category=CheckCategory.IMPORT_STARTUP.value,
                description="probe",
                severity=Severity.ADVISORY,
                runner=_runner,
            )
        )
        problems.append("duplicate check identifiers were accepted")
    except DuplicateCheckError:
        pass
    try:
        active.get("does_not_exist")
        problems.append("an unknown check identifier was resolved instead of raising")
    except UnknownCheckError:
        pass

    manifest = active.manifest()
    if manifest["schema_version"] != SCIENTIFIC_CI_SCHEMA_VERSION:
        problems.append("the verification manifest reports a different schema version")
    if sorted(manifest["profiles"]) != sorted([FAST_PROFILE, FULL_PROFILE]):
        problems.append("the verification manifest does not list the supported profiles")
    for entry in manifest["checks"]:
        if set(entry) < {"id", "severity", "description", "category", "profiles"}:
            problems.append(f"manifest entry for {entry.get('id')} is incomplete")

    live_required = sorted(definition.check_id for definition in active.definitions() if definition.severity is Severity.REQUIRED)
    reviewed_required = sorted(REQUIRED_CHECK_IDS)
    added = sorted(set(live_required) - set(reviewed_required))
    removed = sorted(set(reviewed_required) - set(live_required))
    if added:
        problems.append(f"required checks were added without updating the reviewed baseline: {added}")
    if removed:
        problems.append(f"required checks disappeared from the registry: {removed}")
    if len(BASELINE_EXPECTATIONS) != 9 or len(SCHEMA_VERSIONS) != 10:
        problems.append("the scientific baseline changed size without review")

    if problems:
        return CheckResult(
            check_id="verification_registry_contract",
            category=CheckCategory.IMPORT_STARTUP.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.VERIFICATION_INFRASTRUCTURE_FAILURE,
            expected="a complete, duplicate-free and baseline-consistent check registry",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="verification_registry_contract",
        category=CheckCategory.IMPORT_STARTUP.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="The verification registry loads, rejects duplicates and unknowns, and matches its baseline.",
        evidence={
            "check_count": len(identifiers),
            "required_check_count": len(live_required),
            "required_count": len(active.for_profile(FULL_PROFILE)),
            "categories": manifest["categories"],
            "schema_version": SCIENTIFIC_CI_SCHEMA_VERSION,
        },
    )


@check(
    check_id="verification_result_contract",
    name="Verification result contract",
    category=CheckCategory.IMPORT_STARTUP,
    description="Malformed results are rejected, summaries are deterministic and exit codes follow the documented policy.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=60.0,
)
def verification_result_contract() -> CheckResult:
    problems: list[str] = []

    def _expect_malformed(payload: dict, label: str) -> None:
        try:
            CheckResult(**payload)
            problems.append(f"a malformed check result was accepted: {label}")
        except MalformedCheckResult:
            pass
        except TypeError:
            problems.append(f"a malformed check result raised TypeError instead of MalformedCheckResult: {label}")

    _expect_malformed(
        {
            "check_id": "probe",
            "category": CheckCategory.IMPORT_STARTUP.value,
            "status": "NOT_A_STATUS",
            "severity": Severity.REQUIRED,
            "message": "probe",
        },
        "unknown status",
    )
    _expect_malformed(
        {
            "check_id": "probe",
            "category": CheckCategory.IMPORT_STARTUP.value,
            "status": CheckStatus.PASS,
            "severity": "NOT_A_SEVERITY",
            "message": "probe",
        },
        "unknown severity",
    )
    _expect_malformed(
        {
            "check_id": "probe",
            "category": CheckCategory.IMPORT_STARTUP.value,
            "status": CheckStatus.FAIL,
            "severity": Severity.REQUIRED,
            "message": "probe",
        },
        "failure without a failure category",
    )

    def _result(check_id: str, status: CheckStatus, severity: Severity) -> CheckResult:
        payload = {
            "check_id": check_id,
            "category": CheckCategory.IMPORT_STARTUP.value,
            "status": status,
            "severity": severity,
            "message": f"{check_id} {status.value}",
        }
        if status in (CheckStatus.FAIL, CheckStatus.WARN):
            payload["failure_category"] = FailureCategory.SCIENTIFIC_REGRESSION
        return CheckResult(**payload)

    started = datetime.now(timezone.utc)
    passing = VerificationReport(
        profile=FAST_PROFILE,
        results=[_result("a", CheckStatus.PASS, Severity.REQUIRED), _result("b", CheckStatus.PASS, Severity.ADVISORY)],
        started_at=started,
        duration_ms=1,
    )
    failing = VerificationReport(
        profile=FAST_PROFILE,
        results=[_result("a", CheckStatus.PASS, Severity.REQUIRED), _result("b", CheckStatus.FAIL, Severity.REQUIRED)],
        started_at=started,
        duration_ms=1,
    )
    advisory = VerificationReport(
        profile=FAST_PROFILE,
        results=[_result("a", CheckStatus.WARN, Severity.ADVISORY)],
        started_at=started,
        duration_ms=1,
    )
    infrastructure = VerificationReport(
        profile=FAST_PROFILE,
        results=[_result("a", CheckStatus.PASS, Severity.REQUIRED)],
        started_at=started,
        duration_ms=1,
        infrastructure_error=True,
    )
    if passing.exit_code != EXIT_SUCCESS:
        problems.append("a fully passing report did not return exit code 0")
    if failing.exit_code != EXIT_REQUIRED_FAILURE:
        problems.append("a blocking required failure did not return exit code 1")
    if advisory.exit_code != EXIT_SUCCESS or advisory.result != "PASSED":
        problems.append("an advisory-only warning blocked the verification gate")
    if infrastructure.exit_code != EXIT_INFRASTRUCTURE_ERROR:
        problems.append("a verification infrastructure error did not return exit code 2")
    if passing.summary_lines() != passing.summary_lines():
        problems.append("summary rendering is not deterministic for identical results")
    rebuilt = VerificationReport(
        profile=FAST_PROFILE,
        results=list(passing.results),
        started_at=datetime.now(timezone.utc),
        duration_ms=999,
    )
    if rebuilt.summary_lines() != passing.summary_lines():
        problems.append("summary rendering depends on timestamps or durations")
    if "FAIL" not in render_report(failing):
        problems.append("the rendered report does not surface the failing check")

    report = run_verification(FAST_PROFILE, check_ids=["verification_result_contract"])
    if report.results[0].check_id != "verification_result_contract":
        problems.append("explicit check selection returned an unexpected check")

    if problems:
        return CheckResult(
            check_id="verification_result_contract",
            category=CheckCategory.IMPORT_STARTUP.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.VERIFICATION_INFRASTRUCTURE_FAILURE,
            expected="a strict result contract with deterministic summaries and documented exit codes",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="verification_result_contract",
        category=CheckCategory.IMPORT_STARTUP.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="The result contract rejects malformed results, renders deterministic summaries and maps exit codes.",
        evidence={
            "exit_codes": {"pass": EXIT_SUCCESS, "required_failure": EXIT_REQUIRED_FAILURE, "infrastructure": EXIT_INFRASTRUCTURE_ERROR},
            "malformed_rejections": 3,
            "deterministic_summary": True,
        },
    )
