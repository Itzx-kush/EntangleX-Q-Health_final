"""Controlled classical-vs-quantum protocol verification (Prompt 10).

The parity engine must verify dataset/version, target, population, split, seed,
preprocessing, representation, threshold and calibration parity from persisted
evidence, must report missing evidence instead of assuming parity, and must
never rank classical against quantum models.
"""

from __future__ import annotations

from ..fixtures import persist_chain, persist_comparison_pair
from ..isolation import initialize_database, session
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check
from ._support import expect_app_error, require_fingerprint, walk_keys

REQUIRED_CONTROLS = (
    "dataset_match",
    "dataset_version_match",
    "dataset_hash_match",
    "target_match",
    "test_population_match",
    "train_partition_match",
    "split_hash_match",
    "sampling_policy_match",
    "seed_policy_match",
    "preprocessing_match",
    "feature_representation_match",
    "threshold_protocol_match",
    "calibration_protocol_match",
    "grouping_match",
)
FORBIDDEN_RANKING_KEYS = {"ranking", "rank", "winner", "best_model", "superiority", "scientific_score", "model_score"}


@check(
    check_id="controlled_comparison_contract",
    name="Controlled comparison contract",
    category=CheckCategory.EXPERIMENT_INTEGRITY,
    description="Parity controls, missing-evidence handling, deterministic protocol fingerprint, idempotent persistence and no ranking.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=300.0,
)
def controlled_comparison_contract() -> CheckResult:
    from app.controlled_comparison.service import (
        CONTROLLED_COMPARISON_SCHEMA_VERSION,
        create_protocol,
        preflight_protocol,
        protocol_payload,
    )
    from app.storage.entities import ControlledComparisonProtocol

    initialize_database()
    problems: list[str] = []
    pair = persist_comparison_pair()

    with session() as scope:
        preflight = preflight_protocol(scope, pair.experiment_id)
    if preflight.get("status") not in {"CONTROLLED", "CONTROLLED_WITH_LIMITATIONS", "INCOMPLETE_EVIDENCE"}:
        problems.append(f"a matched synthetic pair reported status {preflight.get('status')!r}")
    pairs = preflight.get("comparison_pairs") or []
    if len(pairs) != 1:
        problems.append(f"expected exactly one comparison pair, found {len(pairs)}")
    else:
        checks_by_name = {entry["name"]: entry for entry in pairs[0]["control_checks"]}
        missing_controls = sorted(set(REQUIRED_CONTROLS) - set(checks_by_name))
        if missing_controls:
            problems.append(f"parity engine no longer reports these required controls: {missing_controls}")
        for name in REQUIRED_CONTROLS:
            entry = checks_by_name.get(name)
            if entry is None:
                continue
            if entry["status"] not in {"PASS", "FAIL", "UNKNOWN"}:
                problems.append(f"control {name} reported an unknown status {entry['status']!r}")
            if entry["passed"] is None and entry["status"] != "UNKNOWN":
                problems.append(f"control {name} has no evidence but is not reported as UNKNOWN")
            if entry["status"] == "PASS" and entry["passed"] is not True:
                problems.append(f"control {name} is reported as PASS without verified evidence")
        for name in ("dataset_match", "dataset_version_match", "dataset_hash_match", "target_match", "seed_policy_match"):
            entry = checks_by_name.get(name)
            if entry is not None and entry["status"] != "PASS":
                problems.append(f"a matched synthetic pair failed the {name} control")
        if pairs[0].get("quantum_provider_provenance", {}).get("real_hardware"):
            problems.append("the comparison payload claims real quantum hardware execution")

    mismatch = persist_comparison_pair(quantum_target="a_different_target")
    with session() as scope:
        mismatched = preflight_protocol(scope, mismatch.experiment_id)
    mismatched_pairs = mismatched.get("comparison_pairs") or []
    if not mismatched_pairs:
        problems.append("a mismatched pair did not produce any comparison pair")
    else:
        entry = {item["name"]: item for item in mismatched_pairs[0]["control_checks"]}.get("target_match")
        if entry is None or entry["status"] != "FAIL":
            problems.append("a target mismatch between classical and quantum evidence was not reported as a control failure")
        if mismatched.get("status") != "NOT_CONTROLLED":
            problems.append(f"a mismatched pair reported overall status {mismatched.get('status')!r}")

    with session() as scope:
        protocol = create_protocol(scope, pair.experiment_id)
        again = create_protocol(scope, pair.experiment_id)
        protocol_id, protocol_fingerprint = protocol.id, protocol.protocol_fingerprint
        payload = protocol_payload(protocol)
        protocol_count = scope.query(ControlledComparisonProtocol).filter(
            ControlledComparisonProtocol.experiment_id == pair.experiment_id
        ).count()
    require_fingerprint(protocol_fingerprint, label="controlled comparison protocol fingerprint")
    if again.id != protocol_id:
        problems.append("creating the same comparison protocol twice did not reuse the existing protocol")
    if protocol_count != 1:
        problems.append(f"expected exactly one persisted comparison protocol, found {protocol_count}")
    if payload.get("schema_version") != CONTROLLED_COMPARISON_SCHEMA_VERSION:
        problems.append("comparison protocol payload reports an unexpected schema version")
    ranking_keys = sorted(walk_keys(payload) & FORBIDDEN_RANKING_KEYS)
    if ranking_keys:
        problems.append(f"comparison protocol exposes ranking keys: {ranking_keys}")
    limitations = " ".join(payload.get("limitations") or []).lower()
    if "no ranking" not in limitations:
        problems.append("comparison protocol limitations no longer state that no ranking is produced")

    chain = persist_chain()
    with expect_app_error("comparison_pair_unavailable"):
        with session() as scope:
            create_protocol(scope, chain.experiment_id)
    with session() as scope:
        fabricated = scope.query(ControlledComparisonProtocol).filter(
            ControlledComparisonProtocol.experiment_id == chain.experiment_id
        ).count()
    if fabricated:
        problems.append("a comparison protocol was persisted for an experiment without a comparable pair")

    if problems:
        return CheckResult(
            check_id="controlled_comparison_contract",
            category=CheckCategory.EXPERIMENT_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="evidence-backed parity controls with no ranking and no fabricated protocols",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="controlled_comparison_contract",
        category=CheckCategory.EXPERIMENT_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Controlled comparison parity, missing-evidence reporting, idempotency and ranking boundaries hold.",
        evidence={
            "matched_status": preflight.get("status"),
            "mismatched_status": mismatched.get("status"),
            "control_count": len(REQUIRED_CONTROLS),
            "protocol_fingerprint": protocol_fingerprint,
            "ranking_keys_present": False,
        },
    )
