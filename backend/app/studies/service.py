from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from ..artifacts.service import register_file, register_metadata
from ..api.schemas import TrainingConfig
from ..config import get_settings
from ..data.splitting import prepare_data
from ..database import session_scope
from ..manifests.service import create_locked_manifest
from ..models.training import train_model
from ..models.hybrid import require_hybrid_dependencies
from ..quantum.backends import require_quantum
from ..runs.service import create_run, transition
from ..storage.entities import Artifact, Experiment, Job, ModelRecord, MultiSeedStudy, Run, StudyRun
from ..storage.files import safe_path, save_model
from ..storage.repository import require
from ..utils.errors import AppError, CancelledError
from ..utils.serialization import clean_json, fingerprint, software_versions, utcnow
from .schemas import MultiSeedStudyRequest
from .stats import MULTI_SEED_LIMITATIONS, aggregate_study_results

logger = logging.getLogger("qhealth.studies")


def create_study(
    session,
    request: MultiSeedStudyRequest,
    *,
    idempotency_key: str | None = None,
) -> tuple[MultiSeedStudy, list[StudyRun]]:
    settings = get_settings()
    max_seeds = getattr(settings, "max_study_seeds", 20)
    if len(request.seeds) > max_seeds:
        raise AppError("seed_budget_exceeded", f"Maximum {max_seeds} seeds allowed per study.", 400)
    if len(request.seeds) < 2:
        raise AppError("invalid_seed_count", "At least 2 unique seeds are required for a multi-seed study.", 400)

    if request.base_experiment_id is not None:
        base_experiment = require(session, Experiment, str(request.base_experiment_id))
        base_config = TrainingConfig.model_validate(base_experiment.config)
        dataset_id = base_experiment.dataset_id
    else:
        base_config = request.config
        assert base_config is not None
        data = prepare_data(base_config)
        if data.dataset_version is not None and base_config.dataset_version_id is None:
            base_config = base_config.model_copy(update={"dataset_version_id": data.dataset_version.id})
        dataset_id = str(base_config.dataset_id)

    if {"vqc", "qsvc", "qnn"}.intersection(base_config.models):
        require_quantum()
    if "hybrid_pennylane_torch" in base_config.models:
        require_hybrid_dependencies()

    locked_config_dict = base_config.model_dump(mode="json")
    fp_dict = {k: v for k, v in locked_config_dict.items() if k != "seed"}
    configuration_fingerprint = fingerprint(fp_dict)

    if idempotency_key is not None:
        idempotency_key = idempotency_key.strip()
        if not 8 <= len(idempotency_key) <= 200 or any(ord(c) < 33 for c in idempotency_key):
            raise AppError("idempotency_key_invalid", "Idempotency-Key must contain 8 to 200 visible non-space characters.")
        operation_key = f"study-request:{fingerprint({'key': idempotency_key})}"
    else:
        operation_key = f"study-request:{uuid4()}"

    existing = session.scalar(select(MultiSeedStudy).where(MultiSeedStudy.operation_key == operation_key))
    if existing is not None:
        if (
            (request.base_experiment_id is not None and existing.base_experiment_id != str(request.base_experiment_id))
            or existing.requested_seeds != list(request.seeds)
            or existing.configuration_fingerprint != configuration_fingerprint
        ):
            raise AppError("idempotency_conflict", "The operation key is not reusable for this study request.", 409)
        existing_runs = list(
            session.scalars(
                select(StudyRun).where(StudyRun.study_id == existing.id).order_by(StudyRun.seed_order.asc())
            )
        )
        return existing, existing_runs

    if request.base_experiment_id is None:
        base_experiment = Experiment(
            id=str(uuid4()),
            dataset_id=dataset_id,
            config=base_config.model_dump(mode="json"),
            status="created",
            summary={
                "study_base": True,
                "dataset_provenance": data.provenance,
                "split": data.split_metadata(),
                "software": software_versions(),
                "limitations": data.quality["warnings"],
            },
        )
        session.add(base_experiment)
        session.flush()


    dataset_version_id = str(base_config.dataset_version_id) if base_config.dataset_version_id else None

    reproducibility = {
        "requested_seeds": list(request.seeds),
        "configuration_fingerprint": configuration_fingerprint,
        "dataset_id": dataset_id,
        "dataset_version_id": dataset_version_id,
        "model_configuration": locked_config_dict,
        "software_versions": software_versions(),
        "statistical_aggregation_protocol": {
            "descriptive_metrics": [
                "accuracy", "sensitivity", "specificity", "precision", "recall", "f1",
                "roc_auc", "pr_auc", "brier_score", "final_training_seconds", "cv_total_seconds",
                "test_inference_seconds", "test_inference_seconds_per_sample",
            ],
            "bootstrap_interval": {
                "method": "bootstrap_percentile",
                "confidence_level": 0.95,
                "resamples": 2000,
            },
            "paired_differences": {
                "method": "matched_seed_delta",
                "delta_definition": "model_a_value - model_b_value",
            },
        },
        "limitations": MULTI_SEED_LIMITATIONS,
    }

    study = MultiSeedStudy(
        id=str(uuid4()),
        base_experiment_id=base_experiment.id,
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
        status="queued",
        operation_key=operation_key,
        requested_seeds=list(request.seeds),
        completed_seeds=[],
        failed_seeds=[],
        cancelled_seeds=[],
        model_identities=list(base_config.models),
        locked_config=locked_config_dict,
        configuration_fingerprint=configuration_fingerprint,
        protocol_version="multi_seed_evaluation_v1",
        aggregate_summary={},
        limitations=MULTI_SEED_LIMITATIONS,
        reproducibility_metadata=reproducibility,
    )
    session.add(study)
    session.flush()

    study_runs: list[StudyRun] = []
    for order, seed in enumerate(request.seeds):
        sr = StudyRun(
            id=str(uuid4()),
            study_id=study.id,
            seed=seed,
            seed_order=order,
            status="queued",
        )
        session.add(sr)
        study_runs.append(sr)

    session.flush()
    return study, study_runs


def execute_study(study_id: str) -> MultiSeedStudy:
    """Executes a multi-seed study across all requested seeds."""
    with session_scope() as session:
        study = require(session, MultiSeedStudy, study_id)
        if study.status in {"completed", "failed", "cancelled"}:
            return study
        study.status = "running"
        study.started_at = utcnow()
        base_experiment = require(session, Experiment, study.base_experiment_id)
        base_config = TrainingConfig.model_validate(study.locked_config)
        study_runs = list(
            session.scalars(
                select(StudyRun).where(StudyRun.study_id == study.id).order_by(StudyRun.seed_order.asc())
            )
        )

    seed_model_metrics: dict[int, dict[str, dict]] = {}

    for sr in study_runs:
        with session_scope() as session:
            current_study = require(session, MultiSeedStudy, study_id)
            if current_study.status == "cancel_requested":
                current_sr = require(session, StudyRun, sr.id)
                current_sr.status = "cancelled"
                current_sr.completed_at = utcnow()
                continue

            current_sr = require(session, StudyRun, sr.id)
            current_sr.status = "running"
            seed = current_sr.seed

            seed_config = base_config.model_copy(update={"seed": seed})
            if "hybrid_pennylane_torch" in seed_config.models:
                seed_config = seed_config.model_copy(
                    update={"hybrid": seed_config.hybrid.model_copy(update={"deterministic_seed": seed})}
                )

            try:
                data = prepare_data(seed_config)
                run_op_key = f"study-run:{study_id}:seed-{seed}:{study.configuration_fingerprint}"
                run = create_run(
                    session,
                    experiment=base_experiment,
                    config=seed_config.model_dump(mode="json"),
                    operation_key=run_op_key,
                    execution_metadata={
                        "executor": "single_process_thread_pool",
                        "study_id": study_id,
                        "seed": seed,
                        "worker_count": 1,
                    },
                    reproducibility_metadata={
                        "dataset_hash": data.dataset_version.content_sha256 if data.dataset_version else data.dataset.sha256,
                        "split": data.split_metadata(),
                        "software": software_versions(),
                        "study_id": study_id,
                        "seed": seed,
                        "protocol": "multi_seed_evaluation_v1",
                    },
                    dataset_version_id=data.dataset_version.id if data.dataset_version else None,
                )
                job_id = str(uuid4())
                create_locked_manifest(
                    session, run=run, experiment=base_experiment, data=data,
                    config=seed_config, job_id=job_id,
                )
                job = Job(id=job_id, experiment_id=base_experiment.id, run_id=run.id, status="running")
                session.add(job)
                current_sr.run_id = run.id
                current_sr.job_id = job.id
                transition(session, run, "queued")
                transition(session, run, "running")
                session.flush()


                # Train models for this seed
                seed_successes, seed_failures = 0, 0
                models_at_seed: dict[str, dict] = {}
                for kind in seed_config.models:
                    model_id = str(uuid4())
                    try:
                        bundle, metrics, details = train_model(kind, seed_config, data, lambda _: None)
                        artifact_hash = save_model(model_id, bundle)
                        model_record = ModelRecord(
                            id=model_id,
                            experiment_id=base_experiment.id,
                            run_id=run.id,
                            dataset_id=str(seed_config.dataset_id),
                            model_type=kind,
                            status="ready",
                            artifact_sha256=artifact_hash,
                            metrics=metrics,
                            details=details,
                        )
                        session.add(model_record)
                        session.flush()

                        model_path = safe_path("models", model_id, ".dill")
                        register_file(
                            session,
                            experiment_id=base_experiment.id,
                            run_id=run.id,
                            model_id=model_id,
                            artifact_type="model",
                            name=f"{kind} fitted model (seed {seed})",
                            description="Integrity-registered fitted estimator bundle for multi-seed study.",
                            path=model_path,
                            storage_reference=f"models/{model_id}.dill",
                            content_type="application/x-python-dill",
                            operation_key=f"model:{model_id}",
                            details={"model_type": kind, "model_artifact_hmac": artifact_hash, "seed": seed, "study_id": study_id},
                        )
                        register_metadata(
                            session,
                            experiment_id=base_experiment.id,
                            run_id=run.id,
                            model_id=model_id,
                            artifact_type="evaluation_result",
                            name=f"{kind} evaluation (seed {seed})",
                            description="Metrics for the frozen model in multi-seed study.",
                            payload=metrics,
                            operation_key=f"evaluation:{model_id}",
                        )
                        if details.get("quantum"):
                            register_metadata(
                                session,
                                experiment_id=base_experiment.id,
                                run_id=run.id,
                                model_id=model_id,
                                artifact_type="quantum_metadata",
                                name=f"{kind} quantum metadata (seed {seed})",
                                description="Quantum resource metadata in multi-seed study.",
                                payload=details["quantum"],
                                operation_key=f"quantum-metadata:{model_id}",
                            )
                        seed_successes += 1
                        models_at_seed[kind] = metrics
                    except CancelledError:
                        raise
                    except Exception as exc:
                        seed_failures += 1
                        error = {
                            "model_type": kind,
                            "exception_type": type(exc).__name__,
                            "code": getattr(exc, "code", "training_failed"),
                            "message": getattr(exc, "message", str(exc)),
                        }
                        session.add(
                            ModelRecord(
                                id=model_id,
                                experiment_id=base_experiment.id,
                                run_id=run.id,
                                dataset_id=str(seed_config.dataset_id),
                                model_type=kind,
                                status="failed",
                                details={"error": error},
                                metrics={},
                            )
                        )

                if seed_failures and not seed_successes:
                    transition(session, run, "failed", failure={"code": "all_models_failed", "message": "All models failed training for this seed."})
                    job.status = "failed"
                    current_sr.status = "failed"
                    current_sr.failure = {"code": "all_models_failed", "message": "All models failed training for this seed."}
                else:
                    transition(session, run, "completed", result_summary={"models_persisted": seed_successes, "models_failed": seed_failures})
                    job.status = "succeeded" if not seed_failures else "partial"
                    current_sr.status = "completed"
                    seed_model_metrics[seed] = models_at_seed

                current_sr.completed_at = utcnow()

            except CancelledError:
                if current_sr.run_id:
                    transition(session, require(session, Run, current_sr.run_id), "cancelled")
                current_sr.status = "cancelled"
                current_sr.completed_at = utcnow()
            except Exception as exc:
                logger.warning("seed_run_failure study_id=%s seed=%s exception=%s", study_id, seed, type(exc).__name__)
                err = {
                    "code": getattr(exc, "code", "seed_run_failed"),
                    "message": getattr(exc, "message", "Seed run failed during execution."),
                    "exception_type": type(exc).__name__,
                }
                if current_sr.run_id:
                    transition(session, require(session, Run, current_sr.run_id), "failed", failure=err)
                if current_sr.job_id:
                    job_rec = session.get(Job, current_sr.job_id)
                    if job_rec:
                        job_rec.status = "failed"
                current_sr.status = "failed"
                current_sr.failure = err
                current_sr.completed_at = utcnow()

    # Finalize study state
    with session_scope() as session:
        study = require(session, MultiSeedStudy, study_id)
        runs_records = list(
            session.scalars(
                select(StudyRun).where(StudyRun.study_id == study.id).order_by(StudyRun.seed_order.asc())
            )
        )
        completed_seeds = [r.seed for r in runs_records if r.status == "completed"]
        failed_seeds = [r.seed for r in runs_records if r.status == "failed"]
        cancelled_seeds = [r.seed for r in runs_records if r.status == "cancelled"]

        study.completed_seeds = completed_seeds
        study.failed_seeds = failed_seeds
        study.cancelled_seeds = cancelled_seeds

        if study.status == "cancel_requested" or (cancelled_seeds and not completed_seeds):
            study.status = "cancelled"
        elif len(completed_seeds) == len(study.requested_seeds):
            study.status = "completed"
        elif completed_seeds:
            study.status = "partial"
        else:
            study.status = "failed"

        study.completed_at = utcnow()

        if completed_seeds:
            # Aggregate results
            model_aggregates, paired_comparisons = aggregate_study_results(
                study_id=study.id,
                completed_seeds=completed_seeds,
                models=list(study.model_identities),
                seed_model_metrics=seed_model_metrics,
            )

            summary_payload = {
                "study_id": study.id,
                "protocol_version": study.protocol_version,
                "base_experiment_id": study.base_experiment_id,
                "dataset_id": study.dataset_id,
                "dataset_version_id": study.dataset_version_id,
                "configuration_fingerprint": study.configuration_fingerprint,
                "requested_seeds": study.requested_seeds,
                "completed_seeds": completed_seeds,
                "failed_seeds": failed_seeds,
                "cancelled_seeds": cancelled_seeds,
                "models": study.model_identities,
                "aggregates": model_aggregates,
                "paired_differences": paired_comparisons,
                "bootstrap_protocol": {
                    "method": "bootstrap_percentile",
                    "confidence_level": 0.95,
                    "resamples": 2000,
                },
                "software": software_versions(),
                "limitations": study.limitations,
            }

            artifact = register_metadata(
                session,
                experiment_id=study.base_experiment_id,
                run_id=None,
                model_id=None,
                artifact_type="multi_seed_study_summary",
                name=f"Multi-seed study {study.id} statistical summary",
                description="Aggregated descriptive multi-seed statistical evaluation and paired differences.",
                payload=clean_json(summary_payload),
                operation_key=f"study-artifact:{study.id}",
            )
            study.study_artifact_id = artifact.id
            summary_payload["artifact_id"] = artifact.id
            study.aggregate_summary = clean_json(summary_payload)

    return study


def list_studies(
    *,
    base_experiment_id: str | None = None,
    dataset_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[MultiSeedStudy]:
    with session_scope() as session:
        query = select(MultiSeedStudy)
        if base_experiment_id:
            query = query.where(MultiSeedStudy.base_experiment_id == base_experiment_id)
        if dataset_id:
            query = query.where(MultiSeedStudy.dataset_id == dataset_id)
        if status:
            query = query.where(MultiSeedStudy.status == status)
        query = query.order_by(MultiSeedStudy.created_at.desc()).offset(offset).limit(limit)
        return list(session.scalars(query))


def get_study(study_id: str) -> MultiSeedStudy:
    with session_scope() as session:
        return require(session, MultiSeedStudy, study_id)


def get_study_runs(study_id: str) -> list[StudyRun]:
    with session_scope() as session:
        require(session, MultiSeedStudy, study_id)
        return list(
            session.scalars(
                select(StudyRun).where(StudyRun.study_id == study_id).order_by(StudyRun.seed_order.asc())
            )
        )


def get_study_detail(study_id: str) -> dict[str, Any]:
    with session_scope() as session:
        study = require(session, MultiSeedStudy, study_id)
        runs = list(
            session.scalars(
                select(StudyRun).where(StudyRun.study_id == study.id).order_by(StudyRun.seed_order.asc())
            )
        )
        summary = study.aggregate_summary if study.aggregate_summary else None
        return {
            "study": study,
            "runs": runs,
            "summary": summary,
            "reproducibility": study.reproducibility_metadata,
            "failure": study.failure,
        }


def cancel_study(study_id: str) -> MultiSeedStudy:
    with session_scope() as session:
        study = require(session, MultiSeedStudy, study_id)
        if study.status in {"queued", "running"}:
            study.status = "cancel_requested"
            runs = list(session.scalars(select(StudyRun).where(StudyRun.study_id == study.id)))
            for sr in runs:
                if sr.status in {"created", "queued"}:
                    sr.status = "cancelled"
                    sr.completed_at = utcnow()
        return study
