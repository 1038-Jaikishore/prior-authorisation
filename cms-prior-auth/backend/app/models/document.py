from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class PatientDocument(BaseModel):
    document_id: str = Field(..., description="Unique document reference key.")
    authorization_id: Optional[str] = Field(None, description="Linked prior auth request ID.")
    patient_id: Optional[str] = Field(None, description="Linked patient identifier.")
    filename: str = Field(..., description="Name of the uploaded file.")
    file_type: str = Field(..., description="Extension: pdf, docx, txt.")
    mime_type: str = Field(..., description="Validated MIME type.")
    upload_status: str = Field("UPLOADED", description="Triage status: UPLOADED, PARSED, EXTRACTED, REVIEW_REQUIRED, CONFIRMED, EXTRACTION_FAILED.")
    page_count: int = Field(0, description="Total page count of document.")
    created_at: str = Field(..., description="Timestamp of document upload.")
    source_type: str = "UPLOADED_DOCUMENT"

class DocumentEvidenceProvenance(BaseModel):
    fact_id: str = Field(..., description="Unique fact reference key.")
    fact_type: str = Field(..., description="Type of clinical parameter extracted.")
    value: str = Field(..., description="Extracted raw value.")
    document_id: str = Field(..., description="Source document key.")
    page_number: int = Field(..., description="Document page number.")
    source_text: str = Field(..., description="Clinical quote supporting this fact.")
    extraction_method: str = "LLM"
    extractor_model: Optional[str] = None
    confidence: Optional[float] = None

class PatientDemographics(BaseModel):
    name: Optional[str] = None
    dob: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None

class RequestedService(BaseModel):
    code: Optional[str] = None
    code_system: Optional[str] = "CPT"
    description: Optional[str] = None

class DiagnosisItem(BaseModel):
    code: Optional[str] = None
    code_system: Optional[str] = "ICD-10-CM"
    description: Optional[str] = None
    code_status: str = "DOCUMENTED"  # "DOCUMENTED" or "NOT_DOCUMENTED"

class PriorTreatmentItem(BaseModel):
    treatment_type: str = Field(..., description="medication, surgery, physical_therapy, etc.")
    name: str = Field(..., description="Name or description of treatment.")
    duration: Optional[str] = None
    status: Optional[str] = None
    treatment_response: Optional[str] = None
    failed: Optional[bool] = None

class DiagnosticResultItem(BaseModel):
    test_name: str
    result: str
    date: Optional[str] = None

class ClinicalProvider(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    facility: Optional[str] = None
    npi: Optional[str] = None

class DocumentGeography(BaseModel):
    state: Optional[str] = None
    zip: Optional[str] = None

class EditHistoryEntry(BaseModel):
    original_value: Any
    new_value: Any
    reviewer_id: str
    timestamp: str
    edit_reason: Optional[str] = None

class ExtractedClinicalDocument(BaseModel):
    document_id: str
    version: int = 1
    status: str = "DRAFT_EXTRACTION"
    patient: PatientDemographics = Field(default_factory=PatientDemographics)
    requested_service: RequestedService = Field(default_factory=RequestedService)
    diagnoses: List[DiagnosisItem] = Field(default_factory=list)
    prior_treatments: List[PriorTreatmentItem] = Field(default_factory=list)
    diagnostic_results: List[DiagnosticResultItem] = Field(default_factory=list)
    clinical_indication: Optional[str] = None
    provider_justification: Optional[str] = None
    provider: ClinicalProvider = Field(default_factory=ClinicalProvider)
    geography: DocumentGeography = Field(default_factory=DocumentGeography)
    missing_fields: List[str] = Field(default_factory=list)
    provenance_records: List[DocumentEvidenceProvenance] = Field(default_factory=list)
    edit_history: List[EditHistoryEntry] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)
