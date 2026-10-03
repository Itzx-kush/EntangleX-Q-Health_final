from sqlalchemy import event, inspect, select

from ..database import SessionLocal
from ..storage.entities import Experiment, PipelineStage, PipelineVersion
from ..utils.errors import AppError

_installed = False


def _protect_pipeline_versions(session, _flush_context, _instances):
    if session.info.get("pipeline_registry_publish"):
        return
    for value in session.dirty:
        value_version_id = (
            value.id if isinstance(value, PipelineVersion)
            else value.pipeline_version_id if isinstance(value, PipelineStage)
            else None
        )
        if value_version_id in session.info.get("pipeline_registry_created_ids", set()):
            continue
        protected_fields = (
            (
                "pipeline_definition_id", "version_number", "version_label",
                "schema_version", "status", "definition_fingerprint",
                "canonical_definition", "parent_pipeline_version_id",
                "controlled_comparison_protocol_id", "artifact_id",
                "description", "source_context", "published_at",
            )
            if isinstance(value, PipelineVersion)
            else (
                "pipeline_version_id", "stage_order", "stage_type", "stage_name",
                "configuration", "component_version", "stage_fingerprint",
            )
            if isinstance(value, PipelineStage)
            else ()
        )
        if not protected_fields or not any(
            inspect(value).attrs[field].history.has_changes()
            for field in protected_fields
        ):
            continue
        version = value if isinstance(value, PipelineVersion) else (
            session.get(PipelineVersion, value.pipeline_version_id)
            if isinstance(value, PipelineStage) else None
        )
        if version is None:
            continue
        used = session.scalar(select(Experiment.id).where(
            Experiment.pipeline_version_id == version.id
        ).limit(1))
        if version.status != "DRAFT" or used is not None:
            raise AppError(
                "pipeline_version_immutable",
                "Published or used Pipeline Versions cannot be modified; create a new version.",
                409,
            )


def install_pipeline_immutability() -> None:
    global _installed
    if _installed:
        return
    event.listen(SessionLocal.class_, "before_flush", _protect_pipeline_versions)
    _installed = True