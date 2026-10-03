from fastapi import APIRouter, HTTPException
from uuid import UUID

from ..database import session_scope
from ..storage.entities import ConditionTask
from ..readiness.schemas import ConditionTaskCreate, ConditionTaskResponse, ReadinessResult
from ..readiness.service import create_condition_task, evaluate_condition_task_readiness

router = APIRouter(prefix="/condition-tasks", tags=["condition-tasks"])

@router.post("", response_model=ConditionTaskResponse, status_code=201)
def create_task(req: ConditionTaskCreate):
    with session_scope() as db:
        task = create_condition_task(db, req)
        db.commit()
        db.refresh(task)
        return task

@router.get("", response_model=list[ConditionTaskResponse])
def list_tasks():
    with session_scope() as db:
        return db.query(ConditionTask).all()

@router.get("/{task_id}", response_model=ConditionTaskResponse)
def get_task(task_id: UUID):
    with session_scope() as db:
        task = db.get(ConditionTask, str(task_id))
        if not task:
            raise HTTPException(404, "ConditionTask not found")
        return task

@router.post("/{task_id}/readiness", response_model=ReadinessResult)
def assess_readiness(task_id: UUID):
    with session_scope() as db:
        result = evaluate_condition_task_readiness(db, str(task_id))
        db.commit()
        return result

@router.get("/{task_id}/capabilities")
def get_task_capabilities(task_id: UUID):
    with session_scope() as db:
        task = db.get(ConditionTask, str(task_id))
        if not task:
            raise HTTPException(404, "ConditionTask not found")
        if not task.readiness_report:
            result = evaluate_condition_task_readiness(db, str(task_id))
            db.commit()
            return result.supported_models
        return task.readiness_report.get("supported_models", [])