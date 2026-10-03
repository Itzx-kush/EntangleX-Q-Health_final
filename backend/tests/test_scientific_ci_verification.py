"""Meta-tests for the Scientific CI verification framework itself.

These tests do not re-verify the scientific modules; they protect the
verification contract: registry integrity, result validation, deterministic
summaries, exit-code policy, manifest shape and the reviewed baseline.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.verification.baseline import BASELINE_EXPECTATIONS, REQUIRED_CHECK_IDS, SCHEMA_VERSIONS
from app.verification.models import (
    SCIENTIFIC_CI_SCHEMA_VERSION,
    CheckCategory,
    CheckResult,
    CheckStatus,
    FailureCategory,
    MalformedCheckResult,
    Severity,
)
from app.verification.registry import (
    CheckDefinition,
    CheckRegistry,
    DuplicateCheckError,
    UnknownCheckError,
    load_checks,
)
from app.verification.service import (
    EXIT_INFRASTRUCTURE_ERROR,
    EXIT_REQUIRED_FAILURE,
    EXIT_SUCCESS,
    VerificationReport,
    render_report,
    run_verification,
    verification_manifest,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]


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


def _report(results: list[CheckResult], *, infrastructure_error: bool = False) -> VerificationReport:
    return VerificationReport(
        profile="fast",
        results=results,
        started_at=datetime.now(timezone.utc),
        duration_ms=1,
        infrastructure_error=infrastructure_error,
    )


def test_registry_loads_every_check_module_once():
    first = load_checks()
    second = load_checks()
    assert first is second
    identifiers = [definition.check_id for definition in first.definitions(include_deprecated=True)]
    assert len(identifiers) == len(set(identifiers))
    assert len(identifiers) >= 30
    for definition in first.definitions(include_deprecated=True):
        assert definition.description
        assert definition.category in CheckCategory._value2member_map_
        assert definition.profiles
        assert callable(definition.runner)


def test_registry_rejects_duplicate_and_unknown_identifiers():
    registry = CheckRegistry()

    def runner() -> CheckResult:
        return _result("probe", CheckStatus.PASS, Severity.ADVISORY)

    definition = CheckDefinition(
        check_id="probe",
        name="probe",
        category=CheckCategory.IMPORT_STARTUP.value,
        description="probe",
        severity=Severity.ADVISORY,
        runner=runner,
    )
    registry.register(definition)
    with pytest.raises(DuplicateCheckError):
        registry.register(definition)
    with pytest.raises(UnknownCheckError):
        registry.get("probe_does_not_exist")
    with pytest.raises(UnknownCheckError):
        registry.select(["probe_does_not_exist"])
    with pytest.raises(ValueError):
        registry.for_profile("not_a_profile")


def test_deprecated_checks_must_name_a_replacement():
    def runner() -> CheckResult:
        return _result("deprecated_probe", CheckStatus.PASS, Severity.ADVISORY)

    with pytest.raises(ValueError):
        CheckDefinition(
            check_id="deprecated_probe",
            name="deprecated probe",
            category=CheckCategory.IMPORT_STARTUP.value,
            description="probe",
            severity=Severity.ADVISORY,
            runner=runner,
            deprecated=True,
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "NOT_A_STATUS", "severity": "REQUIRED", "message": "probe"},
        {"status": "PASS", "severity": "NOT_A_SEVERITY", "message": "probe"},
        {"status": "FAIL", "severity": "REQUIRED", "message": "probe"},
        {"status": "PASS", "severity": "REQUIRED", "message": ""},
    ],
)
def test_malformed_results_are_rejected(payload):
    with pytest.raises(MalformedCheckResult):
        CheckResult(check_id="probe", category=CheckCategory.IMPORT_STARTUP.value, **payload)


def test_result_round_trip_and_blocking_semantics():
    failing = _result("probe", CheckStatus.FAIL, Severity.REQUIRED)
    rebuilt = CheckResult.from_mapping(json.loads(json.dumps(failing.to_dict())))
    assert rebuilt == failing
    assert failing.blocking is True
    assert _result("probe", CheckStatus.WARN, Severity.ADVISORY).blocking is False
    assert _result("probe", CheckStatus.FAIL, Severity.ADVISORY).blocking is False
    assert _result("probe", CheckStatus.SKIPPED, Severity.REQUIRED).blocking is False
    with pytest.raises(MalformedCheckResult):
        CheckResult.from_mapping({"status": "PASS", "severity": "REQUIRED"})


def test_summary_and_exit_codes_are_deterministic():
    passing = _report([_result("b", CheckStatus.PASS, Severity.REQUIRED), _result("a", CheckStatus.PASS, Severity.ADVISORY)])
    failing = _report([_result("a", CheckStatus.FAIL, Severity.REQUIRED)])
    advisory = _report([_result("a", CheckStatus.WARN, Severity.ADVISORY)])
    infrastructure = _report([_result("a", CheckStatus.PASS, Severity.REQUIRED)], infrastructure_error=True)

    assert passing.exit_code == EXIT_SUCCESS
    assert failing.exit_code == EXIT_REQUIRED_FAILURE
    assert advisory.exit_code == EXIT_SUCCESS
    assert infrastructure.exit_code == EXIT_INFRASTRUCTURE_ERROR
    assert passing.result == "PASSED"
    assert failing.result == "FAILED"

    rebuilt = VerificationReport(
        profile="fast",
        results=list(passing.results),
        started_at=datetime.now(timezone.utc),
        duration_ms=12345,
    )
    assert rebuilt.summary_lines() == passing.summary_lines()
    assert "a" in "\n".join(passing.check_lines())
    rendered = render_report(failing)
    assert "Scientific CI FAILURE" in rendered
    assert "SCIENTIFIC_REGRESSION" in rendered


def test_manifest_covers_every_category_and_profile():
    manifest = verification_manifest()
    assert manifest["schema_version"] == SCIENTIFIC_CI_SCHEMA_VERSION
    assert sorted(manifest["profiles"]) == ["fast", "full"]
    categories = {entry["category"] for entry in manifest["checks"]}
    assert categories == {category.value for category in CheckCategory}
    for entry in manifest["checks"]:
        assert entry["severity"] in {"REQUIRED", "ADVISORY"}
        assert entry["profiles"]
        assert entry["timeout_seconds"] > 0


def test_required_checks_match_the_reviewed_baseline():
    registry = load_checks()
    live = sorted(
        definition.check_id
        for definition in registry.definitions()
        if definition.severity is Severity.REQUIRED
    )
    assert live == sorted(REQUIRED_CHECK_IDS)
    assert len(BASELINE_EXPECTATIONS) == 9
    assert len(SCHEMA_VERSIONS) == 10


def test_fast_profile_excludes_only_the_heavier_checks():
    registry = load_checks()
    fast = {definition.check_id for definition in registry.for_profile("fast")}
    full = {definition.check_id for definition in registry.for_profile("full")}
    assert fast <= full
    assert "database_migration_upgrade_path" in full
    assert "database_migration_upgrade_path" not in fast
    assert "fingerprint_canonicalization" in fast


def test_runner_executes_a_fast_subset_with_structured_results():
    report = run_verification(
        "fast",
        check_ids=["fingerprint_canonicalization", "verification_result_contract"],
    )
    assert [result.check_id for result in report.results] == [
        "fingerprint_canonicalization",
        "verification_result_contract",
    ]
    assert all(result.status is CheckStatus.PASS for result in report.results)
    assert report.exit_code == EXIT_SUCCESS
    assert report.to_dict()["counts"]["required_pass"] == 2


def test_unknown_check_selection_is_rejected():
    with pytest.raises(UnknownCheckError):
        run_verification("fast", check_ids=["definitely_not_a_check"])


def test_cli_lists_checks_and_reports_a_structured_failure(tmp_path):
    environment = {"PYTHONPATH": str(BACKEND_ROOT), "QHEALTH_API_TOKEN": "", "QHEALTH_STORAGE_ROOT": str(tmp_path / "cli")}
    listing = subprocess.run(
        [sys.executable, "-m", "app.verification", "--list"],
        cwd=BACKEND_ROOT,
        env={**environment},
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert listing.returncode == 0, listing.stderr
    assert "checks registered" in listing.stdout

    report_path = tmp_path / "report.json"
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.verification",
            "--check",
            "verification_result_contract",
            "--json-out",
            str(report_path),
        ],
        cwd=BACKEND_ROOT,
        env={**environment},
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )
    assert run.returncode in {EXIT_SUCCESS, EXIT_REQUIRED_FAILURE}, run.stderr
    payload = json.loads(report_path.read_text())
    assert payload["schema_version"] == SCIENTIFIC_CI_SCHEMA_VERSION
    assert payload["checks"][0]["check_id"] == "verification_result_contract"
