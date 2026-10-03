"""Import and startup verification.

Deployment-breaking import mistakes must be caught before merge, so these
checks import the application the same way the deployed container does: from
the backend working directory, with the backend directory on ``sys.path``, and
with an isolated storage root and no production secrets.
"""

from __future__ import annotations

import json
import subprocess
import sys

from ..isolation import app_workdir, subprocess_environment
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check

_IMPORT_SCRIPT = """
import json
from app.main import app, api

# Route enumeration goes through the OpenAPI document because FastAPI keeps
# included routers as lazy placeholders on `app.routes`.
paths = set(app.openapi()["paths"])
api_paths = {path for path in paths if path.startswith("/api/")}
assert len(api_paths) >= 30, sorted(api_paths)
assert "/api/health" in paths, "health endpoint missing"
assert api is not None
print(json.dumps({
    "title": app.title,
    "version": app.version,
    "route_count": len(paths),
    "api_route_count": len(api_paths),
    "has_health_endpoint": "/api/health" in paths,
}))
"""

_STARTUP_SCRIPT = """
import json
from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    response = client.get("/api/health")
    payload = response.json()
    assert response.status_code == 200, response.status_code
    assert payload["status"] == "ok", payload
    summary = client.get("/api/system/status")
    assert summary.status_code == 200, summary.status_code
    print(json.dumps({
        "health_status": payload["status"],
        "health_version": payload["version"],
        "authentication_required": payload["authentication_required"],
        "system_status": summary.json()["status"],
    }))
"""


def _run_script(script: str, *, timeout: int) -> tuple[subprocess.CompletedProcess[str], dict]:
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(app_workdir()),
        env=subprocess_environment(),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    payload: dict = {}
    if result.returncode == 0:
        payload = json.loads(result.stdout.strip().splitlines()[-1])
    return result, payload


@check(
    check_id="application_import",
    name="Application import",
    category=CheckCategory.IMPORT_STARTUP,
    description="Imports app.main from the deployment working directory and confirms the API router is constructed.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=180.0,
)
def application_import() -> CheckResult:
    result, payload = _run_script(_IMPORT_SCRIPT, timeout=150)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        tail = "\n".join(detail[-6:])
        return CheckResult(
            check_id="application_import",
            category=CheckCategory.IMPORT_STARTUP.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message=f"`from app.main import app, api` failed in the backend working directory. {tail}",
            evidence={"returncode": result.returncode, "stderr_tail": tail},
            failure_category=FailureCategory.APPLICATION_FAILURE,
            expected="package-safe imports resolved from the backend working directory",
            observed=tail or "import failure",
        )
    if not payload.get("has_health_endpoint"):
        return CheckResult(
            check_id="application_import",
            category=CheckCategory.IMPORT_STARTUP.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="The application imported but does not expose the documented /api/health endpoint.",
            evidence=payload,
            failure_category=FailureCategory.APPLICATION_FAILURE,
            expected="/api/health route registered",
            observed=", ".join(sorted(str(key) for key in payload)),
        )
    return CheckResult(
        check_id="application_import",
        category=CheckCategory.IMPORT_STARTUP.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Application imports from the deployment working directory and exposes the API router.",
        evidence=payload,
    )


@check(
    check_id="application_startup_lifespan",
    name="Application startup and health endpoint",
    category=CheckCategory.IMPORT_STARTUP,
    description="Runs the real lifespan (schema initialization, demo artifacts, job manager) against isolated storage and calls the health endpoint.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=240.0,
)
def application_startup_lifespan() -> CheckResult:
    result, payload = _run_script(_STARTUP_SCRIPT, timeout=210)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        tail = "\n".join(detail[-6:])
        return CheckResult(
            check_id="application_startup_lifespan",
            category=CheckCategory.IMPORT_STARTUP.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message=f"Application startup or the health endpoint failed. {tail}",
            evidence={"returncode": result.returncode, "stderr_tail": tail},
            failure_category=FailureCategory.APPLICATION_FAILURE,
            expected="lifespan completes and /api/health returns status ok without production secrets",
            observed=tail or "startup failure",
        )
    return CheckResult(
        check_id="application_startup_lifespan",
        category=CheckCategory.IMPORT_STARTUP.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Application startup completed and the health endpoint responded without production secrets.",
        evidence=payload,
    )
