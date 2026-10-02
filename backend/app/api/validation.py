from uuid import UUID
from fastapi import APIRouter, Header, Query
from ..database import session_scope
from ..utils.serialization import clean_json
from .schemas import (
    ExternalValidationRequest,
    ExternalValidationOut,
    ValidationPreflightOut,
)
from ..validation.service import (
    execute_validation,
    get_validation,
    list_validations,
    resolve_preflight,
)

router = APIRouter(prefix="/validation/external", tags=["external validation"])


@router.post("", response_model=ExternalValidationOut, status_code=201)
def create_external_validation(
    request: ExternalValidationRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    with session_scope() as session:
        record = execute_validation(
            session,
            model_id=str(request.model_id),
            external_dataset_id=str(request.external_dataset_id),
            external_dataset_version_id=str(request.external_dataset_version_id) if request.external_dataset_version_id else None,
            label_mapping=request.label_mapping,
            idempotency_key=idempotency_key,
            notes=request.notes,
        )
        return ExternalValidationOut(
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


@router.post("/preflight", response_model=ValidationPreflightOut)
def preflight_external_validation(request: ExternalValidationRequest):
    with session_scope() as session:
        result = resolve_preflight(
            session,
            model_id=str(request.model_id),
            external_dataset_id=str(request.external_dataset_id),
            external_dataset_version_id=str(request.external_dataset_version_id) if request.external_dataset_version_id else None,
            label_mapping=request.label_mapping,
        )
        return ValidationPreflightOut(
            ready=result["ready"],
            model_id=str(request.model_id),
            model_type=result["model"].model_type,
            training_dataset=result["training_dataset"],
            external_dataset=result["external_dataset"],
            feature_compatibility=result["feature_compatibility"],
            label_compatibility=result["label_compatibility"],
            threshold_lock=result["threshold_lock"],
            artifact_integrity=result["artifact_integrity"],
            independence=result["independence"],
            warnings=result["warnings"],
            block_reasons=result["block_reasons"],
        )


@router.get("", response_model=list[ExternalValidationOut])
def get_external_validations(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    model_id: UUID | None = None,
    status: str | None = None,
):
    with session_scope() as session:
        records = list_validations(
            session,
            limit=limit,
            offset=offset,
            model_id=str(model_id) if model_id else None,
            status=status,
        )
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


@router.get("/{validation_id}", response_model=ExternalValidationOut)
def get_external_validation_detail(validation_id: UUID):
    with session_scope() as session:
        record = get_validation(session, str(validation_id))
        return ExternalValidationOut(
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


@router.get("/{validation_id}/metrics", response_model=dict)
def get_external_validation_metrics(validation_id: UUID):
    with session_scope() as session:
        record = get_validation(session, str(validation_id))
        return clean_json({
            "validation_id": record.id,
            "model_id": record.model_id,
            "status": record.status,
            "metrics": record.metrics,
            "internal_metrics": record.internal_metrics,
            "comparison": record.comparison,
            "generalization_gap": record.generalization_gap,
            "threshold_metadata": record.threshold_metadata,
            "warnings": record.warnings,
        })


@router.get("/{validation_id}/provenance", response_model=dict)
def get_external_validation_provenance(validation_id: UUID):
    with session_scope() as session:
        record = get_validation(session, str(validation_id))
        return clean_json({
            "validation_id": record.id,
            "model_id": record.model_id,
            "provenance": record.provenance,
            "artifact_id": record.artifact_id,
            "limitations": record.limitations,
        })
