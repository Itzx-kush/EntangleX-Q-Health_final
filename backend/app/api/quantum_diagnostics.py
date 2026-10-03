from fastapi import APIRouter, HTTPException
from typing import List

from ..database import session_scope
from ..storage.entities import QuantumDiagnosticReport
from ..quantum.schemas import QuantumPreflightRequest, QuantumDiagnosticReportOut, QuantumDiagnosticPreflightResponse
from ..quantum.diagnostics import preflight_quantum_diagnostics, generate_quantum_diagnostics
from ..utils.errors import AppError

router = APIRouter(prefix="/quantum/diagnostics", tags=["Quantum Diagnostics"])

@router.post("/preflight", response_model=QuantumDiagnosticPreflightResponse)
def preflight(request: QuantumPreflightRequest):
    with session_scope() as session:
        return preflight_quantum_diagnostics(session, request.experiment_id, request.model_record_id)

@router.post("", response_model=QuantumDiagnosticReportOut)
def create_diagnostics(request: QuantumPreflightRequest):
    with session_scope() as session:
        preflight = preflight_quantum_diagnostics(session, request.experiment_id, request.model_record_id)
        if not preflight.feasible:
            reason = (preflight.blockers or preflight.limitations or ["Quantum diagnostics are not applicable."])[0]
            raise AppError("quantum_diagnostics_infeasible", reason, 400)
        report = generate_quantum_diagnostics(session, request.experiment_id, request.model_record_id)
        
        return QuantumDiagnosticReportOut(**{c.name: getattr(report, c.name) for c in report.__table__.columns})

@router.get("/{id}", response_model=QuantumDiagnosticReportOut)
def get_diagnostics(id: str):
    with session_scope() as session:
        report = session.query(QuantumDiagnosticReport).filter_by(id=id).first()
        if not report:
            raise AppError("quantum_diagnostics_missing", "Diagnostics report not found.", 404)
        return QuantumDiagnosticReportOut(**{c.name: getattr(report, c.name) for c in report.__table__.columns})

@router.get("/run/{model_record_id}", response_model=QuantumDiagnosticReportOut)
def get_diagnostics_by_run(model_record_id: str):
    with session_scope() as session:
        report = session.query(QuantumDiagnosticReport).filter_by(model_record_id=model_record_id).first()
        if not report:
            raise AppError("quantum_diagnostics_missing", "No diagnostics report exists for this model.", 404)
        return QuantumDiagnosticReportOut(**{c.name: getattr(report, c.name) for c in report.__table__.columns})
