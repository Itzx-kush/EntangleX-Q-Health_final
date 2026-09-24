from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile, Response
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from ..config import get_settings
from ..database import session_scope
from ..data import service
from ..data.quality import quality_report
from ..storage.entities import Dataset
from ..storage.repository import recent, require
from ..utils.errors import AppError
from .schemas import DatasetLibraryItem, DatasetOut, DatasetUploadMetadata, ValidateRequest

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _read_upload_limit() -> int:
    return get_settings().upload_limit


async def _read_upload(file: UploadFile) -> bytes:
    content = bytearray()
    while part := await file.read(1024 * 1024):
        content.extend(part)
        if len(content) > _read_upload_limit():
            raise AppError("upload_too_large", "Dataset exceeds the upload size limit.", 413)
    return bytes(content)


@router.get("", response_model=list[DatasetOut])
def list_datasets(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    with session_scope() as session:
        return recent(session, Dataset, limit, offset)


@router.get("/library", response_model=list[DatasetLibraryItem])
def list_dataset_library():
    return service.list_library()


@router.post("/library/{slug}", response_model=DatasetOut, status_code=201)
def use_library_dataset(slug: str):
    return service.register_builtin(slug)


@router.post("/inspect", response_model=dict)
async def inspect_dataset(file: UploadFile = File(...), target: str | None = Form(None), positive_label: str | None = Form(None)):
    try:
        if not file.filename:
            raise AppError("filename_required", "Choose a dataset file to inspect.")
        content = await _read_upload(file)
        return await run_in_threadpool(service.inspect_file, content, file.filename, target, positive_label)
    finally:
        await file.close()


async def _register_upload(metadata_json: str, file: UploadFile, *, legacy_csv_only: bool = False, require_metadata_confirmation: bool = False):
    try:
        try:
            metadata = DatasetUploadMetadata.model_validate_json(metadata_json)
        except ValidationError as exc:
            raise AppError("metadata_invalid", "Upload metadata is invalid. Supply name, target, positive_label, source information and deidentified=true.") from exc
        if not file.filename:
            raise AppError("filename_required", "Choose a dataset file to register.")
        if require_metadata_confirmation and not metadata.metadata_confirmed:
            raise AppError("metadata_confirmation_required", "Review and confirm the detected dataset metadata before registration.")
        if legacy_csv_only and not file.filename.lower().endswith(".csv"):
            raise AppError("extension_not_allowed", "The legacy upload route accepts CSV files; use the dataset registration flow for other formats.")
        content = await _read_upload(file)
        return await run_in_threadpool(service.register_file, content, file.filename, metadata)
    finally:
        await file.close()


@router.post("/register", response_model=DatasetOut, status_code=201)
async def register_dataset(metadata_json: str = Form(...), file: UploadFile = File(...)):
    return await _register_upload(metadata_json, file, require_metadata_confirmation=True)


@router.post("/upload", response_model=DatasetOut, status_code=201)
async def upload_dataset(metadata_json: str = Form(...), file: UploadFile = File(...)):
    # Existing clients keep the same route and CSV semantics; broader formats are
    # also accepted here without changing the downstream dataframe contract.
    return await _register_upload(metadata_json, file)


@router.post("/demo", response_model=DatasetOut, status_code=201)
def load_demo():
    return service.register_demo()


@router.get("/{identity}", response_model=DatasetOut)
def get_dataset(identity: UUID):
    with session_scope() as session:
        return require(session, Dataset, str(identity))


@router.get("/{identity}/provenance", response_model=dict)
def get_provenance(identity: UUID):
    with session_scope() as session:
        return require(session, Dataset, str(identity)).provenance


@router.post("/{identity}/validate", response_model=dict)
def validate_dataset(identity: UUID, request: ValidateRequest):
    dataset, frame = service.load_frame(str(identity))
    return quality_report(frame, dataset.provenance["target"], dataset.provenance["positive_label"], request.features)


@router.delete("/{identity}", status_code=204)
def delete_dataset(identity: UUID):
    service.delete_dataset(str(identity))
    return Response(status_code=204)
