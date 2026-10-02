from datetime import datetime
from uuid import uuid4
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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

class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
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
    status: Mapped[str] = mapped_column(String(24), default="created", index=True)
    operation_key: Mapped[str] = mapped_column(String(128), unique=True)
    config: Mapped[dict] = mapped_column(JSON)
    execution_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    reproducibility_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    result_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    failure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
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
