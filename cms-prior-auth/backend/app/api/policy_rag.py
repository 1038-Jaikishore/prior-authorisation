from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.policy import PolicyRoutingRequest, PolicyRoutingResponse
from app.services.policy_retrieval import PolicyRetrievalService
from app.services.route_retrieve import RouteRetrieveComposer

router = APIRouter(prefix="/api/policy", tags=["Policy RAG"])

class PolicyRetrievalRequest(BaseModel):
    query: str = Field(..., description="Semantic search query text.")
    policy_scope: Optional[Dict[str, List[str]]] = Field(None, description="Metadata filter restricting chunk lookup to specific IDs.")
    document_versions: Optional[Dict[str, str]] = Field(None, description="Optional map of document ID to specific version strings.")
    sections: Optional[List[str]] = Field(None, description="Optional list of section names to query.")
    top_k: int = Field(8, description="Number of policy chunks to retrieve.")
    unrestricted: bool = Field(False, description="Set to True to run unrestricted/debug vector search.")

class RouteRetrieveRequest(BaseModel):
    routing_request: PolicyRoutingRequest = Field(..., description="Volume 3 routing input context.")
    query: str = Field(..., description="RAG search query text.")
    top_k: int = Field(8, description="Number of chunks to return.")

@router.post("/retrieve")
def retrieve_policy(request: PolicyRetrievalRequest):
    """Perform metadata-restricted semantic search across NCD, LCD, and Article chunks."""
    try:
        res = PolicyRetrievalService.retrieve_policy_chunks(
            query=request.query,
            policy_scope=request.policy_scope,
            document_versions=request.document_versions,
            sections=request.sections,
            top_k=request.top_k,
            unrestricted=request.unrestricted
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval query failed: {str(e)}")

@router.post("/route-and-retrieve")
def route_and_retrieve(request: RouteRetrieveRequest):
    """Composition endpoint: Runs Volume 3 routing to restrict Volume 4 vector search boundaries."""
    try:
        res = RouteRetrieveComposer.route_and_retrieve(
            routing_request=request.routing_request,
            query=request.query,
            top_k=request.top_k
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Route and retrieve failed: {str(e)}")
