from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class AuditEvent(BaseModel):
    event_id: str
    authorization_id: str
    event_type: str = Field(..., description="Workflow milestones e.g. POLICY_ROUTED, REVIEWER_ACTION_RECORDED")
    actor_type: str = "SYSTEM"
    actor_id: str
    timestamp: str
    related_object_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ReviewerAction(BaseModel):
    review_id: str
    authorization_id: str
    decision_id: str
    evaluation_id: str
    reviewer_id: str
    action: str = Field(..., description="ACCEPT_RECOMMENDATION, REQUEST_MORE_INFORMATION, ESCALATE, OVERRIDE_RECOMMENDATION, NO_ACTION")
    intended_disposition: Optional[str] = None
    reason: str
    timestamp: str

class DecisionExplanation(BaseModel):
    decision_id: str
    recommended_disposition: str
    summary: str
    why: List[str] = Field(default_factory=list)
    satisfied_requirements: List[str] = Field(default_factory=list)
    blocking_requirements: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    coding_summary: List[str] = Field(default_factory=list)
    policy_summary: List[str] = Field(default_factory=list)
    policy_citations: List[str] = Field(default_factory=list)
    patient_provenance: List[Dict[str, Any]] = Field(default_factory=list)
    generated_by: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None

class PriorAuthorizationReviewCase(BaseModel):
    authorization_id: str
    patient_summary: Dict[str, Any]
    clinical_evidence_packet: Dict[str, Any]
    policy_routing_result: Dict[str, Any]
    retrieved_policy_sections: List[Dict[str, Any]]
    evaluation_bundle: Optional[Dict[str, Any]] = None
    decision_support_result: Optional[Dict[str, Any]] = None
    decision_explanation: Optional[DecisionExplanation] = None
    review_history: List[ReviewerAction] = Field(default_factory=list)
    audit_events: List[AuditEvent] = Field(default_factory=list)
