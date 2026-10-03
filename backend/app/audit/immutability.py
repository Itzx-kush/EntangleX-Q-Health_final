from __future__ import annotations

from sqlalchemy import event
from ..storage.entities import ScientificAuditEvent
from ..utils.errors import AppError


def prevent_audit_modification(mapper, connection, target: ScientificAuditEvent) -> None:
    raise AppError(
        "audit_event_immutable",
        f"Scientific audit events are immutable. Modification of event {target.id} is strictly prohibited.",
        409,
    )


def prevent_audit_deletion(mapper, connection, target: ScientificAuditEvent) -> None:
    raise AppError(
        "audit_event_immutable",
        f"Scientific audit events are immutable. Deletion of event {target.id} is strictly prohibited.",
        409,
    )


def register_audit_immutability() -> None:
    event.listen(ScientificAuditEvent, "before_update", prevent_audit_modification)
    event.listen(ScientificAuditEvent, "before_delete", prevent_audit_deletion)
