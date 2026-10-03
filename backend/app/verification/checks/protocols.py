"""Experiment Protocol verification (Prompt 15).

Verifies protocol definition validity, deterministic fingerprints, template
instantiation, experiment attachment and deterministic compliance output.
Protocol compliance is a factual rule check; it is never reported as scientific
validity.
"""

from __future__ import annotations

from ..fixtures import canonical_protocol_definition, persist_chain, register_fixture_dataset
from ..isolation import initialize_database, session
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check
from ._support import expect_app_error, require_fingerprint


@check(
    check_id="protocol_registry_contract",
    name="Protocol registry contract",
    category=CheckCategory.PROTOCOL_INTEGRITY,
    description="Canonicalization, deterministic fingerprints, template instantiation and publish semantics.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=180.0,
)
def protocol_registry_contract() -> CheckResult:
    from app.protocols.schemas import ProtocolCreateRequest, ProtocolDefinitionSpec, TemplateInstantiateRequest
    from app.protocols.service import (
        canonicalize_definition,
        create_protocol_version,
        definition_fingerprint,
        instantiate_protocol_template,
        list_protocol_templates,
        preflight_definition,
        protocol_payload,
        publish_protocol_version,
    )
    from app.storage.entities import ExperimentProtocolVersion

    initialize_database()
    registered = register_fixture_dataset()
    problems: list[str] = []

    spec = ProtocolDefinitionSpec(**canonical_protocol_definition(registered.id))
    canonical = canonicalize_definition(spec)
    if canonical != canonicalize_definition(canonical):
        problems.append("protocol canonicalization is not stable across repeated canonicalization")
    fingerprint = require_fingerprint(definition_fingerprint(spec), label="protocol definition fingerprint")
    if definition_fingerprint(spec) != fingerprint:
        problems.append("protocol definition fingerprint is not deterministic")

    with session() as scope:
        preflight = preflight_definition(scope, spec)
        if not preflight["publishable"]:
            problems.append(f"a canonical protocol definition is not publishable: {preflight['blockers']}")
        request = ProtocolCreateRequest(
            protocol_name="Synthetic Scientific CI protocol",
            description="Synthetic protocol fixture; not a research claim.",
            source_context="scientific_ci",
            definition=spec,
        )
        version, created = create_protocol_version(scope, request)
        reused, created_again = create_protocol_version(scope, request)
        if not created or created_again or reused.id != version.id:
            problems.append("equivalent protocol definitions did not reuse the existing version")
        publish_protocol_version(scope, version.id)
        payload = protocol_payload(scope, scope.get(ExperimentProtocolVersion, version.id))
        if payload.get("definition_fingerprint") != fingerprint:
            problems.append("published protocol payload exposes a different definition fingerprint")

        templates = list_protocol_templates(scope)
        if not templates:
            problems.append("no built-in protocol templates are registered")
        else:
            template = templates[0]
            instantiated, instantiated_created = instantiate_protocol_template(
                scope,
                template["id"],
                TemplateInstantiateRequest(
                    protocol_name="Synthetic template instance",
                    description="Synthetic template instantiation.",
                    parameters={"test_size": 0.3},
                    source_context="scientific_ci",
                ),
            )
            if not instantiated_created:
                problems.append("template instantiation did not create a new protocol version")
            if not instantiated.definition_fingerprint or len(instantiated.definition_fingerprint) != 64:
                problems.append("template instantiation did not produce a definition fingerprint")

    if problems:
        return CheckResult(
            check_id="protocol_registry_contract",
            category=CheckCategory.PROTOCOL_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="deterministic protocol canonicalization, fingerprints, templates and publish semantics",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="protocol_registry_contract",
        category=CheckCategory.PROTOCOL_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Protocol definitions canonicalize deterministically and templates instantiate new immutable versions.",
        evidence={
            "definition_fingerprint": fingerprint,
            "template_count": len(templates),
            "template_instantiation": "created_new_version",
        },
    )


@check(
    check_id="protocol_attachment_and_compliance",
    name="Protocol attachment and compliance engine",
    category=CheckCategory.PROTOCOL_INTEGRITY,
    description="Attaches a protocol to a synthetic experiment, resolves the reference and verifies deterministic compliance output.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=180.0,
)
def protocol_attachment_and_compliance() -> CheckResult:
    from app.protocols.compliance import evaluate_experiment_compliance
    from app.protocols.service import attach_protocol_to_experiment, create_protocol_version, publish_protocol_version
    from app.protocols.schemas import ProtocolCreateRequest, ProtocolDefinitionSpec
    from app.storage.entities import Experiment

    initialize_database()
    chain = persist_chain()
    problems: list[str] = []

    with session() as scope:
        version, _ = create_protocol_version(
            scope,
            ProtocolCreateRequest(
                protocol_name="Synthetic attachment protocol",
                description="Synthetic protocol fixture.",
                source_context="scientific_ci",
                definition=ProtocolDefinitionSpec(**canonical_protocol_definition(chain.dataset_id)),
            ),
        )
        published = publish_protocol_version(scope, version.id)
        attach_protocol_to_experiment(scope, chain.experiment_id, published.id)
        experiment = scope.get(Experiment, chain.experiment_id)
        if experiment.protocol_version_id != published.id:
            problems.append("attaching a protocol did not record the protocol version reference")
        if not experiment.protocol_fingerprint:
            problems.append("attaching a protocol did not record the protocol fingerprint")

    with session() as scope:
        first = evaluate_experiment_compliance(scope, chain.experiment_id)
    with session() as scope:
        second = evaluate_experiment_compliance(scope, chain.experiment_id)

    if first != second:
        problems.append("compliance output is not deterministic for unchanged experiment state")
    if first.get("status") != "AVAILABLE":
        problems.append(f"compliance engine did not report AVAILABLE (status={first.get('status')})")
    summary = first.get("compliance_summary") or {}
    if summary.get("total_checks", 0) != len(first.get("checks") or []):
        problems.append("compliance summary counts do not match the emitted checks")
    for entry in first.get("checks") or []:
        if entry.get("status") not in {"MATCHED", "MISSING", "MISMATCHED", "NOT_APPLICABLE", "UNVERIFIABLE"}:
            problems.append(f"compliance check {entry.get('rule')} reported an unknown status")
    interpretation = (first.get("interpretation") or "").lower()
    if "does not establish scientific validity" not in interpretation:
        problems.append("compliance output no longer states that it does not establish scientific validity")

    with expect_app_error("protocol_already_attached"):
        with session() as scope:
            conflicting = canonical_protocol_definition(chain.dataset_id)
            conflicting["split_policy"]["test_size"] = 0.35
            other, _ = create_protocol_version(
                scope,
                ProtocolCreateRequest(
                    protocol_name="Synthetic conflicting protocol",
                    description="Synthetic protocol fixture.",
                    source_context="scientific_ci",
                    definition=ProtocolDefinitionSpec(**conflicting),
                ),
            )
            publish_protocol_version(scope, other.id)
            attach_protocol_to_experiment(scope, chain.experiment_id, other.id)

    if problems:
        return CheckResult(
            check_id="protocol_attachment_and_compliance",
            category=CheckCategory.PROTOCOL_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="protocol references resolve and compliance output is deterministic and factual",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="protocol_attachment_and_compliance",
        category=CheckCategory.PROTOCOL_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Protocol references resolve, conflicting attachment is rejected and compliance output is deterministic.",
        evidence={
            "experiment_id": chain.experiment_id,
            "compliance_summary": summary,
            "deterministic": True,
        },
    )
