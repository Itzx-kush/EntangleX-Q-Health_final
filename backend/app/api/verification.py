"""Read-only Scientific CI contract endpoint.

The deployed application exposes only the *static* verification contract: which
checks Scientific CI guarantees, their severity and the scientific schema
versions the repository pins.  It never claims the result of a GitHub Actions
run, and it never executes verification work inside a request.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..verification.baseline import BASELINE_EXPECTATIONS, SCHEMA_VERSIONS
from ..verification.models import SCIENTIFIC_CI_SCHEMA_VERSION
from ..verification.service import verification_manifest

router = APIRouter(tags=["scientific ci"])


@router.get("/system/scientific-ci")
def scientific_ci_contract() -> dict:
    """Describe the Scientific CI contract enforced outside the application."""
    manifest = verification_manifest()
    required = [entry for entry in manifest["checks"] if entry["severity"] == "REQUIRED"]
    advisory = [entry for entry in manifest["checks"] if entry["severity"] == "ADVISORY"]
    return {
        "schema_version": SCIENTIFIC_CI_SCHEMA_VERSION,
        "profiles": manifest["profiles"],
        "categories": manifest["categories"],
        "required_checks": required,
        "advisory_checks": advisory,
        "check_count": len(manifest["checks"]),
        "scientific_schema_versions": SCHEMA_VERSIONS,
        "baseline_fingerprint_count": len(BASELINE_EXPECTATIONS),
        "executed_in_application": False,
        "interpretation": (
            "This endpoint describes the Scientific CI contract that runs outside the deployed application. "
            "It reports no verification result. A passing Scientific CI run verifies implementation-level "
            "scientific and reproducibility invariants only; it is not independent scientific validation of any "
            "model, dataset, experiment, or biomedical conclusion."
        ),
    }
