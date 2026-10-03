from __future__ import annotations

from typing import Literal
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from ..data_quality import (
    DatasetQualityPreflightResponse,
    DatasetQualityRequest,
    DatasetQualityScorecardOut,
    ScorecardComparisonOut,
    assess_dataset_quality,
    compare_scorecards,
    export_scorecard_markdown,
    get_latest_scorecard,
    get_scorecard,
    list_scorecards,
    preflight_dataset_quality,
)
from ..data_quality.service import _to_scorecard_out
from ..database import session_scope
from ..storage.entities import DatasetQualityScorecard, Experiment
from ..storage.repository import require

router = APIRouter(tags=["data-quality"])


@router.post(
    "/datasets/{dataset_id}/quality-scorecard/preflight",
    response_model=DatasetQualityPreflightResponse,
)
def api_preflight_dataset_quality(dataset_id: str, request: DatasetQualityRequest):
    with session_scope() as session:
        return preflight_dataset_quality(session, dataset_id, request)


@router.post(
    "/datasets/{dataset_id}/quality-scorecard",
    response_model=DatasetQualityScorecardOut,
)
def api_assess_dataset_quality(dataset_id: str, request: DatasetQualityRequest):
    with session_scope() as session:
        scorecard = assess_dataset_quality(session, dataset_id, request)
        return _to_scorecard_out(scorecard)


@router.get(
    "/datasets/{dataset_id}/quality-scorecard",
    response_model=list[DatasetQualityScorecardOut],
)
def api_list_dataset_scorecards(
    dataset_id: str,
    dataset_version_id: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    with session_scope() as session:
        items = list_scorecards(session, dataset_id, dataset_version_id, status, limit, offset)
        return [_to_scorecard_out(sc) for sc in items]


@router.get(
    "/datasets/{dataset_id}/quality-scorecard/latest",
    response_model=DatasetQualityScorecardOut,
)
def api_get_latest_scorecard(
    dataset_id: str,
    dataset_version_id: str | None = Query(None),
):
    with session_scope() as session:
        sc = get_latest_scorecard(session, dataset_id, dataset_version_id)
        if not sc:
            raise HTTPException(status_code=404, detail="No quality scorecard found for this dataset/version.")
        return _to_scorecard_out(sc)


@router.get(
    "/datasets/{dataset_id}/quality-scorecard/compare",
    response_model=ScorecardComparisonOut,
)
def api_compare_scorecards(
    dataset_id: str,
    base_id: str = Query(...),
    target_id: str = Query(...),
):
    with session_scope() as session:
        return compare_scorecards(session, base_id, target_id)


@router.get(
    "/datasets/{dataset_id}/quality-scorecard/{scorecard_id}",
    response_model=DatasetQualityScorecardOut,
)
def api_get_scorecard(dataset_id: str, scorecard_id: str):
    with session_scope() as session:
        sc = get_scorecard(session, scorecard_id)
        if sc.dataset_id != dataset_id:
            raise HTTPException(status_code=404, detail="Scorecard not found for this dataset.")
        return _to_scorecard_out(sc)


@router.get(
    "/datasets/{dataset_id}/quality-scorecard/{scorecard_id}/export",
)
def api_export_scorecard(
    dataset_id: str,
    scorecard_id: str,
    format: Literal["json", "markdown"] = Query("json"),
):
    with session_scope() as session:
        sc = get_scorecard(session, scorecard_id)
        if sc.dataset_id != dataset_id:
            raise HTTPException(status_code=404, detail="Scorecard not found for this dataset.")
        if format == "markdown":
            md = export_scorecard_markdown(sc)
            return PlainTextResponse(md, media_type="text/markdown")
        return _to_scorecard_out(sc)


@router.post(
    "/experiments/{experiment_id}/dataset-quality",
    response_model=DatasetQualityScorecardOut,
)
def api_assess_experiment_dataset_quality(
    experiment_id: str,
    request: DatasetQualityRequest | None = None,
):
    req = request or DatasetQualityRequest()
    with session_scope() as session:
        exp = require(session, Experiment, experiment_id)
        req.experiment_id = exp.id
        if not req.protocol_version_id and exp.protocol_version_id:
            req.protocol_version_id = exp.protocol_version_id
        if not req.pipeline_version_id and exp.pipeline_version_id:
            req.pipeline_version_id = exp.pipeline_version_id

        scorecard = assess_dataset_quality(session, exp.dataset_id, req)
        return _to_scorecard_out(scorecard)


@router.get(
    "/experiments/{experiment_id}/dataset-quality",
    response_model=DatasetQualityScorecardOut,
)
def api_get_experiment_dataset_quality(experiment_id: str):
    with session_scope() as session:
        exp = require(session, Experiment, experiment_id)
        stmt = (
            select(DatasetQualityScorecard)
            .where(DatasetQualityScorecard.experiment_id == experiment_id)
            .order_by(DatasetQualityScorecard.created_at.desc())
            .limit(1)
        )
        sc = session.scalar(stmt)
        if not sc:
            # Fall back to latest scorecard for the dataset
            sc = get_latest_scorecard(session, exp.dataset_id)
        if not sc:
            raise HTTPException(status_code=404, detail="No quality scorecard found for this experiment's dataset.")
        return _to_scorecard_out(sc)
