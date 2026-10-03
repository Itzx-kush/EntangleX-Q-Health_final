from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy import func, select

from ..api.schemas import TrainingConfig
from ..storage.entities import (
    ControlledComparisonProtocol,
    Dataset,
    DatasetVersion,
    Experiment,
    PipelineDefinition,
    PipelineStage,
    PipelineVersion,
)
from ..storage.repository import require
from ..utils.errors import AppError
from ..utils.serialization import clean_json, fingerprint, utcnow
from .schemas import PipelineCreateRequest, PipelineDefinitionSpec, STAGE_TYPES

PIPELINE_SCHEMA_VERSION = "pipeline_definition_v1"
REQUIRED_STAGE_TYPES = {
    "data_validation", "preprocessing", "feature_engineering",
    "representation", "model", "evaluation",
}
PUBLISHED_STATUSES = {"ACTIVE", "DEPRECATED", "ARCHIVED"}


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key).strip(): _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, str):
        return value.strip()
    return clean_json(value)


def canonicalize_definition(definition: PipelineDefinitionSpec | dict) -> dict:
    if isinstance(definition, dict) and "schema_version" in definition:
        if definition["schema_version"] != PIPELINE_SCHEMA_VERSION:
            raise ValueError("Unsupported pipeline definition schema version.")
        definition = {key: value for key, value in definition.items() if key != "schema_version"}
    parsed = (
        definition
        if isinstance(definition, PipelineDefinitionSpec)
        else PipelineDefinitionSpec.model_validate(definition)
    )
    payload = parsed.model_dump(mode="json")
    stages = sorted(payload["stages"], key=lambda stage: stage["stage_order"])
    return _normalize({
        "schema_version": PIPELINE_SCHEMA_VERSION,
        "dataset_id": payload.get("dataset_id"),
        "dataset_version_id": payload.get("dataset_version_id"),
        "controlled_comparison_protocol_id": payload.get("controlled_comparison_protocol_id"),
        "stages": stages,
    })


def definition_fingerprint(definition: PipelineDefinitionSpec | dict) -> str:
    return fingerprint(canonicalize_definition(definition))


def _reference_diagnostics(session, canonical: dict) -> tuple[list[dict], list[dict]]:
    blockers: list[dict] = []
    warnings: list[dict] = []
    dataset_id = canonical.get("dataset_id")
    version_id = canonical.get("dataset_version_id")
    protocol_id = canonical.get("controlled_comparison_protocol_id")
    dataset = session.get(Dataset, dataset_id) if dataset_id else None
    version = session.get(DatasetVersion, version_id) if version_id else None
    if dataset_id and not dataset:
        blockers.append({"code": "dataset_not_found", "reference_id": dataset_id})
    if version_id and not version:
        blockers.append({"code": "dataset_version_not_found", "reference_id": version_id})
    if dataset and version and version.dataset_id != dataset.id:
        blockers.append({"code": "dataset_version_mismatch", "reference_id": version_id})
    if protocol_id and not session.get(ControlledComparisonProtocol, protocol_id):
        blockers.append({"code": "controlled_comparison_not_found", "reference_id": protocol_id})
    if not version_id:
        warnings.append({"code": "dataset_version_unavailable", "message": "The definition does not lock an immutable dataset version."})
    return blockers, warnings


def preflight_definition(session, definition: PipelineDefinitionSpec | dict) -> dict:
    try:
        canonical = canonicalize_definition(definition)
    except Exception:
        return {
            "definition_valid": False, "references_valid": False,
            "fingerprint_deterministic": False,
            "all_required_components_present": False, "publishable": False,
            "fingerprint": None,
            "blockers": [{"code": "pipeline_definition_invalid", "message": "The pipeline definition is structurally invalid."}],
            "warnings": [],
        }
    stage_types = [stage["stage_type"] for stage in canonical["stages"]]
    blockers, warnings = _reference_diagnostics(session, canonical)
    unknown = sorted(set(stage_types) - STAGE_TYPES)
    if unknown:
        blockers.append({"code": "pipeline_stage_type_unsupported", "stage_types": unknown})
    missing = sorted(REQUIRED_STAGE_TYPES - set(stage_types))
    if missing:
        blockers.append({"code": "pipeline_stage_required", "stage_types": missing})
    has_quantum_models = any(
        model in {"vqc", "qsvc", "qnn", "hybrid_pennylane_torch"}
        for stage in canonical["stages"] if stage["stage_type"] == "model"
        for model in stage["configuration"].get("models", [])
    )
    if has_quantum_models and "quantum_encoding" not in stage_types:
        blockers.append({"code": "quantum_encoding_required", "message": "Quantum-family model definitions require a quantum encoding stage."})
    candidate = fingerprint(canonical)
    return {
        "definition_valid": not unknown,
        "references_valid": not any(item["code"].endswith(("not_found", "mismatch")) for item in blockers),
        "fingerprint_deterministic": candidate == fingerprint(canonicalize_definition(canonical)),
        "all_required_components_present": not missing and (not has_quantum_models or "quantum_encoding" in stage_types),
        "publishable": not blockers,
        "fingerprint": candidate,
        "canonical_definition": canonical,
        "blockers": blockers,
        "warnings": warnings,
    }


def create_pipeline_version(session, request: PipelineCreateRequest) -> tuple[PipelineVersion, bool]:
    canonical = canonicalize_definition(request.definition)
    candidate = fingerprint(canonical)
    existing = session.scalar(select(PipelineVersion).where(PipelineVersion.definition_fingerprint == candidate))
    if existing:
        return existing, False
    family = session.scalar(select(PipelineDefinition).where(PipelineDefinition.name == request.pipeline_name))
    if family is None:
        family = PipelineDefinition(
            id=str(uuid4()), name=request.pipeline_name,
            description=request.description, source_context=request.source_context,
        )
        session.add(family)
        session.flush()
    parent = None
    if request.parent_pipeline_version_id:
        parent = require(session, PipelineVersion, str(request.parent_pipeline_version_id))
        if parent.pipeline_definition_id != family.id:
            raise AppError("pipeline_parent_family_mismatch", "A derived Pipeline Version must belong to the same pipeline family.", 409)
    next_number = (session.scalar(
        select(func.max(PipelineVersion.version_number))
        .where(PipelineVersion.pipeline_definition_id == family.id)
    ) or 0) + 1
    version = PipelineVersion(
        id=str(uuid4()), pipeline_definition_id=family.id,
        version_number=next_number, version_label=f"v{next_number}",
        schema_version=PIPELINE_SCHEMA_VERSION, status="DRAFT",
        description=request.description, definition_fingerprint=candidate,
        canonical_definition=canonical,
        parent_pipeline_version_id=parent.id if parent else None,
        controlled_comparison_protocol_id=canonical.get("controlled_comparison_protocol_id"),
        source_context=request.source_context,
    )
    session.add(version)
    session.flush()
    session.info.setdefault("pipeline_registry_created_ids", set()).add(version.id)
    for stage in canonical["stages"]:
        stage_basis = {
            "stage_order": stage["stage_order"], "stage_type": stage["stage_type"],
            "stage_name": stage["stage_name"], "configuration": stage["configuration"],
            "component_version": stage.get("component_version"),
        }
        stage_hash = fingerprint(stage_basis)
        session.add(PipelineStage(
            id=str(uuid5(NAMESPACE_URL, f"qhealth:pipeline-stage:{version.id}:{stage['stage_order']}:{stage_hash}")),
            pipeline_version_id=version.id,
            stage_order=stage["stage_order"], stage_type=stage["stage_type"],
            stage_name=stage["stage_name"], configuration=stage["configuration"],
            component_version=stage.get("component_version"),
            stage_fingerprint=stage_hash,
        ))
    session.flush()
    from ..audit.service import record_event
    record_event(
        session,
        event_type="PIPELINE_VERSION_CREATED",
        event_category="PIPELINE",
        object_type="pipeline_version",
        object_id=version.id,
        source_component="pipeline_registry",
        operation_key=f"pipeline-version-created:{version.id}",
        after_fingerprint=version.definition_fingerprint,
        metadata={"pipeline_name": family.name, "version": version.version_label, "schema_version": version.schema_version},
    )
    return version, True


def publish_pipeline_version(session, version_id: str) -> PipelineVersion:
    version = require(session, PipelineVersion, version_id)
    if version.status in PUBLISHED_STATUSES:
        return version
    preflight = preflight_definition(session, version.canonical_definition)
    if not preflight["publishable"]:
        raise AppError("pipeline_not_publishable", "The Pipeline Version failed publish preflight.", 422)
    if preflight["fingerprint"] != version.definition_fingerprint:
        raise AppError("pipeline_fingerprint_mismatch", "The stored Pipeline Version definition is inconsistent.", 409)
    session.info["pipeline_registry_publish"] = True
    try:
        version.status = "ACTIVE"
        version.published_at = utcnow()
        session.flush()
        from ..audit.service import record_event
        record_event(
            session,
            event_type="PIPELINE_VERSION_PUBLISHED",
            event_category="PIPELINE",
            object_type="pipeline_version",
            object_id=version.id,
            source_component="pipeline_registry",
            operation_key=f"pipeline-version-published:{version.id}",
            after_fingerprint=version.definition_fingerprint,
            metadata={"version": version.version_label},
        )
    finally:
        session.info.pop("pipeline_registry_publish", None)
    return version


def pipeline_from_training_config(config: TrainingConfig | dict) -> PipelineDefinitionSpec:
    payload = config.model_dump(mode="json") if isinstance(config, TrainingConfig) else deepcopy(config)
    payload.pop("pipeline_version_id", None)
    pipeline = payload.get("pipeline") or {}
    models = payload.get("models") or []
    stages = [
        {
            "stage_order": 1, "stage_type": "data_validation", "stage_name": "Data validation",
            "component_version": "qhealth-data-v1",
            "configuration": {
                "dataset_id": payload.get("dataset_id"),
                "dataset_version_id": payload.get("dataset_version_id"),
                "condition_task_id": payload.get("condition_task_id"),
                "features": payload.get("features"),
                "duplicate_policy": payload.get("duplicate_policy"),
                "max_samples": payload.get("max_samples"),
            },
        },
        {
            "stage_order": 2, "stage_type": "preprocessing", "stage_name": "Data preparation",
            "component_version": "qhealth-preprocessing-v1",
            "configuration": {
                key: pipeline.get(key) for key in (
                    "imputer", "scaler", "outlier_strategy",
                    "lower_quantile", "upper_quantile",
                )
            },
        },
        {
            "stage_order": 3, "stage_type": "feature_engineering", "stage_name": "Feature engineering",
            "component_version": "qhealth-features-v1",
            "configuration": {
                key: pipeline.get(key) for key in (
                    "log_features", "ratios", "selection", "k_features", "variance_threshold",
                )
            },
        },
        {
            "stage_order": 4, "stage_type": "representation", "stage_name": "Feature representation",
            "component_version": "qhealth-representation-v1",
            "configuration": {
                "pca_components": pipeline.get("pca_components"),
                "pca_whiten": pipeline.get("pca_whiten"),
                "angle_scaling": pipeline.get("angle_scaling"),
                "feature_order": payload.get("features"),
            },
        },
    ]
    uses_quantum = bool({"vqc", "qsvc", "qnn", "hybrid_pennylane_torch"}.intersection(models))
    if uses_quantum:
        stages.append({
            "stage_order": len(stages) + 1,
            "stage_type": "quantum_encoding", "stage_name": "Quantum encoding",
            "component_version": "qhealth-quantum-provider-v1",
            "configuration": {
                "qiskit": payload.get("quantum"),
                "hybrid": payload.get("hybrid"),
                "angle_scaling": pipeline.get("angle_scaling"),
                "representation_dimension": pipeline.get("pca_components"),
                "hardware_execution_claimed": False,
            },
        })
    stages.extend([
        {
            "stage_order": len(stages) + 1, "stage_type": "model", "stage_name": "Model configuration",
            "component_version": "qhealth-models-v1",
            "configuration": {
                "models": models, "parameters": payload.get("parameters"),
                "quantum": payload.get("quantum") if uses_quantum else None,
                "hybrid": payload.get("hybrid") if "hybrid_pennylane_torch" in models else None,
            },
        },
        {
            "stage_order": len(stages) + 2, "stage_type": "evaluation", "stage_name": "Evaluation",
            "component_version": "qhealth-evaluation-v1",
            "configuration": {
                key: payload.get(key) for key in (
                    "seed", "test_size", "cv_folds", "probability_threshold",
                    "threshold_strategy", "target_sensitivity", "calibration",
                    "calibration_folds", "sampling_unit", "group_column",
                )
            },
        },
    ])
    return PipelineDefinitionSpec.model_validate({
        "dataset_id": payload.get("dataset_id"),
        "dataset_version_id": payload.get("dataset_version_id"),
        "stages": stages,
    })


def ensure_pipeline_for_training_config(
    session,
    config: TrainingConfig,
    *,
    parent_pipeline_version_id: str | None = None,
) -> PipelineVersion:
    definition = pipeline_from_training_config(config)
    requested_id = str(config.pipeline_version_id) if config.pipeline_version_id else None
    candidate = definition_fingerprint(definition)
    if requested_id:
        requested = require(session, PipelineVersion, requested_id)
        if requested.status not in PUBLISHED_STATUSES:
            raise AppError("pipeline_version_not_active", "Experiments must use a published Pipeline Version.", 409)
        if requested.definition_fingerprint != candidate:
            raise AppError("pipeline_definition_mismatch", "The selected Pipeline Version does not match the experiment configuration.", 409)
        return requested
    existing = session.scalar(select(PipelineVersion).where(PipelineVersion.definition_fingerprint == candidate))
    if existing:
        if existing.status == "DRAFT":
            publish_pipeline_version(session, existing.id)
        return existing
    request = PipelineCreateRequest(
        pipeline_name="Q-Health Experiment Pipeline",
        description="Canonical pipeline generated from a validated experiment configuration.",
        parent_pipeline_version_id=parent_pipeline_version_id,
        source_context="experiment_configuration",
        definition=definition,
    )
    version, _ = create_pipeline_version(session, request)
    return publish_pipeline_version(session, version.id)


def _stages(session, version_id: str) -> list[PipelineStage]:
    return list(session.scalars(
        select(PipelineStage)
        .where(PipelineStage.pipeline_version_id == version_id)
        .order_by(PipelineStage.stage_order)
    ))


def pipeline_payload(
    session,
    version: PipelineVersion,
    *,
    family: PipelineDefinition | None = None,
    stages: list[PipelineStage] | None = None,
    experiments: list[str] | None = None,
) -> dict:
    family = family or require(session, PipelineDefinition, version.pipeline_definition_id)
    experiments = experiments if experiments is not None else list(session.scalars(
        select(Experiment.id).where(Experiment.pipeline_version_id == version.id).order_by(Experiment.created_at)
    ))
    stages = stages if stages is not None else _stages(session, version.id)
    return {
        "pipeline_version_id": version.id,
        "pipeline_definition_id": family.id,
        "pipeline_name": family.name,
        "version": version.version_label,
        "version_number": version.version_number,
        "schema_version": version.schema_version,
        "status": version.status,
        "description": version.description or family.description,
        "definition_fingerprint": version.definition_fingerprint,
        "parent_pipeline_version_id": version.parent_pipeline_version_id,
        "controlled_comparison_protocol_id": version.controlled_comparison_protocol_id,
        "artifact_id": version.artifact_id,
        "source_context": version.source_context,
        "canonical_definition": clean_json(version.canonical_definition),
        "stages": [{
            "stage_id": stage.id, "stage_order": stage.stage_order,
            "stage_type": stage.stage_type, "stage_name": stage.stage_name,
            "configuration": clean_json(stage.configuration),
            "component_version": stage.component_version,
            "fingerprint": stage.stage_fingerprint,
        } for stage in stages],
        "experiments": experiments,
        "usage_count": len(experiments),
        "published_at": version.published_at,
        "created_at": version.created_at,
        "scientific_boundary": "Pipeline identity records a computational definition; it is not a model-quality or superiority claim.",
    }


def list_pipeline_versions(session, *, limit: int = 100, offset: int = 0) -> list[dict]:
    versions = list(session.scalars(
        select(PipelineVersion)
        .order_by(PipelineVersion.created_at.desc())
        .offset(offset)
        .limit(limit)
    ))
    if not versions:
        return []
    version_ids = [version.id for version in versions]
    family_ids = {version.pipeline_definition_id for version in versions}
    families = {
        family.id: family
        for family in session.scalars(
            select(PipelineDefinition).where(PipelineDefinition.id.in_(family_ids))
        )
    }
    stages_by_version: dict[str, list[PipelineStage]] = {identity: [] for identity in version_ids}
    for stage in session.scalars(
        select(PipelineStage)
        .where(PipelineStage.pipeline_version_id.in_(version_ids))
        .order_by(PipelineStage.pipeline_version_id, PipelineStage.stage_order)
    ):
        stages_by_version[stage.pipeline_version_id].append(stage)
    experiments_by_version: dict[str, list[str]] = {identity: [] for identity in version_ids}
    for pipeline_version_id, experiment_id in session.execute(
        select(Experiment.pipeline_version_id, Experiment.id)
        .where(Experiment.pipeline_version_id.in_(version_ids))
        .order_by(Experiment.created_at)
    ):
        experiments_by_version[pipeline_version_id].append(experiment_id)
    return [
        pipeline_payload(
            session, version,
            family=families[version.pipeline_definition_id],
            stages=stages_by_version[version.id],
            experiments=experiments_by_version[version.id],
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


def diff_pipeline_versions(session, from_id: str, to_id: str) -> dict:
    before = require(session, PipelineVersion, from_id)
    after = require(session, PipelineVersion, to_id)
    before_stages = {stage["stage_type"]: stage for stage in before.canonical_definition["stages"]}
    after_stages = {stage["stage_type"]: stage for stage in after.canonical_definition["stages"]}
    changes = []
    summaries = []
    for stage_type in sorted(set(before_stages) | set(after_stages)):
        left, right = before_stages.get(stage_type), after_stages.get(stage_type)
        if left is None:
            changes.append({"stage": stage_type, "field": None, "change_type": "Added", "before": None, "after": right})
            summaries.append({"stage": stage_type, "status": "Added"})
            continue
        if right is None:
            changes.append({"stage": stage_type, "field": None, "change_type": "Removed", "before": left, "after": None})
            summaries.append({"stage": stage_type, "status": "Removed"})
            continue
        left_values, right_values = _flatten(left["configuration"]), _flatten(right["configuration"])
        stage_changes = []
        for field in sorted(set(left_values) | set(right_values)):
            if left_values.get(field) != right_values.get(field):
                stage_changes.append({
                    "stage": stage_type, "field": field, "change_type": "Changed",
                    "before": left_values.get(field), "after": right_values.get(field),
                })
        changes.extend(stage_changes)
        summaries.append({"stage": stage_type, "status": "Changed" if stage_changes else "Unchanged"})
    return {
        "from_version": before.id, "to_version": after.id,
        "from_fingerprint": before.definition_fingerprint,
        "to_fingerprint": after.definition_fingerprint,
        "changes": changes, "stage_summaries": summaries,
        "has_computational_changes": bool(changes),
        "interpretation": "Differences identify computational changes only; they do not rank Pipeline Versions.",
    }