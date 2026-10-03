"""Deployment integrity: forbidden internal imports and environment parity.

The repository previously failed in production with
``ModuleNotFoundError: No module named 'backend'`` because production modules
imported the application through the repository-level ``backend.`` namespace.
These checks make that regression class permanently detectable.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from ..isolation import BACKEND_ROOT, app_workdir, subprocess_environment
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check

FORBIDDEN_ROOTS = ("backend",)


def _scan(root: Path) -> list[dict]:
    findings: list[dict] = []
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:  # a syntax error is itself a deployment blocker
            findings.append(
                {
                    "path": str(path.relative_to(BACKEND_ROOT)),
                    "line": exc.lineno or 0,
                    "pattern": "SyntaxError",
                }
            )
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in FORBIDDEN_ROOTS:
                findings.append(
                    {
                        "path": str(path.relative_to(BACKEND_ROOT)),
                        "line": node.lineno,
                        "pattern": f"from {node.module} import ...",
                    }
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in FORBIDDEN_ROOTS:
                        findings.append(
                            {
                                "path": str(path.relative_to(BACKEND_ROOT)),
                                "line": node.lineno,
                                "pattern": f"import {alias.name}",
                            }
                        )
    return findings


@check(
    check_id="deployment_import_safety",
    name="Deployment import safety",
    category=CheckCategory.DEPLOYMENT_INTEGRITY,
    description="Scans production backend modules for repository-relative `backend.` imports that break the deployed container.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=60.0,
)
def deployment_import_safety() -> CheckResult:
    findings = _scan(BACKEND_ROOT / "app")
    if findings:
        first = findings[0]
        return CheckResult(
            check_id="deployment_import_safety",
            category=CheckCategory.DEPLOYMENT_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message=(
                f"Forbidden production import detected: {first['path']}:{first['line']} "
                f"({first['pattern']})."
            ),
            evidence={"findings": findings[:20], "finding_count": len(findings)},
            failure_category=FailureCategory.APPLICATION_FAILURE,
            expected="package-safe / relative application imports inside backend/app",
            observed=f"{len(findings)} repository-relative import(s) in production modules",
        )
    return CheckResult(
        check_id="deployment_import_safety",
        category=CheckCategory.DEPLOYMENT_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="No repository-relative `backend.` imports exist in production backend modules.",
        evidence={"scanned_root": "backend/app", "finding_count": 0},
    )


@check(
    check_id="test_module_import_safety",
    name="Test module import safety",
    category=CheckCategory.DEPLOYMENT_INTEGRITY,
    description="Advisory scan for test modules that import the application through the repository-level namespace and fail under `cd backend && pytest`.",
    severity=Severity.ADVISORY,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=60.0,
)
def test_module_import_safety() -> CheckResult:
    findings = _scan(BACKEND_ROOT / "tests")
    if findings:
        first = findings[0]
        return CheckResult(
            check_id="test_module_import_safety",
            category=CheckCategory.DEPLOYMENT_INTEGRITY.value,
            status="WARN",
            severity=Severity.ADVISORY,
            message=(
                f"{len(findings)} test module import(s) use the repository-level namespace, which fails when the "
                f"suite runs from the backend directory (first: {first['path']}:{first['line']})."
            ),
            evidence={"findings": findings[:20], "finding_count": len(findings)},
            failure_category=FailureCategory.TEST_FAILURE,
            expected="test modules import the application as `app.*`",
            observed=f"{len(findings)} repository-relative import(s) in test modules",
        )
    return CheckResult(
        check_id="test_module_import_safety",
        category=CheckCategory.DEPLOYMENT_INTEGRITY.value,
        status="PASS",
        severity=Severity.ADVISORY,
        message="Test modules use package-safe application imports.",
        evidence={"scanned_root": "backend/tests", "finding_count": 0},
    )


_PARITY_SCRIPT = """
import json
from app.config import Settings

local = Settings(deployment_mode="local", cors_origins="", trusted_hosts="localhost", api_token="", groq_api_key="")
result = {
    "local_mode_accepts_empty_optional_configuration": local.deployment_mode == "local",
    "api_token_optional": local.api_token == "",
}

production = Settings(
    deployment_mode="production",
    cors_origins="https://example.invalid",
    trusted_hosts="api.example.invalid",
    api_token="",
)
result["production_mode_requires_explicit_origins"] = production.deployment_mode == "production"

try:
    Settings(deployment_mode="production", cors_origins="*", trusted_hosts="api.example.invalid")
    result["production_wildcard_rejected"] = False
except Exception:
    result["production_wildcard_rejected"] = True

try:
    Settings(deployment_mode="production", cors_origins="https://example.invalid", trusted_hosts="*")
    result["production_wildcard_host_rejected"] = False
except Exception:
    result["production_wildcard_host_rejected"] = True

print(json.dumps(result))
"""


@check(
    check_id="environment_parity",
    name="Environment parity and graceful configuration",
    category=CheckCategory.DEPLOYMENT_INTEGRITY,
    description="Confirms local startup works without secrets and that production mode rejects wildcard network configuration.",
    severity=Severity.ADVISORY,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=90.0,
)
def environment_parity() -> CheckResult:
    result = subprocess.run(
        [sys.executable, "-c", _PARITY_SCRIPT],
        cwd=str(app_workdir()),
        env=subprocess_environment(),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        tail = "\n".join((result.stderr or result.stdout).strip().splitlines()[-5:])
        return CheckResult(
            check_id="environment_parity",
            category=CheckCategory.DEPLOYMENT_INTEGRITY.value,
            status="FAIL",
            severity=Severity.ADVISORY,
            message=f"Configuration parity probe failed: {tail}",
            evidence={"stderr_tail": tail},
            failure_category=FailureCategory.ENVIRONMENT_FAILURE,
            expected="settings load in local mode and reject wildcard production configuration",
            observed=tail or "probe failure",
        )
    import json

    payload = json.loads(result.stdout.strip().splitlines()[-1])
    unmet = sorted(key for key, value in payload.items() if value is not True)
    if unmet:
        return CheckResult(
            check_id="environment_parity",
            category=CheckCategory.DEPLOYMENT_INTEGRITY.value,
            status="WARN",
            severity=Severity.ADVISORY,
            message=f"Configuration parity expectations not met: {', '.join(unmet)}.",
            evidence=payload,
            failure_category=FailureCategory.ENVIRONMENT_FAILURE,
            expected="all environment parity expectations satisfied",
            observed=", ".join(unmet),
        )
    return CheckResult(
        check_id="environment_parity",
        category=CheckCategory.DEPLOYMENT_INTEGRITY.value,
        status="PASS",
        severity=Severity.ADVISORY,
        message="Local startup works without secrets and production mode rejects wildcard network configuration.",
        evidence=payload,
    )
