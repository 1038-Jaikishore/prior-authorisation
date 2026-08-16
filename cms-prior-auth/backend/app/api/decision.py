from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from app.services.prior_auth_evaluation import PriorAuthorizationEvaluationService
from app.services.decision_engine import PriorAuthorizationDecisionService

router = APIRouter(prefix="/api", tags=["decision"])

@router.post("/prior-auth/{authorization_id}/decision-support", response_model=Dict[str, Any])
def create_decision_support(authorization_id: str):
    """Computes a versioned decision support recommendation using the latest evaluation bundle."""
    # 1. Fetch latest EvaluationBundle
    eval_bundle = PriorAuthorizationEvaluationService.get_latest_evaluation(authorization_id)
    if not eval_bundle:
        raise HTTPException(
            status_code=404, 
            detail=f"No policy evaluation bundle found for request '{authorization_id}'. Evaluate the request first."
        )
    
    # 2. Compute decision
    decision = PriorAuthorizationDecisionService.generate_decision(eval_bundle)
    return decision

@router.get("/prior-auth/{authorization_id}/decision-support", response_model=Dict[str, Any])
def get_latest_decision_support(authorization_id: str):
    """Retrieves the latest computed decision support recommendation for an authorization request."""
    decision = PriorAuthorizationDecisionService.get_latest_decision(authorization_id)
    if not decision:
        raise HTTPException(
            status_code=404, 
            detail=f"No decision support recommendation found for request '{authorization_id}'."
        )
    return decision

@router.get("/decisions/{decision_id}", response_model=Dict[str, Any])
def get_decision_by_id(decision_id: str):
    """Retrieves a specific decision support recommendation by its versioned ID."""
    decision = PriorAuthorizationDecisionService.get_decision_by_id(decision_id)
    if not decision:
        raise HTTPException(
            status_code=404, 
            detail=f"Decision support entry '{decision_id}' not found."
        )
    return decision

@router.get("/prior-auth/{authorization_id}/decision-history", response_model=List[Dict[str, Any]])
def get_decision_history(authorization_id: str):
    """Lists all historical decision support recommendation runs for auditing."""
    history = PriorAuthorizationDecisionService.get_decision_history(authorization_id)
    return history
