from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from app.services.review import PriorAuthorizationReviewCaseService
from app.services.explanation import DecisionExplanationService
from app.services.decision_engine import PriorAuthorizationDecisionService
from app.services.prior_auth_evaluation import PriorAuthorizationEvaluationService
from app.services.audit import AuditLogService
from app.db.connection import db_connection

router = APIRouter(prefix="/api/review", tags=["review"])

@router.get("/cases", response_model=List[Dict[str, Any]])
def get_reviewer_cases():
    """Lists summary info for all prior auth requests in the Case Queue."""
    cases = PriorAuthorizationReviewCaseService.list_cases()
    return cases

@router.get("/cases/{authorization_id}", response_model=Dict[str, Any])
def get_case_details(authorization_id: str):
    """Retrieves full details for a case, including evidence, evaluation, decisions, and history."""
    case = PriorAuthorizationReviewCaseService.get_case(authorization_id)
    if not case:
        raise HTTPException(
            status_code=404, 
            detail=f"Prior authorization case '{authorization_id}' not found."
        )
    return case

@router.post("/cases/{authorization_id}/explain", response_model=Dict[str, Any])
def generate_case_explanation(authorization_id: str):
    """Computes/synthesis decision explanation payload for review support."""
    eval_bundle = PriorAuthorizationEvaluationService.get_latest_evaluation(authorization_id)
    if not eval_bundle:
        raise HTTPException(
            status_code=404,
            detail=f"No policy evaluation found for '{authorization_id}'. Evaluate first."
        )
        
    dec = PriorAuthorizationDecisionService.get_latest_decision(authorization_id)
    if not dec:
        raise HTTPException(
            status_code=404,
            detail=f"No decision support result found for '{authorization_id}'. Compute decision first."
        )
        
    explanation = DecisionExplanationService.generate_explanation(dec, eval_bundle)
    return explanation

@router.post("/cases/{authorization_id}/action", response_model=Dict[str, Any])
def record_case_reviewer_action(
    authorization_id: str,
    action: str = Query(..., description="ACCEPT_RECOMMENDATION, REQUEST_MORE_INFORMATION, ESCALATE, OVERRIDE_RECOMMENDATION"),
    reason: str = Query(..., description="The rationale statement for the reviewer's workflow action"),
    intended_disposition: Optional[str] = Query(None, description="Intended state if overriding"),
    reviewer_id: str = Query("demo_reviewer_1", description="Identifier for the review officer")
):
    """Saves a workflow reviewer action or override rationale and updates logs."""
    try:
        action_doc = PriorAuthorizationReviewCaseService.record_action(
            authorization_id=authorization_id,
            reviewer_id=reviewer_id,
            action=action,
            reason=reason,
            intended_disposition=intended_disposition
        )
        return action_doc
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cases/{authorization_id}/history", response_model=List[Dict[str, Any]])
def get_case_reviewer_history(authorization_id: str):
    """Lists historical reviewer actions logs for a case."""
    db = db_connection.get_db()
    history = list(db["reviewer_actions"].find({"authorization_id": authorization_id}).sort("timestamp", -1))
    for h in history:
        h["_id"] = str(h["_id"])
    return history

@router.get("/cases/{authorization_id}/audit", response_model=List[Dict[str, Any]])
def get_case_audit_trail(authorization_id: str):
    """Gets end-to-end audit milestones log timeline for a case."""
    events = AuditLogService.get_events(authorization_id)
    return events
