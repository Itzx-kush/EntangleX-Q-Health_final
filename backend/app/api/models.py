from uuid import UUID
from fastapi import APIRouter, Query
from sqlalchemy import select
from ..data.service import load_frame
from ..database import session_scope
from ..explainability.service import explain
from ..models.prediction import get_bundle, predict
from ..storage.entities import ModelRecord, ExplanationRecord
from ..storage.repository import recent, require
from ..utils.errors import AppError
from ..utils.serialization import clean_json
from .schemas import ModelOut, PredictionRequest, PredictionOut, ExplanationRequest, ExplanationOut, CircuitOut

router = APIRouter(prefix="/models", tags=["model registry, prediction, explainability"])

@router.get("", response_model=list[ModelOut])
def list_models(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    with session_scope() as session:
        return recent(session, ModelRecord, limit, offset)

@router.get("/{identity}", response_model=ModelOut)
def get_model(identity: UUID):
    with session_scope() as session:
        return require(session, ModelRecord, str(identity))

@router.get("/{identity}/input-schema", response_model=dict)
def model_schema(identity: UUID):
    record, bundle = get_bundle(str(identity))
    return {"model_id": str(identity), "features": [{"name": f, "type": "number" if f in bundle["numeric"] else "string", "nullable": True} for f in bundle["features"]], "target_excluded": True, "positive_label": bundle["positive_label"], "negative_label": bundle["negative_label"], "missing_strategy": bundle["config"]["pipeline"]["imputer"]}

@router.get("/{identity}/demo-sample", response_model=dict)
def public_demo_sample(identity: UUID):
    record, bundle = get_bundle(str(identity))
    dataset, frame = load_frame(bundle["dataset_id"])
    if not dataset.provenance.get("is_demo", False):
        raise AppError("demo_only", "Sample retrieval is available only for the bundled public benchmark, never uploaded datasets.", 403)
    values = frame.iloc[bundle["test_indices"][0]][bundle["features"]].to_dict()
    return {"sample": "Public benchmark sample", "features": clean_json(values), "source": dataset.provenance["source"], "target_withheld": True}

@router.post("/{identity}/predict", response_model=PredictionOut)
def predict_samples(identity: UUID, request: PredictionRequest):
    return predict(str(identity), request)

@router.post("/{identity}/explain", response_model=ExplanationOut, status_code=201)
def explain_model(identity: UUID, request: ExplanationRequest):
    return explain(str(identity), request)

@router.get("/{identity}/explanations", response_model=list[ExplanationOut])
def explanations(identity: UUID):
    with session_scope() as session:
        require(session, ModelRecord, str(identity))
        return list(session.scalars(select(ExplanationRecord).where(ExplanationRecord.model_id == str(identity)).order_by(ExplanationRecord.created_at.desc())))

@router.get("/{identity}/circuit", response_model=CircuitOut)
def fitted_circuit(identity: UUID):
    with session_scope() as session:
        record = require(session, ModelRecord, str(identity))
    quantum = record.details.get("quantum")
    if not quantum:
        raise AppError("circuit_unavailable", "A completed quantum model is required for circuit retrieval.", 404)
    return quantum["circuit"]
