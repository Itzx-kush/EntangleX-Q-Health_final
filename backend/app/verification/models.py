"""Structured contract for Scientific CI verification results.

Scientific CI verifies implementation-level scientific, reproducibility and
deployment invariants.  It never decides whether a scientific result is good,
valid, or trustworthy.  Every check therefore reports a factual outcome using
this explicit contract instead of hiding failures inside free text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

# Version of the verification contract itself.  Required checks are never
# removed silently; see docs/scientific_ci_verification.md.
SCIENTIFIC_CI_SCHEMA_VERSION = "scientific_ci_v1"

# Version of the machine-readable baseline artefact produced by the verifier.
SCIENTIFIC_CI_BASELINE_VERSION = "scientific_ci_baseline_v1"


class CheckStatus(str, Enum):
    """Outcome of a single verification check."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    UNVERIFIABLE = "UNVERIFIABLE"


class Severity(str, Enum):
    """Whether a non-passing outcome blocks the verification gate."""

    REQUIRED = "REQUIRED"
    ADVISORY = "ADVISORY"


class FailureCategory(str, Enum):
    """Why a check did not pass, so developers know what to fix."""

    SCIENTIFIC_REGRESSION = "SCIENTIFIC_REGRESSION"
    APPLICATION_FAILURE = "APPLICATION_FAILURE"
    TEST_FAILURE = "TEST_FAILURE"
    MIGRATION_FAILURE = "MIGRATION_FAILURE"
    ENVIRONMENT_FAILURE = "ENVIRONMENT_FAILURE"
    VERIFICATION_INFRASTRUCTURE_FAILURE = "VERIFICATION_INFRASTRUCTURE_FAILURE"


class CheckCategory(str, Enum):
    """Supported Scientific CI categories."""

    IMPORT_STARTUP = "IMPORT / STARTUP"
    DATABASE_MIGRATION = "DATABASE / MIGRATION"
    REPRODUCIBILITY = "REPRODUCIBILITY"
    ARTIFACT_INTEGRITY = "ARTIFACT INTEGRITY"
    DATA_SCHEMA = "DATA / SCHEMA"
    EXPERIMENT_INTEGRITY = "EXPERIMENT INTEGRITY"
    PIPELINE_INTEGRITY = "PIPELINE INTEGRITY"
    PROTOCOL_INTEGRITY = "PROTOCOL INTEGRITY"
    EVIDENCE_INTEGRITY = "EVIDENCE INTEGRITY"
    LINEAGE_INTEGRITY = "LINEAGE INTEGRITY"
    MODEL_CARD_INTEGRITY = "MODEL-CARD INTEGRITY"
    AUDIT_INTEGRITY = "AUDIT INTEGRITY"
    QUANTUM_INTEGRITY = "QUANTUM INTEGRITY"
    DEPLOYMENT_INTEGRITY = "DEPLOYMENT INTEGRITY"


BLOCKING_STATUSES = frozenset({CheckStatus.FAIL})


class MalformedCheckResult(ValueError):
    """Raised when a runner returns something outside the check-result contract."""


@dataclass(frozen=True)
class CheckResult:
    """One structured verification outcome."""

    check_id: str
    category: str
    status: CheckStatus
    severity: Severity
    message: str
    evidence: Mapping[str, Any] = field(default_factory=dict)
    failure_category: FailureCategory | None = None
    expected: str | None = None
    observed: str | None = None
    duration_ms: int = 0

    def __post_init__(self) -> None:
        # Runners may declare statuses as plain strings; normalize them to the
        # enum contract so a typo is rejected instead of silently tolerated.
        try:
            object.__setattr__(self, "status", CheckStatus(self.status))
            object.__setattr__(self, "severity", Severity(self.severity))
            if self.failure_category is not None:
                object.__setattr__(self, "failure_category", FailureCategory(self.failure_category))
        except ValueError as exc:
            raise MalformedCheckResult(str(exc)) from exc
        self.validate()

    def validate(self) -> None:
        if not self.check_id or not isinstance(self.check_id, str):
            raise MalformedCheckResult("check_id must be a non-empty string")
        if not isinstance(self.status, CheckStatus):
            raise MalformedCheckResult(f"status must be a CheckStatus, received {self.status!r}")
        if not isinstance(self.severity, Severity):
            raise MalformedCheckResult(f"severity must be a Severity, received {self.severity!r}")
        if self.failure_category is not None and not isinstance(self.failure_category, FailureCategory):
            raise MalformedCheckResult("failure_category must be a FailureCategory when present")
        if not isinstance(self.evidence, Mapping):
            raise MalformedCheckResult("evidence must be a mapping")
        if not self.message or not isinstance(self.message, str):
            raise MalformedCheckResult("message must be a non-empty string")
        if self.status is not CheckStatus.PASS and self.failure_category is None and self.status in (
            CheckStatus.FAIL,
            CheckStatus.WARN,
        ):
            raise MalformedCheckResult("FAIL and WARN results must declare a failure_category")

    @property
    def blocking(self) -> bool:
        return self.severity is Severity.REQUIRED and self.status in BLOCKING_STATUSES

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "check_id": self.check_id,
            "category": self.category,
            "status": self.status.value,
            "severity": self.severity.value,
            "message": self.message,
            "evidence": _jsonable(self.evidence),
            "duration_ms": self.duration_ms,
        }
        if self.failure_category is not None:
            payload["failure_category"] = self.failure_category.value
        if self.expected is not None:
            payload["expected"] = self.expected
        if self.observed is not None:
            payload["observed"] = self.observed
        return payload

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "CheckResult":
        """Rebuild a result from a serialized mapping, rejecting malformed input."""
        if not isinstance(payload, Mapping):
            raise MalformedCheckResult("check result must be a mapping")
        try:
            status = CheckStatus(payload["status"])
            severity = Severity(payload["severity"])
        except KeyError as exc:  # pragma: no cover - defensive
            raise MalformedCheckResult(f"check result is missing {exc.args[0]!r}") from exc
        except ValueError as exc:
            raise MalformedCheckResult(f"unknown status or severity: {exc}") from exc
        failure_category = payload.get("failure_category")
        return cls(
            check_id=str(payload.get("check_id", "")),
            category=str(payload.get("category", "")),
            status=status,
            severity=severity,
            message=str(payload.get("message", "")),
            evidence=dict(payload.get("evidence") or {}),
            failure_category=FailureCategory(failure_category) if failure_category else None,
            expected=payload.get("expected"),
            observed=payload.get("observed"),
            duration_ms=int(payload.get("duration_ms") or 0),
        )


def _jsonable(value: Any) -> Any:
    from ..utils.serialization import clean_json

    return clean_json(value)


def passed(check_id: str, category: str, severity: Severity, message: str, **evidence: Any) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        category=category,
        status=CheckStatus.PASS,
        severity=severity,
        message=message,
        evidence=evidence,
    )


def warned(
    check_id: str,
    category: str,
    severity: Severity,
    message: str,
    *,
    failure_category: FailureCategory = FailureCategory.SCIENTIFIC_REGRESSION,
    expected: str | None = None,
    observed: str | None = None,
    **evidence: Any,
) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        category=category,
        status=CheckStatus.WARN,
        severity=severity,
        message=message,
        evidence=evidence,
        failure_category=failure_category,
        expected=expected,
        observed=observed,
    )


def failed(
    check_id: str,
    category: str,
    severity: Severity,
    message: str,
    *,
    failure_category: FailureCategory = FailureCategory.SCIENTIFIC_REGRESSION,
    expected: str | None = None,
    observed: str | None = None,
    **evidence: Any,
) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        category=category,
        status=CheckStatus.FAIL,
        severity=severity,
        message=message,
        evidence=evidence,
        failure_category=failure_category,
        expected=expected,
        observed=observed,
    )


def skipped(
    check_id: str,
    category: str,
    severity: Severity,
    message: str,
    **evidence: Any,
) -> CheckResult:
    """The check could not run because its precondition is absent, not because it was inconvenient."""
    return CheckResult(
        check_id=check_id,
        category=category,
        status=CheckStatus.SKIPPED,
        severity=severity,
        message=message,
        evidence=evidence,
    )


def unverifiable(
    check_id: str,
    category: str,
    severity: Severity,
    message: str,
    **evidence: Any,
) -> CheckResult:
    """The invariant exists but the repository provides no evidence to evaluate it."""
    return CheckResult(
        check_id=check_id,
        category=category,
        status=CheckStatus.UNVERIFIABLE,
        severity=severity,
        message=message,
        evidence=evidence,
    )
