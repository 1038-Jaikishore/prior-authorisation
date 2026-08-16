from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from app.services.prior_auth_evaluation import PriorAuthorizationEvaluationService

router = APIRouter(prefix="/api", tags=["Evaluation"])

@router.post("/prior-auth/{authorization_id}/evaluate")
def evaluate_prior_auth_request(
    authorization_id: str,
    override_state: Optional[str] = Query(None, description="Manual state/geography override"),
    override_date: Optional[str] = Query(None, description="Manual service date override (YYYY-MM-DD)")
):
    """Triggers clinical matching and deterministic validations for a request, returns EvaluationBundle."""
    try:
        bundle = PriorAuthorizationEvaluationService.evaluate_request(
            request_id=authorization_id,
            override_state=override_state,
            override_date=override_date
        )
        return bundle
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prior auth evaluation failed: {str(e)}")

@router.get("/prior-auth/{authorization_id}/evaluation")
def get_latest_evaluation(authorization_id: str):
    """Retrieves the latest evaluation bundle for the target request ID."""
    eval_doc = PriorAuthorizationEvaluationService.get_latest_evaluation(authorization_id)
    if not eval_doc:
        raise HTTPException(status_code=404, detail=f"No completed evaluations found for request {authorization_id}")
    return eval_doc

@router.get("/evaluations/{evaluation_id}")
def get_evaluation_by_id(evaluation_id: str):
    """Retrieves a completed evaluation bundle by its unique evaluation ID."""
    eval_doc = PriorAuthorizationEvaluationService.get_evaluation_by_id(evaluation_id)
    if not eval_doc:
        raise HTTPException(status_code=404, detail=f"Evaluation bundle with ID {evaluation_id} not found")
    return eval_doc
