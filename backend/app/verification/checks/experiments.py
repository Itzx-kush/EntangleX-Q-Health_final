"""Experiment and run integrity verification.

Persisted experiments must resolve their dataset, version, pipeline, protocol and
lineage references when those references exist, while legitimate legacy records
that predate the newer registries must remain loadable and must not have
historical state fabricated for them.
"""

from __future__ import annotations

from ..fixtures import persist_chain
from ..isolation import initialize_database, session
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check


@check(
    check_id="experiment_integrity",
    name="Experiment and run integrity",
    category=CheckCategory.EXPERIMENT_INTEGRITY,
    description="Every persisted reference on a synthetic experiment chain resolves, and a legacy record without newer references is tolerated.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=180.0,
)
def experiment_integrity() -> CheckResult:
    from app.storage.entities import Dataset, DatasetVersion, Experiment, ModelRecord, Run

    initialize_database()
    chain = persist_chain(with_pipeline=True, with_protocol=True)
    legacy = persist_chain(legacy=True)
    problems: list[str] = []
    unresolved: list[dict] = []

    with session() as scope:
        experiment = scope.get(Experiment, chain.experiment_id)
        run = scope.get(Run, chain.run_id)
        model = scope.get(ModelRecord, chain.model_id)
        if experiment is None or run is None or model is None:
            problems.append("the synthetic experiment chain did not persist")
        else:
            if scope.get(Dataset, experiment.dataset_id) is None:
                unresolved.append({"field": "experiment.dataset_id", "value": experiment.dataset_id})
            if run.dataset_version_id and scope.get(DatasetVersion, run.dataset_version_id) is None:
                unresolved.append({"field": "run.dataset_version_id", "value": run.dataset_version_id})
            if experiment.pipeline_version_id and scope.get(
                __import__("app.storage.entities", fromlist=["PipelineVersion"]).PipelineVersion,
                experiment.pipeline_version_id,
            ) is None:
                unresolved.append({"field": "experiment.pipeline_version_id", "value": experiment.pipeline_version_id})
            if experiment.protocol_version_id and scope.get(
                __import__("app.storage.entities", fromlist=["ExperimentProtocolVersion"]).ExperimentProtocolVersion,
                experiment.protocol_version_id,
            ) is None:
                unresolved.append({"field": "experiment.protocol_version_id", "value": experiment.protocol_version_id})
            if run.experiment_id != experiment.id or model.experiment_id != experiment.id:
                problems.append("run or model is not linked to the experiment it was created for")
            if model.run_id != run.id:
                problems.append("the model record does not reference its run")
            if not experiment.pipeline_version_id or not experiment.protocol_version_id:
                problems.append("a current experiment did not record its pipeline and protocol references")

        legacy_experiment = scope.get(Experiment, legacy.experiment_id)
        legacy_model = scope.get(ModelRecord, legacy.model_id)
        if legacy_experiment is None or legacy_model is None:
            problems.append("a legacy experiment could not be loaded")
        else:
            if legacy_experiment.pipeline_version_id is not None:
                problems.append("a pipeline version was fabricated for a legacy experiment")
            if legacy_experiment.protocol_version_id is not None:
                problems.append("a protocol version was fabricated for a legacy experiment")

    if unresolved:
        return CheckResult(
            check_id="experiment_integrity",
            category=CheckCategory.EXPERIMENT_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message=f"{len(unresolved)} persisted experiment reference(s) do not resolve.",
            evidence={"unresolved": unresolved},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="every persisted reference resolves to an existing record",
            observed=f"unresolved references: {unresolved[:5]}",
        )
    if problems:
        return CheckResult(
            check_id="experiment_integrity",
            category=CheckCategory.EXPERIMENT_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="current experiments carry resolvable references and legacy records stay loadable",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="experiment_integrity",
        category=CheckCategory.EXPERIMENT_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Experiment, run, model and registry references resolve; legacy records load without fabricated provenance.",
        evidence={
            "experiment_id": chain.experiment_id,
            "resolved_references": [
                "dataset",
                "dataset_version",
                "pipeline_version",
                "protocol_version",
                "run",
                "model",
            ],
            "legacy_experiment_id": legacy.experiment_id,
        },
    )


@check(
    check_id="legacy_compatibility",
    name="Legacy compatibility",
    category=CheckCategory.EXPERIMENT_INTEGRITY,
    description="A legacy experiment without pipeline/protocol references still loads through the evidence, lineage and model-card layers without inventing historical state.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=180.0,
)
def legacy_compatibility() -> CheckResult:
    from app.evidence_packages.service import preflight_package
    from app.lineage.service import lineage_snapshot
    from app.model_cards.service import assemble_card

    initialize_database()
    legacy = persist_chain(legacy=True)
    problems: list[str] = []

    with session() as scope:
        preflight = preflight_package(scope, legacy.experiment_id)
        snapshot = lineage_snapshot(scope, legacy.experiment_id, depth="all")
        card, _source, _artifact = assemble_card(scope, legacy.model_id)

    if not preflight.get("feasible"):
        problems.append("the evidence preflight rejected a legacy experiment outright")
    pipeline_reference = (preflight.get("manifest") or {}).get("pipeline")
    if pipeline_reference and pipeline_reference.get("pipeline_version_id"):
        problems.append("the evidence preflight invented a pipeline reference for a legacy experiment")
    if snapshot.get("status") not in {"COMPLETE", "PARTIAL", "AVAILABLE", "INTEGRITY_REVIEW", "UNVERIFIABLE"}:
        problems.append(f"the lineage snapshot reported an unexpected status for legacy data: {snapshot.get('status')}")
    if card.get("card_status") not in {"INCOMPLETE_EVIDENCE", "COMPLETE_WITH_LIMITATIONS", "COMPLETE"}:
        problems.append(f"the model card reported an unexpected status for legacy data: {card.get('card_status')}")
    if card.get("model_identity", {}).get("run_id") in (None, ""):
        problems.append("the model card did not report the run identity field at all")

    if problems:
        return CheckResult(
            check_id="legacy_compatibility",
            category=CheckCategory.EXPERIMENT_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="legacy records remain loadable and no historical reference is fabricated",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="legacy_compatibility",
        category=CheckCategory.EXPERIMENT_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Legacy experiments remain loadable across evidence, lineage and model-card layers without fabricated references.",
        evidence={
            "legacy_experiment_id": legacy.experiment_id,
            "evidence_status": preflight.get("package_status"),
            "lineage_status": snapshot.get("status"),
            "card_status": card.get("card_status"),
        },
    )
