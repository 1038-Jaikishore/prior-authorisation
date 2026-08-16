import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.db.connection import db_connection
from app.services.audit import AuditLogService
from app.services.decision_engine import PriorAuthorizationDecisionService
from app.services.explanation import DecisionExplanationService
from app.models.review import ReviewerAction, AuditEvent, PriorAuthorizationReviewCase

class PriorAuthorizationReviewCaseService:
    @classmethod
    def get_case(cls, authorization_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves and packages the complete PriorAuthorizationReviewCase context."""
        db = db_connection.get_db()
        
        # 1. Fetch Request
        req = db["authorization_requests"].find_one({"request_id": authorization_id})
        if not req:
            return None
        req["_id"] = str(req["_id"])
        
        # 2. Fetch Patient Demographics
        pat_id = req.get("patient_id")
        pat = db["patients"].find_one({"patient_id": pat_id})
        if pat:
            pat["_id"] = str(pat["_id"])
        else:
            pat = {}
            
        # 3. Fetch ClinicalEvidencePacket
        cep = db["clinical_evidence_packets"].find_one({"authorization_id": authorization_id})
        if cep:
            cep["_id"] = str(cep["_id"])
        else:
            cep = {}
            
        # 4. Fetch routing info
        routing = db["policy_routing_results"].find_one({"authorization_id": authorization_id})
        if routing:
            routing["_id"] = str(routing["_id"])
        else:
            routing = {}
            
        # 5. Fetch retrieved policy passages
        # Fetching large passages only when details are queried
        citations_list = db["policy_retrievals"].find({"authorization_id": authorization_id})
        retrieved_sections = []
        for c in citations_list:
            c["_id"] = str(c["_id"])
            retrieved_sections.append(c)
            
        # 6. Fetch latest Evaluation Bundle
        eval_bundle = db["evaluation_bundles"].find_one(
            {"authorization_id": authorization_id},
            sort=[("provenance.evaluated_at", -1)]
        )
        if eval_bundle:
            eval_bundle["_id"] = str(eval_bundle["_id"])
            
        # 7. Fetch latest Decision support
        dec_support = db["decision_support_results"].find_one(
            {"authorization_id": authorization_id},
            sort=[("created_at", -1)]
        )
        dec_explanation = None
        if dec_support:
            dec_support["_id"] = str(dec_support["_id"])
            # Fetch corresponding explanation
            dec_explanation = DecisionExplanationService.get_explanation(dec_support["decision_id"])
            if not dec_explanation:
                # Generate explanation on demand if not persisted
                dec_explanation = DecisionExplanationService.generate_explanation(dec_support, eval_bundle or {})
                
        # 8. Fetch Review history
        history = list(db["reviewer_actions"].find({"authorization_id": authorization_id}).sort("timestamp", -1))
        for h in history:
            h["_id"] = str(h["_id"])
            
        # 9. Fetch Audit events
        audit_events = AuditLogService.get_events(authorization_id)
        
        case_data = PriorAuthorizationReviewCase(
            authorization_id=authorization_id,
            patient_summary={
                "patient_id": pat_id,
                "first_name": pat.get("first_name", "Unknown"),
                "last_name": pat.get("last_name", "Patient"),
                "dob": pat.get("dob", ""),
                "gender": pat.get("gender", ""),
                "insurance_plan": pat.get("insurance_plan", ""),
                "member_id": pat.get("member_id", ""),
                "state_code": req.get("state_code", "")
            },
            clinical_evidence_packet=cep,
            policy_routing_result=routing,
            retrieved_policy_sections=retrieved_sections,
            evaluation_bundle=eval_bundle,
            decision_support_result=dec_support,
            decision_explanation=dec_explanation,
            review_history=history,
            audit_events=audit_events
        )
        return case_data.model_dump()
        
    @classmethod
    def list_cases(cls) -> List[Dict[str, Any]]:
        """Lists brief summary cases for the queue dashboard view."""
        db = db_connection.get_db()
        requests = list(db["authorization_requests"].find().sort("request_date", -1))
        cases = []
        for req in requests:
            req_id = req["request_id"]
            pat_id = req.get("patient_id")
            
            # Demographics summary
            pat = db["patients"].find_one({"patient_id": pat_id})
            pat_name = f"{pat.get('first_name', '')} {pat.get('last_name', '')}".strip() if pat else "Unknown"
            
            # Latest decision details
            dec = db["decision_support_results"].find_one(
                {"authorization_id": req_id},
                sort=[("created_at", -1)]
            )
            
            disposition = dec.get("recommended_disposition") if dec else "AWAITING_INTAKE"
            missing_count = len(dec.get("missing_information", [])) if dec else 0
            human_review = dec.get("requires_human_review", True) if dec else True
            
            # Event history updates
            last_evt = db["audit_events"].find_one(
                {"authorization_id": req_id},
                sort=[("timestamp", -1)]
            )
            last_updated = last_evt.get("timestamp") if last_evt else req.get("request_date")
            
            cases.append({
                "authorization_id": req_id,
                "patient_name": pat_name,
                "requested_service": req.get("requested_procedure_code", {}).get("canonical_value", "Unknown"),
                "urgency": "Standard", # Default placeholder
                "current_recommendation": disposition,
                "missing_information_count": missing_count,
                "human_review_required": human_review,
                "last_updated": last_updated
            })
        return cases
        
    @classmethod
    def record_action(
        cls,
        authorization_id: str,
        reviewer_id: str,
        action: str,
        reason: str,
        intended_disposition: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submits and audits reviewer manual workflow actions or overrides."""
        db = db_connection.get_db()
        
        # 1. Fetch latest decision to reference
        dec = db["decision_support_results"].find_one(
            {"authorization_id": authorization_id},
            sort=[("created_at", -1)]
        )
        if not dec:
            raise ValueError(f"No recommendation found to review for request '{authorization_id}'")
            
        review_id = f"REV-{authorization_id}-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        action_doc = ReviewerAction(
            review_id=review_id,
            authorization_id=authorization_id,
            decision_id=dec["decision_id"],
            evaluation_id=dec["evaluation_id"],
            reviewer_id=reviewer_id,
            action=action,
            intended_disposition=intended_disposition,
            reason=reason,
            timestamp=timestamp
        )
        
        db["reviewer_actions"].insert_one(action_doc.model_dump())
        
        # Log audit events
        event_type = "REVIEWER_ACTION_RECORDED"
        if action == "OVERRIDE_RECOMMENDATION":
            event_type = "RECOMMENDATION_OVERRIDDEN"
            
        AuditLogService.log_event(
            authorization_id=authorization_id,
            event_type=event_type,
            actor_type="REVIEWER",
            actor_id=reviewer_id,
            related_object_id=review_id,
            metadata={
                "action": action,
                "original_recommendation": dec["recommended_disposition"],
                "new_reviewer_disposition": intended_disposition or dec["recommended_disposition"],
                "reason": reason
            }
        )
        
        return action_doc.model_dump()
