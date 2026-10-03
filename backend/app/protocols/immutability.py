from __future__ import annotations

from sqlalchemy import event, inspect, select

from ..database import SessionLocal
from ..storage.entities import Experiment, ExperimentProtocolVersion
from ..utils.errors import AppError

_installed = False


def _protect_protocol_versions(session, _flush_context, _instances):
    if session.info.get("protocol_registry_publish"):
        return
    for value in session.dirty:
        if not isinstance(value, ExperimentProtocolVersion):
            continue
        if value.id in session.info.get("protocol_registry_created_ids", set()):
            continue
        protected_fields = (
            "protocol_id", "version_number", "version_label",
            "schema_version", "status", "definition_fingerprint",
            "canonical_definition", "parent_protocol_version_id",
            "template_id", "pipeline_version_id",
            "controlled_comparison_protocol_id", "artifact_id",
            "description", "source_context", "published_at",
        )
        if not any(inspect(value).attrs[field].history.has_changes() for field in protected_fields):
            continue
        used = session.scalar(
            select(Experiment.id).where(Experiment.protocol_version_id == value.id).limit(1)
        )
        if value.status != "DRAFT" or used is not None:
            raise AppError(
                "protocol_version_immutable",
                "Published or used Protocol Versions cannot be modified; create a new version.",
                409,
            )


def install_protocol_immutability() -> None:
    global _installed
    if _installed:
        return
    event.listen(SessionLocal.class_, "before_flush", _protect_protocol_versions)
    _installed = True
