from fastapi import APIRouter, HTTPException
from typing import List

from backend.app.database import session_scope
from backend.app.storage.entities import QuantumDiagnosticReport
from backend.app.quantum.schemas import QuantumPreflightRequest, QuantumDiagnosticReportOut, QuantumDiagnosticPreflightResponse
from backend.app.quantum.diagnostics import preflight_quantum_diagnostics, generate_quantum_diagnostics

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
            raise HTTPException(status_code=400, detail="Quantum diagnostics not supported for this model.")
        report = generate_quantum_diagnostics(session, request.experiment_id, request.model_record_id)
        
        return QuantumDiagnosticReportOut(**{c.name: getattr(report, c.name) for c in report.__table__.columns})

@router.get("/{id}", response_model=QuantumDiagnosticReportOut)
def get_diagnostics(id: str):
    with session_scope() as session:
        report = session.query(QuantumDiagnosticReport).filter_by(id=id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Diagnostics report not found")
        return QuantumDiagnosticReportOut(**{c.name: getattr(report, c.name) for c in report.__table__.columns})

@router.get("/run/{model_record_id}", response_model=QuantumDiagnosticReportOut)
def get_diagnostics_by_run(model_record_id: str):
    with session_scope() as session:
        report = session.query(QuantumDiagnosticReport).filter_by(model_record_id=model_record_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Diagnostics report not found for this model")
        return QuantumDiagnosticReportOut(**{c.name: getattr(report, c.name) for c in report.__table__.columns})
