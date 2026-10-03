from uuid import uuid4

import pytest
from sqlalchemy import func, inspect, select

from app.database import engine, session_scope
from app.lineage.service import (
    LINEAGE_SCHEMA_VERSION,
    lineage_preflight,
    lineage_snapshot,
    node_id,
    record_edge,
)
from app.storage.entities import (
    AblationStudy,
    Artifact,
    CalibrationStudy,
    ControlledComparisonProtocol,
    Experiment,
    LineageEdge,
    LineageNode,
    ModelRecord,
    QuantumDiagnosticReport,
    ResearchEvidencePackage,
    Run,
    ThresholdAnalysisStudy,
)
from app.utils.serialization import utcnow


def _experiment_graph(registered, *, parent_id=None, with_run=True, with_model=True):
    experiment_id, run_id, model_id = str(uuid4()), str(uuid4()), str(uuid4())
    config = {
        "dataset_id": registered.id,
        "dataset_version_id": registered.current_version_id,
        "models": ["logistic_regression"],
        "seed": 42,
    }
    with session_scope() as session:
        session.add(Experiment(
            id=experiment_id,
            name=f"Lineage fixture {experiment_id[:8]}",
            dataset_id=registered.id,
            parent_id=parent_id,
            status="completed",
            config=config,
            summary={},
        ))
        session.flush()
        if with_run:
            session.add(Run(
                id=run_id,
                experiment_id=experiment_id,
                dataset_id=registered.id,
                dataset_version_id=registered.current_version_id,
                status="completed",
                operation_key=f"lineage-run:{run_id}",
                config=config,
                execution_metadata={},
                reproducibility_metadata={},
                result_summary={},
                configuration_fingerprint="c" * 64,
            ))
            session.flush()
        if with_model:
            session.add(ModelRecord(
                id=model_id,
                experiment_id=experiment_id,
                run_id=run_id if with_run else None,
                dataset_id=registered.id,
                model_type="logistic_regression",
                status="ready",
                artifact_sha256="a" * 64,
                details={"configuration": config},
                metrics={"test": {"accuracy": 0.8, "sample_count": 20}},
            ))
    return experiment_id, run_id if with_run else None, model_id if with_model else None


def _types(snapshot):
    return {node["object_type"] for node in snapshot["nodes"]}


def _relationships(snapshot):
    return {edge["relationship_type"] for edge in snapshot["edges"]}


def test_additive_lineage_schema_and_indexes_exist():
    inspector = inspect(engine)
    assert {"lineage_nodes", "lineage_edges"}.issubset(inspector.get_table_names())
    node_indexes = {index["name"] for index in inspector.get_indexes("lineage_nodes")}
    edge_indexes = {index["name"] for index in inspector.get_indexes("lineage_edges")}
    assert {"ix_lineage_nodes_object_type", "ix_lineage_nodes_object_id"}.issubset(node_indexes)
    assert {"ix_lineage_edges_source_node_id", "ix_lineage_edges_target_node_id"}.issubset(edge_indexes)


def test_basic_lineage_is_captured_and_deterministic(registered):
    experiment_id, run_id, model_id = _experiment_graph(registered)
    with session_scope() as session:
        first = lineage_snapshot(session, experiment_id, depth="all")
        second = lineage_snapshot(session, experiment_id, depth="all")
    assert first["lineage_schema_version"] == LINEAGE_SCHEMA_VERSION
    assert {"dataset", "dataset_version", "experiment", "run", "model_record"}.issubset(_types(first))
    assert {"selected_by", "produced_run", "produced_model"}.issubset(_relationships(first))
    assert next(node for node in first["nodes"] if node["object_id"] == run_id)["object_type"] == "run"
    assert next(node for node in first["nodes"] if node["object_id"] == model_id)["fingerprint"] == "a" * 64
    assert first["lineage_fingerprint"] == second["lineage_fingerprint"]
    assert all(edge["capture_state"] == "recorded" for edge in first["edges"])


def test_rerun_ancestors_descendants_and_depth_limit(registered):
    parent_id, _, _ = _experiment_graph(registered)
    child_id, _, _ = _experiment_graph(registered, parent_id=parent_id)
    grandchild_id, _, _ = _experiment_graph(registered, parent_id=child_id)
    with session_scope() as session:
        ancestors = lineage_snapshot(session, grandchild_id, direction="ancestors", depth="all")
        descendants = lineage_snapshot(session, parent_id, direction="descendants", depth="all")
        shallow = lineage_snapshot(session, parent_id, direction="descendants", depth=1)
    ancestor_ids = {node["object_id"] for node in ancestors["nodes"]}
    descendant_ids = {node["object_id"] for node in descendants["nodes"]}
    shallow_ids = {node["object_id"] for node in shallow["nodes"]}
    assert {parent_id, child_id, grandchild_id}.issubset(ancestor_ids)
    assert {parent_id, child_id, grandchild_id}.issubset(descendant_ids)
    assert child_id in shallow_ids
    assert grandchild_id not in shallow_ids
    assert any(edge["relationship_type"] == "rerun_of" for edge in descendants["edges"])


def test_legacy_explicit_relationships_are_reconstructed_without_guessing(registered):
    experiment_id, _, _ = _experiment_graph(registered, with_run=False, with_model=False)
    with session_scope() as session:
        node_ids = [
            node_id("experiment", experiment_id),
            node_id("dataset", registered.id),
            node_id("dataset_version", registered.current_version_id),
        ]
        session.query(LineageEdge).filter(
            (LineageEdge.source_node_id.in_(node_ids)) | (LineageEdge.target_node_id.in_(node_ids))
        ).delete(synchronize_session=False)
        session.query(LineageNode).filter(LineageNode.id.in_(node_ids)).delete(synchronize_session=False)
    with session_scope() as session:
        snapshot = lineage_snapshot(session, experiment_id, depth="all")
    assert snapshot["status"] == "PARTIAL"
    assert snapshot["integrity"]["legacy_reconstructed_edges"]
    assert not snapshot["integrity"]["cycles"]
    assert all(node["object_id"] != "guessed-parent" for node in snapshot["nodes"])


def test_missing_reference_and_fingerprint_mismatch_are_reported(registered):
    experiment_id, run_id, model_id = _experiment_graph(registered)
    threshold_id = str(uuid4())
    with session_scope() as session:
        session.add(ThresholdAnalysisStudy(
            id=threshold_id,
            model_id=model_id,
            dataset_id=registered.id,
            dataset_version_id=registered.current_version_id,
            operation_key=f"lineage-threshold:{threshold_id}",
            configuration={},
            status="completed",
            created_at=utcnow(),
        ))
        session.flush()
        session.delete(session.get(ModelRecord, model_id))
    with session_scope() as session:
        node = session.get(LineageNode, node_id("run", run_id))
        node.reference_fingerprint = "f" * 64
    with session_scope() as session:
        snapshot = lineage_snapshot(session, experiment_id, depth="all")
        preflight = lineage_preflight(session, experiment_id)
    assert any(item["object_id"] == model_id for item in snapshot["integrity"]["missing_references"])
    assert any(item["object_id"] == run_id for item in snapshot["integrity"]["fingerprint_mismatches"])
    assert preflight["feasible"] is False
    assert snapshot["status"] == "INTEGRITY_REVIEW"


def test_cycle_protection_duplicate_idempotency_and_immutability(registered):
    a, _, _ = _experiment_graph(registered, with_run=False, with_model=False)
    b, _, _ = _experiment_graph(registered, with_run=False, with_model=False)
    c, _, _ = _experiment_graph(registered, with_run=False, with_model=False)
    with session_scope() as session:
        first = record_edge(
            session, source_type="experiment", source_id=a,
            target_type="experiment", target_id=b,
            relationship_type="rerun_of", metadata={"source": "test"},
        )
        same = record_edge(
            session, source_type="experiment", source_id=a,
            target_type="experiment", target_id=b,
            relationship_type="rerun_of", metadata={"source": "test"},
        )
        assert first.id == same.id
        record_edge(
            session, source_type="experiment", source_id=b,
            target_type="experiment", target_id=c,
            relationship_type="rerun_of",
        )
        with pytest.raises(Exception) as cycle:
            record_edge(
                session, source_type="experiment", source_id=c,
                target_type="experiment", target_id=a,
                relationship_type="rerun_of",
            )
        with pytest.raises(Exception) as rewrite:
            record_edge(
                session, source_type="experiment", source_id=a,
                target_type="experiment", target_id=b,
                relationship_type="rerun_of", metadata={"source": "changed"},
            )
        count = session.scalar(select(func.count()).select_from(LineageEdge).where(
            LineageEdge.source_node_id == node_id("experiment", a),
            LineageEdge.target_node_id == node_id("experiment", b),
            LineageEdge.relationship_type == "rerun_of",
        ))
    assert getattr(cycle.value, "code", None) == "cyclic_provenance_relationship"
    assert getattr(rewrite.value, "code", None) == "immutable_lineage_conflict"
    assert count == 1


def test_evidence_model_card_protocol_and_package_integration(registered):
    experiment_id, run_id, model_id = _experiment_graph(registered)
    artifact_id, card_id = str(uuid4()), str(uuid4())
    calibration_id, threshold_id, ablation_id, diagnostic_id = [str(uuid4()) for _ in range(4)]
    protocol_id, package_id = str(uuid4()), str(uuid4())
    with session_scope() as session:
        session.add_all([
            Artifact(
                id=artifact_id, experiment_id=experiment_id, run_id=run_id, model_id=None,
                artifact_type="research_evidence_package", name="Package artifact",
                description="", integrity_hash="1" * 64, hash_algorithm="sha256",
                content_type="application/json", details={}, immutable=True,
                operation_key=f"lineage-artifact:{artifact_id}",
            ),
            Artifact(
                id=card_id, experiment_id=experiment_id, run_id=run_id, model_id=model_id,
                artifact_type="model_card", name="Model Card", description="",
                integrity_hash="2" * 64, hash_algorithm="sha256",
                content_type="application/json", details={"schema_version": "model_card_v1"},
                immutable=True, operation_key=f"lineage-card:{card_id}",
            ),
        ])
        session.flush()
        session.add_all([
            CalibrationStudy(
                id=calibration_id, model_id=model_id, dataset_id=registered.id,
                dataset_version_id=registered.current_version_id, status="completed",
                operation_key=f"lineage-calibration:{calibration_id}", configuration={},
            ),
            ThresholdAnalysisStudy(
                id=threshold_id, model_id=model_id, dataset_id=registered.id,
                dataset_version_id=registered.current_version_id, status="completed",
                operation_key=f"lineage-threshold:{threshold_id}", configuration={},
            ),
            AblationStudy(
                id=ablation_id, base_experiment_id=experiment_id, base_run_id=run_id,
                dataset_id=registered.id, dataset_version_id=registered.current_version_id,
                status="completed", operation_key=f"lineage-ablation:{ablation_id}",
                configuration_fingerprint="3" * 64,
            ),
            QuantumDiagnosticReport(
                id=diagnostic_id, experiment_id=experiment_id, model_record_id=model_id,
                model_type="vqc", status="completed", configuration_fingerprint="4" * 64,
            ),
            ControlledComparisonProtocol(
                id=protocol_id, experiment_id=experiment_id,
                schema_version="controlled_comparison_v1", status="CONTROLLED",
                operation_key=f"lineage-protocol:{protocol_id}",
                configuration_fingerprint="5" * 64, protocol_fingerprint="6" * 64,
                classical_model_ids=[model_id], quantum_model_ids=[],
            ),
            ResearchEvidencePackage(
                id=package_id, experiment_id=experiment_id,
                schema_version="research_evidence_package_v1", status="PARTIAL",
                package_fingerprint="7" * 64, configuration_fingerprint="c" * 64,
                source_context_type="live_run", evidence_inventory={},
                provenance={"artifact_ids": [card_id]}, limitations=[],
                evidence_gaps=[], manifest={}, artifact_id=artifact_id,
            ),
        ])
    with session_scope() as session:
        snapshot = lineage_snapshot(session, experiment_id, depth="all")
    object_types = _types(snapshot)
    assert {
        "calibration_study", "threshold_analysis_study", "ablation_study",
        "quantum_diagnostic_report", "controlled_comparison_protocol",
        "research_evidence_package", "artifact",
    }.issubset(object_types)
    assert any(
        node["object_id"] == card_id and node["metadata"]["artifact_type"] == "model_card"
        for node in snapshot["nodes"]
    )
    assert {"has_evidence", "documented_by", "packaged_as", "included_in"}.issubset(_relationships(snapshot))


def test_lineage_api_filters_and_safe_errors(client, registered):
    experiment_id, _, _ = _experiment_graph(registered)
    response = client.get(f"/api/experiments/{experiment_id}/lineage?depth=2&direction=both")
    assert response.status_code == 200
    assert response.json()["experiment_id"] == experiment_id
    assert client.get(f"/api/experiments/{experiment_id}/lineage/ancestors?depth=1").status_code == 200
    assert client.get(f"/api/experiments/{experiment_id}/lineage/descendants?depth=1").status_code == 200
    assert client.get(f"/api/experiments/{experiment_id}/lineage/preflight").status_code == 200
    filtered = client.get(
        f"/api/experiments/{experiment_id}/lineage?depth=all&include_artifacts=false&include_evidence=false"
    )
    assert filtered.status_code == 200
    assert "artifact" not in {node["object_type"] for node in filtered.json()["nodes"]}
    assert client.get(f"/api/experiments/{experiment_id}/lineage?depth=99").status_code == 422
    assert client.get(f"/api/experiments/{uuid4()}/lineage").status_code == 404