"""Scientific CI verification for EntangleX Q-Health.

Scientific CI verifies implementation-level scientific, reproducibility,
provenance, data-integrity and deployment invariants.  A passing run means the
configured automated invariants held; it is **not** independent scientific
validation of any model, dataset, experiment or biomedical conclusion.

Run it locally with::

    cd backend
    python -m app.verification            # fast profile (pull-request gate)
    python -m app.verification --profile full
"""

from __future__ import annotations

from .models import (
    SCIENTIFIC_CI_SCHEMA_VERSION,
    CheckCategory,
    CheckResult,
    CheckStatus,
    FailureCategory,
    MalformedCheckResult,
    Severity,
)
from .registry import CheckDefinition, CheckRegistry, DuplicateCheckError, UnknownCheckError, load_checks, registry
from .service import (
    EXIT_INFRASTRUCTURE_ERROR,
    EXIT_REQUIRED_FAILURE,
    EXIT_SUCCESS,
    VerificationReport,
    baseline_document,
    render_failure_detail,
    render_report,
    run_check,
    run_verification,
    verification_manifest,
)

__all__ = [
    "SCIENTIFIC_CI_SCHEMA_VERSION",
    "EXIT_INFRASTRUCTURE_ERROR",
    "EXIT_REQUIRED_FAILURE",
    "EXIT_SUCCESS",
    "CheckCategory",
    "CheckDefinition",
    "CheckRegistry",
    "CheckResult",
    "CheckStatus",
    "DuplicateCheckError",
    "FailureCategory",
    "MalformedCheckResult",
    "Severity",
    "UnknownCheckError",
    "VerificationReport",
    "baseline_document",
    "load_checks",
    "registry",
    "render_failure_detail",
    "render_report",
    "run_check",
    "run_verification",
    "verification_manifest",
]
