import json
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from uuid import uuid4
from sqlalchemy import func, select
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
from backend.app.readiness.service import evaluate_condition_task_readiness
from ..utils.errors import AppError, CancelledError
from ..utils.serialization import clean_json, fingerprint, software_versions, utcnow
from .engine import (PauseRequested, acquire_lease, begin_logical_unit, check_control,
    complete_logical_unit, create_checkpoint, fail_logical_unit, latest_valid_checkpoint,
    mark_paused, recover_stale_jobs, release_lease, request_cancel, request_pause)

logger = logging.getLogger("qhealth.jobs")
ACTIVE = {"queued", "running", "resuming", "checkpointing", "pause_requested", "cancel_requested"}

class TrainingManager:
    """Single-process MVP worker with persistent state, not a distributed queue."""
    def __init__(self):
        self.executor = None
        self.lock = Lock()
        self.futures = {}
        self.worker_id = f"training-worker-{uuid4()}"

    def start(self):
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="qhealth-training")
        # The repository intentionally runs one in-process worker. A new
        # process cannot still own a predecessor's leases.
        with session_scope() as session:
            for job in session.scalars(select(Job).where(
                Job.status.in_({"running", "resuming", "checkpointing", "pause_requested", "cancel_requested"}),
                Job.lease_id.is_not(None),
            )):
                job.lease_expires_at = utcnow()
        recover_stale_jobs()
        with session_scope() as session:
            specs = []
            for job in session.scalars(select(Job).where(Job.status == "queued")):
                if not job.run_id:
                    continue
                run = require(session, Run, job.run_id)
                executions = [(m.model_type, m.id) for m in session.scalars(
                    select(ModelRecord).where(ModelRecord.run_id == run.id).order_by(ModelRecord.created_at))]
                specs.append((job.id, job.experiment_id, run.id, TrainingConfig.model_validate(run.config), executions))
        for spec in specs:
            future = self.executor.submit(self._run, *spec)
            self.futures[spec[0]] = future
            future.add_done_callback(lambda _future, queued_job_id=spec[0]: self.futures.pop(queued_job_id, None))
        with session_scope() as session:
            from ..storage.entities import MultiSeedStudy
            for study in session.scalars(select(MultiSeedStudy).where(MultiSeedStudy.status.in_(ACTIVE))):
                study.status = "interrupted"
                study.completed_at = utcnow()
                study.failure = {"code": "process_interrupted", "message": "The previous process ended before study execution completed."}

    def stop(self):
        if self.executor is None:
            return
        with session_scope() as session:
            for job in session.scalars(select(Job).where(Job.status.in_(ACTIVE))):
                job.status = "cancel_requested"
                job.state = "Server shutdown: waiting for a safe training boundary."
            from ..storage.entities import MultiSeedStudy
            for study in session.scalars(select(MultiSeedStudy).where(MultiSeedStudy.status.in_(ACTIVE))):
                study.status = "cancel_requested"
        self.executor.shutdown(wait=True, cancel_futures=True)
        self.executor = None
        with session_scope() as session:
            for job in session.scalars(select(Job).where(Job.status == "cancel_requested")):
                job.status = "cancelled"
                job.state = "Server shutdown cancelled the queued or running execution."
                job.updated_at = utcnow()
                require(session, Experiment, job.experiment_id).status = "cancelled"
                if job.run_id:
                    for model in session.scalars(select(ModelRecord).where(
                        ModelRecord.run_id == job.run_id,
                        ModelRecord.status.in_(("queued", "running")),
                    )):
                        model.status = "cancelled"
                        model.progress = None
                        model.details = {**model.details, "execution_state": "Cancelled"}
                    run = require(session, Run, job.run_id)
                    if run.status not in {"completed", "failed", "cancelled"}:
                        transition(session, run, "cancelled")
            from ..storage.entities import MultiSeedStudy
            for study in session.scalars(select(MultiSeedStudy).where(MultiSeedStudy.status == "cancel_requested")):
                study.status = "cancelled"
                study.completed_at = utcnow()
                study.failure = {
                    "code": "cancelled",
                    "message": "Server shutdown cancelled the queued or running study.",
                }

    def enqueue(self, config: TrainingConfig, parent_id: str | None = None, idempotency_key: str | None = None):
        if config.condition_task_id:
            with session_scope() as session:
                readiness = evaluate_condition_task_readiness(session, str(config.condition_task_id))
                if readiness.status in ("BLOCKED", "INCOMPLETE_CONFIGURATION"):
                    raise AppError(
                        "task_blocked",
                        f"ConditionTask is not ready for training. Status: {readiness.status}",
                        422,
                    )
        job, experiment, _run = self._enqueue(config, parent_id=parent_id, idempotency_key=idempotency_key)
        return job, experiment

    def enqueue_existing(self, experiment_id: str, idempotency_key: str | None = None):
        with session_scope() as session:
            experiment = require(session, Experiment, experiment_id)
            config = TrainingConfig.model_validate(experiment.config)
        return self._enqueue(config, experiment_id=experiment_id, idempotency_key=idempotency_key)

    def enqueue_study(self, study_id: str):
        if self.executor is None:
            raise AppError("worker_unavailable", "Training worker is not started.", 503)
        self.executor.submit(self._run_study, study_id)

    def _run_study(self, study_id: str):
        from ..studies.service import execute_study
        try:
            execute_study(study_id)
        except Exception as exc:
            logger.warning("study_execution_failure study_id=%s exception=%s", study_id, type(exc).__name__)


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
        # Freeze an omitted current-version selection into the actual execution
        # configuration before creating Experiment/Run/manifest records.
        if data.dataset_version is not None and config.dataset_version_id is None:
            config = config.model_copy(update={"dataset_version_id": data.dataset_version.id})
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
                    sequence = session.scalar(
                        select(func.count()).select_from(Experiment).where(Experiment.dataset_id == str(config.dataset_id))
                    ) or 0
                    dataset_name = " ".join(str(data.dataset.name).split())[:200] or "Dataset"
                    experiment_name = f"{dataset_name} · Training {sequence + 1:02d}"
                    experiment = Experiment(id=str(uuid4()), dataset_id=str(config.dataset_id), parent_id=parent_id,
                        name=experiment_name,
                        config=config.model_dump(mode="json"), summary={"dataset_provenance": data.provenance,
                        "split": data.split_metadata(), "software": software_versions(),
                        "comparison_fingerprint": fingerprint({"dataset": data.dataset_version.content_sha256 if data.dataset_version else data.dataset.sha256, "split": data.split_hash,
                            "features": data.features, "pipeline": config.pipeline.model_dump(), "threshold": config.probability_threshold,
                            "threshold_strategy": config.threshold_strategy, "target_sensitivity": config.target_sensitivity,
                            "calibration": config.calibration, "class_weight": config.parameters.class_weight}),
                        "limitations": data.quality["warnings"]})
                    session.add(experiment)
                    session.flush()
                job_id = str(uuid4())
                from ..quantum.service import service as quantum_execution_service
                run = create_run(
                    session,
                    experiment=experiment,
                    config=config.model_dump(mode="json"),
                    operation_key=operation_key,
                    execution_metadata={
                        "executor": "single_process_thread_pool",
                        "worker_count": 1,
                        "quantum_providers": quantum_execution_service.execution_plan(config.model_dump(mode="json")),
                    },
                    reproducibility_metadata={
                        "dataset_hash": data.dataset_version.content_sha256 if data.dataset_version else data.dataset.sha256,
                        "split": data.split_metadata(),
                        "software": software_versions(),
                    },
                    dataset_version_id=data.dataset_version.id if data.dataset_version else None,
                )
                create_locked_manifest(
                    session, run=run, experiment=experiment, data=data,
                    config=config, job_id=job_id,
                )
                job = Job(
                    id=job_id, experiment_id=experiment.id, run_id=run.id,
                    job_type="training", total_units=len(config.models),
                    configuration_fingerprint=fingerprint(config.model_dump(mode="json")),
                    input_fingerprint=fingerprint({
                        "dataset_id": str(config.dataset_id),
                        "dataset_version_id": str(config.dataset_version_id) if config.dataset_version_id else None,
                        "content_sha256": data.dataset_version.content_sha256 if data.dataset_version else data.dataset.sha256,
                    }),
                )
                session.add(job)
                executions = []
                for kind in config.models:
                    model = ModelRecord(
                        id=str(uuid4()), experiment_id=experiment.id, run_id=run.id,
                        dataset_id=str(config.dataset_id), model_type=kind, status="queued",
                        progress=0, artifact_sha256=None,
                        details={"execution_state": "Queued"}, metrics={},
                    )
                    session.add(model)
                    executions.append((kind, model.id))
                session.flush()
                transition(session, run, "queued")
            try:
                future = self.executor.submit(self._run, job.id, experiment.id, run.id, config, executions)
                self.futures[job.id] = future
                future.add_done_callback(lambda _future, queued_job_id=job.id: self.futures.pop(queued_job_id, None))
            except RuntimeError as exc:
                self._finish(job.id, experiment.id, run.id, "failed", "Worker could not accept the job.")
                raise AppError("worker_unavailable", "Worker could not accept the job.", 503) from exc
        return job, experiment, run

    def cancel(self, identity: str):
        request_cancel(identity)
        with session_scope() as session:
            job = require(session, Job, identity)
            if job.status != "cancel_requested":
                return job
            future = self.futures.get(job.id)
            stop_now = bool((future and future.cancel()) or job.lease_id is None)
            experiment_id, run_id = job.experiment_id, job.run_id
        if stop_now and run_id:
            self.futures.pop(identity, None)
            self._finish(identity, experiment_id, run_id, "cancelled", "Cancelled at a safe execution boundary.")
        with session_scope() as session:
            return require(session, Job, identity)

    def pause(self, identity: str):
        return request_pause(identity)

    def resume(self, identity: str):
        if self.executor is None:
            raise AppError("worker_unavailable", "Training worker is not started.", 503)
        checkpoint = latest_valid_checkpoint(identity)
        if checkpoint is None:
            raise AppError("checkpoint_unavailable", "No valid compatible checkpoint is available.", 409)
        with self.lock:
            with session_scope() as session:
                job = require(session, Job, identity)
                if job.job_type != "training":
                    raise AppError("job_handler_unavailable", "No training handler is registered for this job.", 409)
                if job.resume_count >= get_settings().job_max_resume_attempts:
                    raise AppError("resume_limit_reached", "The maximum resume count has been reached.", 409)
                run = require(session, Run, job.run_id)
                config = TrainingConfig.model_validate(run.config)
                executions = [(m.model_type, m.id) for m in session.scalars(
                    select(ModelRecord).where(ModelRecord.run_id == run.id).order_by(ModelRecord.created_at))]
                experiment_id, run_id = job.experiment_id, run.id
            lease_id, _ = acquire_lease(identity, self.worker_id, resuming=True)
            try:
                future = self.executor.submit(self._run, identity, experiment_id, run_id, config, executions, lease_id, checkpoint.id)
                self.futures[identity] = future
                future.add_done_callback(lambda _future, job_id=identity: self.futures.pop(job_id, None))
            except RuntimeError as exc:
                with session_scope() as session:
                    job = require(session, Job, identity)
                    job.status = "recoverable"
                    release_lease(session, job, lease_id)
                raise AppError("worker_unavailable", "Worker could not accept the resume.", 503) from exc
        with session_scope() as session:
            return require(session, Job, identity)

    def retry(self, identity: str, idempotency_key: str | None = None):
        with session_scope() as session:
            job = require(session, Job, identity)
            if job.status not in {"failed", "recoverable", "interrupted"}:
                raise AppError("retry_not_allowed", "Only a failed or recoverable job may be retried.", 409)
            if job.attempt_count >= get_settings().job_max_attempts:
                raise AppError("attempt_limit_reached", "The maximum attempt count has been reached.", 409)
            experiment_id = job.experiment_id
        return self.enqueue_existing(experiment_id, idempotency_key=idempotency_key or f"job-retry:{identity}")

    def _checkpoint(self, job_id: str, lease_id: str, state: str, progress: int, model_id: str | None = None):
        check_control(job_id, lease_id, safe_boundary=False)
        with session_scope() as session:
            job = require(session, Job, job_id)
            if job.lease_id != lease_id:
                raise AppError("job_lease_lost", "The execution lease is no longer valid.", 409)
            if job.status in {"running", "resuming"}:
                job.status = "running"
            job.state, job.progress, job.current_phase, job.active_unit = state, min(99, progress), "model_training", model_id
            job.updated_at = utcnow()
            if model_id:
                model = require(session, ModelRecord, model_id)
                if model.status in {"queued", "running"}:
                    model.status, model.progress = "running", None
                    model.details = {**model.details, "execution_state": state}
            if job.run_id:
                run = require(session, Run, job.run_id)
                if run.status == "queued":
                    transition(session, run, "running")

    def _finish(self, job_id: str, experiment_id: str, run_id: str, status: str, state: str,
                *, successes: int = 0, failures: int = 0, lease_id: str | None = None):
        with session_scope() as session:
            job = require(session, Job, job_id)
            job.status, job.state, job.updated_at = status, state, utcnow()
            job.completed_units, job.failed_units, job.active_unit = successes, failures, None
            if status in {"succeeded", "partial"}:
                job.progress, job.completed_at = 100, utcnow()
            elif status == "failed":
                job.completed_at = utcnow(); job.failure_category = job.failure_category or "non_recoverable_failure"
            elif status == "cancelled":
                job.cancelled_at, job.failure_category = utcnow(), "cancelled"
            if job.lease_id:
                release_lease(session, job, lease_id)
            experiment = require(session, Experiment, experiment_id)
            experiment.status = status
            experiment.summary = {**experiment.summary, "completed_at": utcnow().isoformat()}
            unfinished = session.scalars(select(ModelRecord).where(ModelRecord.run_id == run_id,
                ModelRecord.status.in_(("queued", "running"))))
            child_status = "cancelled" if status == "cancelled" else "failed"
            for model in unfinished:
                model.status, model.progress = child_status, None
                model.details = {**model.details, "execution_state": "Cancelled" if status == "cancelled" else "Failed"}
            run = require(session, Run, run_id)
            if status in {"succeeded", "partial"}:
                transition(session, run, "completed", result_summary={"outcome": status, "models_persisted": successes, "models_failed": failures})
            elif status == "cancelled": transition(session, run, "cancelled")
            else: transition(session, run, "failed", failure={"code": "scientific_execution_failed", "message": "Scientific execution failed; inspect safe job and model failure metadata."})

    def _run(self, job_id: str, experiment_id: str, run_id: str, config: TrainingConfig,
             executions: list[tuple[str, str]], lease_id: str | None = None, checkpoint_id: str | None = None):
        failures, successes = 0, 0
        try:
            if lease_id is None:
                lease_id, _ = acquire_lease(job_id, self.worker_id)
            checkpoint = latest_valid_checkpoint(job_id) if checkpoint_id else None
            completed_keys = set(checkpoint.checkpoint_state.get("completed_logical_units", []) if checkpoint else [])
            self._checkpoint(job_id, lease_id, "Validating immutable data and reproducible partitions", 0)
            data = prepare_data(config)
            with session_scope() as session:
                require(session, Experiment, experiment_id).status = "running"
            steps_per_model = config.cv_folds + 4
            total_steps, current_step, current_model_id = len(executions) * steps_per_model, 0, None
            def checkpoint_callback(state):
                nonlocal current_step
                current_step += 1
                self._checkpoint(job_id, lease_id, state, int(current_step * 100 / total_steps), current_model_id)
            if checkpoint is None:
                create_checkpoint(job_id, lease_id, {"phase": "model_training", "completed_logical_units": []},
                    checkpoint_type="phase_completion", logical_unit="training_initialized", completed_units=0)
            for index, (kind, identity) in enumerate(executions):
                logical_key, current_model_id = f"training:model:{identity}", identity
                _unit, already_completed = begin_logical_unit(job_id, logical_key, phase="model_training", unit_index=index)
                if already_completed or logical_key in completed_keys:
                    completed_keys.add(logical_key); successes += 1; current_step = (index + 1) * steps_per_model
                    with session_scope() as session:
                        model = require(session, ModelRecord, identity)
                        if model.status != "ready" or not model.artifact_sha256:
                            raise AppError("completed_unit_artifact_missing", "A completed unit is missing its durable model artifact.", 409)
                    self._publish_training_checkpoint(job_id, lease_id, completed_keys, logical_key, successes)
                    continue
                checkpoint_callback(f"Preparing {kind}")
                try:
                    bundle, metrics, details = train_model(kind, config, data, checkpoint_callback)
                    checkpoint_callback(f"Persisting {kind}")
                    artifact_hash = save_model(identity, bundle)
                    with session_scope() as session:
                        model = require(session, ModelRecord, identity)
                        model.status, model.progress, model.artifact_sha256, model.metrics = "ready", 100, artifact_hash, metrics
                        model.details = {**details, "execution_state": "Completed"}; session.flush()
                        model_path = safe_path("models", identity, ".dill")
                        register_file(session, experiment_id=experiment_id, run_id=run_id, model_id=identity,
                            artifact_type="model", name=f"{kind} fitted model", description="Integrity-registered fitted estimator bundle.",
                            path=model_path, storage_reference=f"models/{identity}.dill", content_type="application/x-python-dill",
                            operation_key=f"model:{identity}", details={"model_type": kind, "model_artifact_hmac": artifact_hash})
                        register_metadata(session, experiment_id=experiment_id, run_id=run_id, model_id=identity,
                            artifact_type="evaluation_result", name=f"{kind} evaluation",
                            description="Training, validation and held-out metrics for the frozen model.", payload=metrics,
                            operation_key=f"evaluation:{identity}")
                        if details.get("quantum"):
                            register_metadata(session, experiment_id=experiment_id, run_id=run_id, model_id=identity,
                                artifact_type="quantum_metadata", name=f"{kind} quantum execution metadata",
                                description="Simulator, circuit, configuration and measured resource metadata.",
                                payload=details["quantum"], operation_key=f"quantum-metadata:{identity}")
                    complete_logical_unit(job_id, logical_key, result_reference=f"model:{identity}", result_fingerprint=artifact_hash)
                    completed_keys.add(logical_key); successes += 1
                    self._publish_training_checkpoint(job_id, lease_id, completed_keys, logical_key, successes)
                    control = check_control(job_id, lease_id, safe_boundary=True)
                    if control == "pause": raise PauseRequested()
                    if control == "cancel": raise CancelledError()
                except (CancelledError, PauseRequested):
                    raise
                except Exception as exc:
                    fail_logical_unit(job_id, logical_key); failures += 1
                    error = {"model_type": kind, "exception_type": type(exc).__name__,
                        "code": exc.code if isinstance(exc, AppError) else "training_failed",
                        "message": exc.message if isinstance(exc, AppError) else "Model training failed. Review pipeline dimensions, package versions, and optimization configuration."}
                    logger.warning("model_failure job_id=%s model_type=%s exception_type=%s", job_id, kind, type(exc).__name__)
                    with session_scope() as session:
                        model = require(session, ModelRecord, identity)
                        model.status, model.progress, model.details, model.metrics = "failed", None, {"execution_state": "Failed", "error": error, "configuration": config.model_dump(mode="json")}, {}
                        job = require(session, Job, job_id); job.errors = [*job.errors, error]
                    current_step = (index + 1) * steps_per_model
                    self._checkpoint(job_id, lease_id, f"{kind} failed; continuing remaining models", int(current_step * 100 / total_steps))
            status = "succeeded" if not failures else "partial" if successes else "failed"
            self._finish(job_id, experiment_id, run_id, status, f"Finished: {successes} model(s) persisted; {failures} model(s) failed.", successes=successes, failures=failures, lease_id=lease_id)
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
        except PauseRequested:
            mark_paused(job_id, lease_id)
        except CancelledError:
            self._finish(job_id, experiment_id, run_id, "cancelled", "Stopped at a safe training boundary; completed model records are retained.", successes=successes, failures=failures, lease_id=lease_id)
        except Exception as exc:
            logger.warning("job_failure job_id=%s exception_type=%s", job_id, type(exc).__name__)
            self._finish(job_id, experiment_id, run_id, "failed", "Job failed; inspect dataset integrity, configuration, and dependency installation.", successes=successes, failures=failures, lease_id=lease_id)
        finally:
            self.futures.pop(job_id, None)

    def _publish_training_checkpoint(self, job_id, lease_id, completed_keys, logical_key, successes):
        create_checkpoint(job_id, lease_id, {
            "phase": "model_training", "completed_logical_units": sorted(completed_keys),
            "completed_model_ids": [key.removeprefix("training:model:") for key in sorted(completed_keys)]},
            checkpoint_type="unit_completion", logical_unit=logical_key, completed_units=successes,
            artifact_references=[{"kind": "model", "id": key.removeprefix("training:model:")} for key in sorted(completed_keys)])

manager = TrainingManager()
