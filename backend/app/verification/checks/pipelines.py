"""Pipeline Version Registry verification (Prompt 14).

Verifies canonicalization, deterministic fingerprints, valid stage ordering,
publish/reuse semantics and reference resolution without training any model.
"""

from __future__ import annotations

from ..fixtures import (
    canonical_pipeline_definition,
    canonical_quantum_pipeline_definition,
    register_fixture_dataset,
)
from ..isolation import initialize_database, session
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check
from ._support import require_fingerprint


@check(
    check_id="pipeline_registry_contract",
    name="Pipeline registry contract",
    category=CheckCategory.PIPELINE_INTEGRITY,
    description="Canonicalization, stage ordering, secret rejection, deterministic fingerprints, publish and reuse semantics.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=180.0,
)
def pipeline_registry_contract() -> CheckResult:
    from app.pipelines.schemas import PipelineCreateRequest, PipelineDefinitionSpec, PipelineStageSpec
    from app.pipelines.service import (
        canonicalize_definition,
        create_pipeline_version,
        definition_fingerprint,
        pipeline_payload,
        preflight_definition,
        publish_pipeline_version,
    )
    from app.storage.entities import PipelineVersion

    initialize_database()
    registered = register_fixture_dataset()
    problems: list[str] = []

    definition = canonical_pipeline_definition(registered.id, registered.current_version_id)
    spec = PipelineDefinitionSpec(**definition)
    canonical = canonicalize_definition(spec)
    orders = [stage["stage_order"] for stage in canonical["stages"]]
    if orders != list(range(1, len(orders) + 1)):
        problems.append(f"canonicalized stage order is not contiguous: {orders}")

    first_fingerprint = require_fingerprint(definition_fingerprint(spec), label="pipeline definition fingerprint")
    if definition_fingerprint(spec) != first_fingerprint:
        problems.append("pipeline definition fingerprint is not deterministic")
    quantum_fingerprint = definition_fingerprint(PipelineDefinitionSpec(**canonical_quantum_pipeline_definition()))
    if quantum_fingerprint == first_fingerprint:
        problems.append("classical and quantum pipeline definitions share a fingerprint")

    try:
        PipelineDefinitionSpec(
            stages=[
                PipelineStageSpec(stage_order=1, stage_type="preprocessing", stage_name="a"),
                PipelineStageSpec(stage_order=3, stage_type="model", stage_name="b"),
            ]
        )
        problems.append("non-contiguous stage ordering was accepted")
    except Exception:
        pass

    try:
        PipelineStageSpec(stage_order=1, stage_type="preprocessing", stage_name="a", configuration={"api_key": "x"})
        problems.append("a stage configuration containing credentials was accepted")
    except Exception:
        pass

    with session() as scope:
        preflight = preflight_definition(scope, spec)
        if not preflight["publishable"]:
            problems.append(f"a canonical pipeline definition is not publishable: {preflight['blockers']}")
        if not preflight["fingerprint_deterministic"]:
            problems.append("preflight reports a non-deterministic fingerprint")
        if preflight["fingerprint"] != first_fingerprint:
            problems.append("preflight fingerprint differs from definition_fingerprint")

        request = PipelineCreateRequest(
            pipeline_name="Synthetic Scientific CI pipeline",
            description="Synthetic pipeline fixture; not a research claim.",
            source_context="scientific_ci",
            definition=spec,
        )
        version, created = create_pipeline_version(scope, request)
        reused, created_again = create_pipeline_version(scope, request)
        if not created:
            problems.append("the first pipeline version creation reported reuse")
        if created_again or reused.id != version.id:
            problems.append("an equivalent pipeline definition did not reuse the existing version")
        published = publish_pipeline_version(scope, version.id)
        payload = pipeline_payload(scope, scope.get(PipelineVersion, version.id))
        if published.status not in {"PUBLISHED", "ACTIVE"}:
            problems.append(f"publish did not move the version out of DRAFT (status={published.status})")
        payload_fingerprint = payload.get("definition_fingerprint") or payload.get("fingerprint")
        if payload_fingerprint != first_fingerprint:
            problems.append("published pipeline payload exposes a different definition fingerprint")
        stage_types = {stage["stage_type"] for stage in payload["stages"]}

    if problems:
        return CheckResult(
            check_id="pipeline_registry_contract",
            category=CheckCategory.PIPELINE_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="deterministic canonical pipeline definitions with valid ordering, reuse and publish semantics",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="pipeline_registry_contract",
        category=CheckCategory.PIPELINE_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Pipeline definitions canonicalize deterministically and publish/reuse semantics hold.",
        evidence={
            "definition_fingerprint": first_fingerprint,
            "stage_types": sorted(stage_types),
            "published_status": published.status,
            "quantum_fingerprint_distinct": True,
            "invalid_definitions_rejected": ["non_contiguous_stage_order", "credential_configuration"],
        },
    )
