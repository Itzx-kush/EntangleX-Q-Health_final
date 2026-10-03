from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from uuid import uuid4

from ..database import session_scope
from ..storage.entities import ThresholdAnalysisStudy
from ..threshold.schemas import ThresholdAnalysisRequest, ThresholdPreflightResponse
from ..threshold.service import preflight, execute_threshold_study
from ..utils.serialization import utcnow
from ..utils.errors import AppError
from ..evaluation.context import resolve_model_evaluation_context

router = APIRouter(prefix="/threshold-analysis", tags=["Threshold Analysis"])

@router.post("/preflight", response_model=ThresholdPreflightResponse)
def run_preflight(req: ThresholdAnalysisRequest):
    return preflight(req)

@router.post("")
def create_study(req: ThresholdAnalysisRequest, background_tasks: BackgroundTasks):
    from ..utils.serialization import fingerprint
    pf = preflight(req)
    if not pf.feasible:
        raise AppError("infeasible", "Threshold analysis is not feasible.", 422)
        
    study_id = str(uuid4())
    operation_key = f"threshold:{fingerprint(req.model_dump(mode='json'))}"
    
    with session_scope() as session:
        from sqlalchemy import select
        existing = session.scalar(select(ThresholdAnalysisStudy).where(ThresholdAnalysisStudy.operation_key == operation_key))
        if existing:
            return {"id": existing.id, "status": existing.status}
        context = resolve_model_evaluation_context(
            session, str(req.model_id), str(req.dataset_id),
            str(req.dataset_version_id) if req.dataset_version_id else None,
        )
            
        study = ThresholdAnalysisStudy(
            id=study_id,
            model_id=str(req.model_id),
            dataset_id=str(req.dataset_id),
            dataset_version_id=str(req.dataset_version_id) if req.dataset_version_id else None,
            operation_key=operation_key,
            configuration=req.model_dump(mode="json"),
            provenance=context.source_context(),
            created_at=utcnow()
        )
        session.add(study)
        
    background_tasks.add_task(execute_threshold_study, study_id)
    return {"id": study_id, "status": "created"}

@router.get("/{study_id}")
def get_study(study_id: str):
    with session_scope() as session:
        study = session.get(ThresholdAnalysisStudy, study_id)
        if not study:
            raise HTTPException(status_code=404)
        return {
            "id": study.id,
            "status": study.status,
            "model_id": study.model_id,
            "dataset_id": study.dataset_id,
            "results": study.results,
            "curves": study.curves,
            "summary": study.summary,
            "limitations": study.limitations,
            "failure": study.failure,
            "configuration": study.configuration,
            "provenance": study.provenance,
        }
