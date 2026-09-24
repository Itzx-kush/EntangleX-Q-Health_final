import csv
import hashlib
import io
from threading import Lock
from uuid import uuid4
import numpy as np
import pandas as pd
from sqlalchemy import select
from ..api.schemas import DatasetUploadMetadata
from ..config import get_settings
from ..database import session_scope
from ..storage.entities import Dataset, Experiment
from ..storage.files import atomic_bytes, safe_path, sanitize_filename, verify
from ..storage.repository import require
from ..utils.errors import AppError
from ..utils.serialization import utcnow
from .quality import quality_report

_demo_registration_lock = Lock()
_dataset_delete_lock = Lock()

def parse_csv(content: bytes, target: str) -> pd.DataFrame:
    settings = get_settings()
    if len(content) > settings.upload_limit:
        raise AppError("upload_too_large", "The upload exceeds the configured size limit.", 413)
    if b"\x00" in content:
        raise AppError("invalid_csv", "Binary/NUL content is not supported.")
    try:
        text = content.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text), strict=True))
        header = rows[0]
    except (UnicodeDecodeError, StopIteration, csv.Error) as exc:
        raise AppError("invalid_csv", "Upload a nonempty UTF-8 comma-separated CSV file.") from exc
    if len(header) < 2 or len(header) > settings.max_columns:
        raise AppError("column_limit", "The CSV must contain a target and input features within the column limit.")
    normalized_header = [h.lstrip("\ufeff") for h in header]
    if normalized_header != header:
        header = normalized_header
    derived_readmission_target = target.strip() == "readmitted_30d" and target not in header and "readmitted" in header
    if len(set(header)) != len(header) or any(not h.strip() or h != h.strip() or len(h) > 100 or any(ord(c) < 32 for c in h) for h in header):
        raise AppError("invalid_header", "Column names must be unique, trimmed, nonempty, and at most 100 characters.")
    if any(row and len(row) != len(header) for row in rows[1:]):
        raise AppError("inconsistent_schema", "CSV rows and headers have inconsistent field counts.")
    try:
        # Preserve target labels exactly; infer input numeric types for review.
        source_target = "readmitted" if derived_readmission_target else target
        frame = pd.read_csv(io.StringIO(text), dtype={source_target: "string"}, nrows=settings.max_rows + 1, on_bad_lines="error")
    except (ValueError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise AppError("invalid_csv", "CSV parsing failed; check quoting, delimiters, and the table schema.") from exc
    if len(frame) < 10 or len(frame) > settings.max_rows:
        raise AppError("row_limit", "The dataset must have at least 10 rows and remain within the configured row limit.")
    frame.columns = [str(c).lstrip("\ufeff").strip() for c in frame.columns]
    if list(frame.columns) != header or not isinstance(frame.index, pd.RangeIndex):
        raise AppError("inconsistent_schema", "CSV rows and headers have inconsistent field counts.")
    if derived_readmission_target:
        frame[target] = (frame["readmitted"].astype("string").str.strip() == "<30").astype(int)
        frame = frame.drop(columns=["readmitted", "encounter_id", "patient_nbr"], errors="ignore")
    elif target not in frame.columns and "readmitted" in frame.columns and target.strip() == "readmitted_30d":
        frame[target] = (frame["readmitted"].astype("string").str.strip() == "<30").astype(int)
        frame = frame.drop(columns=["readmitted", "encounter_id", "patient_nbr"], errors="ignore")
    for col in frame.select_dtypes(exclude=np.number):
        # Object arrays use np.nan (not pd.NA) for sklearn's imputers.
        frame[col] = frame[col].map(lambda v: str(v) if pd.notna(v) else np.nan).astype(object)
    return frame

def register_csv(content: bytes, filename: str, metadata: DatasetUploadMetadata, *, license_info: str | None = None) -> Dataset:
    if not filename.lower().endswith(".csv"):
        raise AppError("extension_not_allowed", "Only UTF-8 .csv uploads are accepted.")
    frame = parse_csv(content, metadata.target)
    quality = quality_report(frame, metadata.target, metadata.positive_label)
    identity = str(uuid4())
    timestamp = utcnow()
    sha = hashlib.sha256(content).hexdigest()
    provenance = {
        **metadata.model_dump(exclude={"deidentified"}),
        "task": "binary_classification", "dataset_hash": sha,
        "hash_algorithm": "sha256", "hash_scope": "exact stored CSV bytes",
        "uploaded_at": timestamp.isoformat(), "row_count": len(frame),
        "feature_count": len(frame.columns) - 1,
        "features": [c for c in frame if c != metadata.target],
        "numeric_features": quality["numeric_features"], "categorical_features": quality["categorical_features"],
        "target_classes": quality["target_classes"], "class_distribution": quality["class_distribution"],
        "negative_label": next(c for c in quality["target_classes"] if c != metadata.positive_label),
        "license": license_info, "is_demo": license_info is not None, "deidentification_asserted_by_uploader": True,
        "preprocessing_configuration": "Stored per experiment; source dataset is immutable.",
    }
    path = safe_path("data/datasets", identity, ".csv")
    atomic_bytes(path, content)
    try:
        with session_scope() as session:
            record = Dataset(id=identity, name=metadata.name, filename=sanitize_filename(filename), sha256=sha, provenance=provenance, quality=quality, created_at=timestamp)
            session.add(record)
        return record
    except Exception:
        path.unlink(missing_ok=True)
        raise

def load_frame(identity: str) -> tuple[Dataset, pd.DataFrame]:
    with session_scope() as session:
        record = require(session, Dataset, identity)
    path = safe_path("data/datasets", identity, ".csv")
    verify(path, record.sha256)
    return record, parse_csv(path.read_bytes(), record.provenance["target"])

def register_demo() -> Dataset:
    with _demo_registration_lock:
        return _register_demo()

def _register_demo() -> Dataset:
    from sklearn.datasets import load_breast_cancer
    from importlib.metadata import version
    data = load_breast_cancer(as_frame=True)
    frame = data.data.copy()
    # sklearn target 0 = malignant. Map explicitly; the positive class is malignant.
    frame["diagnosis"] = np.where(data.target.to_numpy() == 0, "malignant", "benign")
    meta = DatasetUploadMetadata(
        name="Breast Cancer Wisconsin Diagnostic", domain="oncology",
        source="UCI Machine Learning Repository, distributed with scikit-learn",
        source_url="https://doi.org/10.24432/C5DW2B", version=f"scikit-learn-{version('scikit-learn')}",
        target="diagnosis", positive_label="malignant", deidentified=True,
    )
    content = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    sha = hashlib.sha256(content).hexdigest()
    with session_scope() as session:
        existing = session.scalar(select(Dataset).where(Dataset.sha256 == sha, Dataset.name == meta.name))
        if existing is not None:
            return existing
    return register_csv(content, "wdbc-benchmark.csv", meta, license_info="UCI CC BY 4.0; Wolberg, Mangasarian, Street & Street (1993). Identifier column is not included in sklearn features.")

def delete_dataset(identity: str) -> None:
    with _dataset_delete_lock:
        _delete_dataset(identity)

def _delete_dataset(identity: str) -> None:
    with session_scope() as session:
        dataset = require(session, Dataset, identity)
        if session.scalar(select(Experiment.id).where(Experiment.dataset_id == identity).limit(1)):
            raise AppError("dataset_in_use", "This dataset is referenced by an experiment and is retained for reproducibility.", 409)
        expected = dataset.sha256
    path = safe_path("data/datasets", identity, ".csv")
    if not path.is_file():
        raise AppError("integrity_error", "Stored dataset is missing and cannot be safely deleted.", 409)
    try:
        original = path.read_bytes()
    except OSError as exc:
        raise AppError("integrity_error", "Stored dataset could not be read and cannot be safely deleted.", 409) from exc
    if hashlib.sha256(original).hexdigest() != expected:
        raise AppError("integrity_error", "Stored dataset integrity has changed.", 409)
    try:
        path.unlink()
    except OSError as exc:
        raise AppError("storage_delete_failed", "Stored dataset could not be removed safely.", 409) from exc
    try:
        with session_scope() as session:
            dataset = require(session, Dataset, identity)
            if session.scalar(select(Experiment.id).where(Experiment.dataset_id == identity).limit(1)):
                raise AppError("dataset_in_use", "This dataset is referenced by an experiment and is retained for reproducibility.", 409)
            session.delete(dataset)
    except Exception:
        try:
            atomic_bytes(path, original)
        except OSError as exc:
            raise AppError("storage_consistency", "Dataset deletion failed and storage could not be restored.", 500) from exc
        raise
