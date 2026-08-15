from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class PatientPriorAuthRequest(BaseModel):
    authorization_id: str = Field(..., description="Canonical Request/Authorization identifier.")
    patient_id: str = Field(..., description="Target patient identifier.")
    provider_id: str = Field(..., description="Requesting provider identifier.")
    requested_service: Dict[str, str] = Field(..., description="Requested service (code and display).")
    diagnosis_codes: List[str] = Field(default_factory=list, description="Associated ICD-10 CM/PCS codes.")
    request_date: str = Field(..., description="Date prior-auth request was made.")
    quantity: Optional[float] = None
    duration: Optional[int] = None
    clinical_indication: str = Field("", description="Narrative clinical indication.")
    provider_justification: str = Field("", description="Narrative provider justification.")
    state_code: Optional[str] = None
    source: str = "synthetic_dataset"

class EvidenceProvenance(BaseModel):
    fact_type: str = Field(..., description="Type of clinical/administrative fact.")
    value: str = Field(..., description="The value of the fact.")
    source_collection: str = Field(..., description="MongoDB collection name or origin.")
    source_record_id: str = Field(..., description="Primary key or index of the source record.")
    source_field: str = Field(..., description="The specific field name within the source record.")

class ClinicalEvidencePacket(BaseModel):
    authorization_id: str = Field(..., description="Origin authorization request identifier.")
    patient_id: str = Field(..., description="Reference patient identifier.")
    requested_service: Dict[str, str] = Field(..., description="Requested CPT/HCPCS code and description.")
    diagnosis_codes: List[str] = Field(default_factory=list, description="Requested ICD-10 diagnosis codes.")
    
    # Demographics
    demographics: Dict[str, Any] = Field(default_factory=dict, description="Age, gender, insurance, state_code.")
    
    # Clinical lists
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    procedures: List[Dict[str, Any]] = Field(default_factory=list)
    surgeries: List[Dict[str, Any]] = Field(default_factory=list)
    medications: List[Dict[str, Any]] = Field(default_factory=list)
    diagnostic_results: List[Dict[str, Any]] = Field(default_factory=list)
    vital_signs: List[Dict[str, Any]] = Field(default_factory=list)
    clinical_assessments: List[Dict[str, Any]] = Field(default_factory=list)
    functional_status: List[Dict[str, Any]] = Field(default_factory=list)
    allergies: List[Dict[str, Any]] = Field(default_factory=list)
    medical_equipment: List[Dict[str, Any]] = Field(default_factory=list)
    care_plans: List[Dict[str, Any]] = Field(default_factory=list)
    social_history: List[Dict[str, Any]] = Field(default_factory=list)
    family_history: List[Dict[str, Any]] = Field(default_factory=list)
    referrals: List[Dict[str, Any]] = Field(default_factory=list)
    encounters: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Processed evidence summary
    prior_treatments: List[Dict[str, Any]] = Field(default_factory=list, description="Attempted treatments (meds, surgeries, devices).")
    clinical_text: List[Dict[str, Any]] = Field(default_factory=list, description="Original raw free text justification inputs.")
    
    # Missing / gaps
    missing_information: List[str] = Field(default_factory=list, description="List of missing clinical criteria indicators.")
    
    # Provenance tracking
    provenance: List[EvidenceProvenance] = Field(default_factory=list, description="List of provenance objects linking facts to sources.")
