from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.db.connection import db_connection
from app.models.policy import PolicyRoutingRequest, PolicyRoutingResponse
from app.services.policy_routing import PolicyRoutingService
from app.core.normalize import (
    normalize_ncd_id,
    normalize_lcd_id_numeric,
    normalize_article_id_numeric
)

router = APIRouter(prefix="/api/policy", tags=["Policy Routing"])

@router.post("/route", response_model=PolicyRoutingResponse)
def route_policy(request: PolicyRoutingRequest):
    """Deterministically route and resolve candidate CMS coverage policies based on request context."""
    try:
        response = PolicyRoutingService.route_policy(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Policy routing failed: {str(e)}")

@router.get("/ncd/{id}")
def get_ncd(id: str, version: Optional[str] = Query(None, description="Optional document version")):
    """Retrieve National Coverage Determination (NCD) details by NCD ID."""
    db = db_connection.get_db()
    norm_id = normalize_ncd_id(id)
    
    query = {"ncd_id.canonical_value": norm_id}
    if version:
        query["document_version"] = version
        
    doc = db["ncds"].find_one(query, {"_id": 0})
    if not doc:
        raise HTTPException(
            status_code=404, 
            detail=f"NCD document with ID '{id}'" + (f" and version '{version}'" if version else "") + " not found."
        )
    return doc

@router.get("/lcd/{id}")
def get_lcd(id: str, version: Optional[str] = Query(None, description="Optional document version")):
    """Retrieve Local Coverage Determination (LCD) details by LCD ID."""
    db = db_connection.get_db()
    norm_id = normalize_lcd_id_numeric(id)
    
    query = {"lcd_id.canonical_value": norm_id}
    if version:
        query["lcd_version"] = version
        
    doc = db["lcds"].find_one(query, {"_id": 0})
    if not doc:
        raise HTTPException(
            status_code=404, 
            detail=f"LCD document with ID '{id}'" + (f" and version '{version}'" if version else "") + " not found."
        )
    return doc

@router.get("/article/{id}")
def get_article(id: str, version: Optional[str] = Query(None, description="Optional document version")):
    """Retrieve Billing and Coding Article details by Article ID."""
    db = db_connection.get_db()
    norm_id = normalize_article_id_numeric(id)
    
    query = {"article_id.canonical_value": norm_id}
    if version:
        query["article_version"] = version
        
    doc = db["articles"].find_one(query, {"_id": 0})
    if not doc:
        raise HTTPException(
            status_code=404, 
            detail=f"Article document with ID '{id}'" + (f" and version '{version}'" if version else "") + " not found."
        )
    return doc
