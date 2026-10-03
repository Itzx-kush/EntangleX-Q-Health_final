from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy import func, select

from ..artifacts.service import register_metadata
from ..storage.entities import (
    Artifact,
    ControlledComparisonProtocol,
    Dataset,
    DatasetVersion,
    Experiment,
    ExperimentProtocol,
    ExperimentProtocolVersion,
    PipelineVersion,
    ProtocolTemplate,
    Run,
)
from ..storage.repository import require
from ..utils.errors import AppError
from ..utils.serialization import clean_json, fingerprint, utcnow
from .schemas import (
    ALLOWED_METRICS,
    ALLOWED_TASK_TYPES,
    ProtocolCreateRequest,
    ProtocolDefinitionSpec,
    TemplateInstantiateRequest,
)

PROTOCOL_SCHEMA_VERSION = "protocol_definition_v1"
PUBLISHED_STATUSES = {"PUBLISHED", "DEPRECATED", "ARCHIVED"}


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key).strip(): _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, str):
        return value.strip()
    return clean_json(value)


def canonicalize_definition(definition: ProtocolDefinitionSpec | dict) -> dict:
    if isinstance(definition, dict) and "schema_version" in definition:
        if definition["schema_version"] != PROTOCOL_SCHEMA_VERSION:
            raise ValueError("Unsupported protocol definition schema version.")
        definition = {key: value for key, value in definition.items() if key != "schema_version"}
    parsed = (
        definition
        if isinstance(definition, ProtocolDefinitionSpec)
        else ProtocolDefinitionSpec.model_validate(definition)
    )
    payload = parsed.model_dump(mode="json")
    return _normalize({
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "study_metadata": payload.get("study_metadata") or {},
        "dataset_policy": payload.get("dataset_policy") or {},
        "split_policy": payload.get("split_policy") or {},
        "randomness_policy": payload.get("randomness_policy") or {},
        "model_policy": payload.get("model_policy") or {},
        "pipeline_policy": payload.get("pipeline_policy") or {},
        "evaluation_policy": payload.get("evaluation_policy") or {},
        "threshold_policy": payload.get("threshold_policy") or {},
        "calibration_policy": payload.get("calibration_policy") or {},
        "validation_extensions": payload.get("validation_extensions") or {},
        "quantum_controls": payload.get("quantum_controls") or {},
        "constraints": payload.get("constraints") or {},
    })


def definition_fingerprint(definition: ProtocolDefinitionSpec | dict) -> str:
    return fingerprint(canonicalize_definition(definition))


def _reference_diagnostics(session, canonical: dict) -> tuple[list[dict], list[dict]]:
    blockers: list[dict] = []
    warnings: list[dict] = []

    dataset_policy = canonical.get("dataset_policy") or {}
    dataset_id = dataset_policy.get("dataset_id")
    version_id = dataset_policy.get("dataset_version_id")
    pipeline_policy = canonical.get("pipeline_policy") or {}
    pipeline_id = pipeline_policy.get("pipeline_version_id")
    quantum_controls = canonical.get("quantum_controls") or {}
    controlled_id = quantum_controls.get("controlled_comparison_protocol_id")
    ext_val = (canonical.get("validation_extensions") or {}).get("external_validation") or {}
    ext_dataset_id = ext_val.get("external_dataset_id")

    dataset = session.get(Dataset, str(dataset_id)) if dataset_id else None
    version = session.get(DatasetVersion, str(version_id)) if version_id else None

    if dataset_id and not dataset:
        blockers.append({"code": "dataset_not_found", "message": f"Referenced dataset {dataset_id} was not found.", "reference_id": str(dataset_id)})
    if version_id and not version:
        blockers.append({"code": "dataset_version_not_found", "message": f"Referenced dataset version {version_id} was not found.", "reference_id": str(version_id)})
    if dataset and version and version.dataset_id != dataset.id:
        blockers.append({"code": "dataset_version_mismatch", "message": "Dataset version does not belong to the referenced dataset.", "reference_id": str(version_id)})
    if pipeline_id and not session.get(PipelineVersion, str(pipeline_id)):
        blockers.append({"code": "pipeline_version_not_found", "message": f"Referenced pipeline version {pipeline_id} was not found.", "reference_id": str(pipeline_id)})
    if controlled_id and not session.get(ControlledComparisonProtocol, str(controlled_id)):
        blockers.append({"code": "controlled_comparison_not_found", "message": f"Referenced controlled comparison protocol {controlled_id} was not found.", "reference_id": str(controlled_id)})
    if ext_dataset_id and not session.get(Dataset, str(ext_dataset_id)):
        blockers.append({"code": "external_dataset_not_found", "message": f"Referenced external validation dataset {ext_dataset_id} was not found.", "reference_id": str(ext_dataset_id)})

    if dataset_id and not version_id:
        warnings.append({"code": "dataset_version_unlocked", "message": "The protocol specifies a dataset but does not lock an immutable dataset version."})
    if ext_val.get("requirement") == "REQUIRED" and not ext_dataset_id:
        warnings.append({"code": "external_dataset_unspecified", "message": "External validation is marked REQUIRED but no external dataset ID is pre-locked."})

    return blockers, warnings


def preflight_definition(session, definition: ProtocolDefinitionSpec | dict) -> dict:
    try:
        canonical = canonicalize_definition(definition)
    except Exception as exc:
        return {
            "valid": False,
            "publishable": False,
            "fingerprint_deterministic": False,
            "fingerprint": None,
            "canonical_definition": None,
            "errors": [{"code": "protocol_definition_invalid", "message": str(exc)}],
            "warnings": [],
        }

    blockers, warnings = _reference_diagnostics(session, canonical)

    eval_policy = canonical.get("evaluation_policy") or {}
    primary_metric = eval_policy.get("primary_metric")
    if primary_metric and primary_metric not in ALLOWED_METRICS:
        blockers.append({"code": "unsupported_primary_metric", "message": f"Metric '{primary_metric}' is not supported.", "metric": primary_metric})

    for secondary in eval_policy.get("secondary_metrics", []):
        if secondary not in ALLOWED_METRICS:
            blockers.append({"code": "unsupported_secondary_metric", "message": f"Metric '{secondary}' is not supported.", "metric": secondary})

    study_meta = canonical.get("study_metadata") or {}
    task_type = study_meta.get("task_type")
    if task_type and task_type not in ALLOWED_TASK_TYPES:
        blockers.append({"code": "unsupported_task_type", "message": f"Task type '{task_type}' is not supported.", "task_type": task_type})

    split_policy = canonical.get("split_policy") or {}
    test_size = split_policy.get("test_size", 0.2)
    if not (0.01 <= test_size <= 0.9):
        blockers.append({"code": "invalid_test_size", "message": "Holdout test size must be between 0.01 and 0.9."})
    cv_folds = split_policy.get("cv_folds", 5)
    if not (2 <= cv_folds <= 30):
        blockers.append({"code": "invalid_cv_folds", "message": "CV fold count must be between 2 and 30."})

    rand_policy = canonical.get("randomness_policy") or {}
    multi_count = rand_policy.get("multi_seed_count", 1)
    if multi_count < 1:
        blockers.append({"code": "invalid_seed_count", "message": "Multi-seed count must be at least 1."})

    candidate = fingerprint(canonical)
    deterministic = candidate == fingerprint(canonicalize_definition(canonical))

    return {
        "valid": not any(item["code"].endswith(("_invalid", "_unsupported")) for item in blockers),
        "publishable": len(blockers) == 0,
        "fingerprint_deterministic": deterministic,
        "fingerprint": candidate,
        "canonical_definition": canonical,
        "blockers": blockers,
        "errors": blockers,
        "warnings": warnings,
    }


def create_protocol_version(session, request: ProtocolCreateRequest) -> tuple[ExperimentProtocolVersion, bool]:
    canonical = canonicalize_definition(request.definition)
    candidate = fingerprint(canonical)

    existing = session.scalar(
        select(ExperimentProtocolVersion).where(ExperimentProtocolVersion.definition_fingerprint == candidate)
    )
    if existing:
        return existing, False

    parent = None
    if request.parent_protocol_version_id:
        parent = require(session, ExperimentProtocolVersion, str(request.parent_protocol_version_id))
        family = require(session, ExperimentProtocol, parent.protocol_id)
    else:
        family = session.scalar(
            select(ExperimentProtocol).where(ExperimentProtocol.name == request.protocol_name)
        )
        if family is None:
            family = ExperimentProtocol(
                id=str(uuid4()),
                name=request.protocol_name,
                description=request.description,
                template_id=str(request.template_id) if request.template_id else None,
                source_context=request.source_context,
            )
            session.add(family)
            session.flush()

    next_number = (
        session.scalar(
            select(func.max(ExperimentProtocolVersion.version_number))
            .where(ExperimentProtocolVersion.protocol_id == family.id)
        )
        or 0
    ) + 1

    pipeline_policy = canonical.get("pipeline_policy") or {}
    quantum_controls = canonical.get("quantum_controls") or {}

    version = ExperimentProtocolVersion(
        id=str(uuid4()),
        protocol_id=family.id,
        version_number=next_number,
        version_label=f"v{next_number}",
        schema_version=PROTOCOL_SCHEMA_VERSION,
        status="DRAFT",
        description=request.description,
        definition_fingerprint=candidate,
        canonical_definition=canonical,
        parent_protocol_version_id=parent.id if parent else None,
        template_id=str(request.template_id) if request.template_id else (parent.template_id if parent else None),
        pipeline_version_id=pipeline_policy.get("pipeline_version_id"),
        controlled_comparison_protocol_id=quantum_controls.get("controlled_comparison_protocol_id"),
        source_context=request.source_context,
    )
    session.add(version)
    session.flush()
    session.info.setdefault("protocol_registry_created_ids", set()).add(version.id)
    return version, True


def publish_protocol_version(session, version_id: str) -> ExperimentProtocolVersion:
    version = require(session, ExperimentProtocolVersion, version_id)
    if version.status in PUBLISHED_STATUSES:
        return version

    preflight = preflight_definition(session, version.canonical_definition)
    if not preflight["publishable"]:
        raise AppError("protocol_not_publishable", "The Protocol Version failed publish preflight.", 422)
    if preflight["fingerprint"] != version.definition_fingerprint:
        raise AppError("protocol_fingerprint_mismatch", "The stored Protocol Version definition is inconsistent.", 409)

    session.info["protocol_registry_publish"] = True
    try:
        version.status = "PUBLISHED"
        version.published_at = utcnow()
        session.flush()
    finally:
        session.info.pop("protocol_registry_publish", None)

    return version


def protocol_payload(
    session,
    version: ExperimentProtocolVersion,
    *,
    family: ExperimentProtocol | None = None,
    experiments: list[str] | None = None,
) -> dict:
    family = family or require(session, ExperimentProtocol, version.protocol_id)
    experiments = experiments if experiments is not None else list(session.scalars(
        select(Experiment.id).where(Experiment.protocol_version_id == version.id).order_by(Experiment.created_at)
    ))
    return {
        "protocol_version_id": version.id,
        "protocol_id": family.id,
        "protocol_name": family.name,
        "version": version.version_label,
        "version_number": version.version_number,
        "schema_version": version.schema_version,
        "status": version.status,
        "description": version.description or family.description,
        "definition_fingerprint": version.definition_fingerprint,
        "parent_protocol_version_id": version.parent_protocol_version_id,
        "template_id": version.template_id,
        "pipeline_version_id": version.pipeline_version_id,
        "controlled_comparison_protocol_id": version.controlled_comparison_protocol_id,
        "artifact_id": version.artifact_id,
        "source_context": version.source_context,
        "canonical_definition": clean_json(version.canonical_definition),
        "experiments": experiments,
        "usage_count": len(experiments),
        "published_at": version.published_at.isoformat() if version.published_at else None,
        "created_at": version.created_at.isoformat() if version.created_at else None,
        "scientific_boundary": "An experiment protocol defines experimental rules and reproducibility requirements. It does not establish scientific validity, model quality, or performance.",
    }


def list_protocol_versions(session, *, limit: int = 100, offset: int = 0) -> list[dict]:
    versions = list(session.scalars(
        select(ExperimentProtocolVersion)
        .order_by(ExperimentProtocolVersion.created_at.desc())
        .offset(offset)
        .limit(limit)
    ))
    if not versions:
        return []

    version_ids = [version.id for version in versions]
    family_ids = {version.protocol_id for version in versions}
    families = {
        family.id: family
        for family in session.scalars(
            select(ExperimentProtocol).where(ExperimentProtocol.id.in_(family_ids))
        )
    }

    experiments_by_version: dict[str, list[str]] = {vid: [] for vid in version_ids}
    for protocol_version_id, experiment_id in session.execute(
        select(Experiment.protocol_version_id, Experiment.id)
        .where(Experiment.protocol_version_id.in_(version_ids))
        .order_by(Experiment.created_at)
    ):
        if protocol_version_id:
            experiments_by_version[protocol_version_id].append(experiment_id)

    return [
        protocol_payload(
            session,
            version,
            family=families.get(version.protocol_id),
            experiments=experiments_by_version.get(version.id, []),
        )
        for version in versions
    ]


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key in sorted(value):
            path = f"{prefix}.{key}" if prefix else key
            result.update(_flatten(value[key], path))
        return result
    if isinstance(value, list):
        return {prefix: value}
    return {prefix: value}


def diff_protocol_versions(session, from_id: str, to_id: str) -> dict:
    before = require(session, ExperimentProtocolVersion, from_id)
    after = require(session, ExperimentProtocolVersion, to_id)

    categories = [
        "study_metadata", "dataset_policy", "split_policy",
        "randomness_policy", "model_policy", "pipeline_policy",
        "evaluation_policy", "threshold_policy", "calibration_policy",
        "validation_extensions", "quantum_controls", "constraints",
    ]

    changes: list[dict[str, Any]] = []
    category_summaries: list[dict[str, Any]] = []

    for cat in categories:
        left = before.canonical_definition.get(cat) or {}
        right = after.canonical_definition.get(cat) or {}

        left_flat = _flatten(left)
        right_flat = _flatten(right)

        cat_changes = []
        for field in sorted(set(left_flat) | set(right_flat)):
            left_val = left_flat.get(field)
            right_val = right_flat.get(field)
            if left_val != right_val:
                change_type = "Added" if left_val is None else ("Removed" if right_val is None else "Changed")
                cat_changes.append({
                    "category": cat,
                    "field": field,
                    "change_type": change_type,
                    "before": left_val,
                    "after": right_val,
                })
        changes.extend(cat_changes)
        category_summaries.append({
            "category": cat,
            "status": "Changed" if cat_changes else "Unchanged",
        })

    return {
        "from_version": before.id,
        "to_version": after.id,
        "from_fingerprint": before.definition_fingerprint,
        "to_fingerprint": after.definition_fingerprint,
        "changes": changes,
        "change_count": len(changes),
        "identical": not bool(changes),
        "category_summaries": category_summaries,
        "has_protocol_changes": bool(changes),
        "interpretation": "Differences identify explicit experimental rule changes only; they do not rank protocols or imply quality.",
    }


def list_protocol_templates(session) -> list[dict]:
    templates = list(session.scalars(select(ProtocolTemplate).order_by(ProtocolTemplate.created_at)))
    return [{
        "id": template.id,
        "template_id": template.id,
        "name": template.name,
        "description": template.description,
        "version": template.version,
        "status": template.status,
        "task_type": template.task_type,
        "canonical_definition": clean_json(template.canonical_definition),
        "parameters_schema": clean_json(template.parameters_schema),
        "template_fingerprint": template.template_fingerprint,
        "created_at": template.created_at.isoformat() if template.created_at else None,
    } for template in templates]


def get_protocol_template(session, template_id: str) -> dict:
    template = require(session, ProtocolTemplate, template_id)
    return {
        "id": template.id,
        "template_id": template.id,
        "name": template.name,
        "description": template.description,
        "version": template.version,
        "status": template.status,
        "task_type": template.task_type,
        "canonical_definition": clean_json(template.canonical_definition),
        "parameters_schema": clean_json(template.parameters_schema),
        "template_fingerprint": template.template_fingerprint,
        "created_at": template.created_at.isoformat() if template.created_at else None,
    }


def instantiate_protocol_template(
    session,
    template_id: str,
    request: TemplateInstantiateRequest,
) -> tuple[ExperimentProtocolVersion, bool]:
    template = require(session, ProtocolTemplate, template_id)
    definition = deepcopy(template.canonical_definition)

    params = request.parameters or {}
    if "cv_folds" in params:
        definition.setdefault("split_policy", {})["cv_folds"] = int(params["cv_folds"])
        definition.setdefault("constraints", {})["required_cv_folds"] = int(params["cv_folds"])
    if "test_size" in params:
        definition.setdefault("split_policy", {})["test_size"] = float(params["test_size"])
    if "primary_metric" in params:
        definition.setdefault("evaluation_policy", {})["primary_metric"] = str(params["primary_metric"])
    if "n_seeds" in params:
        n_seeds = int(params["n_seeds"])
        definition.setdefault("randomness_policy", {})["multi_seed_count"] = n_seeds
        definition.setdefault("validation_extensions", {}).setdefault("multi_seed", {})["min_seed_count"] = n_seeds
        definition.setdefault("constraints", {})["minimum_seed_count"] = n_seeds
    if "calibration_required" in params:
        is_req = bool(params["calibration_required"])
        definition.setdefault("calibration_policy", {})["requirement"] = "REQUIRED" if is_req else "OPTIONAL"
        definition.setdefault("constraints", {})["calibration_required"] = is_req
    if "threshold_strategy" in params:
        definition.setdefault("threshold_policy", {})["strategy"] = str(params["threshold_strategy"])
    if "dataset_id" in params and params["dataset_id"]:
        definition.setdefault("dataset_policy", {})["dataset_id"] = str(params["dataset_id"])
    if "pipeline_version_id" in params and params["pipeline_version_id"]:
        definition.setdefault("pipeline_policy", {})["pipeline_version_id"] = str(params["pipeline_version_id"])
        definition.setdefault("pipeline_policy", {})["requirement"] = "REQUIRED"
    if "external_dataset_id" in params and params["external_dataset_id"]:
        definition.setdefault("validation_extensions", {}).setdefault("external_validation", {})["external_dataset_id"] = str(params["external_dataset_id"])
        definition.setdefault("validation_extensions", {}).setdefault("external_validation", {})["requirement"] = "REQUIRED"

    create_req = ProtocolCreateRequest(
        protocol_name=request.protocol_name,
        description=request.description or f"Protocol instantiated from template '{template.name}'",
        template_id=template.id,
        source_context=request.source_context or "template_instantiation",
        definition=ProtocolDefinitionSpec.model_validate(definition),
    )
    return create_protocol_version(session, create_req)


def attach_protocol_to_experiment(
    session,
    experiment_id: str,
    protocol_version_id: str,
) -> ExperimentProtocolVersion:
    experiment = require(session, Experiment, experiment_id)
    version = require(session, ExperimentProtocolVersion, protocol_version_id)

    if experiment.protocol_version_id:
        if experiment.protocol_version_id != version.id:
            raise AppError(
                "protocol_already_attached",
                f"Experiment '{experiment_id}' already has protocol version '{experiment.protocol_version_id}' attached. Protocols are immutable and cannot be altered.",
                409,
            )
        return version

    experiment.protocol_version_id = version.id
    experiment.protocol_fingerprint = version.definition_fingerprint

    runs = list(session.scalars(select(Run).where(Run.experiment_id == experiment_id)))
    for run in runs:
        if not run.protocol_version_id:
            run.protocol_version_id = version.id
            run.protocol_fingerprint = version.definition_fingerprint

    session.flush()
    return version

