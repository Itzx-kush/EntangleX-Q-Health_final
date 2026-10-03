from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from ..database import SessionLocal
from ..storage.entities import LineageEdge, LineageNode
from ..utils.serialization import utcnow
from .service import LINEAGE_SCHEMA_VERSION, specs_for_object

_installed = False


def _capture_after_flush(session, _flush_context) -> None:
    """Record relationships at creation time without another ORM flush cycle."""
    node_rows: dict[str, dict] = {}
    edge_rows: dict[str, dict] = {}
    for value in session.new:
        if isinstance(value, (LineageNode, LineageEdge)):
            continue
        nodes, edges = specs_for_object(value)
        for node in nodes:
            node_rows[node["id"]] = {
                "id": node["id"],
                "object_type": node["object_type"],
                "object_id": node["object_id"],
                "schema_version": LINEAGE_SCHEMA_VERSION,
                "reference_fingerprint": node.get("fingerprint"),
                "reference_metadata": node.get("metadata") or {},
                "recorded_at": utcnow(),
            }
        for edge in edges:
            edge_rows[edge["id"]] = {
                "id": edge["id"],
                "source_node_id": edge["source_node_id"],
                "target_node_id": edge["target_node_id"],
                "relationship_type": edge["relationship_type"],
                "schema_version": LINEAGE_SCHEMA_VERSION,
                "relationship_fingerprint": edge["relationship_fingerprint"],
                "relationship_metadata": edge.get("metadata") or {},
                "immutable": True,
                "recorded_at": utcnow(),
            }
    if not node_rows and not edge_rows:
        return
    connection = session.connection()
    if node_rows:
        connection.execute(
            sqlite_insert(LineageNode.__table__).values(list(node_rows.values())).on_conflict_do_nothing()
        )
    if edge_rows:
        connection.execute(
            sqlite_insert(LineageEdge.__table__).values(list(edge_rows.values())).on_conflict_do_nothing()
        )


def install_lineage_capture() -> None:
    global _installed
    if _installed:
        return
    event.listen(SessionLocal.class_, "after_flush", _capture_after_flush)
    _installed = True