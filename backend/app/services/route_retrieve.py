from typing import Dict, Any, List
from app.models.policy import PolicyRoutingRequest
from app.services.policy_routing import PolicyRoutingService
from app.services.policy_retrieval import PolicyRetrievalService

class RouteRetrieveComposer:
    @staticmethod
    def route_and_retrieve(routing_request: PolicyRoutingRequest, query: str, top_k: int = 8) -> Dict[str, Any]:
        """Composes routing and metadata-restricted retrieval services sequentially."""
        
        # 1. Execute Volume 3 deterministic routing
        routing_response = PolicyRoutingService.route_policy(routing_request)
        
        # 2. Extract policy scope details
        ncd_ids = [n["ncd_id"] for n in routing_response.applicable_ncds]
        if not ncd_ids:
            ncd_ids = [n["ncd_id"] for n in routing_response.candidate_ncds]
            
        lcd_ids = [l["lcd_id"] for l in routing_response.applicable_lcds]
        if not lcd_ids:
            lcd_ids = [l["lcd_id"] for l in routing_response.candidate_lcds]
            
        article_ids = [a["article_id"] for a in routing_response.related_articles]
        
        policy_scope = {
            "ncd_ids": list(set(ncd_ids)),
            "lcd_ids": list(set(lcd_ids)),
            "article_ids": list(set(article_ids))
        }
        
        # 3. Extract version requirements
        document_versions = {}
        for n in (routing_response.applicable_ncds or routing_response.candidate_ncds):
            document_versions[n["ncd_id"]] = n.get("version")
        for l in (routing_response.applicable_lcds or routing_response.candidate_lcds):
            document_versions[l["lcd_id"]] = l.get("version")
        for a in routing_response.related_articles:
            document_versions[a["article_id"]] = a.get("article_version")
            
        # 4. Handle partial policy warnings
        warnings = list(routing_response.warnings)
        if routing_response.routing_status == "PARTIAL_POLICY_DATA":
            warnings.append("Partial policy data detected: retrieval is incomplete due to missing master records.")
            
        # 5. Execute metadata-restricted RAG query
        # Set unrestricted to True ONLY if the resolved scope is empty (e.g. no LCD/NCD/Article candidate exists at all)
        # to avoid throwing a ValueError but still warning the user
        scope_has_records = any(policy_scope.values())
        unrestricted_flag = not scope_has_records
        
        if unrestricted_flag:
            warnings.append("Policy scope is empty. Executing unrestricted/debug fallback retrieval.")
            
        retrieval_res = PolicyRetrievalService.retrieve_policy_chunks(
            query=query,
            policy_scope=policy_scope,
            document_versions=document_versions,
            top_k=top_k,
            unrestricted=unrestricted_flag
        )
        
        # 6. Gather warnings and citations
        warnings.extend(retrieval_res["warnings"])
        results = retrieval_res["results"]
        citations = [item["citation"] for item in results]
        
        return {
            "routing_result": routing_response,
            "retrieval_result": results,
            "citations": citations,
            "warnings": list(set(warnings))
        }
