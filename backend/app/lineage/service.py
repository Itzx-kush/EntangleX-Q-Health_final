from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Iterable
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

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
    Job,
    JobCheckpoint,
    JobExecutionUnit,
    LineageEdge,
    LineageNode,
    ModelRecord,
    MultiSeedStudy,
    QuantumDiagnosticReport,
    ResearchEvidencePackage,
    RobustnessRecord,
    Run,
    StudyRun,
    ThresholdAnalysisStudy,
)
from ..storage.repository import require
from ..utils.errors import AppError
from ..utils.serialization import clean_json, fingerprint, utcnow

LINEAGE_SCHEMA_VERSION = "deep_experiment_lineage_v1"
MAX_ALL_DEPTH = 12
MAX_GRAPH_NODES = 500

EVIDENCE_TYPES = {
    "multi_seed_study", "study_run", "external_validation",
    "distribution_shift_analysis", "calibration_study",
    "threshold_analysis_study", "robustness_record", "ablation_study",
    "quantum_diagnostic_report", "controlled_comparison_protocol",
    "explanation_record", "research_evidence_package",
}

MODEL_BY_TYPE = {
    "dataset": Dataset,
    "dataset_version": DatasetVersion,
    "experiment": Experiment,
    "run": Run,
    "job": Job,
    "job_checkpoint": JobCheckpoint,
    "job_execution_unit": JobExecutionUnit,
    "model_record": ModelRecord,
    "artifact": Artifact,
    "multi_seed_study": MultiSeedStudy,
    "study_run": StudyRun,
    "external_validation": ExternalValidation,
    "distribution_shift_analysis": DistributionShiftAnalysis,
    "calibration_study": CalibrationStudy,
    "threshold_analysis_study": ThresholdAnalysisStudy,
    "robustness_record": RobustnessRecord,
    "ablation_study": AblationStudy,
    "quantum_diagnostic_report": QuantumDiagnosticReport,
    "controlled_comparison_protocol": ControlledComparisonProtocol,
    "explanation_record": ExplanationRecord,
    "research_evidence_package": ResearchEvidencePackage,
}

TYPE_BY_MODEL = {model: object_type for object_type, model in MODEL_BY_TYPE.items()}

ALLOWED_RELATIONSHIPS = {
    "has_version": {("dataset", "dataset_version")},
    "selected_by": {
        ("dataset", "experiment"), ("dataset_version", "experiment"),
        ("dataset_version", "run"), ("dataset_version", "model_record"),
        ("dataset_version", "multi_seed_study"),
        ("dataset_version", "external_validation"),
        ("dataset_version", "distribution_shift_analysis"),
        ("dataset_version", "calibration_study"),
        ("dataset_version", "threshold_analysis_study"),
        ("dataset_version", "ablation_study"),
    },
    "rerun_of": {("experiment", "experiment")},
    "produced_run": {("experiment", "run"), ("multi_seed_study", "run")},
    "scheduled_as": {
        ("experiment", "job"), ("run", "job"), ("multi_seed_study", "job"),
    },
    "checkpointed_as": {("job", "job_checkpoint")},
    "executed_unit": {("job", "job_execution_unit")},
    "produced_model": {("experiment", "model_record"), ("run", "model_record")},
    "has_evidence": {
        ("experiment", object_type) for object_type in EVIDENCE_TYPES
    } | {
        ("model_record", object_type) for object_type in EVIDENCE_TYPES
    } | {
        ("run", object_type) for object_type in EVIDENCE_TYPES
    } | {
        ("multi_seed_study", "study_run"),
        ("multi_seed_study", "external_validation"),
        ("multi_seed_study", "distribution_shift_analysis"),
        ("external_validation", "distribution_shift_analysis"),
    },
    "produced_experiment": {("ablation_study", "experiment")},
    "produced_artifact": {
        ("experiment", "artifact"), ("run", "artifact"),
        ("model_record", "artifact"), ("job", "artifact"),
        ("job_checkpoint", "artifact"),
    } | {(object_type, "artifact") for object_type in EVIDENCE_TYPES},
    "documented_by": {("model_record", "artifact")},
    "packaged_as": {("experiment", "research_evidence_package")},
    "included_in": {
        ("artifact", "research_evidence_package"),
        *((object_type, "research_evidence_package") for object_type in EVIDENCE_TYPES if object_type != "research_evidence_package"),
    },
    "represented_by": {("research_evidence_package", "artifact")},
}


def node_id(object_type: str, object_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"qhealth:lineage-node:{object_type}:{object_id}"))


def edge_id(source_type: str, source_id: str, target_type: str, target_id: str, relationship: str) -> str:
    return str(uuid5(
        NAMESPACE_URL,
        f"qhealth:lineage-edge:{source_type}:{source_id}:{relationship}:{target_type}:{target_id}",
    ))


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _stable_fingerprint(value: Any, object_type: str) -> str | None:
    for field in (
        "package_fingerprint", "protocol_fingerprint", "configuration_fingerprint",
        "state_fingerprint", "result_fingerprint", "integrity_hash",
        "version_signature", "artifact_sha256", "sha256",
    ):
        found = getattr(value, field, None)
        if found:
            return str(found)
    if object_type == "dataset_version":
        return getattr(value, "content_sha256", None)
    if object_type == "experiment":
        return fingerprint(getattr(value, "config", {}) or {})
    if object_type in {"calibration_study", "threshold_analysis_study", "distribution_shift_analysis"}:
        return fingerprint(getattr(value, "configuration", {}) or {})
    return None


def _node_from_object(value: Any) -> dict:
    object_type = TYPE_BY_MODEL[type(value)]
    object_id = str(value.id)
    metadata: dict[str, Any] = {}
    for field in (
        "name", "status", "model_type", "artifact_type", "version_label",
        "version_number", "checkpoint_type", "logical_unit", "job_type",
        "method", "perturbation_type", "schema_version", "source_context_type",
    ):
        found = getattr(value, field, None)
        if found is not None:
            metadata[field] = clean_json(found)
    if object_type == "artifact":
        metadata["immutable"] = bool(value.immutable)
        metadata["content_type"] = value.content_type
    return {
        "id": node_id(object_type, object_id),
        "object_type": object_type,
        "object_id": object_id,
        "label": metadata.get("name") or metadata.get("artifact_type") or metadata.get("model_type") or object_type.replace("_", " "),
        "status": metadata.get("status"),
        "version": metadata.get("version_label") or metadata.get("schema_version"),
        "fingerprint": _stable_fingerprint(value, object_type),
        "created_at": _iso(getattr(value, "created_at", None) or getattr(value, "recorded_at", None)),
        "exists": True,
        "metadata": metadata,
    }


def _placeholder(object_type: str, object_id: str | None) -> dict | None:
    if not object_id:
        return None
    return {
        "id": node_id(object_type, str(object_id)),
        "object_type": object_type,
        "object_id": str(object_id),
        "label": object_type.replace("_", " "),
        "status": None,
        "version": None,
        "fingerprint": None,
        "created_at": None,
        "exists": False,
        "metadata": {},
    }


def _edge(
    source_type: str,
    source_id: str | None,
    target_type: str,
    target_id: str | None,
    relationship: str,
    *,
    timestamp: datetime | None = None,
    metadata: dict | None = None,
) -> tuple[list[dict], dict] | None:
    if not source_id or not target_id:
        return None
    source_id, target_id = str(source_id), str(target_id)
    basis = {
        "schema_version": LINEAGE_SCHEMA_VERSION,
        "source_type": source_type, "source_id": source_id,
        "target_type": target_type, "target_id": target_id,
        "relationship_type": relationship,
    }
    return (
        [_placeholder(source_type, source_id), _placeholder(target_type, target_id)],
        {
            "id": edge_id(source_type, source_id, target_type, target_id, relationship),
            "source_node_id": node_id(source_type, source_id),
            "target_node_id": node_id(target_type, target_id),
            "relationship_type": relationship,
            "schema_version": LINEAGE_SCHEMA_VERSION,
            "relationship_fingerprint": fingerprint(basis),
            "recorded_at": _iso(timestamp),
            "metadata": clean_json(metadata or {}),
            "capture_state": "legacy_reconstructed",
        },
    )


def specs_for_object(value: Any) -> tuple[list[dict], list[dict]]:
    """Return safe node/edge references supported by explicit persisted fields."""
    if type(value) not in TYPE_BY_MODEL:
        return [], []
    nodes = [_node_from_object(value)]
    edges: list[dict] = []
    created = getattr(value, "created_at", None)

    def add(source_type, source_id, target_type, target_id, relationship, metadata=None):
        result = _edge(
            source_type, source_id, target_type, target_id, relationship,
            timestamp=created, metadata=metadata,
        )
        if result:
            extra_nodes, edge = result
            nodes.extend(node for node in extra_nodes if node)
            edges.append(edge)

    if isinstance(value, DatasetVersion):
        add("dataset", value.dataset_id, "dataset_version", value.id, "has_version")
    elif isinstance(value, Experiment):
        version_id = (value.config or {}).get("dataset_version_id")
        add("dataset", value.dataset_id, "experiment", value.id, "selected_by")
        add("dataset_version", version_id, "experiment", value.id, "selected_by")
        add("experiment", value.parent_id, "experiment", value.id, "rerun_of", {"target_is_rerun": True})
    elif isinstance(value, Run):
        add("experiment", value.experiment_id, "run", value.id, "produced_run")
        add("dataset_version", value.dataset_version_id, "run", value.id, "selected_by")
    elif isinstance(value, Job):
        add("experiment", value.experiment_id, "job", value.id, "scheduled_as")
        add("run", value.run_id, "job", value.id, "scheduled_as")
        add("job", value.id, "artifact", value.output_artifact_id, "produced_artifact")
    elif isinstance(value, JobCheckpoint):
        add("job", value.job_id, "job_checkpoint", value.id, "checkpointed_as")
        for artifact_id in value.artifact_references or []:
            add("job_checkpoint", value.id, "artifact", artifact_id, "produced_artifact")
    elif isinstance(value, JobExecutionUnit):
        add("job", value.job_id, "job_execution_unit", value.id, "executed_unit")
    elif isinstance(value, ModelRecord):
        add("experiment", value.experiment_id, "model_record", value.id, "produced_model")
        add("run", value.run_id, "model_record", value.id, "produced_model")
        version_id = (value.details or {}).get("dataset_version_id") or (value.details or {}).get("configuration", {}).get("dataset_version_id")
        add("dataset_version", version_id, "model_record", value.id, "selected_by")
    elif isinstance(value, Artifact):
        relationship = "documented_by" if value.artifact_type == "model_card" else "produced_artifact"
        add("experiment", value.experiment_id, "artifact", value.id, "produced_artifact")
        add("run", value.run_id, "artifact", value.id, "produced_artifact")
        add("model_record", value.model_id, "artifact", value.id, relationship)
    elif isinstance(value, MultiSeedStudy):
        add("experiment", value.base_experiment_id, "multi_seed_study", value.id, "has_evidence")
        add("dataset_version", value.dataset_version_id, "multi_seed_study", value.id, "selected_by")
        add("multi_seed_study", value.id, "artifact", value.study_artifact_id, "produced_artifact")
    elif isinstance(value, StudyRun):
        add("multi_seed_study", value.study_id, "study_run", value.id, "has_evidence")
        add("multi_seed_study", value.study_id, "run", value.run_id, "produced_run")
        add("multi_seed_study", value.study_id, "job", value.job_id, "scheduled_as")
    elif isinstance(value, ExternalValidation):
        add("experiment", value.experiment_id, "external_validation", value.id, "has_evidence")
        add("model_record", value.model_id, "external_validation", value.id, "has_evidence")
        add("run", value.run_id, "external_validation", value.id, "has_evidence")
        add("multi_seed_study", value.study_id, "external_validation", value.id, "has_evidence")
        add("dataset_version", value.training_dataset_version_id, "external_validation", value.id, "selected_by", {"role": "training"})
        add("dataset_version", value.external_dataset_version_id, "external_validation", value.id, "selected_by", {"role": "external"})
        add("external_validation", value.id, "artifact", value.artifact_id, "produced_artifact")
    elif isinstance(value, DistributionShiftAnalysis):
        add("model_record", value.model_id, "distribution_shift_analysis", value.id, "has_evidence")
        add("external_validation", value.external_validation_id, "distribution_shift_analysis", value.id, "has_evidence")
        add("multi_seed_study", value.parent_study_id, "distribution_shift_analysis", value.id, "has_evidence")
        add("dataset_version", value.reference_dataset_version_id, "distribution_shift_analysis", value.id, "selected_by", {"role": "reference"})
        add("dataset_version", value.comparison_dataset_version_id, "distribution_shift_analysis", value.id, "selected_by", {"role": "comparison"})
        add("distribution_shift_analysis", value.id, "artifact", value.artifact_id, "produced_artifact")
    elif isinstance(value, CalibrationStudy):
        add("model_record", value.model_id, "calibration_study", value.id, "has_evidence")
        add("dataset_version", value.dataset_version_id, "calibration_study", value.id, "selected_by")
        add("calibration_study", value.id, "artifact", value.artifact_id, "produced_artifact")
    elif isinstance(value, ThresholdAnalysisStudy):
        add("model_record", value.model_id, "threshold_analysis_study", value.id, "has_evidence")
        add("dataset_version", value.dataset_version_id, "threshold_analysis_study", value.id, "selected_by")
    elif isinstance(value, RobustnessRecord):
        add("experiment", value.experiment_id, "robustness_record", value.id, "has_evidence")
        add("model_record", value.model_id, "robustness_record", value.id, "has_evidence")
    elif isinstance(value, AblationStudy):
        add("experiment", value.base_experiment_id, "ablation_study", value.id, "has_evidence")
        add("run", value.base_run_id, "ablation_study", value.id, "has_evidence")
        add("dataset_version", value.dataset_version_id, "ablation_study", value.id, "selected_by")
        add("ablation_study", value.id, "experiment", value.ablation_experiment_id, "produced_experiment")
        add("ablation_study", value.id, "artifact", value.artifact_id, "produced_artifact")
    elif isinstance(value, QuantumDiagnosticReport):
        add("experiment", value.experiment_id, "quantum_diagnostic_report", value.id, "has_evidence")
        add("model_record", value.model_record_id, "quantum_diagnostic_report", value.id, "has_evidence")
    elif isinstance(value, ControlledComparisonProtocol):
        add("experiment", value.experiment_id, "controlled_comparison_protocol", value.id, "has_evidence")
        for model_id_value in (value.classical_model_ids or []) + (value.quantum_model_ids or []):
            add("model_record", model_id_value, "controlled_comparison_protocol", value.id, "has_evidence")
        add("controlled_comparison_protocol", value.id, "artifact", value.artifact_id, "produced_artifact")
    elif isinstance(value, ExplanationRecord):
        add("model_record", value.model_id, "explanation_record", value.id, "has_evidence")
        add("run", value.run_id, "explanation_record", value.id, "has_evidence")
    elif isinstance(value, ResearchEvidencePackage):
        add("experiment", value.experiment_id, "research_evidence_package", value.id, "packaged_as")
        add("research_evidence_package", value.id, "artifact", value.artifact_id, "represented_by")
        for artifact_id_value in (value.provenance or {}).get("artifact_ids", []):
            if artifact_id_value != value.artifact_id:
                add("artifact", artifact_id_value, "research_evidence_package", value.id, "included_in")
    return nodes, edges


def _all_specs(session) -> tuple[dict[str, dict], list[dict], list[LineageNode], list[LineageEdge]]:
    node_map: dict[str, dict] = {}
    edges: list[dict] = []
    for model in MODEL_BY_TYPE.values():
        for value in session.scalars(select(model)):
            nodes, produced = specs_for_object(value)
            for node in nodes:
                current = node_map.get(node["id"])
                if current is None or (node["exists"] and not current["exists"]):
                    node_map[node["id"]] = node
            edges.extend(produced)
    persisted_nodes = list(session.scalars(select(LineageNode)))
    persisted_edges = list(session.scalars(select(LineageEdge)))
    persisted_by_key = {
        (edge.source_node_id, edge.target_node_id, edge.relationship_type): edge
        for edge in persisted_edges
    }
    seen: set[tuple[str, str, str]] = set()
    unique_edges: list[dict] = []
    for edge in edges:
        key = (edge["source_node_id"], edge["target_node_id"], edge["relationship_type"])
        if key in seen:
            continue
        seen.add(key)
        persisted = persisted_by_key.get(key)
        if persisted:
            edge.update({
                "id": persisted.id,
                "relationship_fingerprint": persisted.relationship_fingerprint,
                "recorded_at": _iso(persisted.recorded_at),
                "metadata": clean_json(persisted.relationship_metadata or {}),
                "capture_state": "recorded",
            })
        unique_edges.append(edge)
    for edge in persisted_edges:
        key = (edge.source_node_id, edge.target_node_id, edge.relationship_type)
        if key not in seen:
            unique_edges.append({
                "id": edge.id,
                "source_node_id": edge.source_node_id,
                "target_node_id": edge.target_node_id,
                "relationship_type": edge.relationship_type,
                "schema_version": edge.schema_version,
                "relationship_fingerprint": edge.relationship_fingerprint,
                "recorded_at": _iso(edge.recorded_at),
                "metadata": clean_json(edge.relationship_metadata or {}),
                "capture_state": "recorded",
            })
    for persisted in persisted_nodes:
        if persisted.id not in node_map:
            node_map[persisted.id] = {
                "id": persisted.id, "object_type": persisted.object_type,
                "object_id": persisted.object_id,
                "label": persisted.object_type.replace("_", " "),
                "status": None, "version": None,
                "fingerprint": persisted.reference_fingerprint,
                "created_at": _iso(persisted.recorded_at),
                "exists": False, "metadata": clean_json(persisted.reference_metadata or {}),
            }
    return node_map, unique_edges, persisted_nodes, persisted_edges


def _is_allowed(edge: dict, nodes: dict[str, dict]) -> bool:
    source, target = nodes.get(edge["source_node_id"]), nodes.get(edge["target_node_id"])
    if not source or not target:
        return False
    return (source["object_type"], target["object_type"]) in ALLOWED_RELATIONSHIPS.get(edge["relationship_type"], set())


def _cycles(nodes: set[str], edges: list[dict]) -> list[list[str]]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge["source_node_id"] in nodes and edge["target_node_id"] in nodes:
            adjacency[edge["source_node_id"]].append(edge["target_node_id"])
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []
    found: list[list[str]] = []

    def visit(node: str):
        if node in visiting:
            index = stack.index(node)
            found.append(stack[index:] + [node])
            return
        if node in visited:
            return
        visiting.add(node)
        stack.append(node)
        for target in adjacency.get(node, []):
            visit(target)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for node in sorted(nodes):
        visit(node)
    return found[:20]


def _traverse(center: str, edges: list[dict], direction: str, depth: int) -> tuple[set[str], dict[str, int]]:
    incoming: dict[str, list[str]] = defaultdict(list)
    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        outgoing[edge["source_node_id"]].append(edge["target_node_id"])
        incoming[edge["target_node_id"]].append(edge["source_node_id"])

    selected = {center}
    distances = {center: 0}

    def walk(adjacency: dict[str, list[str]]):
        queue = deque([(center, 0)])
        local_seen = {center}
        while queue and len(selected) < MAX_GRAPH_NODES:
            current, current_depth = queue.popleft()
            if current_depth >= depth:
                continue
            for adjacent in sorted(adjacency.get(current, [])):
                selected.add(adjacent)
                distances[adjacent] = min(distances.get(adjacent, depth + 1), current_depth + 1)
                if adjacent not in local_seen:
                    local_seen.add(adjacent)
                    queue.append((adjacent, current_depth + 1))

    if direction in {"ancestors", "both"}:
        walk(incoming)
    if direction in {"descendants", "both"}:
        walk(outgoing)
    return selected, distances


def lineage_snapshot(
    session,
    experiment_id: str,
    *,
    depth: int | str = 3,
    direction: str = "both",
    include_artifacts: bool = True,
    include_evidence: bool = True,
) -> dict:
    require(session, Experiment, experiment_id)
    if direction not in {"ancestors", "descendants", "both"}:
        raise AppError("invalid_lineage_request", "Lineage direction must be ancestors, descendants, or both.", 422)
    if depth == "all":
        resolved_depth = MAX_ALL_DEPTH
    else:
        try:
            resolved_depth = int(depth)
        except (TypeError, ValueError):
            raise AppError("invalid_lineage_request", "Lineage depth must be 1-12 or all.", 422)
        if not 1 <= resolved_depth <= MAX_ALL_DEPTH:
            raise AppError("invalid_lineage_request", "Lineage depth must be 1-12 or all.", 422)

    nodes, all_edges, persisted_nodes, persisted_edges = _all_specs(session)
    filtered_nodes = {
        key: node for key, node in nodes.items()
        if (include_artifacts or node["object_type"] != "artifact")
        and (include_evidence or node["object_type"] not in EVIDENCE_TYPES)
    }
    filtered_edges = [
        edge for edge in all_edges
        if edge["source_node_id"] in filtered_nodes and edge["target_node_id"] in filtered_nodes
    ]
    center = node_id("experiment", experiment_id)
    selected, distances = _traverse(center, filtered_edges, direction, resolved_depth)
    selected &= set(filtered_nodes)
    selected_edges = [
        edge for edge in filtered_edges
        if edge["source_node_id"] in selected and edge["target_node_id"] in selected
    ]

    duplicate_counts: dict[tuple[str, str, str], int] = defaultdict(int)
    for edge in persisted_edges:
        duplicate_counts[(edge.source_node_id, edge.target_node_id, edge.relationship_type)] += 1
    duplicates = [
        {"source_node_id": key[0], "target_node_id": key[1], "relationship_type": key[2], "count": count}
        for key, count in duplicate_counts.items() if count > 1
    ]
    missing = sorted(
        {
            node["id"]: {
                "node_id": node["id"], "object_type": node["object_type"],
                "object_id": node["object_id"],
            }
            for node in filtered_nodes.values()
            if node["id"] in selected and not node["exists"]
        }.values(),
        key=lambda value: (value["object_type"], value["object_id"]),
    )
    invalid_edges = [
        {"edge_id": edge["id"], "relationship_type": edge["relationship_type"], "reason": "unsupported relationship or node types"}
        for edge in selected_edges if not _is_allowed(edge, filtered_nodes)
    ]
    current_fingerprints = {node["id"]: node.get("fingerprint") for node in filtered_nodes.values()}
    fingerprint_mismatches = [
        {
            "node_id": persisted.id,
            "object_type": persisted.object_type,
            "object_id": persisted.object_id,
            "recorded_fingerprint": persisted.reference_fingerprint,
            "current_fingerprint": current_fingerprints.get(persisted.id),
        }
        for persisted in persisted_nodes
        if persisted.id in selected
        and persisted.reference_fingerprint
        and current_fingerprints.get(persisted.id)
        and persisted.reference_fingerprint != current_fingerprints[persisted.id]
    ]
    cycles = _cycles(selected, selected_edges)
    legacy_edges = [edge["id"] for edge in selected_edges if edge["capture_state"] == "legacy_reconstructed"]
    integrity = {
        "missing_references": missing,
        "orphaned_edges": [
            {"edge_id": edge.id, "source_node_id": edge.source_node_id, "target_node_id": edge.target_node_id}
            for edge in persisted_edges
            if edge.source_node_id not in {node.id for node in persisted_nodes}
            or edge.target_node_id not in {node.id for node in persisted_nodes}
        ],
        "invalid_edges": invalid_edges,
        "duplicate_relationships": duplicates,
        "fingerprint_mismatches": fingerprint_mismatches,
        "cycles": cycles,
        "legacy_reconstructed_edges": legacy_edges,
        "truncated": len(selected) >= MAX_GRAPH_NODES,
    }
    severe = any((cycles, invalid_edges, fingerprint_mismatches, duplicates, integrity["orphaned_edges"]))
    status = "INTEGRITY_REVIEW" if severe else (
        "LEGACY_UNRESOLVED" if missing else (
            "PARTIAL" if legacy_edges or integrity["truncated"] else "COMPLETE"
        )
    )
    selected_nodes = sorted(
        ({**filtered_nodes[key], "depth": distances.get(key, 0)} for key in selected),
        key=lambda node: (node["depth"], node["object_type"], node["object_id"]),
    )
    selected_edges = sorted(
        selected_edges,
        key=lambda edge: (edge["relationship_type"], edge["source_node_id"], edge["target_node_id"]),
    )
    roots = sorted(
        node["id"] for node in selected_nodes
        if not any(edge["target_node_id"] == node["id"] for edge in selected_edges)
    )
    fingerprint_basis = {
        "schema_version": LINEAGE_SCHEMA_VERSION,
        "nodes": [
            {
                "id": node["id"], "object_type": node["object_type"],
                "object_id": node["object_id"], "fingerprint": node["fingerprint"],
            }
            for node in sorted(selected_nodes, key=lambda value: value["id"])
        ],
        "edges": [
            {
                "source_node_id": edge["source_node_id"],
                "target_node_id": edge["target_node_id"],
                "relationship_type": edge["relationship_type"],
                "relationship_fingerprint": edge["relationship_fingerprint"],
            }
            for edge in sorted(selected_edges, key=lambda value: value["id"])
        ],
    }
    return {
        "experiment_id": experiment_id,
        "lineage_schema_version": LINEAGE_SCHEMA_VERSION,
        "status": status,
        "lineage_fingerprint": fingerprint(fingerprint_basis),
        "roots": roots,
        "nodes": selected_nodes,
        "edges": selected_edges,
        "summary": {
            "node_count": len(selected_nodes),
            "edge_count": len(selected_edges),
            "root_count": len(roots),
            "max_depth": max((node["depth"] for node in selected_nodes), default=0),
            "requested_depth": depth,
            "direction": direction,
        },
        "integrity": integrity,
        "limitations": [
            "Lineage records persisted provenance metadata; it does not establish causality, scientific validity, or model quality.",
            "Legacy relationships are reconstructed only from explicit persisted identifiers and are marked partial.",
        ],
    }


def lineage_preflight(session, experiment_id: str) -> dict:
    snapshot = lineage_snapshot(
        session, experiment_id, depth="all", direction="both",
        include_artifacts=True, include_evidence=True,
    )
    integrity = snapshot["integrity"]
    return {
        "experiment_id": experiment_id,
        "feasible": not any((
            integrity["cycles"], integrity["invalid_edges"],
            integrity["fingerprint_mismatches"], integrity["duplicate_relationships"],
        )),
        "status": snapshot["status"],
        "lineage_fingerprint": snapshot["lineage_fingerprint"],
        "summary": snapshot["summary"],
        "integrity": integrity,
    }


def record_edge(
    session,
    *,
    source_type: str,
    source_id: str,
    target_type: str,
    target_id: str,
    relationship_type: str,
    metadata: dict | None = None,
    source_fingerprint: str | None = None,
    target_fingerprint: str | None = None,
) -> LineageEdge:
    if (source_type, target_type) not in ALLOWED_RELATIONSHIPS.get(relationship_type, set()):
        raise AppError("invalid_lineage_relationship", "The requested lineage relationship is not supported.", 422)
    source_node_id, target_node_id = node_id(source_type, source_id), node_id(target_type, target_id)
    if source_node_id == target_node_id:
        raise AppError("cyclic_provenance_relationship", "A lineage relationship cannot point to itself.", 409)
    existing = session.scalar(select(LineageEdge).where(
        LineageEdge.source_node_id == source_node_id,
        LineageEdge.target_node_id == target_node_id,
        LineageEdge.relationship_type == relationship_type,
    ))
    basis = {
        "schema_version": LINEAGE_SCHEMA_VERSION,
        "source_type": source_type, "source_id": source_id,
        "target_type": target_type, "target_id": target_id,
        "relationship_type": relationship_type,
    }
    relationship_fingerprint = fingerprint(basis)
    if existing:
        if (
            existing.relationship_fingerprint != relationship_fingerprint
            or (existing.relationship_metadata or {}) != (metadata or {})
        ):
            raise AppError("immutable_lineage_conflict", "The historical lineage relationship cannot be rewritten.", 409)
        return existing

    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in session.scalars(select(LineageEdge)):
        adjacency[edge.source_node_id].append(edge.target_node_id)
    queue, visited = deque([target_node_id]), set()
    while queue:
        current = queue.popleft()
        if current == source_node_id:
            raise AppError("cyclic_provenance_relationship", "The lineage relationship would create a cycle.", 409)
        if current in visited:
            continue
        visited.add(current)
        queue.extend(adjacency.get(current, []))

    for object_type, object_id_value, fingerprint_value in (
        (source_type, source_id, source_fingerprint),
        (target_type, target_id, target_fingerprint),
    ):
        identity = node_id(object_type, object_id_value)
        if session.get(LineageNode, identity) is None:
            session.add(LineageNode(
                id=identity, object_type=object_type, object_id=object_id_value,
                schema_version=LINEAGE_SCHEMA_VERSION,
                reference_fingerprint=fingerprint_value,
                reference_metadata={},
            ))
    session.flush()
    edge = LineageEdge(
        id=edge_id(source_type, source_id, target_type, target_id, relationship_type),
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        relationship_type=relationship_type,
        schema_version=LINEAGE_SCHEMA_VERSION,
        relationship_fingerprint=relationship_fingerprint,
        relationship_metadata=metadata or {},
        immutable=True,
        recorded_at=utcnow(),
    )
    session.add(edge)
    session.flush()
    return edge