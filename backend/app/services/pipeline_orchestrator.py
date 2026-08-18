from typing import Dict, Any, Optional
from app.models.decision import PipelineDecisionResult
from app.services.prior_auth_intake import PriorAuthorizationIntakeService
from app.services.ncd_evaluation_engine import NCDEvaluationEngine
from app.services.lcd_evaluation_engine import LCDEvaluationEngine
from app.services.article_evaluation_engine import ArticleEvaluationEngine
from app.services.decision_engine import ConfidenceDecisionEngine
from app.services.explanation_engine import ExplanationEngine

class PriorAuthPipelineOrchestrator:
    @staticmethod
    def run_full_pipeline(
        authorization_id: str,
        override_state: Optional[str] = None,
        override_date: Optional[str] = None
    ) -> PipelineDecisionResult:
        """
        Executes the full CMS Prior Authorization AI Pipeline (Phases 1 through 5).
        Handles early exit (DENY) if Phase 4 fails.
        """
        
        # 1. Execute Phases 1-3 (Routing and Retrieval)
        pipeline_res = PriorAuthorizationIntakeService.execute_route_and_retrieve(
            request_id=authorization_id,
            override_state=override_state,
            override_date=override_date
        )
        
        clinical_evidence = pipeline_res.get("clinical_evidence_packet")
        retrieval_result = pipeline_res.get("policy_retrieval", {}).get("results", [])
        routing_response = pipeline_res.get("policy_routing")
        
        if not clinical_evidence:
            raise ValueError(f"Failed to build ClinicalEvidencePacket for {authorization_id}")
            
        # 2. Execute Phase 4 (NCD Semantic Evaluation)
        ncd_decision = NCDEvaluationEngine.evaluate_ncds(
            clinical_evidence=clinical_evidence,
            retrieval_result=retrieval_result
        )
        
        # 3. If NCD is COVERED or NOT ADDRESSED, proceed to Phase 5 (LCD Evaluation)
        if ncd_decision.ncd_determination == "NOT COVERED":
            from app.models.decision import LCDSemanticEvaluationResult
            lcd_decision = LCDSemanticEvaluationResult(
                lcd_determination="NOT ADDRESSED",
                semantic_similarity_score=0.0,
                confidence_score=1.0,
                key_policy_excerpts=[],
                conditions=[],
                reasoning="Applicable NCD resulted in NOT COVERED."
            )
        else:
            lcd_decision = LCDEvaluationEngine.evaluate_lcds(
                clinical_evidence=clinical_evidence,
                retrieval_result=retrieval_result
            )
        
        # 5. Proceed to Phase 6 (Article Evaluation)
        article_decision = ArticleEvaluationEngine.evaluate_articles(
            clinical_evidence=clinical_evidence,
            retrieval_result=retrieval_result
        )
        
        # 6. Proceed to Phase 7 (Confidence & Decision Engine)
        phase7_decision = ConfidenceDecisionEngine.compute_decision(
            clinical_evidence=clinical_evidence,
            ncd_decision=ncd_decision,
            lcd_decision=lcd_decision,
            article_decision=article_decision
        )

        # 7. Map Phase 7 output to final PipelineDecisionResult
        status_map = {
            "APPROVE": "APPROVED",
            "DENY": "DENIED",
            "PEND": "PENDING_MANUAL_REVIEW",
            "NURSE_REVIEW": "PENDING_MANUAL_REVIEW"
        }

        ncd_ids = [n.get("ncd_id") for n in routing_response.applicable_ncds] if routing_response and routing_response.applicable_ncds else ([n.get("ncd_id") for n in routing_response.candidate_ncds] if routing_response else [])
        lcd_ids = [l.get("lcd_id") for l in routing_response.applicable_lcds] if routing_response and routing_response.applicable_lcds else ([l.get("lcd_id") for l in routing_response.candidate_lcds] if routing_response else [])
        article_ids = [a.get("article_id") for a in routing_response.related_articles] if routing_response else []

        req_service = clinical_evidence.requested_service if clinical_evidence else {}
        phase3_routing = {
            "requested_hcpcs": req_service.get("code", "UNKNOWN") if isinstance(req_service, dict) else getattr(req_service, "code", "UNKNOWN"),
            "ncd_policies": ncd_ids,
            "lcd_policies": lcd_ids,
            "article_policies": article_ids
        }

        pipeline_result = PipelineDecisionResult(
            final_status=status_map.get(phase7_decision.recommendation, "PENDING_MANUAL_REVIEW"),
            ncd_decision=ncd_decision,
            lcd_decision=lcd_decision,
            article_decision=article_decision,
            phase7_decision=phase7_decision,
            clinical_evidence=clinical_evidence.dict() if hasattr(clinical_evidence, 'dict') else clinical_evidence,
            phase3_routing=phase3_routing
        )

        # 8. Phase 8: Generate Final Explanation
        final_markdown_explanation = ExplanationEngine.generate_explanation(pipeline_result)
        pipeline_result.final_explanation = final_markdown_explanation

        return pipeline_result
