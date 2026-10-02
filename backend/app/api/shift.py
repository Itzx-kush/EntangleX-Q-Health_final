from uuid import UUID
from fastapi import APIRouter, Header, Query
from ..database import session_scope
from ..utils.serialization import clean_json
from .schemas import (
    DistributionShiftOut,
    DistributionShiftPreflightOut,
    DistributionShiftRequest,
)
from ..shift.service import (
    execute_shift_analysis,
    get_dataset_shift_analyses,
    get_shift_analysis,
    list_shift_analyses,
    resolve_shift_preflight,
)

router = APIRouter(prefix="/shift-analysis", tags=["distribution shift"])
dataset_shift_router = APIRouter(prefix="/datasets", tags=["distribution shift"])


def _to_shift_out(record) -> DistributionShiftOut:
    return DistributionShiftOut(
        id=record.id,
        reference_dataset_id=record.reference_dataset_id,
        reference_dataset_version_id=record.reference_dataset_version_id,
        reference_content_sha256=record.reference_content_sha256,
        comparison_dataset_id=record.comparison_dataset_id,
        comparison_dataset_version_id=record.comparison_dataset_version_id,
        comparison_content_sha256=record.comparison_content_sha256,
        model_id=record.model_id,
        external_validation_id=record.external_validation_id,
        parent_study_id=record.parent_study_id,
        model_seed=record.model_seed,
        status=record.status,
        operation_key=record.operation_key,
        policy_version=record.policy_version,
        configuration=clean_json(record.configuration),
        schema_analysis=clean_json(record.schema_analysis),
        target_analysis=clean_json(record.target_analysis),
        missingness_analysis=clean_json(record.missingness_analysis),
        feature_shifts=clean_json(record.feature_shifts),
        summary=clean_json(record.summary),
        flagged_features=record.flagged_features,
        warnings=record.warnings,
        limitations=record.limitations,
        provenance=clean_json(record.provenance),
        artifact_id=record.artifact_id,
        failure=record.failure,
        execution_time_seconds=record.execution_time_seconds,
        created_at=record.created_at,
        completed_at=record.completed_at,
    )


@router.post("", response_model=DistributionShiftOut, status_code=201)
def create_distribution_shift_analysis(
    request: DistributionShiftRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Execute distribution-shift analysis between a reference and comparison dataset."""
    with session_scope() as session:
        record = execute_shift_analysis(
            session,
            request,
            idempotency_key=idempotency_key,
        )
        return _to_shift_out(record)


@router.post("/preflight", response_model=DistributionShiftPreflightOut, status_code=200)
def inspect_distribution_shift_preflight(
    request: DistributionShiftRequest,
):
    """Non-mutating 12-step preflight inspection of datasets, schemas, and optional model requirements."""
    with session_scope() as session:
        res = resolve_shift_preflight(
            session,
            reference_dataset_id=str(request.reference_dataset_id),
            comparison_dataset_id=str(request.comparison_dataset_id),
            reference_dataset_version_id=str(request.reference_dataset_version_id) if request.reference_dataset_version_id else None,
            comparison_dataset_version_id=str(request.comparison_dataset_version_id) if request.comparison_dataset_version_id else None,
            model_id=str(request.model_id) if request.model_id else None,
            external_validation_id=str(request.external_validation_id) if request.external_validation_id else None,
            config=request.config.model_dump(mode="json") if request.config else None,
        )
        return DistributionShiftPreflightOut(**clean_json(res))


@router.get("", response_model=list[DistributionShiftOut])
def get_distribution_shift_analyses(
    reference_dataset_id: UUID | None = Query(default=None),
    comparison_dataset_id: UUID | None = Query(default=None),
    model_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Retrieve historical distribution-shift analyses with optional filtering."""
    with session_scope() as session:
        records = list_shift_analyses(
            session,
            reference_dataset_id=str(reference_dataset_id) if reference_dataset_id else None,
            comparison_dataset_id=str(comparison_dataset_id) if comparison_dataset_id else None,
            model_id=str(model_id) if model_id else None,
            limit=limit,
            offset=offset,
        )
        return [_to_shift_out(r) for r in records]


@router.get("/{analysis_id}", response_model=DistributionShiftOut)
def get_single_distribution_shift_analysis(analysis_id: str):
    """Retrieve complete distribution-shift analysis record by ID."""
    with session_scope() as session:
        record = get_shift_analysis(session, analysis_id)
        return _to_shift_out(record)


@router.get("/{analysis_id}/features")
def get_distribution_shift_features(
    analysis_id: str,
    flagged_only: bool = Query(default=False),
    model_input_only: bool = Query(default=False),
):
    """Retrieve feature-level distribution shift table with optional filtering."""
    with session_scope() as session:
        record = get_shift_analysis(session, analysis_id)
        features = record.feature_shifts
        if flagged_only:
            features = [f for f in features if f.get("flagged")]
        if model_input_only:
            features = [f for f in features if f.get("is_model_input")]
        return clean_json({
            "analysis_id": record.id,
            "policy_version": record.policy_version,
            "total_features": len(record.feature_shifts),
            "returned_features": len(features),
            "flagged_only": flagged_only,
            "model_input_only": model_input_only,
            "features": features,
        })


@router.get("/{analysis_id}/provenance")
def get_distribution_shift_provenance(analysis_id: str):
    """Retrieve complete cryptographic and software provenance for the shift analysis."""
    with session_scope() as session:
        record = get_shift_analysis(session, analysis_id)
        return clean_json({
            "analysis_id": record.id,
            "status": record.status,
            "operation_key": record.operation_key,
            "artifact_id": record.artifact_id,
            "provenance": record.provenance,
            "limitations": record.limitations,
            "warnings": record.warnings,
        })


@dataset_shift_router.get("/{dataset_id}/shift-analysis", response_model=list[DistributionShiftOut])
def get_dataset_related_shift_analyses(
    dataset_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Retrieve all shift analyses involving the specified dataset as either reference or comparison."""
    with session_scope() as session:
        records = get_dataset_shift_analyses(session, dataset_id, limit=limit, offset=offset)
        return [_to_shift_out(r) for r in records]
