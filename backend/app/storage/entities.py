from datetime import datetime
from uuid import uuid4
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
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
    status: Mapped[str] = mapped_column(String(24), default="queued")
    config: Mapped[dict] = mapped_column(JSON)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

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
    status: Mapped[str] = mapped_column(String(24), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[str] = mapped_column(String(200), default="Waiting for worker")
    errors: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

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
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), index=True)
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

