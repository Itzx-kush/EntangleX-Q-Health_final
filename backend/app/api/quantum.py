from fastapi import APIRouter
from ..quantum.backends import availability
from ..quantum.circuits import circuit_description
from .schemas import CircuitRequest, CircuitOut

router = APIRouter(prefix="/quantum", tags=["quantum simulation"])

@router.get("/capabilities", response_model=dict)
def capabilities():
    return availability()

@router.post("/circuit", response_model=CircuitOut)
def preview_circuit(request: CircuitRequest):
    return circuit_description(request.quantum, request.model_type, request.seed)
