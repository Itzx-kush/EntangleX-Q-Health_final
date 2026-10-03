from fastapi import APIRouter
from ..quantum.backends import availability
from ..quantum.circuits import circuit_description
from ..quantum.errors import QuantumProviderError
from ..quantum.resource_advisor import advise_resources, resource_policy
from ..quantum.service import service
from ..utils.errors import AppError
from .schemas import CircuitRequest, CircuitOut, ProviderPreflightRequest, ResourceAdvisorRequest

router = APIRouter(prefix="/quantum", tags=["quantum simulation"])

@router.get("/capabilities", response_model=dict)
def capabilities():
    return availability()


def _provider_call(callable_):
    try:
        return callable_()
    except QuantumProviderError as exc:
        status = 404 if exc.category.value == "CONFIGURATION_ERROR" else 503
        raise AppError(f"quantum_provider_{exc.category.value.lower()}", exc.safe_message, status) from exc


@router.get("/providers", response_model=list[dict])
def providers():
    return service.list_providers()


@router.get("/providers/health", response_model=dict)
def provider_health():
    return service.health()


@router.get("/providers/{provider_id}", response_model=dict)
def provider(provider_id: str):
    return _provider_call(lambda: service.provider(provider_id))


@router.get("/providers/{provider_id}/backends", response_model=list[dict])
def provider_backends(provider_id: str):
    return _provider_call(lambda: service.list_backends(provider_id))


@router.get("/providers/{provider_id}/capabilities", response_model=dict)
def provider_capabilities(provider_id: str):
    return _provider_call(
        lambda: {
            "provider_id": provider_id,
            "backends": [
                {"backend_id": item["backend_id"], "capabilities": item["capabilities"]}
                for item in service.list_backends(provider_id)
            ],
        }
    )


@router.post("/providers/preflight", response_model=dict)
def provider_preflight(request: ProviderPreflightRequest):
    return _provider_call(
        lambda: service.preflight(
            request.provider_id,
            request.backend_id,
            request.configuration,
            request.requested_capabilities,
        )
    )

@router.post("/circuit", response_model=CircuitOut)
def preview_circuit(request: CircuitRequest):
    return circuit_description(request.quantum, request.model_type, request.seed)

@router.get("/resource-policy", response_model=dict)
def resource_budget_policy():
    return resource_policy()

@router.post("/resource-advisor", response_model=dict)
def resource_advisor(request: ResourceAdvisorRequest):
    return advise_resources(request)
