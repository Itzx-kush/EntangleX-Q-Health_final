"""Data privacy and secret-safety verification.

Scientific CI must not require real secrets, must not commit credentials and must
never emit patient-level or raw record payloads.  These checks are deliberately
narrow and purposeful rather than a generic string scanner.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..fixtures import persist_chain
from ..isolation import BACKEND_ROOT, REPO_ROOT, initialize_database, session
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check
from ._support import flatten_strings, sensitive_keys_present

SKIP_DIRECTORIES = {".git", "node_modules", ".venv", "dist", "build", "__pycache__", ".pytest_cache"}
SECRET_PATTERNS = {
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private_key_block": re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    "slack_token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    "openai_key": re.compile(r"sk-[A-Za-z0-9]{32,}"),
}
SCAN_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml", ".toml", ".env", ".md", ".cfg", ".ini"}


def _iter_repository_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRECTORIES for part in path.relative_to(REPO_ROOT).parts):
            continue
        if path.suffix in SCAN_SUFFIXES or path.name.startswith(".env"):
            files.append(path)
    return files


@check(
    check_id="privacy_and_secret_safety",
    name="Privacy and secret safety",
    category=CheckCategory.DATA_SCHEMA,
    description="No committed secrets or .env files, no patient-level payloads in generated research artefacts, and synthetic-only fixtures.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=180.0,
)
def privacy_and_secret_safety() -> CheckResult:
    from app.evidence_packages.service import preflight_package
    from app.lineage.service import lineage_snapshot
    from app.model_cards.service import assemble_card

    initialize_database()
    problems: list[str] = []
    findings: list[dict] = []

    for path in _iter_repository_files():
        if path.name == ".env":
            findings.append({"path": str(path.relative_to(REPO_ROOT)), "pattern": "committed_env_file"})
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append({"path": str(path.relative_to(REPO_ROOT)), "pattern": name})
    if findings:
        problems.append(f"potential committed secrets detected: {findings[:5]}")

    chain = persist_chain(with_pipeline=True, with_protocol=True)
    with session() as scope:
        evidence = preflight_package(scope, chain.experiment_id)
        lineage = lineage_snapshot(scope, chain.experiment_id, depth="all")
        card, _source, _payload = assemble_card(scope, chain.model_id)

    for label, payload in (("evidence manifest", evidence), ("lineage snapshot", lineage), ("model card", card)):
        keys = sensitive_keys_present(payload)
        if keys:
            problems.append(f"the {label} exposes prohibited keys: {keys}")
        text = flatten_strings(payload).lower()
        for forbidden in ("patient_id", "patient_identifier", "mrn", "ssn", "raw_patient_rows"):
            if forbidden in text:
                problems.append(f"the {label} contains the patient-level term {forbidden!r}")

    fixtures_text = (BACKEND_ROOT / "app" / "verification" / "fixtures.py").read_text(encoding="utf-8")
    for forbidden in ("read_csv(", "read_excel(", "open("):
        if forbidden in fixtures_text:
            problems.append(f"the verification fixtures read external data via {forbidden!r}")
    if "synthetic" not in fixtures_text.lower():
        problems.append("the verification fixtures no longer declare their synthetic scope")

    data_files = [
        path
        for path in (REPO_ROOT / "data").rglob("*")
        if path.is_file() and path.suffix.lower() in {".csv", ".tsv", ".xlsx", ".parquet"}
    ]
    if data_files:
        problems.append(f"record-like data files are committed under data/: {[str(p.name) for p in data_files[:5]]}")

    if problems:
        return CheckResult(
            check_id="privacy_and_secret_safety",
            category=CheckCategory.DATA_SCHEMA.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems, "findings": findings[:10]},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="no committed secrets and no patient-level payloads in generated research artefacts",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="privacy_and_secret_safety",
        category=CheckCategory.DATA_SCHEMA.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="No committed secrets, no .env file, synthetic-only fixtures and no patient-level payloads in generated artefacts.",
        evidence={
            "scanned_file_count": len(_iter_repository_files()),
            "secret_patterns_checked": sorted(SECRET_PATTERNS),
            "artifacts_checked": ["evidence manifest", "lineage snapshot", "model card"],
            "committed_record_files": 0,
        },
    )
