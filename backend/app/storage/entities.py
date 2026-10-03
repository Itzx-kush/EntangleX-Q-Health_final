from datetime import datetime
from uuid import uuid4
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base
from ..utils.serialization import utcnow

def new_id() -> str:
    return str(uuid4())

class Dataset(Base):
    __tablename__ = "datasets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160))
    filename: Mapped[str] = mapped_column(String(200))
    sha256: Mapped[str] = mapped_column(String(64))
    provenance: Mapped[dict] = mapped_column(JSON)
    quality: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    current_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"), nullable=True, index=True)

class DatasetVersion(Base):
    """Immutable concrete snapshot belonging to a logical Dataset."""

    __tablename__ = "dataset_versions"
    __table_args__ = (
        UniqueConstraint("dataset_id", "version_number", name="uq_dataset_versions_number"),
        UniqueConstraint("dataset_id", "version_signature", name="uq_dataset_versions_signature"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    version_label: Mapped[str] = mapped_column(String(24))
    content_sha256: Mapped[str] = mapped_column(String(64), index=True)
    schema_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    version_signature: Mapped[str] = mapped_column(String(64))
    row_count: Mapped[int] = mapped_column(Integer)
    feature_count: Mapped[int] = mapped_column(Integer)
    target: Mapped[str] = mapped_column(String(100))
    positive_label: Mapped[str] = mapped_column(String(64))
    negative_label: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(40), default="binary_classification")
    class_distribution: Mapped[dict] = mapped_column(JSON)
    source_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    quality_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    storage_reference: Mapped[str] = mapped_column(String(320))
    status: Mapped[str] = mapped_column(String(24), default="ready", index=True)
    immutable: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("experiments.id"), nullable=True)
    pipeline_version_id: Mapped[str | None] = mapped_column(ForeignKey("pipeline_versions.id"), nullable=True, index=True)
    protocol_version_id: Mapped[str | None] = mapped_column(ForeignKey("experiment_protocol_versions.id"), nullable=True, index=True)
    protocol_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="queued")
    config: Mapped[dict] = mapped_column(JSON)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

class ModelRecord(Base):
    __tablename__ = "models"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), index=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"), nullable=True, index=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"))
    model_type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24))
    progress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    artifact_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), index=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"), nullable=True, unique=True)
    job_type: Mapped[str] = mapped_column(String(48), default="training", index=True)
    status: Mapped[str] = mapped_column(String(24), default="queued")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    total_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_units: Mapped[int] = mapped_column(Integer, default=0)
    failed_units: Mapped[int] = mapped_column(Integer, default=0)
    skipped_units: Mapped[int] = mapped_column(Integer, default=0)
    active_unit: Mapped[str | None] = mapped_column(String(160), nullable=True)
    current_phase: Mapped[str | None] = mapped_column(String(80), nullable=True)
    state: Mapped[str] = mapped_column(String(200), default="Waiting for worker")
    errors: Mapped[list] = mapped_column(JSON, default=list)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    resume_count: Mapped[int] = mapped_column(Integer, default=0)
    worker_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    lease_id: Mapped[str | None] = mapped_column(String(36), nullable=True, unique=True)
    leased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    current_checkpoint_id: Mapped[str | None] = mapped_column(ForeignKey("job_checkpoints.id"), nullable=True, index=True)
    configuration_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    input_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    output_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("artifacts.id"), nullable=True, index=True)
    failure_category: Mapped[str | None] = mapped_column(String(48), nullable=True, index=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(240), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class JobCheckpoint(Base):
    __tablename__ = "job_checkpoints"
    __table_args__ = (UniqueConstraint("job_id", "sequence_number", name="uq_job_checkpoints_sequence"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    sequence_number: Mapped[int] = mapped_column(Integer)
    checkpoint_type: Mapped[str] = mapped_column(String(32), default="unit_completion")
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    logical_unit: Mapped[str | None] = mapped_column(String(160), nullable=True)
    completed_units: Mapped[int] = mapped_column(Integer, default=0)
    checkpoint_state: Mapped[dict] = mapped_column(JSON, default=dict)
    state_fingerprint: Mapped[str] = mapped_column(String(64))
    input_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    configuration_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    artifact_references: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class JobExecutionUnit(Base):
    __tablename__ = "job_execution_units"
    __table_args__ = (UniqueConstraint("job_id", "logical_key", name="uq_job_execution_units_logical_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    logical_key: Mapped[str] = mapped_column(String(200))
    phase: Mapped[str | None] = mapped_column(String(80), nullable=True)
    unit_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="running", index=True)
    result_reference: Mapped[str | None] = mapped_column(String(320), nullable=True)
    result_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class JobEvent(Base):
    __tablename__ = "job_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(48), index=True)
    from_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    checkpoint_id: Mapped[str | None] = mapped_column(ForeignKey("job_checkpoints.id"), nullable=True, index=True)
    worker_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class ExplanationRecord(Base):
    __tablename__ = "explanations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    model_id: Mapped[str] = mapped_column(ForeignKey("models.id"), index=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"), nullable=True, index=True)
    method: Mapped[str] = mapped_column(String(24))
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class RobustnessRecord(Base):
    __tablename__ = "robustness_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), index=True)
    model_id: Mapped[str] = mapped_column(ForeignKey("models.id"), index=True)
    perturbation_type: Mapped[str] = mapped_column(String(32), index=True)
    perturbation_level: Mapped[float] = mapped_column()
    random_seed: Mapped[int] = mapped_column(Integer)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Run(Base):
    """One concrete scientific execution of an Experiment.

    Job owns scheduling state. Run owns the durable scientific execution
    identity and therefore remains visible after the Job has terminated.
    """

    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), index=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"), nullable=True, index=True)
    pipeline_version_id: Mapped[str | None] = mapped_column(ForeignKey("pipeline_versions.id"), nullable=True, index=True)
    protocol_version_id: Mapped[str | None] = mapped_column(ForeignKey("experiment_protocol_versions.id"), nullable=True, index=True)
    protocol_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="created", index=True)
    operation_key: Mapped[str] = mapped_column(String(128), unique=True)
    config: Mapped[dict] = mapped_column(JSON)
    execution_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    reproducibility_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    result_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    failure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    manifest_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("artifacts.id"), nullable=True, unique=True)
    configuration_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reproducibility_status: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    manifest_locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Artifact(Base):
    """Registry metadata for a file-backed or metadata-only research output."""

    __tablename__ = "artifacts"
    __table_args__ = (
        UniqueConstraint("operation_key", name="uq_artifacts_operation_key"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    experiment_id: Mapped[str | None] = mapped_column(ForeignKey("experiments.id"), nullable=True, index=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"), nullable=True, index=True)
    model_id: Mapped[str | None] = mapped_column(ForeignKey("models.id"), nullable=True, index=True)
    artifact_type: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    storage_reference: Mapped[str | None] = mapped_column(String(320), nullable=True)
    integrity_hash: Mapped[str] = mapped_column(String(64))
    hash_algorithm: Mapped[str] = mapped_column(String(16), default="sha256")
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    immutable: Mapped[bool] = mapped_column(Boolean, default=True)
    operation_key: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class MultiSeedStudy(Base):
    """First-class multi-seed statistical evaluation study across deterministic seeds."""

    __tablename__ = "multi_seed_studies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    base_experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), index=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="created", index=True)
    operation_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    requested_seeds: Mapped[list] = mapped_column(JSON)
    completed_seeds: Mapped[list] = mapped_column(JSON, default=list)
    failed_seeds: Mapped[list] = mapped_column(JSON, default=list)
    cancelled_seeds: Mapped[list] = mapped_column(JSON, default=list)
    model_identities: Mapped[list] = mapped_column(JSON)
    locked_config: Mapped[dict] = mapped_column(JSON)
    configuration_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    protocol_version: Mapped[str] = mapped_column(String(32), default="multi_seed_evaluation_v1")
    aggregate_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    limitations: Mapped[list] = mapped_column(JSON, default=list)
    reproducibility_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    study_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("artifacts.id"), nullable=True, index=True)
    failure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StudyRun(Base):
    """Link between a MultiSeedStudy and a concrete execution Run."""

    __tablename__ = "study_runs"
    __table_args__ = (
        UniqueConstraint("study_id", "seed", name="uq_study_runs_study_seed"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    study_id: Mapped[str] = mapped_column(ForeignKey("multi_seed_studies.id"), index=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"), nullable=True, index=True)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id"), nullable=True, index=True)
    seed: Mapped[int] = mapped_column(Integer)
    seed_order: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="created", index=True)
    failure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExternalValidation(Base):
    """First-class record of external dataset validation for an explicitly locked model."""

    __tablename__ = "external_validations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    model_id: Mapped[str] = mapped_column(ForeignKey("models.id"), index=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"), nullable=True, index=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), index=True)
    training_dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    training_dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"), nullable=True, index=True)
    external_dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    external_dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"), nullable=True, index=True)
    study_id: Mapped[str | None] = mapped_column(ForeignKey("multi_seed_studies.id"), nullable=True, index=True)
    study_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="created", index=True)
    operation_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    compatibility: Mapped[dict] = mapped_column(JSON, default=dict)
    label_mapping: Mapped[dict] = mapped_column(JSON, default=dict)
    threshold_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    internal_metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    comparison: Mapped[dict] = mapped_column(JSON, default=dict)
    generalization_gap: Mapped[dict] = mapped_column(JSON, default=dict)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("artifacts.id"), nullable=True, index=True)
    limitations: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    failure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)



class ThresholdAnalysisStudy(Base):
    __tablename__ = 'threshold_analysis_studies'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    model_id: Mapped[str] = mapped_column(String, index=True)
    dataset_id: Mapped[str] = mapped_column(String, index=True)
    dataset_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    operation_key: Mapped[str] = mapped_column(String, index=True)
    configuration: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default='created')
    results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    curves: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    limitations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    failure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class CalibrationStudy(Base):
    """First-class record of calibration evaluation and method comparison for a locked model."""
    __tablename__ = "calibration_studies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    model_id: Mapped[str] = mapped_column(ForeignKey("models.id"), index=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"), nullable=True, index=True)
    
    status: Mapped[str] = mapped_column(String(24), default="created", index=True)
    operation_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    curves: Mapped[dict] = mapped_column(JSON, default=dict)
    comparisons: Mapped[dict] = mapped_column(JSON, default=dict)
    limitations: Mapped[list] = mapped_column(JSON, default=list)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("artifacts.id"), nullable=True, index=True)
    failure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    execution_time_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
class DistributionShiftAnalysis(Base):
    """First-class record of distribution / dataset shift analysis between two datasets or versions."""

    __tablename__ = "distribution_shift_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    reference_dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    reference_dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"), nullable=True, index=True)
    reference_content_sha256: Mapped[str] = mapped_column(String(64))
    comparison_dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    comparison_dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"), nullable=True, index=True)
    comparison_content_sha256: Mapped[str] = mapped_column(String(64))
    model_id: Mapped[str | None] = mapped_column(ForeignKey("models.id"), nullable=True, index=True)
    external_validation_id: Mapped[str | None] = mapped_column(ForeignKey("external_validations.id"), nullable=True, index=True)
    parent_study_id: Mapped[str | None] = mapped_column(ForeignKey("multi_seed_studies.id"), nullable=True, index=True)
    model_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="created", index=True)
    operation_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    policy_version: Mapped[str] = mapped_column(String(32))
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    schema_analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    target_analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    missingness_analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    feature_shifts: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    flagged_features: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    limitations: Mapped[list] = mapped_column(JSON, default=list)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("artifacts.id"), nullable=True, index=True)
    failure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    execution_time_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConditionTask(Base):
    __tablename__ = "condition_tasks"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    condition_name: Mapped[str] = mapped_column(String(200), nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False, default="binary_classification")
    target_column: Mapped[str] = mapped_column(String(200), nullable=False)
    positive_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    negative_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dataset_id: Mapped[str] = mapped_column(String(36), nullable=False)
    dataset_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    
    readiness_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    readiness_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    readiness_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AblationStudy(Base):
    """One controlled ablation study derived from a completed baseline experiment."""

    __tablename__ = "ablation_studies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    base_experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), index=True)
    base_run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"), nullable=True, index=True)
    ablation_experiment_id: Mapped[str | None] = mapped_column(ForeignKey("experiments.id"), nullable=True, index=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"), nullable=True, index=True)
    condition_task_id: Mapped[str | None] = mapped_column(ForeignKey("condition_tasks.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="created", index=True)
    operation_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    baseline_configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    ablation_configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    changed_components: Mapped[str] = mapped_column(Text, default="")
    held_constant: Mapped[list] = mapped_column(JSON, default=list)
    configuration_diff: Mapped[dict] = mapped_column(JSON, default=dict)
    configuration_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    comparison_results: Mapped[dict] = mapped_column(JSON, default=dict)
    limitations: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("artifacts.id"), nullable=True, index=True)
    failure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class QuantumDiagnosticReport(Base):
    __tablename__ = "quantum_diagnostic_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    experiment_id: Mapped[str] = mapped_column(String(36), ForeignKey("experiments.id"), index=True)
    model_record_id: Mapped[str] = mapped_column(String(36), ForeignKey("models.id"), index=True)
    model_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="completed")
    model_configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    feature_encoding: Mapped[dict] = mapped_column(JSON, default=dict)
    circuit_structure: Mapped[dict] = mapped_column(JSON, default=dict)
    resource_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    optimizer_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    training_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    execution_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    stability_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    noise_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    limitations: Mapped[list] = mapped_column(JSON, default=list)
    configuration_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ControlledComparisonProtocol(Base):
    """Immutable evidence that classical/quantum pairs were control-checked."""

    __tablename__ = "controlled_comparison_protocols"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), index=True)
    schema_version: Mapped[str] = mapped_column(String(48))
    status: Mapped[str] = mapped_column(String(40), index=True)
    operation_key: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    configuration_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    protocol_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    classical_model_ids: Mapped[list] = mapped_column(JSON, default=list)
    quantum_model_ids: Mapped[list] = mapped_column(JSON, default=list)
    comparison_pairs: Mapped[list] = mapped_column(JSON, default=list)
    control_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    limitations: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("artifacts.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ResearchEvidencePackage(Base):
    """Immutable manifest of the persisted evidence state for an experiment."""

    __tablename__ = "research_evidence_packages"
    __table_args__ = (
        UniqueConstraint(
            "experiment_id",
            "package_fingerprint",
            name="uq_research_evidence_package_snapshot",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), index=True)
    schema_version: Mapped[str] = mapped_column(String(48))
    status: Mapped[str] = mapped_column(String(24), index=True)
    package_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    configuration_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_context_type: Mapped[str] = mapped_column(String(40), index=True)
    evidence_inventory: Mapped[dict] = mapped_column(JSON, default=dict)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    limitations: Mapped[list] = mapped_column(JSON, default=list)
    evidence_gaps: Mapped[list] = mapped_column(JSON, default=list)
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class LineageNode(Base):
    """Immutable reference to a persisted provenance object."""

    __tablename__ = "lineage_nodes"
    __table_args__ = (
        UniqueConstraint("object_type", "object_id", name="uq_lineage_node_object"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    object_type: Mapped[str] = mapped_column(String(48), index=True)
    object_id: Mapped[str] = mapped_column(String(64), index=True)
    schema_version: Mapped[str] = mapped_column(String(40))
    reference_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reference_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class LineageEdge(Base):
    """Append-only provenance relationship between two lineage references."""

    __tablename__ = "lineage_edges"
    __table_args__ = (
        UniqueConstraint(
            "source_node_id", "target_node_id", "relationship_type",
            name="uq_lineage_edge_relationship",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_node_id: Mapped[str] = mapped_column(ForeignKey("lineage_nodes.id"), index=True)
    target_node_id: Mapped[str] = mapped_column(ForeignKey("lineage_nodes.id"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(48), index=True)
    schema_version: Mapped[str] = mapped_column(String(40))
    relationship_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    relationship_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    immutable: Mapped[bool] = mapped_column(Boolean, default=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class PipelineDefinition(Base):
    """Named pipeline family containing immutable computational versions."""

    __tablename__ = "pipeline_definitions"
    __table_args__ = (UniqueConstraint("name", name="uq_pipeline_definition_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    source_context: Mapped[str | None] = mapped_column(String(48), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class PipelineVersion(Base):
    """One immutable, fingerprinted computational pipeline definition."""

    __tablename__ = "pipeline_versions"
    __table_args__ = (
        UniqueConstraint("pipeline_definition_id", "version_number", name="uq_pipeline_version_number"),
        UniqueConstraint("definition_fingerprint", name="uq_pipeline_version_fingerprint"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    pipeline_definition_id: Mapped[str] = mapped_column(ForeignKey("pipeline_definitions.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    version_label: Mapped[str] = mapped_column(String(24))
    schema_version: Mapped[str] = mapped_column(String(48))
    status: Mapped[str] = mapped_column(String(24), default="DRAFT", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    definition_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    canonical_definition: Mapped[dict] = mapped_column(JSON)
    parent_pipeline_version_id: Mapped[str | None] = mapped_column(ForeignKey("pipeline_versions.id"), nullable=True, index=True)
    controlled_comparison_protocol_id: Mapped[str | None] = mapped_column(ForeignKey("controlled_comparison_protocols.id"), nullable=True, index=True)
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("artifacts.id"), nullable=True, index=True)
    source_context: Mapped[str | None] = mapped_column(String(48), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class PipelineStage(Base):
    """Ordered component snapshot belonging to exactly one Pipeline Version."""

    __tablename__ = "pipeline_stages"
    __table_args__ = (
        UniqueConstraint("pipeline_version_id", "stage_order", name="uq_pipeline_stage_order"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    pipeline_version_id: Mapped[str] = mapped_column(ForeignKey("pipeline_versions.id"), index=True)
    stage_order: Mapped[int] = mapped_column(Integer)
    stage_type: Mapped[str] = mapped_column(String(48), index=True)
    stage_name: Mapped[str] = mapped_column(String(120))
    configuration: Mapped[dict] = mapped_column(JSON)
    component_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stage_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProtocolTemplate(Base):
    """Reusable experimental specification template with configurable parameters."""

    __tablename__ = "protocol_templates"
    __table_args__ = (UniqueConstraint("name", name="uq_protocol_template_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[str] = mapped_column(String(24), default="v1")
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE", index=True)
    task_type: Mapped[str] = mapped_column(String(64), default="binary_classification")
    canonical_definition: Mapped[dict] = mapped_column(JSON)
    parameters_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    template_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ExperimentProtocol(Base):
    """Named research protocol family containing immutable versioned specifications."""

    __tablename__ = "experiment_protocols"
    __table_args__ = (UniqueConstraint("name", name="uq_experiment_protocol_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    template_id: Mapped[str | None] = mapped_column(ForeignKey("protocol_templates.id"), nullable=True, index=True)
    source_context: Mapped[str | None] = mapped_column(String(48), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ExperimentProtocolVersion(Base):
    """One immutable, fingerprinted research experimental protocol version."""

    __tablename__ = "experiment_protocol_versions"
    __table_args__ = (
        UniqueConstraint("protocol_id", "version_number", name="uq_experiment_protocol_version_number"),
        UniqueConstraint("definition_fingerprint", name="uq_experiment_protocol_version_fingerprint"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    protocol_id: Mapped[str] = mapped_column(ForeignKey("experiment_protocols.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    version_label: Mapped[str] = mapped_column(String(24))
    schema_version: Mapped[str] = mapped_column(String(48))
    status: Mapped[str] = mapped_column(String(24), default="DRAFT", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    definition_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    canonical_definition: Mapped[dict] = mapped_column(JSON)
    parent_protocol_version_id: Mapped[str | None] = mapped_column(ForeignKey("experiment_protocol_versions.id"), nullable=True, index=True)
    template_id: Mapped[str | None] = mapped_column(ForeignKey("protocol_templates.id"), nullable=True, index=True)
    pipeline_version_id: Mapped[str | None] = mapped_column(ForeignKey("pipeline_versions.id"), nullable=True, index=True)
    controlled_comparison_protocol_id: Mapped[str | None] = mapped_column(ForeignKey("controlled_comparison_protocols.id"), nullable=True, index=True)
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("artifacts.id"), nullable=True, index=True)
    source_context: Mapped[str | None] = mapped_column(String(48), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ScientificAuditEvent(Base):
    """First-class immutable audit record of a meaningful research-platform event."""

    __tablename__ = "scientific_audit_events"
    __table_args__ = (
        Index("ix_audit_events_object_type_id", "object_type", "object_id"),
        Index("ix_audit_events_parent_object_id", "parent_object_type", "parent_object_id"),
        Index("ix_audit_events_occurred_at_id", "occurred_at", "id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    schema_version: Mapped[str] = mapped_column(String(32), default="scientific_audit_event_v1")
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    event_category: Mapped[str] = mapped_column(String(32), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor_type: Mapped[str] = mapped_column(String(24), default="SYSTEM")
    actor_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_component: Mapped[str] = mapped_column(String(64), index=True)
    operation_key: Mapped[str | None] = mapped_column(String(240), nullable=True, index=True)
    object_type: Mapped[str] = mapped_column(String(48), index=True)
    object_id: Mapped[str] = mapped_column(String(64), index=True)
    parent_object_type: Mapped[str | None] = mapped_column(String(48), nullable=True, index=True)
    parent_object_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    before_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    after_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    previous_event_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    metadata_payload: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class SubgroupAnalysisStudy(Base):
    """First-class record of biomedical subgroup analysis and stratified evaluation."""
    __tablename__ = "subgroup_analysis_studies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    schema_version: Mapped[str] = mapped_column(String(32), default="subgroup_analysis_v1")
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), index=True)
    model_id: Mapped[str] = mapped_column(ForeignKey("models.id"), index=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"), nullable=True, index=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="created", index=True)
    operation_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    definition_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    subgroup_field: Mapped[str] = mapped_column(String(100), index=True)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    overall_population: Mapped[dict] = mapped_column(JSON, default=dict)
    subgroups_results: Mapped[list] = mapped_column(JSON, default=list)
    comparisons: Mapped[list] = mapped_column(JSON, default=list)
    limitations: Mapped[list] = mapped_column(JSON, default=list)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("artifacts.id"), nullable=True, index=True)
    failure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class DatasetQualityScorecard(Base):
    """First-class reproducible assessment of dataset quality and readiness."""

    __tablename__ = "dataset_quality_scorecards"
    __table_args__ = (
        Index("ix_scorecard_dataset_version", "dataset_id", "dataset_version_id"),
        Index("ix_scorecard_created_at_id", "created_at", "id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    schema_version: Mapped[str] = mapped_column(String(32), default="dataset_quality_scorecard_v1")
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"), nullable=True, index=True)
    experiment_id: Mapped[str | None] = mapped_column(ForeignKey("experiments.id"), nullable=True, index=True)
    protocol_version_id: Mapped[str | None] = mapped_column(ForeignKey("experiment_protocol_versions.id"), nullable=True, index=True)
    pipeline_version_id: Mapped[str | None] = mapped_column(ForeignKey("pipeline_versions.id"), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(24), default="PASS", index=True)
    operation_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    assessment_fingerprint: Mapped[str] = mapped_column(String(64), index=True)

    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    domains: Mapped[dict] = mapped_column(JSON, default=dict)
    schema_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    limitations: Mapped[list] = mapped_column(JSON, default=list)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)

    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("artifacts.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
