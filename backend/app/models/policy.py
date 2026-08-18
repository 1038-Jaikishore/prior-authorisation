from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class PolicyRoutingRequest(BaseModel):
    hcpcs_code: str = Field(..., description="CPT/HCPCS code representing the requested service.")
    diagnosis_codes: List[str] = Field(default_factory=list, description="List of ICD-10-CM diagnosis codes.")
    icd10_pcs_codes: List[str] = Field(default_factory=list, description="List of ICD-10-PCS procedure codes.")
    modifiers: List[str] = Field(default_factory=list, description="List of HCPCS modifier codes.")
    revenue_code: Optional[str] = Field(None, description="UB-04 Revenue code.")
    bill_type_code: Optional[str] = Field(None, description="UB-04 Bill Type code.")
    state: Optional[str] = Field(None, description="Full state name (e.g. Texas).")
    state_code: Optional[str] = Field(None, description="Two-letter state code (e.g. TX).")
    zip_code: Optional[str] = Field(None, description="Five-digit ZIP code.")
    date_of_service: str = Field("2026-08-20", description="Date of service in YYYY-MM-DD format.")
    provider_id: Optional[str] = Field(None, description="National Provider Identifier (NPI) of the provider.")
    facility_id: Optional[str] = Field(None, description="Provider/Facility Identifier.")

class RoutingTraceStep(BaseModel):
    step: int
    action: str
    input: Any
    result: Any

class UnresolvedReference(BaseModel):
    referenced_id: str
    referenced_version: Optional[str] = None
    relationship_source: str
    source_file: Optional[str] = None
    reason: str

class PolicyRoutingResponse(BaseModel):
    routing_status: str
    normalized_request: Dict[str, Any]
    candidate_ncds: List[Dict[str, Any]] = []
    applicable_ncds: List[Dict[str, Any]] = []
    candidate_lcds: List[Dict[str, Any]] = []
    applicable_lcds: List[Dict[str, Any]] = []
    related_articles: List[Dict[str, Any]] = []
    jurisdiction: Optional[Dict[str, Any]] = None
    contractor: Optional[Dict[str, Any]] = None
    coding_context: Dict[str, Any] = {}
    unresolved_references: List[UnresolvedReference] = []
    warnings: List[str] = []
    routing_confidence: float
    routing_trace: List[RoutingTraceStep] = []
