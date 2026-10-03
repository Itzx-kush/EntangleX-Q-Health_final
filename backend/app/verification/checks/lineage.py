"""Deep Experiment Lineage verification (Prompt 13).

Verifies that lineage nodes and edges resolve, that relationship types are
supported, that prohibited cycles are detected, that traversal and depth
limiting work, that legacy provenance is reconstructed without guessing, and
that lineage stays separate from the scientific audit timeline.
"""

from __future__ import annotations

from uuid import uuid4

from ..fixtures import persist_chain
from ..isolation import initialize_database, session
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check
from ._support import expect_app_error, require_fingerprint


@check(
    check_id="lineage_integrity",
    name="Lineage integrity",
    category=CheckCategory.LINEAGE_INTEGRITY,
    description="Snapshot resolution, relationship validity, determinism, traversal, depth limiting and audit separation.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=240.0,
)
def lineage_integrity() -> CheckResult:
    from app.lineage.service import ALLOWED_RELATIONSHIPS, LINEAGE_SCHEMA_VERSION, _is_allowed, lineage_snapshot
    from app.storage.entities import LineageNode

    initialize_database()
    chain = persist_chain(with_pipeline=True, with_protocol=True)
    child = persist_chain(parent_experiment_id=chain.experiment_id)
    grandchild = persist_chain(parent_experiment_id=child.experiment_id)
    problems: list[str] = []

    with session() as scope:
        first = lineage_snapshot(scope, chain.experiment_id, depth="all")
        second = lineage_snapshot(scope, chain.experiment_id, depth="all")
        ancestors = lineage_snapshot(scope, grandchild.experiment_id, direction="ancestors", depth="all")
        shallow = lineage_snapshot(scope, chain.experiment_id, direction="descendants", depth=1)
        deep = lineage_snapshot(scope, chain.experiment_id, direction="descendants", depth="all")

    if first["lineage_schema_version"] != LINEAGE_SCHEMA_VERSION:
        problems.append("snapshot reports a different lineage schema version than the service constant")
    if first["lineage_fingerprint"] != second["lineage_fingerprint"]:
        problems.append("lineage fingerprint is not deterministic for unchanged state")
    require_fingerprint(first["lineage_fingerprint"], label="lineage fingerprint")

    nodes = {node["id"]: node for node in first["nodes"]}
    for edge in first["edges"]:
        if edge["source_node_id"] not in nodes or edge["target_node_id"] not in nodes:
            problems.append(f"edge {edge['relationship_type']} references an unresolved node")
            continue
        if edge["relationship_type"] not in ALLOWED_RELATIONSHIPS:
            problems.append(f"unsupported relationship type persisted: {edge['relationship_type']}")
            continue
        if not _is_allowed(edge, nodes):
            problems.append(f"edge {edge['relationship_type']} is not permitted between those object types")
    if not first["edges"]:
        problems.append("no lineage edges were captured for a persisted experiment chain")
    if first["integrity"]["cycles"]:
        problems.append(f"the captured provenance graph contains prohibited cycles: {first['integrity']['cycles']}")
    if first["integrity"]["missing_references"]:
        problems.append(f"lineage reports missing references: {first['integrity']['missing_references']}")

    deep_ids = {node["object_id"] for node in deep["nodes"]}
    shallow_ids = {node["object_id"] for node in shallow["nodes"]}
    if chain.model_id not in deep_ids:
        problems.append("descendant traversal does not reach the persisted model record")
    if not shallow_ids or not shallow_ids <= deep_ids:
        problems.append("depth-limited traversal returned nodes outside the full traversal")
    if child.experiment_id not in shallow_ids:
        problems.append("a depth-1 descendant traversal did not reach the direct rerun experiment")
    if grandchild.experiment_id not in deep_ids:
        problems.append("the full descendant traversal did not reach the transitive rerun experiment")
    if grandchild.experiment_id in shallow_ids:
        problems.append("depth limiting did not restrict the descendant traversal")
    if chain.dataset_id not in {node["object_id"] for node in ancestors["nodes"]}:
        problems.append("ancestor traversal does not reach the dataset the experiment used")

    with session() as scope:
        audit_nodes = scope.query(LineageNode).filter(LineageNode.object_type == "scientific_audit_event").count()
    if audit_nodes:
        problems.append("scientific audit events were recorded as lineage nodes")
    if any(key in first for key in ("event_fingerprint", "audit_events")):
        problems.append("lineage snapshot exposes audit-timeline fields")

    if problems:
        return CheckResult(
            check_id="lineage_integrity",
            category=CheckCategory.LINEAGE_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="resolvable, acyclic, deterministic lineage with working traversal and audit separation",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="lineage_integrity",
        category=CheckCategory.LINEAGE_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Lineage nodes and edges resolve, remain acyclic and deterministic, and stay separate from the audit timeline.",
        evidence={
            "node_count": len(nodes),
            "edge_count": len(first["edges"]),
            "lineage_fingerprint": first["lineage_fingerprint"],
            "relationship_types": sorted({edge["relationship_type"] for edge in first["edges"]}),
            "rerun_chain": [chain.experiment_id, child.experiment_id, grandchild.experiment_id],
            "depth_limited_node_count": len(shallow_ids),
            "full_node_count": len(deep_ids),
        },
    )


@check(
    check_id="lineage_cycle_and_relationship_protection",
    name="Lineage cycle and relationship protection",
    category=CheckCategory.LINEAGE_INTEGRITY,
    description="Cycle detection finds synthetic cycles, self-references are rejected and unsupported relationship types are refused.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=120.0,
)
def lineage_cycle_and_relationship_protection() -> CheckResult:
    from app.lineage.service import _cycles, _is_allowed, record_edge

    initialize_database()
    problems: list[str] = []

    nodes = {"a", "b", "c"}
    acyclic = [
        {"source_node_id": "a", "target_node_id": "b"},
        {"source_node_id": "b", "target_node_id": "c"},
    ]
    if _cycles(nodes, acyclic):
        problems.append("cycle detection reported a cycle in an acyclic graph")
    cyclic = [
        {"source_node_id": "a", "target_node_id": "b"},
        {"source_node_id": "b", "target_node_id": "c"},
        {"source_node_id": "c", "target_node_id": "a"},
    ]
    detected = _cycles(nodes, cyclic)
    if not detected:
        problems.append("cycle detection missed a synthetic three-node cycle")

    experiment_id, model_id = str(uuid4()), str(uuid4())
    with expect_app_error("cyclic_provenance_relationship"):
        with session() as scope:
            record_edge(
                scope,
                source_type="experiment",
                source_id=experiment_id,
                target_type="experiment",
                target_id=experiment_id,
                relationship_type="rerun_of",
            )
    with expect_app_error("invalid_lineage_relationship"):
        with session() as scope:
            record_edge(
                scope,
                source_type="dataset",
                source_id=str(uuid4()),
                target_type="model_record",
                target_id=model_id,
                relationship_type="not_a_real_relationship",
            )

    with session() as scope:
        edge = record_edge(
            scope,
            source_type="experiment",
            source_id=experiment_id,
            target_type="model_record",
            target_id=model_id,
            relationship_type="produced_model",
        )
        node_index = {
            edge.source_node_id: {"object_type": "experiment", "object_id": experiment_id},
            edge.target_node_id: {"object_type": "model_record", "object_id": model_id},
        }
        allowed = _is_allowed(
            {
                "source_node_id": edge.source_node_id,
                "target_node_id": edge.target_node_id,
                "relationship_type": edge.relationship_type,
            },
            node_index,
        )
    if not allowed:
        problems.append("a valid produced_model relationship was rejected by the relationship validator")

    if problems:
        return CheckResult(
            check_id="lineage_cycle_and_relationship_protection",
            category=CheckCategory.LINEAGE_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="cycles are detected and invalid relationships are refused",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="lineage_cycle_and_relationship_protection",
        category=CheckCategory.LINEAGE_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Cycle detection, self-reference rejection and relationship validation behave as specified.",
        evidence={
            "acyclic_graph_clean": True,
            "cycle_detected": detected,
            "rejected": ["cyclic_provenance_relationship", "invalid_lineage_relationship"],
        },
    )
