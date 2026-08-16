from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class PolicyRequirement(BaseModel):
    requirement_id: str = Field(..., description="Unique ID for this requirement (e.g., REQ-L33942-001)")
    document_type: str = Field(..., description="Type of document: NCD, LCD, or Article")
    document_id: str = Field(..., description="CMS document ID (e.g. L33942)")
    document_version: str = Field(..., description="Version of the document")
    section: str = Field(..., description="Section of the document (e.g., indication, description)")
    citation: str = Field(..., description="Canonical citation string (e.g. LCD:L33942:v50:indication:chunk_01)")
    policy_role: str = Field("APPLICABLE", description="Role: CONTROLLING, APPLICABLE, RELATED_REFERENCE, UNRESOLVED, UNKNOWN")
    requirement_text: str = Field(..., description="Narrative clinical or administrative rule text")
    requirement_type: str = Field("OTHER_CLINICAL", description="e.g. DIAGNOSIS, SYMPTOM, DURATION, PRIOR_TREATMENT, failed_treatment, medication, etc.")
    mandatory: bool = Field(True, description="Whether this condition must be met")
    conditional: bool = Field(False, description="Whether this applies only under specific circumstances")
    condition_text: Optional[str] = Field(None, description="The condition phrase if conditional")
    structured_constraints: Dict[str, Any] = Field(default_factory=dict, description="Parsed structured constraints if deterministic")
    extraction_method: str = Field("RULE_OR_LLM", description="Extraction method used: DETERMINISTIC, LLM, or MANUAL")
    extraction_confidence: Optional[float] = Field(None, description="Model confidence score if applicable")

class PatientEvidence(BaseModel):
    evidence_id: str = Field(..., description="Unique identifier for the patient evidence item")
    fact_type: str = Field(..., description="Type of fact (e.g., diagnosis, medication, vital, procedure, lab)")
    value: str = Field(..., description="Canonical value representation (e.g., M17.11)")
    display_value: str = Field(..., description="Human-readable text (e.g., Osteoarthritis)")
    date: Optional[str] = Field(None, description="Date of the record or event")
    source_collection: str = Field(..., description="MongoDB source collection (e.g. patient_conditions)")
    source_record_id: str = Field(..., description="MongoDB ObjectId string")
    source_field: str = Field(..., description="Specific field name containing the fact value")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Detailed ingestion/row metrics details")
    evidence_quality: str = Field("STRUCTURED", description="STRUCTURED, EXTRACTED_FROM_TEXT, PATIENT_REPORTED, PROVIDER_REPORTED, UNKNOWN")

class RequirementEvaluation(BaseModel):
    requirement_id: str = Field(..., description="Target requirement ID")
    status: str = Field(..., description="MET, NOT_MET, UNCLEAR, NOT_APPLICABLE")
    policy_requirement: PolicyRequirement = Field(..., description="The evaluated policy requirement details")
    matching_evidence: List[PatientEvidence] = Field(default_factory=list, description="Evidence confirming the condition is met")
    contradicting_evidence: List[PatientEvidence] = Field(default_factory=list, description="Evidence proving the condition is not met")
    missing_information: List[str] = Field(default_factory=list, description="What information is missing or unclear")
    rationale: str = Field(..., description="Detailed match explanation text")
    policy_citation: str = Field(..., description="CMS citation string")
    patient_provenance: List[Dict[str, Any]] = Field(default_factory=list, description="List of source file and row indices of matched evidence")

class CodingValidation(BaseModel):
    validator: str = Field(..., description="Name of validator (e.g., LCD_HCPCS, ARTICLE_ICD10, JURISDICTION, etc.)")
    status: str = Field(..., description="PASS, FAIL, WARNING, UNKNOWN, NOT_EVALUATED, MANUAL_REVIEW_REQUIRED")
    subject: str = Field(..., description="The value being checked (e.g. CPT/HCPCS, ICD-10, Modifier)")
    policy_document: Optional[str] = Field(None, description="Display ID of the source policy document")
    reason: str = Field(..., description="Detailed description of the check outcome")
    source_records: List[Dict[str, Any]] = Field(default_factory=list, description="Matched database reference rows")
    warnings: List[str] = Field(default_factory=list, description="Optional warning comments")

class EvaluationBundle(BaseModel):
    authorization_id: str = Field(..., description="The request ID from authorization_requests")
    evaluation_id: str = Field(..., description="Unique database ID of this evaluation run")
    policy_context: Dict[str, List[str]] = Field(
        default_factory=lambda: {"controlling_policies": [], "applicable_policies": [], "related_reference_policies": []},
        description="Categorized policy documents mapped in this session"
    )
    requirements: List[PolicyRequirement] = Field(default_factory=list, description="All extracted policy requirements")
    requirement_evaluations: List[RequirementEvaluation] = Field(default_factory=list, description="Evaluations mapped to patient facts")
    coding_validations: List[CodingValidation] = Field(default_factory=list, description="Coding validations results")
    administrative_validations: List[CodingValidation] = Field(default_factory=list, description="Administrative checks results (MAC, Date, Version)")
    summary: Dict[str, int] = Field(
        default_factory=lambda: {
            "requirements_total": 0, "met": 0, "not_met": 0, "unclear": 0, "not_applicable": 0,
            "validation_pass": 0, "validation_fail": 0, "validation_warning": 0
        },
        description="Counts metrics for reporting"
    )
    missing_information: List[str] = Field(default_factory=list, description="All clinical or documentation gaps identified")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Metadata audit trail of extraction and match versions")
