"""Scientific schema contracts.

Structured scientific outputs are compared against the reviewable baseline in
``app/verification/baseline.py``.  A scientific schema version or a canonical
fixture fingerprint can only change when the baseline is updated in the same
pull request, so an invariant is never removed or rewritten silently.
"""

from __future__ import annotations

from ..baseline import BASELINE_EXPECTATIONS, SCHEMA_VERSIONS
from ..isolation import initialize_database
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check


def _live_schema_versions() -> dict[str, str]:
    from app.audit.schemas import EVENT_SCHEMA_VERSION
    from app.controlled_comparison.service import CONTROLLED_COMPARISON_SCHEMA_VERSION
    from app.data_quality.service import SCORECARD_SCHEMA_VERSION
    from app.evidence_packages.service import PACKAGE_SCHEMA_VERSION
    from app.lineage.service import LINEAGE_SCHEMA_VERSION
    from app.manifests.service import MANIFEST_SCHEMA_VERSION
    from app.model_cards.service import MODEL_CARD_SCHEMA_VERSION
    from app.pipelines.service import PIPELINE_SCHEMA_VERSION
    from app.protocols.service import PROTOCOL_SCHEMA_VERSION

    return {
        "research_evidence_package": PACKAGE_SCHEMA_VERSION,
        "deep_experiment_lineage": LINEAGE_SCHEMA_VERSION,
        "pipeline_definition": PIPELINE_SCHEMA_VERSION,
        "protocol_definition": PROTOCOL_SCHEMA_VERSION,
        "scientific_audit_event": EVENT_SCHEMA_VERSION,
        "dataset_quality_scorecard": SCORECARD_SCHEMA_VERSION,
        "model_card": MODEL_CARD_SCHEMA_VERSION,
        "controlled_comparison_protocol": CONTROLLED_COMPARISON_SCHEMA_VERSION,
        "run_manifest": MANIFEST_SCHEMA_VERSION,
        "subgroup_analysis": "subgroup_analysis_v1",
    }


@check(
    check_id="scientific_schema_contracts",
    name="Scientific schema contracts",
    category=CheckCategory.DATA_SCHEMA,
    description="Live scientific schema versions and canonical fixture fingerprints match the reviewed baseline.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=120.0,
)
def scientific_schema_contracts() -> CheckResult:
    initialize_database()
    problems: list[str] = []

    live = _live_schema_versions()
    for name, expected in SCHEMA_VERSIONS.items():
        observed = live.get(name)
        if observed is None:
            problems.append(f"schema contract {name} is no longer exposed by the application")
        elif observed != expected:
            problems.append(
                f"schema version for {name} changed from {expected!r} to {observed!r} without updating the Scientific CI baseline"
            )

    from .fingerprints import _canonical_inputs, _fingerprint_systems

    systems = dict(_fingerprint_systems())
    observed_fingerprints: dict[str, str] = {}
    for label, canonical, _changed in _canonical_inputs():
        observed_fingerprints[label] = systems[label](canonical)
    for label, expected in BASELINE_EXPECTATIONS.items():
        observed = observed_fingerprints.get(label)
        if observed is None:
            problems.append(f"baseline expectation {label} no longer maps to a canonical fixture")
        elif observed != expected:
            problems.append(
                f"canonical fixture fingerprint for {label} changed from {expected} to {observed} "
                "without updating the Scientific CI baseline"
            )

    structured_outputs = _structured_output_contracts()
    for name, missing in structured_outputs.items():
        if missing:
            problems.append(f"structured output {name} no longer exposes: {sorted(missing)}")

    if problems:
        return CheckResult(
            check_id="scientific_schema_contracts",
            category=CheckCategory.DATA_SCHEMA.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="reviewed scientific schema versions and canonical fixture fingerprints",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="scientific_schema_contracts",
        category=CheckCategory.DATA_SCHEMA.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Scientific schema versions, canonical fixture fingerprints and structured output contracts match the baseline.",
        evidence={
            "schema_contract_count": len(SCHEMA_VERSIONS),
            "fingerprint_expectation_count": len(BASELINE_EXPECTATIONS),
            "structured_outputs": sorted(structured_outputs),
        },
    )


def _structured_output_contracts() -> dict[str, set[str]]:
    """Required fields for each structured scientific output."""
    from app.audit.schemas import ScientificAuditEventOut
    from app.data_quality.schemas import DatasetQualityScorecardOut, ScorecardSummary
    from app.lineage.service import lineage_snapshot
    from app.manifests.schemas import RunManifest
    from app.subgroups.schemas import SubgroupStudyOut
    from app.quantum.diagnostics import QuantumDiagnosticPreflightResponse

    from ..fixtures import persist_chain

    chain = persist_chain()
    from ..isolation import session

    with session() as scope:
        snapshot = lineage_snapshot(scope, chain.experiment_id, depth=1)

    contracts: dict[str, set[str]] = {}
    contracts["run_manifest"] = {
        "identity",
        "dataset",
        "sampling",
        "split",
        "preprocessing",
        "models",
        "evaluation_protocol",
        "reproducibility",
    } - set(RunManifest.model_fields)
    contracts["dataset_quality_scorecard"] = {
        "id",
        "dataset_id",
        "status",
        "assessment_fingerprint",
        "summary",
        "domains",
        "schema_snapshot",
    } - set(DatasetQualityScorecardOut.model_fields)
    contracts["dataset_quality_summary"] = {
        "overall_status",
        "total_checks",
        "passed",
        "warnings",
        "failed",
        "not_applicable",
        "unverifiable",
    } - set(ScorecardSummary.model_fields)
    contracts["subgroup_study"] = {
        "id",
        "experiment_id",
        "model_id",
        "status",
        "definition_fingerprint",
        "subgroup_field",
        "overall_population",
        "subgroups_results",
        "comparisons",
        "limitations",
    } - set(SubgroupStudyOut.model_fields)
    contracts["scientific_audit_event"] = {
        "id",
        "event_type",
        "event_category",
        "occurred_at",
        "object_type",
        "object_id",
        "event_fingerprint",
    } - set(ScientificAuditEventOut.model_fields)
    contracts["quantum_diagnostic_preflight"] = {"feasible", "blockers", "warnings", "limitations"} - set(
        QuantumDiagnosticPreflightResponse.model_fields
    )
    contracts["lineage_snapshot"] = {
        "lineage_schema_version",
        "lineage_fingerprint",
        "nodes",
        "edges",
        "integrity",
        "status",
    } - set(snapshot)
    return contracts
