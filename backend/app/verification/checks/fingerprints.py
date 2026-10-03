"""Fingerprint determinism verification.

Every scientific identity in the platform is derived from the single shared
canonical fingerprint implementation.  These checks prove that canonical input
always produces the same fingerprint, that meaningful canonical changes produce
a different fingerprint, and that the result is stable across processes.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime

from ..fixtures import (
    ALTERNATE_SEED,
    canonical_audit_event_fields,
    canonical_circuit_configuration,
    canonical_comparison_index,
    canonical_manifest_payload,
    canonical_pipeline_definition,
    canonical_protocol_definition,
    canonical_quantum_pipeline_definition,
    canonical_scorecard_assessment_fields,
    canonical_subgroup_study_fields,
)
from ..isolation import app_workdir, subprocess_environment
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check
from ._support import require_fingerprint


def _fingerprint_systems() -> list[tuple[str, object]]:
    """(label, callable(canonical) -> fingerprint) for every scientific identity."""
    from app.controlled_comparison.service import _index_fingerprint
    from app.data_quality.service import compute_assessment_fingerprint
    from app.manifests.service import configuration_fingerprint
    from app.pipelines.service import definition_fingerprint as pipeline_fingerprint
    from app.protocols.service import definition_fingerprint as protocol_fingerprint
    from app.quantum.diagnostics import compute_circuit_fingerprint
    from app.subgroups.schemas import SubgroupRule
    from app.subgroups.service import compute_study_fingerprint
    from app.utils.serialization import fingerprint

    def subgroup(definition: dict) -> str:
        return compute_study_fingerprint(
            definition["experiment_id"],
            definition["model_id"],
            definition["dataset_hash"],
            definition["subgroup_field"],
            [SubgroupRule(**rule) for rule in definition["rules"]],
            definition["minimum_n"],
            definition["missing_value_policy"],
            definition["reference_subgroup_id"],
        )

    def scorecard(definition: dict) -> str:
        return compute_assessment_fingerprint(
            definition["dataset_id"],
            definition["dataset_version_id"],
            definition["content_sha256"],
            definition["configuration"],
            definition["context"],
        )

    def audit_event(definition: dict) -> str:
        from app.audit.service import compute_event_fingerprint

        fields = dict(definition)
        fields["occurred_at"] = datetime.fromisoformat(fields["occurred_at"])
        return compute_event_fingerprint(**fields)

    return [
        ("canonical_json", lambda definition: fingerprint(definition)),
        ("reproducibility_manifest", lambda definition: configuration_fingerprint(definition)),
        ("pipeline_definition", lambda definition: pipeline_fingerprint(definition)),
        ("protocol_definition", lambda definition: protocol_fingerprint(definition)),
        ("subgroup_study", subgroup),
        ("dataset_quality_scorecard", scorecard),
        ("scientific_audit_event", audit_event),
        ("quantum_circuit", lambda definition: compute_circuit_fingerprint(definition["model_type"], definition)),
        ("controlled_comparison_index", lambda definition: _index_fingerprint([definition])),
    ]


def _canonical_inputs() -> list[tuple[str, dict, dict]]:
    """(label, canonical input, meaningfully changed input) for each system."""
    pipeline = canonical_pipeline_definition()
    changed_pipeline = canonical_quantum_pipeline_definition()
    protocol = canonical_protocol_definition()
    changed_protocol = canonical_protocol_definition()
    changed_protocol["split_policy"]["test_size"] = 0.4
    subgroup = canonical_subgroup_study_fields()
    changed_subgroup = canonical_subgroup_study_fields()
    changed_subgroup["minimum_n"] = 25
    scorecard = canonical_scorecard_assessment_fields()
    changed_scorecard = canonical_scorecard_assessment_fields()
    changed_scorecard["configuration"] = {"thresholds": {}, "target_column": "other_target"}
    audit = canonical_audit_event_fields()
    changed_audit = canonical_audit_event_fields()
    changed_audit["after_fingerprint"] = "1" * 64
    circuit = canonical_circuit_configuration()
    changed_circuit = canonical_circuit_configuration()
    changed_circuit["reps"] = 3
    comparison = canonical_comparison_index()
    changed_comparison = canonical_comparison_index()
    changed_comparison["split_seed"] = ALTERNATE_SEED
    manifest = canonical_manifest_payload()
    changed_manifest = canonical_manifest_payload()
    changed_manifest["sampling"]["max_samples"] = 64
    return [
        ("canonical_json", manifest, changed_manifest),
        ("reproducibility_manifest", manifest, changed_manifest),
        ("pipeline_definition", pipeline, changed_pipeline),
        ("protocol_definition", protocol, changed_protocol),
        ("subgroup_study", subgroup, changed_subgroup),
        ("dataset_quality_scorecard", scorecard, changed_scorecard),
        ("scientific_audit_event", audit, changed_audit),
        ("quantum_circuit", circuit, changed_circuit),
        ("controlled_comparison_index", comparison, changed_comparison),
    ]


@check(
    check_id="fingerprint_canonicalization",
    name="Fingerprint canonicalization",
    category=CheckCategory.REPRODUCIBILITY,
    description="Verifies that the shared canonical serialization is order-independent, value-sensitive and stable for edge values.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=60.0,
)
def fingerprint_canonicalization() -> CheckResult:
    from app.utils.serialization import canonical_json_bytes, fingerprint

    problems: list[str] = []
    ordered = {"alpha": 1, "beta": [1, 2, 3], "gamma": {"nested": True}}
    reordered = {"gamma": {"nested": True}, "beta": [1, 2, 3], "alpha": 1}
    if fingerprint(ordered) != fingerprint(reordered):
        problems.append("mapping key order changes the fingerprint")

    if fingerprint({"values": [1, 2, 3]}) == fingerprint({"values": [3, 2, 1]}):
        problems.append("sequence order no longer changes the fingerprint")

    if fingerprint({"value": float("nan")}) != fingerprint({"value": None}):
        problems.append("non-finite floats are not canonicalized to null")

    if fingerprint({"value": float("inf")}) != fingerprint({"value": None}):
        problems.append("infinite floats are not canonicalized to null")

    if canonical_json_bytes(ordered) != canonical_json_bytes(reordered):
        problems.append("canonical bytes are not stable for reordered mappings")

    if fingerprint({"a": 1}) == fingerprint({"a": 2}):
        problems.append("different scalar values produce the same fingerprint")

    if problems:
        return CheckResult(
            check_id="fingerprint_canonicalization",
            category=CheckCategory.REPRODUCIBILITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="canonical serialization is order-independent, value-sensitive and finite-safe",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="fingerprint_canonicalization",
        category=CheckCategory.REPRODUCIBILITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Canonical serialization is deterministic, order-independent for mappings and finite-safe.",
        evidence={
            "sample_fingerprint": fingerprint(ordered),
            "key_order_independent": True,
            "sequence_order_sensitive": True,
            "non_finite_normalized": True,
        },
    )


@check(
    check_id="fingerprint_determinism_matrix",
    name="Fingerprint determinism matrix",
    category=CheckCategory.REPRODUCIBILITY,
    description="Recomputes every scientific identity fingerprint twice from canonical fixtures and confirms changes are detected.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=120.0,
)
def fingerprint_determinism_matrix() -> CheckResult:
    systems = dict(_fingerprint_systems())
    results: dict[str, dict] = {}
    problems: list[str] = []
    for label, canonical, changed in _canonical_inputs():
        compute = systems[label]
        first = require_fingerprint(compute(canonical), label=label)
        second = require_fingerprint(compute(canonical), label=label)
        changed_value = compute(changed)
        require_fingerprint(changed_value, label=f"{label} (changed)")
        results[label] = {"fingerprint": first, "deterministic": first == second, "change_detected": changed_value != first}
        if first != second:
            problems.append(f"{label}: repeated computation produced different fingerprints")
        if changed_value == first:
            problems.append(f"{label}: a meaningful canonical change did not change the fingerprint")
    if problems:
        return CheckResult(
            check_id="fingerprint_determinism_matrix",
            category=CheckCategory.REPRODUCIBILITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"systems": results, "problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="same canonical input -> same fingerprint, meaningful change -> different fingerprint",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="fingerprint_determinism_matrix",
        category=CheckCategory.REPRODUCIBILITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Every scientific identity fingerprint is deterministic and sensitive to canonical change.",
        evidence={"system_count": len(results), "systems": results},
    )


_CROSS_PROCESS_SCRIPT = """
import json
from app.verification.checks.fingerprints import fingerprint_determinism_matrix

result = fingerprint_determinism_matrix()
print(json.dumps({entry: payload["fingerprint"] for entry, payload in result.evidence["systems"].items()}))
"""


@check(
    check_id="fingerprint_cross_process_determinism",
    name="Cross-process fingerprint determinism",
    category=CheckCategory.REPRODUCIBILITY,
    description="Recomputes the canonical fixture fingerprints in a fresh interpreter and compares them with the in-process values.",
    severity=Severity.REQUIRED,
    profiles=(FULL_PROFILE,),
    timeout_seconds=180.0,
)
def fingerprint_cross_process_determinism() -> CheckResult:
    in_process = fingerprint_determinism_matrix()
    if in_process.status != "PASS":
        return CheckResult(
            check_id="fingerprint_cross_process_determinism",
            category=CheckCategory.REPRODUCIBILITY.value,
            status="SKIPPED",
            severity=Severity.REQUIRED,
            message="In-process fingerprint determinism failed, so the cross-process comparison was not attempted.",
            evidence={"upstream_check": "fingerprint_determinism_matrix"},
        )
    result = subprocess.run(
        [sys.executable, "-c", _CROSS_PROCESS_SCRIPT],
        cwd=str(app_workdir()),
        env=subprocess_environment(),
        capture_output=True,
        text=True,
        timeout=150,
        check=False,
    )
    if result.returncode != 0:
        tail = "\n".join((result.stderr or result.stdout).strip().splitlines()[-5:])
        return CheckResult(
            check_id="fingerprint_cross_process_determinism",
            category=CheckCategory.REPRODUCIBILITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message=f"Recomputing fixture fingerprints in a fresh interpreter failed: {tail}",
            evidence={"stderr_tail": tail},
            failure_category=FailureCategory.VERIFICATION_INFRASTRUCTURE_FAILURE,
            expected="fresh interpreter recomputes the same fixture fingerprints",
            observed=tail or "subprocess failure",
        )
    fresh = json.loads(result.stdout.strip().splitlines()[-1])
    mismatches = sorted(
        entry
        for entry, value in fresh.items()
        if in_process.evidence["systems"].get(entry, {}).get("fingerprint") != value
    )
    if mismatches:
        return CheckResult(
            check_id="fingerprint_cross_process_determinism",
            category=CheckCategory.REPRODUCIBILITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message=f"Fingerprints differ between processes for: {mismatches}.",
            evidence={"mismatches": mismatches, "fresh": fresh},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="identical fingerprints in a fresh interpreter",
            observed=f"mismatched systems: {mismatches}",
        )
    return CheckResult(
        check_id="fingerprint_cross_process_determinism",
        category=CheckCategory.REPRODUCIBILITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Canonical fixture fingerprints are identical in a fresh interpreter.",
        evidence={"system_count": len(fresh), "fingerprints": fresh},
    )
