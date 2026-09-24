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
from .schemas import DatasetOut, DatasetUploadMetadata, ValidateRequest

router = APIRouter(prefix="/datasets", tags=["datasets"])

@router.get("", response_model=list[DatasetOut])
def list_datasets(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    with session_scope() as session:
        return recent(session, Dataset, limit, offset)

@router.post("/upload", response_model=DatasetOut, status_code=201)
async def upload_dataset(metadata_json: str = Form(...), file: UploadFile = File(...)):
    try:
        try:
            metadata = DatasetUploadMetadata.model_validate_json(metadata_json)
        except ValidationError as exc:
            raise AppError("metadata_invalid", "Upload metadata is invalid. Supply name, target, positive_label, source information and deidentified=true.") from exc
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise AppError("extension_not_allowed", "Only UTF-8 .csv uploads are accepted.")
        content = bytearray()
        while part := await file.read(1024 * 1024):
            content.extend(part)
            if len(content) > get_settings().upload_limit:
                raise AppError("upload_too_large", "Dataset exceeds the upload size limit.", 413)
        return await run_in_threadpool(service.register_csv, bytes(content), file.filename, metadata)
    finally:
        await file.close()

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
