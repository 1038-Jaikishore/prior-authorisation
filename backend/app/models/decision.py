from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Any

class NumericalEvaluation(BaseModel):
    patient_value: Optional[float] = Field(None, description="The numerical value extracted from the patient evidence. Null if missing.")
    operator: str = Field(..., description="The mathematical operator: <=, <, >=, >, ==")
    threshold: float = Field(..., description="The numerical threshold required by the policy.")
    source_evidence: str = Field(..., description="The patient evidence string that contains this value.")

class PolicyRequirement(BaseModel):
    description: str = Field(..., description="A description of the requirement extracted from the policy.")
    pathway: str = Field(..., description="The name of the alternative pathway this requirement belongs to (e.g., 'Group I', 'Group II'). Use 'Global' for mandatory overarching rules.")
    is_numerical: bool = Field(..., description="Whether this requirement is a numerical threshold.")
    numerical_evaluation: Optional[NumericalEvaluation] = Field(None, description="The mathematical extraction if is_numerical is true.")
    llm_is_met: bool = Field(..., description="The LLM's opinion on whether this requirement is met.")
    computed_is_met: Optional[bool] = Field(None, description="The deterministic Python evaluation result for numerical requirements.")
    status: Literal['MET', 'FAILED', 'MISSING', 'AMBIGUOUS'] = Field(..., description="The status of the requirement: MET, FAILED, MISSING evidence, or AMBIGUOUS.")

class PathwayResult(BaseModel):
    pathway_name: str
    status: Literal['MET', 'FAILED', 'MISSING', 'AMBIGUOUS']
    requirements: List[PolicyRequirement]

class NCDSemanticEvaluationResult(BaseModel):
    ncd_determination: Literal['COVERED', 'NOT COVERED', 'NOT ADDRESSED'] = Field(
        ..., description="The final semantic determination based on the NCD text."
    )
    semantic_similarity_score: float = Field(..., description="Score 0.0 to 1.0 indicating how well clinical facts match NCD requirements.")
    confidence_score: float = Field(..., description="Score 0.0 to 1.0 indicating AI confidence in its determination based on completeness of evidence.")
    key_policy_excerpts: List[str] = Field(
        default_factory=list, description="Exact sentences from the NCD that justify the determination."
    )
    conditions: List[str] = Field(
        default_factory=list, description="Any specific conditions or limitations found in the text."
    )
    reasoning: str = Field(
        ..., description="A short paragraph justifying the decision based only on the CMS text."
    )
    requirements_evaluated: List['PolicyRequirement'] = Field(
        default_factory=list, description="A list of all policy requirements explicitly evaluated by the LLM."
    )
    pathways_evaluated: List['PathwayResult'] = Field(
        default_factory=list, description="The aggregated results of each logical pathway."
    )

class LCDSemanticEvaluationResult(BaseModel):
    lcd_determination: Literal['COVERED', 'NOT COVERED', 'NOT ADDRESSED'] = Field(
        ..., description="The final semantic determination based on the LCD text."
    )
    semantic_similarity_score: float = Field(..., description="Score 0.0 to 1.0 indicating how well clinical facts match LCD requirements.")
    confidence_score: float = Field(..., description="Score 0.0 to 1.0 indicating AI confidence in its determination based on completeness of evidence.")
    key_policy_excerpts: List[str] = Field(
        default_factory=list, description="Exact sentences from the LCD that justify the determination."
    )
    conditions: List[str] = Field(
        default_factory=list, description="Any specific conditions or limitations found in the text."
    )
    reasoning: str = Field(
        ..., description="A short paragraph justifying the decision based only on the CMS text."
    )
    requirements_evaluated: List['PolicyRequirement'] = Field(
        default_factory=list, description="A list of all policy requirements explicitly evaluated by the LLM."
    )
    pathways_evaluated: List['PathwayResult'] = Field(
        default_factory=list, description="The aggregated results of each logical pathway."
    )

class ValidationChecklist(BaseModel):
    icd_10_cm: Literal['PASS', 'FAIL', 'NOT_APPLICABLE']
    icd_10_pcs: Literal['PASS', 'FAIL', 'NOT_APPLICABLE']
    cpt_hcpcs: Literal['PASS', 'FAIL', 'NOT_APPLICABLE']
    modifiers: Literal['PASS', 'FAIL', 'NOT_APPLICABLE']
    revenue_codes: Literal['PASS', 'FAIL', 'NOT_APPLICABLE']
    coding_rules: Literal['PASS', 'FAIL', 'NOT_APPLICABLE']

class ArticleSemanticEvaluationResult(BaseModel):
    article_determination: Literal['COVERED', 'NOT COVERED', 'NOT ADDRESSED'] = Field(
        ..., description="The final semantic determination based on the Article text."
    )
    administrative_match_score: float = Field(..., description="Score 0.0 to 1.0 based on how many administrative validation data points passed.")
    validation_checklist: ValidationChecklist = Field(
        ..., description="Granular PASS/FAIL/NOT_APPLICABLE status for all 6 administrative deterministic checks."
    )
    key_policy_excerpts: List[str] = Field(
        default_factory=list, description="Exact sentences from the Article that justify the determination."
    )
    matching_codes: List[str] = Field(
        default_factory=list, description="The specific codes from the patient facts that matched the Article."
    )
    mismatched_codes: List[str] = Field(
        default_factory=list, description="The specific codes that caused a FAIL condition."
    )
    reasoning: str = Field(
        ..., description="A short paragraph justifying the decision based strictly on the checklist."
    )

class Phase7DecisionOutput(BaseModel):
    overall_confidence_score: float = Field(..., description="Weighted average/aggregation of the NCD, LCD, and Article scores")
    evidence_summary: str = Field(..., description="A summary of the clinical and administrative evidence provided.")
    gap_analysis: str = Field(..., description="What evidence or coding is missing or contradictory.")
    recommendation: Literal['APPROVE', 'DENY', 'PEND', 'NURSE_REVIEW'] = Field(...)

class PipelineDecisionResult(BaseModel):
    final_status: Literal['APPROVED', 'DENIED', 'PENDING_MANUAL_REVIEW'] = Field(
        ..., description="The overall Prior Authorization status (Mapped from Phase 7 Recommendation)."
    )
    ncd_decision: Optional[NCDSemanticEvaluationResult] = None
    lcd_decision: Optional[LCDSemanticEvaluationResult] = None
    article_decision: Optional[ArticleSemanticEvaluationResult] = None
    phase7_decision: Optional[Phase7DecisionOutput] = None
    final_explanation: Optional[str] = Field(
        None, description="The final reasoning string compiled across all phases."
    )
    clinical_evidence: Optional[dict] = Field(
        None, description="Display-only: The Phase 1/2 clinical evidence."
    )
    phase3_routing: Optional[dict] = Field(
        None, description="Display-only: The Phase 3 routing results."
    )
