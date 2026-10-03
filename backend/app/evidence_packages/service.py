from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from ..artifacts.service import register_metadata
from ..demo_readiness import ARTIFACT_VERSION, READY_DEMO_DATASETS, validate_packaged_dataset
from ..storage.entities import (
    AblationStudy,
    Artifact,
    CalibrationStudy,
    ControlledComparisonProtocol,
    Dataset,
    DatasetVersion,
    DistributionShiftAnalysis,
    Experiment,
    ExplanationRecord,
    ExternalValidation,
    ModelRecord,
    MultiSeedStudy,
    QuantumDiagnosticReport,
    ResearchEvidencePackage,
    RobustnessRecord,
    Run,
    ThresholdAnalysisStudy,
)
from ..storage.repository import require
from ..utils.errors import AppError
from ..utils.serialization import clean_json, fingerprint

PACKAGE_SCHEMA_VERSION = "research_evidence_package_v1"
PACKAGE_ARTIFACT_TYPE = "research_evidence_package"
QUANTUM_MODELS = {"vqc", "qsvc", "qnn", "hybrid_pennylane_torch"}
COMPLETE_STATES = {"completed", "complete", "ready", "succeeded", "success"}
METRICS = {
    "accuracy", "balanced_accuracy", "sensitivity", "specificity", "precision",
    "recall", "f1", "roc_auc", "pr_auc", "brier_score", "log_loss", "mcc",
    "true_positive", "true_negative", "false_positive", "false_negative",
    "confusion_matrix", "sample_count", "undefined_metrics",
}
TIMING = {
    "final_training_seconds", "cv_total_seconds", "cv_fold_seconds",
    "test_inference_seconds", "test_inference_seconds_per_sample",
}
OPERATING_POINT = {
    "selection_strategy", "selected_threshold", "threshold_feasible",
    "threshold_source", "number_of_oof_samples", "cv_fold_count",
}


def _time(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _record_time(record: Any) -> str | None:
    return _time(
        getattr(record, "completed_at", None)
        or getattr(record, "updated_at", None)
        or getattr(record, "created_at", None)
    )


def _artifact_ids(records: Iterable[Any], field: str = "artifact_id") -> list[str]:
    return sorted({value for record in records if (value := getattr(record, field, None))})


def _fingerprints(records: Iterable[Any]) -> list[str]:
    values: set[str] = set()
    for record in records:
        for field in ("configuration_fingerprint", "protocol_fingerprint"):
            value = getattr(record, field, None)
            if value:
                values.add(value)
        provenance = getattr(record, "provenance", None) or {}
        for field in ("configuration_fingerprint", "comparison_fingerprint"):
            value = provenance.get(field)
            if value:
                values.add(value)
    return sorted(values)


def _category(
    records: list[Any],
    *,
    artifact_field: str = "artifact_id",
    not_applicable: bool = False,
    limitations: list[str] | None = None,
) -> dict:
    if not_applicable:
        return {
            "status": "not_applicable", "record_count": 0, "referenced_ids": [],
            "artifact_ids": [], "latest_compatible_evidence": None,
            "configuration_fingerprints": [], "evidence_timestamp": None,
            "limitations": limitations or [], "availability_reason": "not applicable to the persisted model families",
        }
    if not records:
        return {
            "status": "not_available", "record_count": 0, "referenced_ids": [],
            "artifact_ids": [], "latest_compatible_evidence": None,
            "configuration_fingerprints": [], "evidence_timestamp": None,
            "limitations": limitations or [], "availability_reason": "no compatible persisted evidence record exists",
        }
    ordered = sorted(records, key=lambda value: _record_time(value) or "")
    complete = [
        record for record in ordered
        if not hasattr(record, "status")
        or str(getattr(record, "status", "")).lower() in COMPLETE_STATES
    ]
    status = "available" if len(complete) == len(records) else "limited"
    merged_limitations = list(limitations or [])
    for record in ordered:
        merged_limitations.extend(getattr(record, "limitations", None) or [])
    return {
        "status": status,
        "record_count": len(records),
        "referenced_ids": sorted(record.id for record in records),
        "artifact_ids": _artifact_ids(records, artifact_field),
        "latest_compatible_evidence": ordered[-1].id,
        "configuration_fingerprints": _fingerprints(records),
        "evidence_timestamp": _record_time(ordered[-1]),
        "limitations": sorted({str(value) for value in merged_limitations}),
        "availability_reason": "compatible persisted evidence is referenced",
    }


def _verified_context(experiment: Experiment, models: list[ModelRecord]) -> dict | None:
    if not any((model.details or {}).get("experiment_kind") == "precomputed_verified_demo" for model in models):
        return None
    for slug in READY_DEMO_DATASETS:
        checked = validate_packaged_dataset(slug)
        if checked["experiment"]["id"] == experiment.id:
            return {
                "type": "verified_demo_experiment",
                "precomputed": True,
                "slug": slug,
                "artifact_version": ARTIFACT_VERSION,
                "manifest_sha256": checked["manifest_sha256"],
                "dataset_hash": checked["dataset"].get("sha256"),
                "verified_model_artifact_hashes": sorted(
                    model.get("artifact_sha256") for model in checked["models"] if model.get("artifact_sha256")
                ),
            }
    # Legacy verified-demo rows can predate installation of the bundled manifest.
    return {
        "type": "verified_demo_experiment",
        "precomputed": True,
        "artifact_version": (experiment.summary or {}).get("artifact_version"),
        "manifest_sha256": (experiment.summary or {}).get("manifest_sha256"),
        "dataset_hash": None,
        "verified_model_artifact_hashes": sorted(
            model.artifact_sha256 for model in models if model.artifact_sha256
        ),
    }


def _evaluation(models: list[ModelRecord]) -> dict:
    rows = []
    for model in models:
        test = (model.metrics or {}).get("test")
        if not isinstance(test, dict) or not test:
            continue
        timing = (model.metrics or {}).get("timing") or {}
        operating = (model.metrics or {}).get("operating_point") or (model.details or {}).get("operating_point") or {}
        rows.append({
            "model_id": model.id,
            "metrics": clean_json({key: test[key] for key in sorted(METRICS) if key in test}),
            "metric_availability": sorted(key for key in METRICS if key in test),
            "undefined_metrics": clean_json(test.get("undefined_metrics", [])),
            "evaluation_sample_count": test.get("sample_count"),
            "operating_point": clean_json({key: operating[key] for key in sorted(OPERATING_POINT) if key in operating}),
            "timing": clean_json({key: timing[key] for key in sorted(TIMING) if key in timing}),
        })
    status = "available" if rows and len(rows) == len(models) else ("incomplete" if rows else "not_available")
    return {
        "status": status, "record_count": len(rows),
        "referenced_ids": sorted(row["model_id"] for row in rows), "artifact_ids": [],
        "latest_compatible_evidence": rows[-1]["model_id"] if rows else None,
        "configuration_fingerprints": [], "evidence_timestamp": None,
        "limitations": [], "availability_reason": (
            "persisted held-out evaluation metrics are referenced"
            if rows else "no persisted held-out evaluation metrics exist"
        ),
        "evaluations": rows,
    }


def _model_cards(artifacts: list[Artifact], model_ids: set[str]) -> dict:
    records = [
        artifact for artifact in artifacts
        if artifact.artifact_type == "model_card" and artifact.model_id in model_ids
    ]
    result = _category(records, artifact_field="id")
    result["cards"] = [{
        "model_id": artifact.model_id,
        "artifact_id": artifact.id,
        "schema_version": (artifact.details or {}).get("schema_version"),
        "card_status": (artifact.details or {}).get("card_status"),
        "integrity_hash": artifact.integrity_hash,
    } for artifact in sorted(records, key=lambda item: item.id)]
    return result


def _group_validation(experiment: Experiment, models: list[ModelRecord]) -> dict:
    referenced = [
        model.id for model in models
        if (model.details or {}).get("group_validation") or (model.metrics or {}).get("group_validation")
    ]
    if not referenced and (experiment.summary or {}).get("group_validation"):
        referenced = [experiment.id]
    if not referenced:
        return _category([])
    return {
        **_category([]),
        "status": "available", "record_count": len(referenced),
        "referenced_ids": sorted(referenced),
        "latest_compatible_evidence": sorted(referenced)[-1],
        "availability_reason": "persisted group-aware validation metadata is referenced",
    }


def _load_evidence(session, experiment: Experiment) -> dict:
    models = list(session.scalars(
        select(ModelRecord).where(ModelRecord.experiment_id == experiment.id).order_by(ModelRecord.id)
    ))
    model_ids = {model.id for model in models}
    runs = list(session.scalars(
        select(Run).where(Run.experiment_id == experiment.id).order_by(Run.created_at, Run.id)
    ))
    artifacts = list(session.scalars(
        select(Artifact).where(Artifact.experiment_id == experiment.id).order_by(Artifact.id)
    ))
    multi_seed = list(session.scalars(select(MultiSeedStudy).where(MultiSeedStudy.base_experiment_id == experiment.id)))
    external = list(session.scalars(select(ExternalValidation).where(ExternalValidation.experiment_id == experiment.id)))
    external_ids = {record.id for record in external}
    shift = list(session.scalars(select(DistributionShiftAnalysis).where(
        (DistributionShiftAnalysis.model_id.in_(model_ids) if model_ids else False)
        | (DistributionShiftAnalysis.external_validation_id.in_(external_ids) if external_ids else False)
    )))
    calibration = list(session.scalars(select(CalibrationStudy).where(
        CalibrationStudy.model_id.in_(model_ids) if model_ids else False
    )))
    threshold = list(session.scalars(select(ThresholdAnalysisStudy).where(
        ThresholdAnalysisStudy.model_id.in_(model_ids) if model_ids else False
    )))
    robustness = list(session.scalars(select(RobustnessRecord).where(RobustnessRecord.experiment_id == experiment.id)))
    ablation = list(session.scalars(select(AblationStudy).where(AblationStudy.base_experiment_id == experiment.id)))
    diagnostics = list(session.scalars(select(QuantumDiagnosticReport).where(
        QuantumDiagnosticReport.experiment_id == experiment.id
    )))
    protocols = list(session.scalars(select(ControlledComparisonProtocol).where(
        ControlledComparisonProtocol.experiment_id == experiment.id
    )))
    explanations = list(session.scalars(select(ExplanationRecord).where(
        ExplanationRecord.model_id.in_(model_ids) if model_ids else False
    )))
    return {
        "models": models, "runs": runs, "artifacts": artifacts,
        "multi_seed": multi_seed, "external_validation": external,
        "distribution_shift": shift, "calibration": calibration,
        "threshold": threshold, "robustness": robustness, "ablation": ablation,
        "quantum_diagnostics": diagnostics, "controlled_comparison": protocols,
        "explainability": explanations,
    }


def _validate(
    session,
    experiment: Experiment,
    dataset: Dataset,
    version: DatasetVersion | None,
    evidence: dict,
    source_context: dict,
) -> tuple[list[dict], list[dict]]:
    blockers: list[dict] = []
    warnings: list[dict] = []
    model_ids = {model.id for model in evidence["models"]}
    run_ids = {run.id for run in evidence["runs"]}
    if experiment.deleted_at is not None:
        blockers.append({"code": "experiment_archived", "message": "Archived experiments cannot be packaged."})
    if version and version.dataset_id != dataset.id:
        blockers.append({"code": "dataset_version_mismatch", "message": "The dataset version does not belong to the experiment dataset."})
    for model in evidence["models"]:
        if model.dataset_id != dataset.id:
            blockers.append({"code": "model_dataset_mismatch", "record_id": model.id})
        if model.run_id and model.run_id not in run_ids and source_context["type"] != "verified_demo_experiment":
            blockers.append({"code": "model_run_mismatch", "record_id": model.id})
    for run in evidence["runs"]:
        if run.dataset_id != dataset.id:
            blockers.append({"code": "run_dataset_mismatch", "record_id": run.id})
        if version and run.dataset_version_id and run.dataset_version_id != version.id:
            blockers.append({"code": "run_dataset_version_mismatch", "record_id": run.id})
    for record in evidence["external_validation"]:
        if record.training_dataset_id != dataset.id or record.model_id not in model_ids:
            blockers.append({"code": "external_validation_identity_mismatch", "record_id": record.id})
    for record in evidence["quantum_diagnostics"]:
        if record.model_record_id not in model_ids:
            blockers.append({"code": "quantum_diagnostic_identity_mismatch", "record_id": record.id})
    known_artifacts = {artifact.id: artifact for artifact in evidence["artifacts"]}
    references: list[tuple[Any, str, str | None]] = []
    for key, field in (
        ("multi_seed", "study_artifact_id"), ("external_validation", "artifact_id"),
        ("distribution_shift", "artifact_id"), ("calibration", "artifact_id"),
        ("ablation", "artifact_id"), ("controlled_comparison", "artifact_id"),
    ):
        for record in evidence[key]:
            references.append((record, field, getattr(record, "model_id", None)))
    for record, field, expected_model in references:
        artifact_id = getattr(record, field, None)
        if not artifact_id:
            continue
        artifact = known_artifacts.get(artifact_id) or session.get(Artifact, artifact_id)
        if not artifact or artifact.experiment_id != experiment.id:
            blockers.append({"code": "package_artifact_conflict", "record_id": record.id})
        elif expected_model and artifact.model_id not in {None, expected_model}:
            blockers.append({"code": "package_artifact_conflict", "record_id": record.id})
    run_fingerprints = sorted({run.configuration_fingerprint for run in evidence["runs"] if run.configuration_fingerprint})
    if len(run_fingerprints) > 1:
        blockers.append({"code": "configuration_fingerprint_mismatch", "message": "Persisted experiment runs disagree on configuration identity."})
    if not version:
        warnings.append({"code": "dataset_version_unavailable", "message": "This legacy experiment has no immutable dataset version reference."})
    if source_context["type"] == "verified_demo_experiment" and not source_context.get("manifest_sha256"):
        warnings.append({"code": "verified_manifest_unavailable", "message": "The legacy verified-demo row does not expose a manifest hash."})
    return blockers, warnings


def preflight_package(session, experiment_id: str) -> dict:
    experiment = require(session, Experiment, experiment_id)
    dataset = require(session, Dataset, experiment.dataset_id)
    evidence = _load_evidence(session, experiment)
    verified = _verified_context(experiment, evidence["models"])
    source_context = verified or {"type": "live_run", "precomputed": False}
    run_versions = {run.dataset_version_id for run in evidence["runs"] if run.dataset_version_id}
    version_id = next(iter(run_versions), None) if len(run_versions) == 1 else dataset.current_version_id
    configured_version = (experiment.config or {}).get("dataset_version_id")
    version_id = version_id or configured_version or dataset.current_version_id
    version = session.get(DatasetVersion, version_id) if version_id else None
    blockers, warnings = _validate(session, experiment, dataset, version, evidence, source_context)

    models = evidence["models"]
    has_quantum = any(model.model_type in QUANTUM_MODELS for model in models)
    inventory = {
        "evaluation": _evaluation(models),
        "multi_seed": _category(evidence["multi_seed"], artifact_field="study_artifact_id"),
        "external_validation": _category(evidence["external_validation"]),
        "distribution_shift": _category(evidence["distribution_shift"]),
        "group_validation": _group_validation(experiment, models),
        "calibration": _category(evidence["calibration"]),
        "threshold": _category(evidence["threshold"]),
        "robustness": _category(evidence["robustness"]),
        "ablation": _category(evidence["ablation"]),
        "quantum_diagnostics": _category(evidence["quantum_diagnostics"], not_applicable=not has_quantum),
        "controlled_comparison": _category(evidence["controlled_comparison"], not_applicable=not has_quantum),
        "model_cards": _model_cards(evidence["artifacts"], {model.id for model in models}),
        "explainability": _category(evidence["explainability"]),
    }
    configuration_fingerprints = sorted({
        run.configuration_fingerprint for run in evidence["runs"] if run.configuration_fingerprint
    })
    governing_fingerprint = (
        configuration_fingerprints[0]
        if len(configuration_fingerprints) == 1
        else fingerprint(experiment.config or {})
    )
    artifact_ids = sorted({
        artifact_id
        for category in inventory.values()
        for artifact_id in category.get("artifact_ids", [])
    })
    artifact_hashes = {
        artifact.id: artifact.integrity_hash
        for artifact in evidence["artifacts"]
        if artifact.id in artifact_ids
    }
    models_payload = [{
        "model_id": model.id,
        "model_type": model.model_type,
        "status": model.status,
        "run_id": model.run_id,
        "artifact_sha256": model.artifact_sha256,
        "model_card_artifact_id": next((
            card["artifact_id"] for card in inventory["model_cards"].get("cards", [])
            if card["model_id"] == model.id
        ), None),
        "quantum_execution": clean_json({
            key: (model.details or {}).get("quantum", {}).get(key)
            for key in ("provider_id", "backend", "execution_kind", "real_hardware")
            if key in (model.details or {}).get("quantum", {})
        }) or None,
    } for model in models]
    gaps = [
        {"category": key, "status": value["status"], "reason": value["availability_reason"]}
        for key, value in inventory.items()
        if value["status"] in {"not_available", "incomplete", "limited"}
    ]
    core_gaps = []
    if not models:
        core_gaps.append("model_identity")
    if inventory["evaluation"]["status"] != "available":
        core_gaps.append("persisted_evaluation")
    if not version:
        core_gaps.append("dataset_version")
    if source_context["type"] == "live_run" and not evidence["runs"]:
        core_gaps.append("run_provenance")
    if not dataset.sha256:
        core_gaps.append("dataset_hash")

    status = "BLOCKED" if blockers else (
        "INCOMPLETE" if core_gaps else (
            "PARTIAL" if gaps else "READY"
        )
    )
    limitations = sorted({
        "This package is a research-evidence manifest; it is not clinical validation, regulatory approval, or evidence of quantum advantage.",
        *[str(item) for item in (experiment.summary or {}).get("limitations", [])],
        *[str(item) for category in inventory.values() for item in category.get("limitations", [])],
    })
    fingerprint_basis = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "experiment": {
            "id": experiment.id, "status": experiment.status,
            "configuration_fingerprint": governing_fingerprint,
        },
        "dataset": {
            "id": dataset.id, "version_id": version.id if version else None,
            "content_sha256": version.content_sha256 if version else dataset.sha256,
            "schema_fingerprint": version.schema_fingerprint if version else None,
        },
        "models": models_payload,
        "run_ids": sorted(run.id for run in evidence["runs"]),
        "evidence_inventory": inventory,
        "artifact_hashes": artifact_hashes,
        "source_context": source_context,
    }
    package_fingerprint = fingerprint(fingerprint_basis)
    package_id = str(uuid5(NAMESPACE_URL, f"qhealth:evidence-package:{experiment.id}:{package_fingerprint}"))
    artifact_id = str(uuid5(NAMESPACE_URL, f"qhealth:evidence-package-artifact:{experiment.id}:{package_fingerprint}"))
    manifest = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "package_id": package_id,
        "package_status": status,
        "package_fingerprint": package_fingerprint,
        "configuration_fingerprint": governing_fingerprint,
        "experiment": {
            "id": experiment.id, "name": experiment.name, "status": experiment.status,
            "configuration_fingerprint": governing_fingerprint,
        },
        "dataset": {
            "dataset_id": dataset.id, "name": dataset.name,
            "dataset_version_id": version.id if version else None,
            "content_sha256": version.content_sha256 if version else dataset.sha256,
            "schema_fingerprint": version.schema_fingerprint if version else None,
            "target": version.target if version else (dataset.provenance or {}).get("target"),
            "target_type": version.target_type if version else None,
        },
        "models": models_payload,
        "source_context": source_context,
        "evidence_inventory": inventory,
        "provenance": {
            "experiment_id": experiment.id,
            "run_ids": sorted(run.id for run in evidence["runs"]),
            "artifact_ids": artifact_ids,
            "configuration_fingerprints": configuration_fingerprints or [governing_fingerprint],
            "evidence_source_fingerprints": sorted({
                value for category in inventory.values()
                for value in category.get("configuration_fingerprints", [])
            }),
        },
        "integrity": {
            "dataset_hash": version.content_sha256 if version else dataset.sha256,
            "model_artifact_hashes": sorted(
                model.artifact_sha256 for model in models if model.artifact_sha256
            ),
            "evidence_artifact_hashes": artifact_hashes,
            "package_fingerprint": package_fingerprint,
            "artifact_id": artifact_id,
            "hash_algorithm": "sha256",
        },
        "limitations": limitations,
        "evidence_gaps": gaps,
    }
    return {
        "feasible": not blockers,
        "package_status": status,
        "package_fingerprint_candidate": package_fingerprint,
        "evidence_inventory": inventory,
        "blockers": blockers,
        "warnings": warnings,
        "missing_evidence": gaps,
        "core_missing_evidence": core_gaps,
        "manifest": manifest,
    }


def package_payload(session, package: ResearchEvidencePackage) -> dict:
    artifact = require(session, Artifact, package.artifact_id)
    payload = clean_json(dict(package.manifest))
    payload["created_at"] = _time(package.created_at)
    payload["artifact"] = {
        "id": artifact.id,
        "artifact_type": artifact.artifact_type,
        "content_type": artifact.content_type,
        "integrity_hash": artifact.integrity_hash,
        "hash_algorithm": artifact.hash_algorithm,
        "immutable": artifact.immutable,
    }
    return payload


def create_package(session, experiment_id: str) -> tuple[ResearchEvidencePackage, bool]:
    preflight = preflight_package(session, experiment_id)
    if not preflight["feasible"]:
        raise AppError("package_blocked", "The evidence package failed integrity preflight.", 409)
    manifest = preflight["manifest"]
    existing = session.scalar(select(ResearchEvidencePackage).where(
        ResearchEvidencePackage.experiment_id == experiment_id,
        ResearchEvidencePackage.package_fingerprint == manifest["package_fingerprint"],
    ))
    if existing:
        return existing, False
    artifact = register_metadata(
        session,
        experiment_id=experiment_id,
        run_id=None,
        model_id=None,
        artifact_type=PACKAGE_ARTIFACT_TYPE,
        name=f"Research evidence package {manifest['package_id']}",
        description="Immutable machine-readable manifest of persisted experiment evidence.",
        payload=manifest,
        operation_key=f"research-evidence-package:{experiment_id}:{manifest['package_fingerprint']}",
        artifact_id=manifest["integrity"]["artifact_id"],
    )
    package = ResearchEvidencePackage(
        id=manifest["package_id"],
        experiment_id=experiment_id,
        schema_version=PACKAGE_SCHEMA_VERSION,
        status=manifest["package_status"],
        package_fingerprint=manifest["package_fingerprint"],
        configuration_fingerprint=manifest["configuration_fingerprint"],
        source_context_type=manifest["source_context"]["type"],
        evidence_inventory=manifest["evidence_inventory"],
        provenance=manifest["provenance"],
        limitations=manifest["limitations"],
        evidence_gaps=manifest["evidence_gaps"],
        manifest=manifest,
        artifact_id=artifact.id,
    )
    session.add(package)
    session.flush()
    return package, True


def latest_package(session, experiment_id: str) -> ResearchEvidencePackage:
    require(session, Experiment, experiment_id)
    package = session.scalar(select(ResearchEvidencePackage).where(
        ResearchEvidencePackage.experiment_id == experiment_id
    ).order_by(ResearchEvidencePackage.created_at.desc(), ResearchEvidencePackage.id.desc()))
    if not package:
        raise AppError("package_not_found", "No research evidence package exists for this experiment.", 404)
    return package


def specific_package(session, experiment_id: str, package_id: str) -> ResearchEvidencePackage:
    package = session.scalar(select(ResearchEvidencePackage).where(
        ResearchEvidencePackage.id == package_id,
        ResearchEvidencePackage.experiment_id == experiment_id,
    ))
    if not package:
        raise AppError("package_not_found", "The research evidence package was not found.", 404)
    return package