from fastapi import APIRouter
from ..quantum.backends import availability
from ..quantum.circuits import circuit_description
from ..quantum.resource_advisor import advise_resources, resource_policy
from .schemas import CircuitRequest, CircuitOut, ResourceAdvisorRequest

router = APIRouter(prefix="/quantum", tags=["quantum simulation"])

@router.get("/capabilities", response_model=dict)
def capabilities():
    return availability()

@router.post("/circuit", response_model=CircuitOut)
def preview_circuit(request: CircuitRequest):
    return circuit_description(request.quantum, request.model_type, request.seed)

@router.get("/resource-policy", response_model=dict)
def resource_budget_policy():
    return resource_policy()

@router.post("/resource-advisor", response_model=dict)
def resource_advisor(request: ResourceAdvisorRequest):
    return advise_resources(request)
