from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel

from ..saved_reports.auth import SupabasePrincipal, require_supabase_user
from ..saved_reports.service import (
    delete_saved_report,
    download_saved_report,
    get_saved_report,
    list_saved_reports,
    save_research_report,
)

router = APIRouter(prefix="/me/research-reports", tags=["saved research reports"])
Principal = Annotated[SupabasePrincipal, Depends(require_supabase_user)]


class SaveResearchReportRequest(BaseModel):
    experiment_id: UUID


@router.get("")
def list_my_research_reports(principal: Principal, experiment_id: UUID | None = Query(None)):
    return list_saved_reports(principal, str(experiment_id) if experiment_id else None)


@router.post("", status_code=201)
def save_my_research_report(request: SaveResearchReportRequest, principal: Principal):
    return save_research_report(principal, str(request.experiment_id))


@router.get("/{saved_report_id}")
def get_my_research_report(saved_report_id: UUID, principal: Principal):
    return get_saved_report(principal, str(saved_report_id))[1]


@router.get("/{saved_report_id}/download")
def download_my_research_report(saved_report_id: UUID, principal: Principal):
    content, record = download_saved_report(principal, str(saved_report_id))
    return Response(content, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="qhealth-saved-report-{record["experiment_id"]}.pdf"',
        "Cache-Control": "no-store, private",
    })


@router.delete("/{saved_report_id}")
def delete_my_research_report(saved_report_id: UUID, principal: Principal):
    return delete_saved_report(principal, str(saved_report_id))
