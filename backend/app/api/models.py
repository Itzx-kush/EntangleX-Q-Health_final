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
from .schemas import ModelOut, PredictionRequest, PredictionOut, ExplanationRequest, ExplanationOut, CircuitOut, ExternalValidationOut
from ..validation.service import list_validations

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
    # Built-in library datasets are packaged public benchmarks and may safely
    # provide a withheld prediction sample. Uploaded datasets never do.
    is_public_benchmark = dataset.provenance.get("origin") == "built_in" or dataset.provenance.get("is_demo", False)
    if not is_public_benchmark:
        raise AppError("demo_only", "Sample retrieval is available only for bundled public benchmarks, never uploaded datasets.", 403)
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

@router.get("/{identity}/external-validation", response_model=list[ExternalValidationOut])
def model_external_validations(identity: UUID):
    with session_scope() as session:
        require(session, ModelRecord, str(identity))
        records = list_validations(session, model_id=str(identity))
        return [
            ExternalValidationOut(
                id=record.id,
                model_id=record.model_id,
                model_type=record.provenance.get("model_type", "unknown"),
                run_id=record.run_id,
                experiment_id=record.experiment_id,
                training_dataset_id=record.training_dataset_id,
                training_dataset_version_id=record.training_dataset_version_id,
                external_dataset_id=record.external_dataset_id,
                external_dataset_version_id=record.external_dataset_version_id,
                study_id=record.study_id,
                study_seed=record.study_seed,
                status=record.status,
                operation_key=record.operation_key,
                compatibility=clean_json(record.compatibility),
                label_mapping=clean_json(record.label_mapping),
                threshold_metadata=clean_json(record.threshold_metadata),
                metrics=clean_json(record.metrics),
                internal_metrics=clean_json(record.internal_metrics),
                comparison=clean_json(record.comparison),
                generalization_gap=clean_json(record.generalization_gap),
                provenance=clean_json(record.provenance),
                artifact_id=record.artifact_id,
                limitations=record.limitations,
                warnings=record.warnings,
                failure=record.failure,
                created_at=record.created_at,
                completed_at=record.completed_at,
            )
            for record in records
        ]
