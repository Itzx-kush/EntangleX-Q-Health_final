from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from app.api.schemas import TrainingConfig
from app.database import engine, session_scope
from app.evidence_packages.service import preflight_package
from app.experiments.reports import report_data
from app.lineage.service import lineage_snapshot
from app.model_cards.service import assemble_card
from app.pipelines.schemas import PipelineCreateRequest
from app.pipelines.service import (
    create_pipeline_version,
    definition_fingerprint,
    diff_pipeline_versions,
    ensure_pipeline_for_training_config,
    pipeline_from_training_config,
    pipeline_payload,
    preflight_definition,
    publish_pipeline_version,
)
from app.storage.entities import Experiment, ModelRecord, PipelineStage, PipelineVersion, Run
from app.utils.errors import AppError


def _request(config: TrainingConfig, *, name: str, parent: str | None = None, scaler: str | None = None):
    definition = pipeline_from_training_config(config).model_dump(mode="json")
    if scaler:
        next(stage for stage in definition["stages"] if stage["stage_type"] == "preprocessing")[
            "configuration"
        ]["scaler"] = scaler
    return PipelineCreateRequest(
        pipeline_name=name,
        description="Synthetic registry test definition.",
        parent_pipeline_version_id=parent,
        source_context="test",
        definition=definition,
    )


def test_additive_registry_schema_and_indexes_exist():
    inspector = inspect(engine)
    assert {"pipeline_definitions", "pipeline_versions", "pipeline_stages"}.issubset(
        inspector.get_table_names()
    )
    assert "pipeline_version_id" in {
        column["name"] for column in inspector.get_columns("experiments")
    }
    assert "pipeline_version_id" in {
        column["name"] for column in inspector.get_columns("runs")
    }
    version_indexes = {item["name"] for item in inspector.get_indexes("pipeline_versions")}
    stage_indexes = {item["name"] for item in inspector.get_indexes("pipeline_stages")}
    assert "ix_pipeline_versions_definition_fingerprint" in version_indexes
    assert "ix_pipeline_stages_pipeline_version_id" in stage_indexes


def test_canonicalization_fingerprint_and_preflight_are_deterministic(config):
    definition = pipeline_from_training_config(config)
    reordered = deepcopy(definition.model_dump(mode="json"))
    reordered["stages"] = [
        {key: stage[key] for key in reversed(stage)}
        for stage in reordered["stages"]
    ]
    with session_scope() as session:
        first = preflight_definition(session, definition)
        second = preflight_definition(session, reordered)
    assert first["publishable"] is True
    assert first["fingerprint_deterministic"] is True
    assert first["fingerprint"] == second["fingerprint"] == definition_fingerprint(definition)

    changed = deepcopy(definition.model_dump(mode="json"))
    next(stage for stage in changed["stages"] if stage["stage_type"] == "preprocessing")[
        "configuration"
    ]["scaler"] = "minmax"
    assert definition_fingerprint(changed) != first["fingerprint"]


def test_invalid_definition_and_secret_configuration_are_rejected(client, config):
    payload = _request(config, name=f"Invalid {uuid4()}").model_dump(mode="json")
    payload["definition"]["stages"] = payload["definition"]["stages"][1:]
    for index, stage in enumerate(payload["definition"]["stages"], start=1):
        stage["stage_order"] = index
    response = client.post("/api/pipelines/preflight", json=payload)
    assert response.status_code == 200
    assert response.json()["publishable"] is False
    assert any(item["code"] == "pipeline_stage_required" for item in response.json()["blockers"])

    secret = _request(config, name=f"Secret {uuid4()}").model_dump(mode="json")
    secret["definition"]["stages"][0]["configuration"]["api_token"] = "never-store"
    assert client.post("/api/pipelines", json=secret).status_code == 422


def test_create_publish_reuse_immutability_and_version_history(config):
    family = f"Registry family {uuid4()}"
    with session_scope() as session:
        first, created = create_pipeline_version(session, _request(config, name=family))
        assert created and first.status == "DRAFT"
        first = publish_pipeline_version(session, first.id)
        first_id, first_fingerprint = first.id, first.definition_fingerprint
    with session_scope() as session:
        reused, created = create_pipeline_version(session, _request(config, name=family))
        assert created is False and reused.id == first_id
        second, created = create_pipeline_version(
            session, _request(config, name=family, parent=first_id, scaler="minmax")
        )
        assert created and second.version_label == "v2"
        assert second.parent_pipeline_version_id == first_id
        second_id = publish_pipeline_version(session, second.id).id
    with session_scope() as session:
        first = session.get(PipelineVersion, first_id)
        first.description = "silent rewrite"
        with pytest.raises(AppError) as error:
            session.flush()
        assert error.value.code == "pipeline_version_immutable"
        session.rollback()
    with session_scope() as session:
        payload = pipeline_payload(session, session.get(PipelineVersion, second_id))
    assert payload["version"] == "v2"
    assert payload["definition_fingerprint"] != first_fingerprint


def test_diff_reports_changed_and_unchanged_stages(config):
    family = f"Diff family {uuid4()}"
    with session_scope() as session:
        first, _ = create_pipeline_version(session, _request(config, name=family))
        publish_pipeline_version(session, first.id)
        second, _ = create_pipeline_version(
            session, _request(config, name=family, parent=first.id, scaler="minmax")
        )
        publish_pipeline_version(session, second.id)
        diff = diff_pipeline_versions(session, first.id, second.id)
    assert diff["has_computational_changes"] is True
    assert any(
        item["stage"] == "preprocessing"
        and item["field"] == "scaler"
        and item["change_type"] == "Changed"
        for item in diff["changes"]
    )
    assert any(
        item["stage"] == "feature_engineering" and item["status"] == "Unchanged"
        for item in diff["stage_summaries"]
    )


def test_classical_and_quantum_definitions_capture_expected_stages(config):
    classical = pipeline_from_training_config(config)
    assert "quantum_encoding" not in {item.stage_type for item in classical.stages}
    quantum_payload = config.model_dump(mode="json")
    quantum_payload.update({
        "models": ["qnn"],
        "max_samples": 60,
        "parameters": {**quantum_payload["parameters"], "class_weight": None},
        "pipeline": {
            **quantum_payload["pipeline"],
            "pca_components": quantum_payload["quantum"]["qubits"],
            "angle_scaling": True,
        },
    })
    quantum = pipeline_from_training_config(TrainingConfig.model_validate(quantum_payload))
    encoding = next(item for item in quantum.stages if item.stage_type == "quantum_encoding")
    assert encoding.configuration["hardware_execution_claimed"] is False
    assert encoding.configuration["qiskit"]["qubits"] == quantum_payload["quantum"]["qubits"]


def test_experiment_run_lineage_and_exact_pipeline_binding(config, registered):
    family = f"Binding family {uuid4()}"
    experiment_id, run_id = str(uuid4()), str(uuid4())
    with session_scope() as session:
        version, _ = create_pipeline_version(session, _request(config, name=family))
        publish_pipeline_version(session, version.id)
        version_id = version.id
        experiment = Experiment(
            id=experiment_id,
            dataset_id=registered.id,
            pipeline_version_id=version_id,
            status="completed",
            config={**config.model_dump(mode="json"), "pipeline_version_id": version_id},
            summary={},
        )
        session.add(experiment)
        session.flush()
        session.add(Run(
            id=run_id,
            experiment_id=experiment_id,
            dataset_id=registered.id,
            dataset_version_id=registered.current_version_id,
            pipeline_version_id=version_id,
            status="completed",
            operation_key=f"pipeline-run:{run_id}",
            config=experiment.config,
            execution_metadata={},
            reproducibility_metadata={},
            result_summary={},
        ))
    with session_scope() as session:
        snapshot = lineage_snapshot(session, experiment_id, depth="all")
    types = {node["object_type"] for node in snapshot["nodes"]}
    relationships = {edge["relationship_type"] for edge in snapshot["edges"]}
    assert {"pipeline_definition", "pipeline_version", "pipeline_stage"}.issubset(types)
    assert {"uses_pipeline", "has_pipeline_version", "has_stage"}.issubset(relationships)


def test_rerun_equivalent_configuration_reuses_pipeline(config):
    with session_scope() as session:
        first = ensure_pipeline_for_training_config(session, config)
        retained = ensure_pipeline_for_training_config(
            session, config, parent_pipeline_version_id=first.id
        )
        assert retained.id == first.id


def test_pipeline_identity_is_referenced_by_evidence_card_and_report(config, registered):
    experiment_id, run_id, model_id = str(uuid4()), str(uuid4()), str(uuid4())
    with session_scope() as session:
        version = ensure_pipeline_for_training_config(session, config)
        pipeline_id, pipeline_fingerprint = version.id, version.definition_fingerprint
        payload = {**config.model_dump(mode="json"), "pipeline_version_id": pipeline_id}
        session.add(Experiment(
            id=experiment_id, name="Pipeline integration fixture",
            dataset_id=registered.id, pipeline_version_id=pipeline_id,
            status="completed", config=payload, summary={"limitations": []},
        ))
        session.flush()
        session.add(Run(
            id=run_id, experiment_id=experiment_id, dataset_id=registered.id,
            dataset_version_id=registered.current_version_id,
            pipeline_version_id=pipeline_id, status="completed",
            operation_key=f"pipeline-integration:{run_id}", config=payload,
            execution_metadata={}, reproducibility_metadata={},
            result_summary={}, configuration_fingerprint="c" * 64,
            reproducibility_status="complete",
        ))
        session.flush()
        session.add(ModelRecord(
            id=model_id, experiment_id=experiment_id, run_id=run_id,
            dataset_id=registered.id, model_type="logistic_regression",
            status="ready", artifact_sha256="a" * 64,
            details={"supports_probability": True},
            metrics={"test": {"accuracy": 0.8, "sample_count": 20}},
        ))
    with session_scope() as session:
        package = preflight_package(session, experiment_id)["manifest"]
        card, _, _ = assemble_card(session, model_id)
    report = report_data(experiment_id)
    assert package["pipeline"]["pipeline_version_id"] == pipeline_id
    assert package["pipeline"]["pipeline_fingerprint"] == pipeline_fingerprint
    assert card["reproducibility"]["pipeline_version_id"] == pipeline_id
    assert card["provenance"]["source_context"]["pipeline_fingerprint"] == pipeline_fingerprint
    assert report["pipeline_version"]["pipeline_version_id"] == pipeline_id


def test_pipeline_api_available_and_legacy_states(client, config, registered):
    create = client.post(
        "/api/pipelines",
        json=_request(config, name=f"API family {uuid4()}").model_dump(mode="json"),
    )
    assert create.status_code == 201
    pipeline = create.json()
    assert client.post(f"/api/pipelines/{pipeline['pipeline_version_id']}/publish").status_code == 200
    legacy_id = str(uuid4())
    exact_id = str(uuid4())
    with session_scope() as session:
        session.add_all([
            Experiment(
                id=legacy_id, dataset_id=registered.id, status="completed",
                config=config.model_dump(mode="json"), summary={},
            ),
            Experiment(
                id=exact_id, dataset_id=registered.id,
                pipeline_version_id=pipeline["pipeline_version_id"], status="completed",
                config=config.model_dump(mode="json"), summary={},
            ),
        ])
    legacy = client.get(f"/api/experiments/{legacy_id}/pipeline")
    exact = client.get(f"/api/experiments/{exact_id}/pipeline")
    assert legacy.status_code == 200 and legacy.json()["status"] == "LEGACY_UNRESOLVED"
    assert exact.status_code == 200 and exact.json()["status"] == "AVAILABLE"
    assert exact.json()["pipeline_version"]["pipeline_version_id"] == pipeline["pipeline_version_id"]


def test_used_published_stage_is_immutable(config, registered):
    with session_scope() as session:
        version, _ = create_pipeline_version(
            session, _request(config, name=f"Used pipeline {uuid4()}")
        )
        publish_pipeline_version(session, version.id)
        version_id = version.id
        session.add(Experiment(
            id=str(uuid4()), dataset_id=registered.id,
            pipeline_version_id=version_id, status="created",
            config=config.model_dump(mode="json"), summary={},
        ))
    with session_scope() as session:
        stage = session.query(PipelineStage).filter_by(pipeline_version_id=version_id).first()
        stage.configuration = {"changed": True}
        with pytest.raises(AppError) as error:
            session.flush()
        assert error.value.code == "pipeline_version_immutable"
        session.rollback()