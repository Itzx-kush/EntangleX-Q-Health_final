from fastapi import APIRouter,HTTPException
from sqlalchemy import select
from uuid import UUID
from backend.app.database import session_scope
from backend.app.storage.entities import AblationStudy
from backend.app.ablation.schemas import AblationPreflightResponse,AblationStudyOut,AblationStudyRequest
from backend.app.ablation.service import enqueue_ablation_studies,get_base_experiment,preflight_ablation_study

router=APIRouter(prefix="/ablation-studies",tags=["ablation"])

@router.post("/preflight",response_model=AblationPreflightResponse)
def preflight_ablation(request:AblationStudyRequest):
    with session_scope() as session:
        experiment=get_base_experiment(session,str(request.base_experiment_id))
        return preflight_ablation_study(session,experiment,request)

@router.post("",status_code=202,response_model=list[AblationStudyOut])
def execute_ablation(request:AblationStudyRequest):
    with session_scope() as session:
        experiment=get_base_experiment(session,str(request.base_experiment_id))
        preflight=preflight_ablation_study(session,experiment,request)
    if not preflight.feasible:
        raise HTTPException(status_code=422,detail={"code":"ablation_invalid","blockers":preflight.blockers})
    return enqueue_ablation_studies(experiment,request,preflight)

@router.get("/by-experiment/{experiment_id}",response_model=list[AblationStudyOut])
def list_ablation_studies(experiment_id:UUID):
    with session_scope() as session:
        return list(session.scalars(select(AblationStudy).where(AblationStudy.base_experiment_id==str(experiment_id)).order_by(AblationStudy.created_at.desc())))

@router.get("/{study_id}",response_model=AblationStudyOut)
def get_ablation_study(study_id:UUID):
    with session_scope() as session:
        study=session.get(AblationStudy,str(study_id))
        if not study: raise HTTPException(status_code=404,detail="Ablation study not found")
        return study
