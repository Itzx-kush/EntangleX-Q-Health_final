from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Header, Query

from ..database import session_scope
from ..jobs.manager import manager
from ..storage.repository import require
from ..storage.entities import MultiSeedStudy
from ..studies.schemas import (
    MultiSeedStudyDetailOut,
    MultiSeedStudyOut,
    MultiSeedStudyRequest,
    MultiSeedStudyResponse,
    MultiSeedStudySummaryOut,
    PairedMetricComparisonOut,
    StudyRunOut,
)
from ..studies.service import cancel_study, create_study, get_study_detail, get_study_runs, list_studies
from ..utils.errors import AppError

router = APIRouter(prefix="/studies/multi-seed", tags=["multi-seed evaluation"])


@router.post("", response_model=MultiSeedStudyResponse, status_code=202)
def create_multi_seed_study(
    request: MultiSeedStudyRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    with session_scope() as session:
        study, runs = create_study(session, request, idempotency_key=idempotency_key)
        study_id = study.id
        already_terminal = study.status in {"completed", "failed", "cancelled", "running"}

    if not already_terminal:
        manager.enqueue_study(study_id)

    with session_scope() as session:
        study = require(session, MultiSeedStudy, study_id)
        runs = get_study_runs(study_id)
        return {"study": study, "runs": runs}


@router.get("", response_model=list[MultiSeedStudyOut])
def get_multi_seed_studies(
    base_experiment_id: UUID | None = None,
    dataset_id: UUID | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return list_studies(
        base_experiment_id=str(base_experiment_id) if base_experiment_id else None,
        dataset_id=str(dataset_id) if dataset_id else None,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/{study_id}", response_model=MultiSeedStudyDetailOut)
def get_multi_seed_study(study_id: UUID):
    return get_study_detail(str(study_id))


@router.get("/{study_id}/runs", response_model=list[StudyRunOut])
def get_multi_seed_study_runs(study_id: UUID):
    return get_study_runs(str(study_id))


@router.get("/{study_id}/summary", response_model=MultiSeedStudySummaryOut)
def get_multi_seed_study_summary(study_id: UUID):
    detail = get_study_detail(str(study_id))
    summary = detail.get("summary")
    if not summary:
        raise AppError("study_summary_unavailable", "Multi-seed statistical summary is not yet available for this study.", 409)
    return summary


@router.get("/{study_id}/comparison", response_model=list[PairedMetricComparisonOut])
def get_multi_seed_study_comparison(study_id: UUID):
    detail = get_study_detail(str(study_id))
    summary = detail.get("summary")
    if not summary or "paired_differences" not in summary:
        raise AppError("study_comparison_unavailable", "Multi-seed paired comparisons are not yet available for this study.", 409)
    return summary["paired_differences"]


@router.post("/{study_id}/cancel", response_model=MultiSeedStudyOut)
def cancel_multi_seed_study(study_id: UUID):
    return cancel_study(str(study_id))
