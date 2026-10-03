"""API endpoints for Biomedical Subgroup Analysis & Stratified Evaluation."""
from __future__ import annotations

import json
from uuid import UUID
from fastapi import APIRouter, Response

from ..subgroups.schemas import (
    SubgroupAnalysisRequest,
    SubgroupPreflightResponse,
    SubgroupStudyOut,
)
from ..subgroups.service import (
    create_subgroup_study,
    export_study,
    get_study,
    list_studies_for_experiment,
    run_preflight,
)

router = APIRouter(prefix="/experiments", tags=["Subgroup Analysis"])


@router.post("/{identity}/subgroup-analysis/preflight", response_model=SubgroupPreflightResponse)
def preflight_subgroup_analysis(identity: UUID, request: SubgroupAnalysisRequest) -> SubgroupPreflightResponse:
    """Preflight check validating dataset, model, and subgroup definitions."""
    return run_preflight(str(identity), request)


@router.post("/{identity}/subgroup-analysis", response_model=SubgroupStudyOut)
def run_subgroup_analysis(identity: UUID, request: SubgroupAnalysisRequest) -> SubgroupStudyOut:
    """Create and execute an immutable biomedical subgroup analysis study."""
    return create_subgroup_study(str(identity), request)


@router.get("/{identity}/subgroup-analysis", response_model=list[SubgroupStudyOut])
def get_subgroup_analyses(identity: UUID) -> list[SubgroupStudyOut]:
    """List all subgroup analysis studies recorded for an experiment."""
    return list_studies_for_experiment(str(identity))


@router.get("/{identity}/subgroup-analysis/{study_id}", response_model=SubgroupStudyOut)
def get_subgroup_study_by_id(identity: UUID, study_id: str) -> SubgroupStudyOut:
    """Get a specific subgroup analysis study by ID."""
    return get_study(str(identity), study_id)


@router.get("/{identity}/subgroup-analysis/{study_id}/export")
def export_subgroup_study_json(identity: UUID, study_id: str):
    """Download deterministic machine-readable JSON export of a subgroup study."""
    payload = export_study(str(identity), study_id)
    content = json.dumps(payload, indent=2)
    return Response(
        content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="qhealth-subgroup-{study_id}.json"',
            "Cache-Control": "no-store",
        },
    )
