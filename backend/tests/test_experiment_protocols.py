from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import inspect, select

from app.api.schemas import TrainingConfig
from app.database import engine, session_scope
from app.evidence_packages.service import preflight_package
from app.experiments.reports import html_report, report_data
from app.lineage.service import lineage_snapshot
from app.manifests.service import build_manifest
from app.model_cards.service import assemble_card
from app.protocols.compliance import evaluate_experiment_compliance
from app.protocols.schemas import (
    ALLOWED_METRICS,
    ProtocolCreateRequest,
    ProtocolDefinitionSpec,
    TemplateInstantiateRequest,
)
from app.protocols.service import (
    attach_protocol_to_experiment,
    canonicalize_definition,
    create_protocol_version,
    definition_fingerprint,
    diff_protocol_versions,
    instantiate_protocol_template,
    list_protocol_templates,
    list_protocol_versions,
    preflight_definition,
    protocol_payload,
    publish_protocol_version,
)
from app.protocols.templates import BUILTIN_TEMPLATES
from app.storage.entities import (
    Artifact,
    ControlledComparisonProtocol,
    Dataset,
    Experiment,
    ExperimentProtocol,
    ExperimentProtocolVersion,
    ModelRecord,
    PipelineVersion,
    ProtocolTemplate,
    Run,
)
from app.utils.errors import AppError


def _sample_definition(
    *,
    task_type: str = "binary_classification",
    primary_metric: str = "roc_auc",
    cv_folds: int = 5,
    test_size: float = 0.2,
    seeds: list[int] | None = None,
    calibration_req: str = "REQUIRED",
    external_req: str = "OPTIONAL",
    pipeline_version_id: str | None = None,
    controlled_id: str | None = None,
) -> dict:
    return {
        "study_metadata": {
            "study_purpose": "Biomedical Diabetes Classification Protocol",
            "task_type": task_type,
            "task_description": "Standard binary classification protocol for clinical tabular data.",
            "experiment_scope": "biomedical_classification",
        },
        "dataset_policy": {
            "target_column": "Outcome",
            "positive_label": "1",
            "negative_label": "0",
        },
        "split_policy": {
            "strategy": "stratified_kfold",
            "test_size": test_size,
            "cv_folds": cv_folds,
            "stratify": True,
            "split_seed": 42,
        },
        "randomness_policy": {
            "primary_seed": 42,
            "seed_list": seeds or [42, 101, 202, 303, 404],
            "multi_seed_count": len(seeds or [42, 101, 202, 303, 404]),
            "determinism_required": True,
        },
        "model_policy": {
            "allowed_model_types": ["logistic_regression", "random_forest", "hybrid_pennylane_torch"],
            "model_families": ["classical", "hybrid"],
        },
        "pipeline_policy": {
            "requirement": "REQUIRED" if pipeline_version_id else "OPTIONAL",
            "pipeline_version_id": pipeline_version_id,
        },
        "evaluation_policy": {
            "primary_metric": primary_metric,
            "secondary_metrics": ["pr_auc", "f1"],
            "confidence_intervals": True,
            "statistical_reporting": True,
        },
        "threshold_policy": {
            "requirement": "REQUIRED",
            "strategy": "fixed",
            "fixed_threshold": 0.5,
            "lock_threshold": True,
        },
        "calibration_policy": {
            "requirement": calibration_req,
            "method": "isotonic",
            "calibration_split": "cv",
            "calibration_metrics": ["brier_score"],
        },
        "validation_extensions": {
            "multi_seed": {"requirement": "REQUIRED", "min_seed_count": 5},
            "external_validation": {"requirement": external_req},
            "distribution_shift": {"requirement": "OPTIONAL"},
            "group_validation": {"requirement": "DISABLED"},
            "robustness": {"requirement": "OPTIONAL", "perturbation_types": ["gaussian_noise"]},
            "ablation": {"requirement": "DISABLED"},
        },
        "quantum_controls": {
            "requirement": "REQUIRED" if controlled_id else "OPTIONAL",
            "controlled_comparison_protocol_id": controlled_id,
            "dataset_parity": True,
            "sample_parity": True,
            "test_population_parity": True,
            "preprocessing_parity": True,
            "seed_policy_parity": True,
            "provider_provenance": True,
        },
        "constraints": {
            "minimum_seed_count": 5,
            "required_cv_folds": cv_folds,
            "required_metrics": [primary_metric],
            "calibration_required": calibration_req == "REQUIRED",
            "threshold_must_be_locked": True,
        },
    }


def _create_request(name: str, definition: dict, parent_protocol_version_id: str | None = None) -> ProtocolCreateRequest:
    return ProtocolCreateRequest(
        protocol_name=name,
        description="Test experiment protocol definition.",
        parent_protocol_version_id=parent_protocol_version_id,
        source_context="unit_tests",
        definition=ProtocolDefinitionSpec.model_validate(definition),
    )


def _setup_experiment_and_run(session, registered, config, *, protocol_version=None):
    experiment_id = str(uuid4())
    run_id = str(uuid4())
    model_id = str(uuid4())
    payload = config.model_dump(mode="json")

    experiment = Experiment(
        id=experiment_id,
        name="Protocol Test Experiment",
        dataset_id=registered.id,
        pipeline_version_id=None,
        protocol_version_id=protocol_version.id if protocol_version else None,
        protocol_fingerprint=protocol_version.definition_fingerprint if protocol_version else None,
        status="completed",
        config=payload,
        summary={
            "dataset_provenance": registered.provenance,
            "split": {"cv_folds": 5, "test_size": 0.2, "seed": 42},
            "limitations": [],
        },
    )
    session.add(experiment)
    session.flush()

    run = Run(
        id=run_id,
        experiment_id=experiment_id,
        dataset_id=registered.id,
        dataset_version_id=registered.current_version_id,
        pipeline_version_id=None,
        protocol_version_id=protocol_version.id if protocol_version else None,
        protocol_fingerprint=protocol_version.definition_fingerprint if protocol_version else None,
        status="completed",
        operation_key=f"protocol-test:{run_id}",
        config=payload,
        execution_metadata={},
        reproducibility_metadata={"split_seed": 42},
        result_summary={},
        configuration_fingerprint="c" * 64,
        reproducibility_status="complete",
    )
    session.add(run)
    session.flush()

    model = ModelRecord(
        id=model_id,
        experiment_id=experiment_id,
        run_id=run_id,
        dataset_id=registered.id,
        model_type="logistic_regression",
        status="ready",
        artifact_sha256="a" * 64,
        details={"supports_probability": True},
        metrics={
            "test": {"roc_auc": 0.85, "pr_auc": 0.78, "f1": 0.75, "sample_count": 24},
            "validation": {"mean_roc_auc": 0.82},
            "calibration": {"brier_score": 0.12},
            "operating_point": {"threshold": 0.5, "locked": True},
        },
    )
    session.add(model)
    session.flush()

    return experiment, run, model


def test_protocol_schema_and_indexes_exist():
    inspector = inspect(engine)
    assert {"protocol_templates", "experiment_protocols", "experiment_protocol_versions"}.issubset(
        inspector.get_table_names()
    )
    assert "protocol_version_id" in {col["name"] for col in inspector.get_columns("experiments")}
    assert "protocol_fingerprint" in {col["name"] for col in inspector.get_columns("experiments")}
    assert "protocol_version_id" in {col["name"] for col in inspector.get_columns("runs")}
    assert "protocol_fingerprint" in {col["name"] for col in inspector.get_columns("runs")}

    version_indexes = {idx["name"] for idx in inspector.get_indexes("experiment_protocol_versions")}
    assert "ix_exp_proto_ver_fingerprint" in version_indexes
    assert "ix_experiments_protocol_version_id" in {idx["name"] for idx in inspector.get_indexes("experiments")}

    with session_scope() as session:
        templates = list_protocol_templates(session)
        assert len(templates) >= 5
        template_names = {t["name"] for t in templates}
        assert "Biomedical Binary Classification" in template_names
        assert "External Validation Study" in template_names
        assert "Quantum-vs-Classical Controlled Study" in template_names


def test_canonicalization_and_fingerprint_deterministic():
    def1 = _sample_definition(primary_metric="roc_auc", cv_folds=5)
    def2 = deepcopy(def1)
    # Reorder dictionary keys
    def2["split_policy"] = {k: def2["split_policy"][k] for k in reversed(list(def2["split_policy"].keys()))}
    def2["study_metadata"]["task_description"] = "  Standard binary classification protocol for clinical tabular data.  "

    fp1 = definition_fingerprint(def1)
    fp2 = definition_fingerprint(def2)
    # Whitespace in description gets stripped in normalizer
    assert fp1 == fp2

    # Semantic change changes fingerprint
    def3 = deepcopy(def1)
    def3["split_policy"]["cv_folds"] = 10
    fp3 = definition_fingerprint(def3)
    assert fp3 != fp1

    # Evaluation metric change changes fingerprint
    def4 = deepcopy(def1)
    def4["evaluation_policy"]["primary_metric"] = "pr_auc"
    fp4 = definition_fingerprint(def4)
    assert fp4 != fp1


def test_invalid_protocol_definitions_rejected():
    # Test invalid CV folds (< 2)
    bad_cv = _sample_definition()
    bad_cv["split_policy"]["cv_folds"] = 1
    with pytest.raises(Exception):
        ProtocolDefinitionSpec.model_validate(bad_cv)

    # Test invalid metric
    bad_metric = _sample_definition()
    bad_metric["evaluation_policy"]["primary_metric"] = "unknown_metric_foo"
    with pytest.raises(Exception):
        ProtocolDefinitionSpec.model_validate(bad_metric)

    # Test invalid requirement
    bad_req = _sample_definition()
    bad_req["calibration_policy"]["requirement"] = "MAYBE"
    with pytest.raises(Exception):
        ProtocolDefinitionSpec.model_validate(bad_req)


def test_preflight_checks_and_warnings():
    with session_scope() as session:
        # Valid definition
        valid_def = _sample_definition()
        res = preflight_definition(session, valid_def)
        assert res["valid"] is True
        assert res["publishable"] is True
        assert res["blockers"] == []

        # Definition referencing non-existent pipeline version
        bad_pipe = _sample_definition(pipeline_version_id=str(uuid4()))
        res_pipe = preflight_definition(session, bad_pipe)
        assert res_pipe["publishable"] is False
        assert any(b["code"] == "pipeline_version_not_found" for b in res_pipe["blockers"])

        # Definition referencing non-existent controlled protocol
        bad_ctrl = _sample_definition(controlled_id=str(uuid4()))
        res_ctrl = preflight_definition(session, bad_ctrl)
        assert res_ctrl["publishable"] is False
        assert any(b["code"] == "controlled_comparison_not_found" for b in res_ctrl["blockers"])

        # External validation required without external dataset ID yields warning
        warn_ext = _sample_definition(external_req="REQUIRED")
        res_ext = preflight_definition(session, warn_ext)
        assert res_ext["publishable"] is True
        assert any(w["code"] == "external_dataset_unspecified" for w in res_ext["warnings"])


def test_create_publish_idempotency_and_immutability():
    proto_name = f"Cardiology Clinical Study {uuid4().hex[:8]}"
    def_data = _sample_definition()

    with session_scope() as session:
        v1, created = create_protocol_version(session, _create_request(proto_name, def_data))
        assert created is True
        assert v1.status == "DRAFT"
        assert v1.version_number == 1
        v1_id = v1.id
        v1_fp = v1.definition_fingerprint

        # Idempotent re-creation
        v1_again, created_again = create_protocol_version(session, _create_request(proto_name, def_data))
        assert created_again is False
        assert v1_again.id == v1_id

        # Publish
        published = publish_protocol_version(session, v1_id)
        assert published.status == "PUBLISHED"
        assert published.published_at is not None


    # Mutating published protocol raises AppError
    with session_scope() as session:
        v1_db = session.get(ExperimentProtocolVersion, v1_id)
        v1_db.description = "Silent modification attempt"
        with pytest.raises(AppError) as exc_info:
            session.flush()
        assert exc_info.value.code == "protocol_version_immutable"
        session.rollback()


def test_protocol_version_derivation_and_diff():
    proto_name = f"Neurology Study {uuid4().hex[:8]}"
    def1 = _sample_definition(cv_folds=5, primary_metric="roc_auc")
    def2 = _sample_definition(cv_folds=10, primary_metric="pr_auc")

    with session_scope() as session:
        v1, _ = create_protocol_version(session, _create_request(proto_name, def1))
        v1 = publish_protocol_version(session, v1.id)
        v1_id = v1.id

        # Derive v2
        v2, created = create_protocol_version(session, _create_request(proto_name, def2, parent_protocol_version_id=v1_id))
        assert created is True
        assert v2.version_number == 2
        assert v2.parent_protocol_version_id == v1_id
        v2 = publish_protocol_version(session, v2.id)
        v2_id = v2.id

        # Diff v1 and v2
        diff = diff_protocol_versions(session, v1_id, v2_id)
        assert diff["identical"] is False
        assert diff["change_count"] > 0
        diff_fields = {c["field"] for c in diff["changes"]}
        assert "cv_folds" in diff_fields
        assert "primary_metric" in diff_fields

        # Diff identical
        diff_same = diff_protocol_versions(session, v1_id, v1_id)
        assert diff_same["identical"] is True
        assert diff_same["change_count"] == 0


def test_template_instantiation():
    with session_scope() as session:
        templates = list_protocol_templates(session)
        tmpl = next(t for t in templates if t["name"] == "Biomedical Binary Classification")

        req = TemplateInstantiateRequest(
            protocol_name=f"Instantiated Study {uuid4().hex[:6]}",
            description="Testing template instantiation",
            parameters={
                "cv_folds": 10,
                "primary_metric": "pr_auc",
                "calibration_required": True,
            },
        )
        version, created = instantiate_protocol_template(session, tmpl["id"], req)
        assert created is True
        assert version.version_number == 1
        assert version.template_id == tmpl["id"]
        assert version.canonical_definition["split_policy"]["cv_folds"] == 10
        assert version.canonical_definition["evaluation_policy"]["primary_metric"] == "pr_auc"
        assert version.canonical_definition["calibration_policy"]["requirement"] == "REQUIRED"


def test_attach_protocol_to_experiment_and_run(registered, config):
    proto_name = f"Trial Study {uuid4().hex[:6]}"
    def_data = _sample_definition()

    with session_scope() as session:
        experiment, run, model = _setup_experiment_and_run(session, registered, config)
        exp_id, run_id = experiment.id, run.id

        v1, _ = create_protocol_version(session, _create_request(proto_name, def_data))
        v1 = publish_protocol_version(session, v1.id)
        v1_id = v1.id
        v1_fp = v1.definition_fingerprint

        # Attach to experiment
        version = attach_protocol_to_experiment(session, exp_id, v1_id)
        assert version.id == v1_id

        exp_db = session.get(Experiment, exp_id)
        assert exp_db.protocol_version_id == v1_id
        assert exp_db.protocol_fingerprint == v1_fp

        # Associated run also gets protocol attached
        run_db = session.get(Run, run_id)
        assert run_db.protocol_version_id == v1_id
        assert run_db.protocol_fingerprint == v1_fp

        # Attaching a different protocol to the same experiment raises 409
        v2, _ = create_protocol_version(
            session,
            _create_request(proto_name, _sample_definition(cv_folds=10), parent_protocol_version_id=v1_id),
        )
        with pytest.raises(AppError) as exc_info:
            attach_protocol_to_experiment(session, exp_id, v2.id)
        assert exc_info.value.code == "protocol_already_attached"


def test_factual_compliance_evaluation(registered, config):
    proto_name = f"Compliance Test Protocol {uuid4().hex[:6]}"
    def_data = _sample_definition()

    with session_scope() as session:
        experiment, run, model = _setup_experiment_and_run(session, registered, config)
        exp_id = experiment.id

        v1, _ = create_protocol_version(session, _create_request(proto_name, def_data))
        v1 = publish_protocol_version(session, v1.id)
        attach_protocol_to_experiment(session, exp_id, v1.id)

        compliance = evaluate_experiment_compliance(session, exp_id)

        assert compliance["experiment_id"] == exp_id
        assert compliance["protocol_version_id"] == v1.id
        assert compliance["status"] == "AVAILABLE"
        assert "compliance_summary" in compliance

        summary = compliance["compliance_summary"]
        assert "total_checks" in summary
        assert summary["total_checks"] > 0
        assert "matched" in summary
        assert "missing" in summary
        assert "mismatched" in summary
        assert "not_applicable" in summary
        assert "unverifiable" in summary

        # Confirm NO quality/percentage score exists
        assert "score" not in summary
        assert "percentage" not in summary
        assert "grade" not in summary

        # All checks have valid factual statuses
        valid_statuses = {"MATCHED", "MISSING", "MISMATCHED", "NOT_APPLICABLE", "UNVERIFIABLE"}
        for check in compliance["checks"]:
            assert check["status"] in valid_statuses
            assert "category" in check
            assert "rule" in check
            assert "expected" in check
            assert "actual" in check
            assert "details" in check


def test_legacy_experiment_without_protocol(registered, config):
    with session_scope() as session:
        experiment, run, model = _setup_experiment_and_run(session, registered, config)
        exp_id = experiment.id

    with session_scope() as session:
        compliance = evaluate_experiment_compliance(session, exp_id)
        assert compliance["status"] == "UNAVAILABLE"
        assert compliance["compliance_summary"]["total_checks"] == 0

    # Reports don't crash and report LEGACY_UNSPECIFIED
    data = report_data(exp_id)
    assert data["protocol"]["status"] == "LEGACY_UNSPECIFIED"

    html = html_report(exp_id)
    assert "<h2>Experiment protocol</h2>" in html
    assert "LEGACY_UNSPECIFIED" in html


def test_lineage_and_manifest_integration(registered, config):
    proto_name = f"Lineage Protocol {uuid4().hex[:6]}"
    def_data = _sample_definition()

    with session_scope() as session:
        v1, _ = create_protocol_version(session, _create_request(proto_name, def_data))
        v1 = publish_protocol_version(session, v1.id)
        v1_id = v1.id
        v1_fp = v1.definition_fingerprint

        experiment, run, model = _setup_experiment_and_run(session, registered, config, protocol_version=v1)
        exp_id, model_id = experiment.id, model.id

    with session_scope() as session:
        # Lineage snapshot contains protocol nodes & edges
        snapshot = lineage_snapshot(session, exp_id, depth="all")
        types = {node["object_type"] for node in snapshot["nodes"]}
        relationships = {edge["relationship_type"] for edge in snapshot["edges"]}
        assert "protocol_version" in types
        assert "applied_to" in relationships

        # Research evidence package preflight includes protocol identity
        pkg_preflight = preflight_package(session, exp_id)
        assert "protocol" in pkg_preflight["manifest"]
        assert pkg_preflight["manifest"]["protocol"]["protocol_version_id"] == v1_id
        assert pkg_preflight["manifest"]["protocol"]["protocol_fingerprint"] == v1_fp

        # Model card contains protocol section
        card, source, _ = assemble_card(session, model_id)
        assert "protocol" in source
        assert source["protocol"]["protocol_version_id"] == v1_id
        assert card["reproducibility"]["protocol_version_id"] == v1_id



