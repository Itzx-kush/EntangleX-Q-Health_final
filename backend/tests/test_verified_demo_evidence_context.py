from uuid import uuid4

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sqlalchemy import func, select

from app.api.schemas import TrainingConfig
from app.calibration.schemas import CalibrationRequest
from app.calibration.service import execute_calibration_study, preflight as calibration_preflight
from app.data.splitting import prepare_data
from app.database import session_scope
from app.evaluation.context import resolve_model_evaluation_context
from app.model_cards.service import assemble_card
from app.storage.entities import (
    CalibrationStudy, Experiment, ModelRecord, Run, ThresholdAnalysisStudy,
)
from app.storage.files import save_model
from app.threshold.schemas import ThresholdAnalysisRequest
from app.threshold.service import execute_threshold_study, preflight as threshold_preflight
from app.utils.serialization import fingerprint, utcnow


def _verified_demo_model(registered, monkeypatch, model_type="logistic_regression"):
    experiment_id, model_id = str(uuid4()), str(uuid4())
    config = TrainingConfig(
        dataset_id=registered.id,
        dataset_version_id=registered.current_version_id,
        models=[model_type],
        max_samples=100,
        duplicate_policy="drop_exact",
    ).model_dump(mode="json")
    artifact_hash = "a" * 64
    experiment = {
        "id": experiment_id, "dataset_id": registered.id, "config": config,
    }
    packaged_model = {
        "id": model_id, "experiment_id": experiment_id,
        "dataset_id": registered.id, "artifact_sha256": artifact_hash,
    }
    monkeypatch.setattr(
        "app.evaluation.context.validate_packaged_dataset",
        lambda _slug: {
            "catalog": {"sha256": registered.sha256},
            "dataset": {"id": registered.id},
            "experiment": experiment,
            "models": [packaged_model],
            "manifest_sha256": "b" * 64,
        },
    )
    monkeypatch.setattr("app.evaluation.context.verify_installed_model", lambda _model: None)
    with session_scope() as session:
        session.add(Experiment(
            id=experiment_id, name="Verified demo context fixture",
            dataset_id=registered.id, status="succeeded", config=config,
            summary={"artifact_version": "test-verified-package"},
        ))
        session.add(ModelRecord(
            id=model_id, experiment_id=experiment_id, run_id=None,
            dataset_id=registered.id, model_type=model_type, status="ready",
            artifact_sha256=artifact_hash,
            details={
                "experiment_kind": "precomputed_verified_demo",
                "dataset_provenance": {"library_slug": "early-stage-diabetes"},
            },
            metrics={"test": {"accuracy": 0.8}},
        ))
    return experiment_id, model_id, config


def _persist_fitted_artifact(model_id: str, config: dict):
    data = prepare_data(TrainingConfig.model_validate(config))
    estimator = make_pipeline(SimpleImputer(strategy="median"), LogisticRegression(max_iter=200))
    estimator.fit(data.X.iloc[data.train], data.y[data.train])
    artifact_hash = save_model(model_id, {"estimator": estimator})
    with session_scope() as session:
        session.get(ModelRecord, model_id).artifact_sha256 = artifact_hash
    return artifact_hash


def test_verified_demo_context_uses_experiment_config_without_fake_run(registered, monkeypatch):
    experiment_id, model_id, config = _verified_demo_model(registered, monkeypatch)
    with session_scope() as session:
        before = session.scalar(select(func.count()).select_from(Run))
        context = resolve_model_evaluation_context(session, model_id, registered.id)
        after = session.scalar(select(func.count()).select_from(Run))
    assert context.source_context_type == "verified_demo_experiment"
    assert context.run is None
    assert context.experiment.id == experiment_id
    assert context.training_config.seed == config["seed"]
    assert context.configuration_fingerprint == fingerprint(config)
    assert before == after


def test_verified_demo_calibration_computes_and_persists_provenance(registered, monkeypatch):
    _, model_id, config = _verified_demo_model(registered, monkeypatch)
    artifact_hash = _persist_fitted_artifact(model_id, config)
    # Keep the verified package contract aligned with the test artifact.
    with session_scope() as session:
        session.get(ModelRecord, model_id).artifact_sha256 = artifact_hash
    original = __import__("app.evaluation.context", fromlist=["validate_packaged_dataset"]).validate_packaged_dataset
    monkeypatch.setattr(
        "app.evaluation.context.validate_packaged_dataset",
        lambda slug: {
            **original(slug),
            "models": [{**original(slug)["models"][0], "id": model_id, "artifact_sha256": artifact_hash}],
        },
    )
    request = CalibrationRequest(
        model_id=model_id, dataset_id=registered.id, calibration_method="none",
        calibration_protocol="dedicated_split", calibration_size=.5,
    )
    assert calibration_preflight(request).feasible is True
    study_id = str(uuid4())
    with session_scope() as session:
        run_count = session.scalar(select(func.count()).select_from(Run))
        session.add(CalibrationStudy(
            id=study_id, model_id=model_id, dataset_id=registered.id,
            dataset_version_id=registered.current_version_id,
            operation_key=f"test-calibration:{study_id}",
            configuration=request.model_dump(mode="json"), created_at=utcnow(),
        ))
    execute_calibration_study(study_id)
    with session_scope() as session:
        study = session.get(CalibrationStudy, study_id)
        assert session.scalar(select(func.count()).select_from(Run)) == run_count
        assert study.status == "completed"
        assert study.metrics["brier_score"] >= 0
        assert study.curves["reliability_curve"]
        assert study.provenance["type"] == "verified_demo_experiment"
        card, _, _ = assemble_card(session, model_id)
        assert card["calibration"]["status"] == "available"


def test_verified_demo_threshold_separates_selection_and_evaluation(registered, monkeypatch):
    _, model_id, config = _verified_demo_model(registered, monkeypatch)
    artifact_hash = _persist_fitted_artifact(model_id, config)
    with session_scope() as session:
        session.get(ModelRecord, model_id).artifact_sha256 = artifact_hash
    original = __import__("app.evaluation.context", fromlist=["validate_packaged_dataset"]).validate_packaged_dataset
    monkeypatch.setattr(
        "app.evaluation.context.validate_packaged_dataset",
        lambda slug: {
            **original(slug),
            "models": [{**original(slug)["models"][0], "id": model_id, "artifact_sha256": artifact_hash}],
        },
    )
    request = ThresholdAnalysisRequest(
        model_id=model_id, dataset_id=registered.id,
        selection_method="youden_j", selection_size=.5,
    )
    assert threshold_preflight(request).feasible is True
    study_id = str(uuid4())
    with session_scope() as session:
        run_count = session.scalar(select(func.count()).select_from(Run))
        session.add(ThresholdAnalysisStudy(
            id=study_id, model_id=model_id, dataset_id=registered.id,
            dataset_version_id=registered.current_version_id,
            operation_key=f"test-threshold:{study_id}",
            configuration=request.model_dump(mode="json"), created_at=utcnow(),
        ))
    execute_threshold_study(study_id)
    with session_scope() as session:
        study = session.get(ThresholdAnalysisStudy, study_id)
        assert session.scalar(select(func.count()).select_from(Run)) == run_count
        assert study.status == "completed"
        assert study.results["selected_operating_point"]["threshold"] is not None
        assert study.summary["selection_samples"] > 0
        assert study.summary["evaluated_samples"] > 0
        assert study.provenance["type"] == "verified_demo_experiment"
        assert study.provenance["threshold_protocol"]["threshold_frozen_before_evaluation"] is True
        card, _, _ = assemble_card(session, model_id)
        assert card["threshold"]["status"] == "available"