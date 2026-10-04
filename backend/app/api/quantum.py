from fastapi import APIRouter
from ..quantum.backends import availability
from ..quantum.circuits import circuit_description
from ..quantum.errors import QuantumProviderError
from ..quantum.resource_advisor import advise_resources, resource_policy
from ..quantum.service import service
from ..quantum.visualization import visualization_service
from ..utils.errors import AppError
from ..quantum.schemas import (
    QuantumVisualizationContract,
    QuantumVisualizationEvidenceOut,
    QuantumVisualizationEvidenceRequest,
    QuantumVisualizationPreviewRequest,
    QuantumVisualizationSimulationRequest,
)
from ..artifacts.service import register_metadata
from ..database import session_scope
from ..storage.entities import Experiment, ModelRecord
from ..storage.repository import require
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


@router.post("/visualization/preview", response_model=QuantumVisualizationContract)
def visualization_preview(request: QuantumVisualizationPreviewRequest):
    contract, _artifacts = visualization_service.preview(request)
    return contract


@router.post("/visualization/simulate", response_model=QuantumVisualizationContract)
def visualization_simulate(request: QuantumVisualizationSimulationRequest):
    return visualization_service.simulate(request)


@router.post("/visualization/evidence", response_model=QuantumVisualizationEvidenceOut, status_code=201)
def save_visualization_evidence(request: QuantumVisualizationEvidenceRequest):
    model_id = str(request.model_record_id)
    with session_scope() as session:
        model = require(session, ModelRecord, model_id)
        experiment = require(session, Experiment, model.experiment_id)
        if model.model_type not in {"vqc", "qsvc", "qnn"}:
            raise AppError("quantum_visualization_invalid_context", "Saved simulation evidence requires a persisted Qiskit quantum model.", 422)
        if model.dataset_id != experiment.dataset_id:
            raise AppError("quantum_visualization_invalid_context", "The persisted model dataset does not match its experiment dataset.", 409)
        if request.simulation.model_type != model.model_type:
            raise AppError("quantum_visualization_invalid_context", "The simulation model type must match the selected persisted model.", 422)
        if request.simulation.dataset_id not in (None, model.dataset_id):
            raise AppError("quantum_visualization_invalid_context", "The selected dataset does not match the persisted model dataset.", 422)
        if request.simulation.experiment_id not in (None, model.experiment_id):
            raise AppError("quantum_visualization_invalid_context", "The selected experiment does not match the persisted model experiment.", 422)
        if (experiment.summary or {}).get("experiment_kind") == "precomputed_verified_demo":
            raise AppError("quantum_visualization_invalid_context", "Visualization evidence cannot be attached to the protected verified-demo experiment.", 403)
        simulation_request = request.simulation.model_copy(update={
            "dataset_id": model.dataset_id,
            "experiment_id": model.experiment_id,
        })

    # Re-run the explicitly requested bounded simulation on the backend. Never trust
    # a client-submitted statevector or probability array as research evidence.
    contract = visualization_service.simulate(simulation_request)
    if contract.status != "SIMULATION_AVAILABLE" or contract.provider.hardware_available:
        raise AppError("quantum_simulation_unavailable", "The backend did not return a valid local-simulator visualization result.", 503)

    payload = {
        "schema_version": "quantum_visualization_evidence_v1",
        "evidence_status": "AVAILABLE",
        "source": "backend_bounded_local_simulator",
        "experiment_id": model.experiment_id,
        "model_record_id": model_id,
        "run_id": model.run_id,
        "dataset_id": model.dataset_id,
        "request_fingerprint": contract.request_fingerprint,
        "interpretation": "Explicit visualization simulation only; this is not a fitted-model prediction, training result, or hardware execution.",
        "contract": contract.model_dump(mode="json"),
    }
    operation_key = f"quantum-visualization:{model_id}:{contract.request_fingerprint}"
    with session_scope() as session:
        current_model = require(session, ModelRecord, model_id)
        current_experiment = require(session, Experiment, current_model.experiment_id)
        if (
            current_experiment.id != model.experiment_id
            or current_experiment.dataset_id != model.dataset_id
            or current_model.run_id != model.run_id
            or current_model.model_type != model.model_type
        ):
            raise AppError("quantum_visualization_invalid_context", "Persisted model context changed while saving visualization evidence.", 409)
        artifact = register_metadata(
            session,
            experiment_id=current_model.experiment_id,
            run_id=current_model.run_id,
            model_id=current_model.id,
            artifact_type="quantum_visualization_evidence",
            name="Quantum visualization simulation",
            description="Backend-generated bounded local-simulator visualization; not a fitted-model evaluation.",
            payload=payload,
            operation_key=operation_key,
        )
    return QuantumVisualizationEvidenceOut(
        artifact_id=artifact.id,
        experiment_id=model.experiment_id,
        model_record_id=model_id,
        run_id=model.run_id,
        request_fingerprint=contract.request_fingerprint,
        contract=contract,
    )


@router.get("/resource-policy", response_model=dict)
def resource_budget_policy():
    return resource_policy()

@router.post("/resource-advisor", response_model=dict)
def resource_advisor(request: ResourceAdvisorRequest):
    return advise_resources(request)
