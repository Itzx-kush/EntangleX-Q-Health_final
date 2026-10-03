"""Execution engine for Scientific CI verification.

The engine is intentionally boring and deterministic: it runs a bounded set of
registered checks, each with its own timeout, and turns their structured
results into a stable report, a deterministic summary and an exit code.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from .models import (
    SCIENTIFIC_CI_SCHEMA_VERSION,
    CheckResult,
    CheckStatus,
    FailureCategory,
    MalformedCheckResult,
    Severity,
)
from .registry import (
    FAST_PROFILE,
    SUPPORTED_PROFILES,
    CheckDefinition,
    CheckRegistry,
    load_checks,
)

EXIT_SUCCESS = 0
EXIT_REQUIRED_FAILURE = 1
EXIT_INFRASTRUCTURE_ERROR = 2

RESULT_PASSED = "PASSED"
RESULT_FAILED = "FAILED"
RESULT_INFRASTRUCTURE_ERROR = "VERIFICATION_INFRASTRUCTURE_ERROR"


@dataclass
class VerificationReport:
    """Complete outcome of one verification run."""

    profile: str
    results: list[CheckResult]
    started_at: datetime
    duration_ms: int
    schema_version: str = SCIENTIFIC_CI_SCHEMA_VERSION
    infrastructure_error: bool = False
    requested: list[str] = field(default_factory=list)

    # ---- counts ---------------------------------------------------------- #
    def _count(self, severity: Severity, status: CheckStatus) -> int:
        return sum(1 for item in self.results if item.severity is severity and item.status is status)

    @property
    def required_pass(self) -> int:
        return self._count(Severity.REQUIRED, CheckStatus.PASS)

    @property
    def required_fail(self) -> int:
        return self._count(Severity.REQUIRED, CheckStatus.FAIL)

    @property
    def advisory_pass(self) -> int:
        return self._count(Severity.ADVISORY, CheckStatus.PASS)

    @property
    def advisory_warn(self) -> int:
        return self._count(Severity.ADVISORY, CheckStatus.WARN)

    @property
    def advisory_fail(self) -> int:
        return self._count(Severity.ADVISORY, CheckStatus.FAIL)

    @property
    def skipped(self) -> int:
        return sum(1 for item in self.results if item.status is CheckStatus.SKIPPED)

    @property
    def unverifiable(self) -> int:
        return sum(1 for item in self.results if item.status is CheckStatus.UNVERIFIABLE)

    @property
    def warnings(self) -> int:
        return sum(1 for item in self.results if item.status is CheckStatus.WARN)

    @property
    def blocking_failures(self) -> list[CheckResult]:
        return [item for item in self.results if item.blocking]

    @property
    def failure_categories(self) -> list[str]:
        return sorted({item.failure_category.value for item in self.results if item.failure_category is not None})

    @property
    def result(self) -> str:
        if self.infrastructure_error:
            return RESULT_INFRASTRUCTURE_ERROR
        return RESULT_FAILED if self.blocking_failures else RESULT_PASSED

    @property
    def exit_code(self) -> int:
        if self.infrastructure_error:
            return EXIT_INFRASTRUCTURE_ERROR
        return EXIT_REQUIRED_FAILURE if self.blocking_failures else EXIT_SUCCESS

    # ---- serialization --------------------------------------------------- #
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "profile": self.profile,
            "started_at": self.started_at.isoformat(),
            "duration_ms": self.duration_ms,
            "result": self.result,
            "exit_code": self.exit_code,
            "counts": {
                "required_pass": self.required_pass,
                "required_fail": self.required_fail,
                "advisory_pass": self.advisory_pass,
                "advisory_warn": self.advisory_warn,
                "advisory_fail": self.advisory_fail,
                "skipped": self.skipped,
                "unverifiable": self.unverifiable,
            },
            "failure_categories": self.failure_categories,
            "checks": [item.to_dict() for item in self.results],
        }

    # ---- deterministic rendering ----------------------------------------- #
    def summary_lines(self) -> list[str]:
        """Deterministic summary: depends only on the check outcomes."""
        lines = [
            "Scientific CI Verification",
            "",
            f"Profile: {self.profile}",
            "",
            "Required:",
            f"  PASS  {self.required_pass:>3}",
            f"  FAIL  {self.required_fail:>3}",
            "",
            "Advisory:",
            f"  PASS  {self.advisory_pass:>3}",
            f"  WARN  {self.advisory_warn:>3}",
            f"  FAIL  {self.advisory_fail:>3}",
            "",
            "Skipped:",
            f"  {self.skipped:>3}",
            "",
            "Unverifiable:",
            f"  {self.unverifiable:>3}",
            "",
            "Result:",
            f"  {self.result}",
        ]
        return lines

    def check_lines(self) -> list[str]:
        """One concise line per check, ordered by check identifier."""
        return [
            f"  {item.status.value:<12} {item.check_id}"
            for item in sorted(self.results, key=lambda entry: entry.check_id)
        ]


def render_report(report: VerificationReport, *, show_checks: bool = True) -> str:
    """Human-readable report. Failures always carry actionable detail."""
    blocks: list[str] = []
    if show_checks:
        blocks.append("Scientific CI checks")
        blocks.append("")
        blocks.extend(report.check_lines())
        blocks.append("")
    blocks.extend(report.summary_lines())
    for result in report.blocking_failures:
        blocks.append("")
        blocks.append(render_failure_detail(result))
    for result in report.results:
        if result.status in (CheckStatus.WARN,) and result.severity is Severity.ADVISORY:
            blocks.append("")
            blocks.append(render_failure_detail(result, heading="Scientific CI ADVISORY"))
    return "\n".join(blocks)


def render_failure_detail(result: CheckResult, *, heading: str = "Scientific CI FAILURE") -> str:
    """Actionable failure block; never a bare 'test failed'."""
    lines = [
        heading,
        "",
        "Check:",
        result.check_id,
        "",
        "Category:",
        result.category,
        "",
        "Status:",
        result.status.value,
        "",
        "Failure category:",
        result.failure_category.value if result.failure_category else "UNSPECIFIED",
        "",
        "Reason:",
        result.message,
    ]
    if result.expected:
        lines.extend(["", "Expected:", result.expected])
    if result.observed:
        lines.extend(["", "Observed:", result.observed])
    return "\n".join(lines)


def _classify_exception(exc: BaseException) -> FailureCategory:
    from app.utils.errors import AppError

    if isinstance(exc, TimeoutError):
        return FailureCategory.VERIFICATION_INFRASTRUCTURE_FAILURE
    if isinstance(exc, MalformedCheckResult):
        return FailureCategory.VERIFICATION_INFRASTRUCTURE_FAILURE
    if isinstance(exc, ModuleNotFoundError):
        missing = (exc.name or "").split(".")[0]
        return FailureCategory.APPLICATION_FAILURE if missing in {"app", ""} else FailureCategory.ENVIRONMENT_FAILURE
    if isinstance(exc, ImportError):
        return FailureCategory.APPLICATION_FAILURE
    if isinstance(exc, AppError):
        return FailureCategory.APPLICATION_FAILURE
    return FailureCategory.APPLICATION_FAILURE


def run_check(definition: CheckDefinition) -> CheckResult:
    """Execute one check in a daemon thread so a hung check cannot block CI."""
    outcome: queue.Queue[Any] = queue.Queue(maxsize=1)

    def worker() -> None:
        try:
            outcome.put(definition.runner())
        except BaseException as exc:  # noqa: BLE001 - the runner is untrusted by design
            outcome.put(exc)

    thread = threading.Thread(target=worker, name=f"scientific-ci:{definition.check_id}", daemon=True)
    started = time_millis()
    thread.start()
    thread.join(definition.timeout_seconds)
    if thread.is_alive():
        return CheckResult(
            check_id=definition.check_id,
            category=definition.category,
            status=CheckStatus.FAIL,
            severity=definition.severity,
            message=f"Check exceeded its {definition.timeout_seconds:g}s Scientific CI timeout.",
            evidence={"timeout_seconds": definition.timeout_seconds},
            failure_category=FailureCategory.VERIFICATION_INFRASTRUCTURE_FAILURE,
            expected="check completes within its configured timeout",
            observed="check did not return before the timeout elapsed",
            duration_ms=time_millis() - started,
        )
    payload = outcome.get_nowait()
    duration = time_millis() - started
    if isinstance(payload, BaseException):
        return CheckResult(
            check_id=definition.check_id,
            category=definition.category,
            status=CheckStatus.FAIL,
            severity=definition.severity,
            message=f"Check raised {type(payload).__name__}: {_safe_text(payload)}",
            evidence={"exception_type": type(payload).__name__},
            failure_category=_classify_exception(payload),
            expected="check returns a structured CheckResult",
            observed=type(payload).__name__,
            duration_ms=duration,
        )
    if not isinstance(payload, CheckResult):
        return CheckResult(
            check_id=definition.check_id,
            category=definition.category,
            status=CheckStatus.FAIL,
            severity=definition.severity,
            message="Check returned a value outside the check-result contract.",
            evidence={"returned_type": type(payload).__name__},
            failure_category=FailureCategory.VERIFICATION_INFRASTRUCTURE_FAILURE,
            expected="CheckResult",
            observed=type(payload).__name__,
            duration_ms=duration,
        )
    if payload.check_id != definition.check_id:
        return CheckResult(
            check_id=definition.check_id,
            category=definition.category,
            status=CheckStatus.FAIL,
            severity=definition.severity,
            message="Check reported a result for a different check identifier.",
            evidence={"reported_check_id": payload.check_id},
            failure_category=FailureCategory.VERIFICATION_INFRASTRUCTURE_FAILURE,
            expected=definition.check_id,
            observed=payload.check_id,
            duration_ms=duration,
        )
    return CheckResult(
        check_id=payload.check_id,
        category=payload.category,
        status=payload.status,
        severity=payload.severity,
        message=payload.message,
        evidence=payload.evidence,
        failure_category=payload.failure_category,
        expected=payload.expected,
        observed=payload.observed,
        duration_ms=duration,
    )


def time_millis() -> int:
    import time

    return int(time.monotonic() * 1000)


def _safe_text(exc: BaseException) -> str:
    text = str(exc).strip().replace("\n", " ")
    return text[:400] if text else exc.__class__.__name__


def run_verification(
    profile: str = FAST_PROFILE,
    *,
    check_ids: Iterable[str] | None = None,
    include_deprecated: bool = False,
    check_registry: CheckRegistry | None = None,
    progress: Callable[[CheckResult], None] | None = None,
) -> VerificationReport:
    """Run a profile (or an explicit check selection) and return a structured report."""
    if profile not in SUPPORTED_PROFILES:
        raise ValueError(f"Unknown Scientific CI profile: {profile!r}")
    active_registry = check_registry or load_checks()
    if check_ids:
        definitions = active_registry.select(check_ids)
    else:
        definitions = active_registry.for_profile(profile, include_deprecated=include_deprecated)

    started_at = datetime.now(timezone.utc)
    started = time_millis()
    results: list[CheckResult] = []
    for definition in definitions:
        result = run_check(definition)
        results.append(result)
        if progress is not None:
            progress(result)
    return VerificationReport(
        profile=profile,
        results=results,
        started_at=started_at,
        duration_ms=time_millis() - started,
        requested=[definition.check_id for definition in definitions],
    )


def verification_manifest(check_registry: CheckRegistry | None = None) -> dict[str, Any]:
    """Machine-readable description of everything Scientific CI guarantees."""
    active_registry = check_registry or load_checks()
    return active_registry.manifest()


def baseline_document(check_registry: CheckRegistry | None = None) -> dict[str, Any]:
    """Lightweight, stable baseline metadata committed with the repository."""
    from .baseline import BASELINE_EXPECTATIONS, SCHEMA_VERSIONS

    active_registry = check_registry or load_checks()
    return {
        "baseline_version": "scientific_ci_baseline_v1",
        "schema_version": SCIENTIFIC_CI_SCHEMA_VERSION,
        "profiles": list(SUPPORTED_PROFILES),
        "supported_check_ids": [item.check_id for item in active_registry.definitions(include_deprecated=True)],
        "required_check_ids": [
            item.check_id for item in active_registry.definitions() if item.severity is Severity.REQUIRED
        ],
        "scientific_schema_versions": SCHEMA_VERSIONS,
        "fixture_fingerprint_expectations": BASELINE_EXPECTATIONS,
        "environment": {
            "python": ">=3.11",
            "node": "22.x",
            "runtime_profile": "isolated synthetic fixtures",
        },
    }
