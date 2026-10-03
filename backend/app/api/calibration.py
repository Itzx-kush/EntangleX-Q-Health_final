from fastapi import APIRouter, BackgroundTasks
from uuid import uuid4

from ..database import session_scope
from ..storage.entities import CalibrationStudy
from ..calibration.schemas import CalibrationRequest, CalibrationPreflightResponse
from ..calibration.service import preflight, execute_calibration_study
from ..evaluation.context import resolve_model_evaluation_context
from ..utils.errors import AppError
from ..utils.serialization import utcnow

router = APIRouter(prefix="/calibration", tags=["Calibration"])

@router.post("/preflight", response_model=CalibrationPreflightResponse)
def run_preflight(req: CalibrationRequest):
    return preflight(req)

@router.post("")
def create_study(req: CalibrationRequest, background_tasks: BackgroundTasks):
    from ..utils.serialization import fingerprint
    pf = preflight(req)
    if not pf.feasible:
        raise AppError(
            "calibration_infeasible",
            "Calibration study is not feasible: " + "; ".join(pf.limitations),
            422,
        )
        
    study_id = str(uuid4())
    operation_key = f"calibration:{fingerprint(req.model_dump(mode='json'))}"
    
    with session_scope() as session:
        # Check idempotency
        from sqlalchemy import select
        existing = session.scalar(select(CalibrationStudy).where(CalibrationStudy.operation_key == operation_key))
        if existing:
            return {"id": existing.id, "status": existing.status}
        context = resolve_model_evaluation_context(
            session, str(req.model_id), str(req.dataset_id),
            str(req.dataset_version_id) if req.dataset_version_id else None,
        )
            
        study = CalibrationStudy(
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
        
    background_tasks.add_task(execute_calibration_study, study_id)
    return {"id": study_id, "status": "created"}

@router.get("/{study_id}")
def get_study(study_id: str):
    with session_scope() as session:
        study = session.get(CalibrationStudy, study_id)
        if not study:
            raise AppError("calibration_study_missing", "Calibration study not found.", 404)
        return {
            "id": study.id,
            "status": study.status,
            "model_id": study.model_id,
            "dataset_id": study.dataset_id,
            "metrics": study.metrics,
            "curves": study.curves,
            "summary": study.summary,
            "limitations": study.limitations,
            "provenance": study.provenance,
            "failure": study.failure
        }
