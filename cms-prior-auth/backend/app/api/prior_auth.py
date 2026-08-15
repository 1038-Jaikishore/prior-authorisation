from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from app.db.connection import db_connection
from app.models.patient import PatientPriorAuthRequest, ClinicalEvidencePacket
from app.services.prior_auth_intake import PriorAuthorizationIntakeService

router = APIRouter(prefix="/api/prior-auth", tags=["Prior Authorization Intake"])

@router.get("", response_model=List[Dict[str, Any]])
def list_requests():
    """List all available prior authorization requests."""
    try:
        return PriorAuthorizationIntakeService.list_authorization_requests()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{authorization_id}", response_model=Dict[str, Any])
def get_request(authorization_id: str):
    """Retrieve detailed properties of a single prior authorization request."""
    try:
        req = PriorAuthorizationIntakeService.get_authorization_request(authorization_id)
        if not req:
            raise HTTPException(status_code=404, detail=f"Request ID '{authorization_id}' not found.")
        return req
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", response_model=Dict[str, Any])
def create_request(request: PatientPriorAuthRequest):
    """Create and submit a new prior authorization request into the database."""
    db = db_connection.get_db()
    
    # Check if request already exists
    existing = db["authorization_requests"].find_one({"request_id": request.authorization_id})
    if existing:
        raise HTTPException(status_code=400, detail=f"Request ID '{request.authorization_id}' already exists.")
        
    doc = {
        "request_id": request.authorization_id,
        "patient_id": request.patient_id,
        "provider_id": request.provider_id,
        "requested_procedure_code": {
            "source_value": request.requested_service.get("code", ""),
            "canonical_value": request.requested_service.get("code", ""),
            "display_value": request.requested_service.get("code", "")
        },
        "diagnosis_code": [
            {
                "source_value": code,
                "canonical_value": code.replace(".", ""),
                "display_value": code
            } for code in request.diagnosis_codes
        ],
        "request_date": request.request_date,
        "requested_quantity": request.quantity,
        "requested_duration_days": request.duration,
        "clinical_indication": request.clinical_indication,
        "provider_justification": request.provider_justification,
        "status": "Pending",
        "source": request.source,
        "inserted_at": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        db["authorization_requests"].insert_one(doc)
        doc["_id"] = str(doc["_id"])
        return doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save request: {str(e)}")

@router.post("/{authorization_id}/build-evidence", response_model=Dict[str, Any])
def build_evidence(
    authorization_id: str,
    override_state: Optional[str] = Query(None, description="Optional state code override"),
    override_date: Optional[str] = Query(None, description="Optional date override")
):
    """Compile structured and unstructured clinical facts into a ClinicalEvidencePacket."""
    try:
        res = PriorAuthorizationIntakeService.compile_evidence_packet(
            request_id=authorization_id,
            override_state=override_state,
            override_date=override_date
        )
        return {
            "evidence_packet": res["packet"].model_dump(),
            "provider": res["provider"]
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{authorization_id}/route-and-retrieve", response_model=Dict[str, Any])
def route_and_retrieve(
    authorization_id: str,
    override_state: Optional[str] = Query(None, description="Optional state code override"),
    override_date: Optional[str] = Query(None, description="Optional date override")
):
    """Runs the prior auth combined intake routing and policy retrieval workflow."""
    try:
        res = PriorAuthorizationIntakeService.execute_route_and_retrieve(
            request_id=authorization_id,
            override_state=override_state,
            override_date=override_date
        )
        # Convert Pydantic schemas to dict for JSON serialization
        if hasattr(res["clinical_evidence_packet"], "model_dump"):
            res["clinical_evidence_packet"] = res["clinical_evidence_packet"].model_dump()
        if hasattr(res["policy_routing"], "model_dump"):
            res["policy_routing"] = res["policy_routing"].model_dump()
            
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from datetime import datetime, timezone
