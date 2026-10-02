import json
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from uuid import uuid4
from sqlalchemy import select
from ..artifacts.service import register_file, register_metadata
from ..api.schemas import TrainingConfig
from ..config import get_settings
from ..data.splitting import prepare_data
from ..database import session_scope
from ..models.training import train_model
from ..models.hybrid import require_hybrid_dependencies
from ..manifests.service import create_locked_manifest
from ..quantum.backends import require_quantum
from ..runs.service import create_run, transition
from ..storage.entities import Experiment, Job, ModelRecord, Run
from ..storage.files import atomic_bytes, safe_path, save_model
from ..storage.repository import require
from ..utils.errors import AppError, CancelledError
from ..utils.serialization import clean_json, fingerprint, software_versions, utcnow

logger = logging.getLogger("qhealth.jobs")
ACTIVE = {"queued", "running", "cancel_requested"}

class TrainingManager:
    """Single-process MVP worker with persistent state, not a distributed queue."""
    def __init__(self):
        self.executor = None
        self.lock = Lock()

    def start(self):
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="qhealth-training")
        with session_scope() as session:
            for job in session.scalars(select(Job).where(Job.status.in_(ACTIVE))):
                job.status = "interrupted"
                job.state = "Previous process ended; rerun creates a new experiment."
                job.updated_at = utcnow()
                require(session, Experiment, job.experiment_id).status = "interrupted"
                if job.run_id:
                    run = require(session, Run, job.run_id)
                    if run.status not in {"completed", "failed", "cancelled"}:
                        transition(session, run, "failed", failure={
                            "code": "process_interrupted",
                            "message": "The previous process ended before scientific execution completed.",
                        })

    def stop(self):
        if self.executor is None:
            return
        with session_scope() as session:
            for job in session.scalars(select(Job).where(Job.status.in_(ACTIVE))):
                job.status = "cancel_requested"
                job.state = "Server shutdown: waiting for a safe training boundary."
        self.executor.shutdown(wait=True, cancel_futures=True)
        self.executor = None
        with session_scope() as session:
            for job in session.scalars(select(Job).where(Job.status == "cancel_requested")):
                job.status = "cancelled"
                job.state = "Server shutdown cancelled the queued or running execution."
                job.updated_at = utcnow()
                if job.run_id:
                    run = require(session, Run, job.run_id)
                    if run.status not in {"completed", "failed", "cancelled"}:
                        transition(session, run, "cancelled")

    def enqueue(self, config: TrainingConfig, parent_id: str | None = None, idempotency_key: str | None = None):
        job, experiment, _run = self._enqueue(config, parent_id=parent_id, idempotency_key=idempotency_key)
        return job, experiment

    def enqueue_existing(self, experiment_id: str, idempotency_key: str | None = None):
        with session_scope() as session:
            experiment = require(session, Experiment, experiment_id)
            config = TrainingConfig.model_validate(experiment.config)
        return self._enqueue(config, experiment_id=experiment_id, idempotency_key=idempotency_key)

    def _enqueue(
        self,
        config: TrainingConfig,
        *,
        parent_id: str | None = None,
        experiment_id: str | None = None,
        idempotency_key: str | None = None,
    ):
        if self.executor is None:
            raise AppError("worker_unavailable", "Training worker is not started.", 503)
        if idempotency_key is not None:
            idempotency_key = idempotency_key.strip()
            if not 8 <= len(idempotency_key) <= 200 or any(ord(char) < 33 for char in idempotency_key):
                raise AppError("idempotency_key_invalid", "Idempotency-Key must contain 8 to 200 visible non-space characters.")
        data = prepare_data(config)  # Preflight validation, not model fitting.
        if {"vqc", "qsvc", "qnn"}.intersection(config.models):
            require_quantum()
        if "hybrid_pennylane_torch" in config.models:
            require_hybrid_dependencies()
        with self.lock:
            with session_scope() as session:
                operation_key = (
                    f"training-request:{fingerprint({'key': idempotency_key})}"
                    if idempotency_key else f"training-job:{uuid4()}"
                )
                existing_run = session.scalar(select(Run).where(Run.operation_key == operation_key))
                if existing_run is not None:
                    existing_job = session.scalar(select(Job).where(Job.run_id == existing_run.id))
                    existing_experiment = require(session, Experiment, existing_run.experiment_id)
                    if (
                        existing_job is None
                        or existing_run.config != config.model_dump(mode="json")
                        or (experiment_id is not None and existing_run.experiment_id != experiment_id)
                    ):
                        raise AppError("idempotency_conflict", "The operation key is not reusable for this training request.", 409)
                    return existing_job, existing_experiment, existing_run
                count = len(list(session.scalars(select(Job.id).where(Job.status.in_(ACTIVE)))))
                if count >= get_settings().max_queued_jobs:
                    raise AppError("queue_full", "The bounded training queue is full.", 429)
                if parent_id:
                    require(session, Experiment, parent_id)
                if experiment_id:
                    experiment = require(session, Experiment, experiment_id)
                    if experiment.dataset_id != str(config.dataset_id):
                        raise AppError("experiment_dataset_mismatch", "The experiment and run configuration must use the same dataset.", 409)
                else:
                    experiment = Experiment(id=str(uuid4()), dataset_id=str(config.dataset_id), parent_id=parent_id,
                        config=config.model_dump(mode="json"), summary={"dataset_provenance": data.dataset.provenance,
                        "split": data.split_metadata(), "software": software_versions(),
                        "comparison_fingerprint": fingerprint({"dataset": data.dataset.sha256, "split": data.split_hash,
                            "features": data.features, "pipeline": config.pipeline.model_dump(), "threshold": config.probability_threshold,
                            "threshold_strategy": config.threshold_strategy, "target_sensitivity": config.target_sensitivity,
                            "calibration": config.calibration, "class_weight": config.parameters.class_weight}),
                        "limitations": data.quality["warnings"]})
                    session.add(experiment)
                    session.flush()
                job_id = str(uuid4())
                run = create_run(
                    session,
                    experiment=experiment,
                    config=config.model_dump(mode="json"),
                    operation_key=operation_key,
                    execution_metadata={"executor": "single_process_thread_pool", "worker_count": 1},
                    reproducibility_metadata={
                        "dataset_hash": data.dataset.sha256,
                        "split": data.split_metadata(),
                        "software": software_versions(),
                    },
                )
                create_locked_manifest(
                    session, run=run, experiment=experiment, data=data,
                    config=config, job_id=job_id,
                )
                job = Job(id=job_id, experiment_id=experiment.id, run_id=run.id)
                session.add(job)
                session.flush()
                transition(session, run, "queued")
            try:
                self.executor.submit(self._run, job.id, experiment.id, run.id, config)
            except RuntimeError as exc:
                self._finish(job.id, experiment.id, run.id, "failed", "Worker could not accept the job.")
                raise AppError("worker_unavailable", "Worker could not accept the job.", 503) from exc
        return job, experiment, run

    def cancel(self, identity: str):
        with session_scope() as session:
            job = require(session, Job, identity)
            if job.status in ACTIVE:
                job.status = "cancel_requested"
                job.state = "Cancellation requested; current fit may finish before stopping."
                job.updated_at = utcnow()
            return job

    def _checkpoint(self, job_id: str, state: str, progress: int):
        with session_scope() as session:
            job = require(session, Job, job_id)
            if job.status == "cancel_requested":
                raise CancelledError()
            job.status, job.state, job.progress = "running", state, min(99, progress)
            job.updated_at = utcnow()
            if job.run_id:
                run = require(session, Run, job.run_id)
                if run.status == "queued":
                    transition(session, run, "running")

    def _finish(self, job_id: str, experiment_id: str, run_id: str, status: str, state: str, *, successes: int = 0, failures: int = 0):
        with session_scope() as session:
            job = require(session, Job, job_id)
            job.status, job.state, job.updated_at = status, state, utcnow()
            if status in {"succeeded", "partial"}:
                job.progress = 100
            experiment = require(session, Experiment, experiment_id)
            experiment.status = status
            experiment.summary = {**experiment.summary, "completed_at": utcnow().isoformat()}
            run = require(session, Run, run_id)
            if status in {"succeeded", "partial"}:
                transition(session, run, "completed", result_summary={
                    "outcome": status,
                    "models_persisted": successes,
                    "models_failed": failures,
                })
            elif status == "cancelled":
                transition(session, run, "cancelled")
            else:
                transition(session, run, "failed", failure={
                    "code": "scientific_execution_failed",
                    "message": "Scientific execution failed; inspect safe job and model failure metadata.",
                })

    def _run(self, job_id: str, experiment_id: str, run_id: str, config: TrainingConfig):
        failures, successes = 0, 0
        try:
            self._checkpoint(job_id, "Validating immutable data and reproducible partitions", 1)
            data = prepare_data(config)
            with session_scope() as session:
                require(session, Experiment, experiment_id).status = "running"
            total_steps, current_step = len(config.models) * (config.cv_folds + 2) + 1, 1
            def checkpoint(state):
                nonlocal current_step
                self._checkpoint(job_id, state, int(current_step * 100 / total_steps))
                current_step += 1
            for kind in config.models:
                identity = str(uuid4())
                self._checkpoint(job_id, f"Preparing {kind}", int(current_step * 100 / total_steps))
                try:
                    bundle, metrics, details = train_model(kind, config, data, checkpoint)
                    # A cancelled fit is not persisted as a completed model.
                    self._checkpoint(job_id, f"Persisting {kind}", int(current_step * 100 / total_steps))
                    artifact_hash = save_model(identity, bundle)
                    with session_scope() as session:
                        model = ModelRecord(id=identity, experiment_id=experiment_id, run_id=run_id, dataset_id=str(config.dataset_id),
                            model_type=kind, status="ready", artifact_sha256=artifact_hash, metrics=metrics, details=details)
                        session.add(model)
                        session.flush()
                        model_path = safe_path("models", identity, ".dill")
                        register_file(
                            session, experiment_id=experiment_id, run_id=run_id, model_id=identity,
                            artifact_type="model", name=f"{kind} fitted model",
                            description="Integrity-registered fitted estimator bundle.",
                            path=model_path, storage_reference=f"models/{identity}.dill",
                            content_type="application/x-python-dill", operation_key=f"model:{identity}",
                            details={"model_type": kind, "model_artifact_hmac": artifact_hash},
                        )
                        register_metadata(
                            session, experiment_id=experiment_id, run_id=run_id, model_id=identity,
                            artifact_type="evaluation_result", name=f"{kind} evaluation",
                            description="Training, validation and held-out metrics for the frozen model.",
                            payload=metrics, operation_key=f"evaluation:{identity}",
                        )
                        if details.get("quantum"):
                            register_metadata(
                                session, experiment_id=experiment_id, run_id=run_id, model_id=identity,
                                artifact_type="quantum_metadata", name=f"{kind} quantum execution metadata",
                                description="Simulator, circuit, configuration and measured resource metadata.",
                                payload=details["quantum"], operation_key=f"quantum-metadata:{identity}",
                            )
                    successes += 1
                except CancelledError:
                    raise
                except Exception as exc:
                    failures += 1
                    # No exception text, feature values, stack-local data, or raw records in logs.
                    error = {"model_type": kind, "exception_type": type(exc).__name__,
                             "code": exc.code if isinstance(exc, AppError) else "training_failed",
                             "message": exc.message if isinstance(exc, AppError) else "Model training failed. Review pipeline dimensions, package versions, and optimization configuration."}
                    logger.warning("model_failure job_id=%s model_type=%s exception_type=%s", job_id, kind, type(exc).__name__)
                    with session_scope() as session:
                        session.add(ModelRecord(id=identity, experiment_id=experiment_id, run_id=run_id, dataset_id=str(config.dataset_id),
                            model_type=kind, status="failed", details={"error": error, "configuration": config.model_dump(mode="json")}, metrics={}))
                        job = require(session, Job, job_id)
                        job.errors = [*job.errors, error]
            status = "succeeded" if not failures else "partial" if successes else "failed"
            self._finish(job_id, experiment_id, run_id, status, f"Finished: {successes} model(s) persisted; {failures} model(s) failed.", successes=successes, failures=failures)
            # A private metadata snapshot; public reports are built separately.
            with session_scope() as session:
                experiment = require(session, Experiment, experiment_id)
                snapshot = {"experiment_id": experiment.id, "config": experiment.config, "summary": experiment.summary, "status": experiment.status}
            try:
                atomic_bytes(safe_path("experiments", experiment_id, ".json"), json.dumps(clean_json(snapshot), indent=2).encode())
            except OSError as exc:
                logger.warning("snapshot_failure experiment_id=%s exception_type=%s", experiment_id, type(exc).__name__)
                with session_scope() as session:
                    record = require(session, Experiment, experiment_id)
                    record.summary = {**record.summary, "snapshot_warning": "Optional file snapshot failed; committed registry records remain available."}
        except CancelledError:
            self._finish(job_id, experiment_id, run_id, "cancelled", "Stopped at a safe training boundary; completed model records are retained.", successes=successes, failures=failures)
        except Exception as exc:
            logger.warning("job_failure job_id=%s exception_type=%s", job_id, type(exc).__name__)
            self._finish(job_id, experiment_id, run_id, "failed", "Job failed; inspect dataset integrity, configuration, and dependency installation.", successes=successes, failures=failures)

manager = TrainingManager()
