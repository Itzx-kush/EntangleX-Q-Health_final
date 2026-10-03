from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class QuantumPreflightRequest(BaseModel):
    experiment_id: str
    model_record_id: str

class QuantumDiagnosticFinding(BaseModel):
    severity: str # INFO, WARNING, BLOCKER
    code: str
    title: str
    description: str
    evidence: Optional[Dict[str, Any]] = None
    recommendation: Optional[str] = None

class QuantumDiagnosticReportOut(BaseModel):
    id: str
    experiment_id: str
    model_record_id: str
    model_type: str
    status: str
    created_at: datetime
    
    model_configuration: Dict[str, Any]
    feature_encoding: Dict[str, Any]
    circuit_structure: Dict[str, Any]
    resource_profile: Dict[str, Any]
    optimizer_profile: Dict[str, Any]
    training_profile: Dict[str, Any]
    execution_profile: Dict[str, Any]
    stability_profile: Dict[str, Any]
    noise_profile: Dict[str, Any]
    
    warnings: List[QuantumDiagnosticFinding]
    limitations: List[str]
    
    configuration_fingerprint: Optional[str] = None
    provenance: Dict[str, Any]

class QuantumDiagnosticPreflightResponse(BaseModel):
    feasible: bool
    blockers: List[str] = Field(default_factory=list)
    unsupported_fields: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
