from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class DecisionFactor(BaseModel):
    factor_id: str
    factor_type: str = Field(..., description="CLINICAL_REQUIREMENT, CODING_VALIDATION, POLICY_ROUTING, ADMINISTRATIVE")
    status: str
    effect: str = Field(..., description="SUPPORTS_APPROVAL, BLOCKING_FAILURE, BLOCKING_MISSING_INFORMATION, REQUIRES_HUMAN_REVIEW, NON_BLOCKING_WARNING, INFORMATIONAL")
    description: str
    policy_citation: Optional[str] = None
    patient_provenance: List[Dict[str, Any]] = Field(default_factory=list)

class MissingInformationRequest(BaseModel):
    request_type: str = Field(..., description="CLINICAL_DOCUMENTATION, ADMINISTRATIVE_FIELD")
    requirement_id: Optional[str] = None
    description: str
    policy_citation: Optional[str] = None
    priority: str = "REQUIRED"

class DecisionSupportResult(BaseModel):
    decision_id: str
    evaluation_id: str
    authorization_id: str
    recommended_disposition: str = Field(..., description="APPROVE, DENY, PEND, NURSE_REVIEW, DECISION_SUPPORT_UNAVAILABLE")
    decision_type: str = "DECISION_SUPPORT"
    requires_human_review: bool = True
    reason_codes: List[str] = Field(default_factory=list)
    decision_factors: List[DecisionFactor] = Field(default_factory=list)
    missing_information: List[MissingInformationRequest] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    policy_citations: List[str] = Field(default_factory=list)
    patient_provenance: List[Dict[str, Any]] = Field(default_factory=list)
    decision_certainty: str = Field(..., description="HIGH, MODERATE, LOW")
    rule_version: str = "v1"
    created_at: str
