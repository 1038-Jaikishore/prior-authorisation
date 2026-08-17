import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException
from app.db.connection import db_connection
from app.services.prior_auth_intake import PriorAuthorizationIntakeService
from app.services.prior_auth_evaluation import PriorAuthorizationEvaluationService
from app.services.decision_engine import PriorAuthorizationDecisionService
from app.services.explanation import DecisionExplanationService
from app.services.document_mapper import DocumentEvidenceMapper
from app.services.audit import AuditLogService

def clean_db_objects(val: Any) -> Any:
    if isinstance(val, dict):
        return {k: clean_db_objects(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [clean_db_objects(x) for x in val]
    elif type(val).__name__ == "ObjectId":
        return str(val)
    return val

class DocumentPriorAuthEvaluationService:
    @classmethod
    def evaluate_document(
        cls,
        document_id: str,
        hcpcs_override: Optional[str] = None,
        state_override: Optional[str] = None,
        dos_override: Optional[str] = None,
        reviewer_id: str = "demo_reviewer"
    ) -> Dict[str, Any]:
        """Orchestrates the entire confirmed document to prior authorization decision flow."""
        db = db_connection.get_db()
        
        # 1. Load document metadata & extraction
        doc = db["patient_documents"].find_one({"document_id": document_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Document record not found.")
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
            
        extraction = db["document_extractions"].find_one({"document_id": document_id})
        if not extraction:
            raise HTTPException(status_code=404, detail="Document extraction draft not found.")
            
        # 2. Only confirmed extractions allowed
        if extraction.get("status") != "CONFIRMED":
            raise HTTPException(status_code=400, detail="DOCUMENT_EXTRACTION_NOT_CONFIRMED")
            
        # 3. Map extraction fields using DocumentEvidenceMapper
        try:
            mapped_data = DocumentEvidenceMapper.map_document_to_request_data(
                extraction=extraction,
                hcpcs_override=hcpcs_override,
                state_override=state_override,
                dos_override=dos_override
            )
        except ValueError as ve:
            # Propagate specific routing field error code
            raise HTTPException(status_code=400, detail=str(ve))
            
        # Determine overrides vs extracted provenance markers
        is_hcpcs_manual = bool(hcpcs_override and hcpcs_override != extraction.get("requested_service", {}).get("code"))
        is_state_manual = bool(state_override and state_override != extraction.get("geography", {}).get("state"))
        is_dos_manual = bool(dos_override and dos_override != extraction.get("requested_service", {}).get("date_of_service"))
        
        # 4. Resolve Patient (create structured record if missing)
        patient_id = doc.get("patient_id")
        patient_info = extraction.get("patient", {})
        if not patient_id:
            patient_id = f"PT_DOC_{str(uuid.uuid4())[:6].upper()}"
            db["patients"].insert_one({
                "patient_id": patient_id,
                "first_name": patient_info.get("name", "Unknown").split(" ")[0],
                "last_name": patient_info.get("name", "Unknown").split(" ")[-1] if " " in patient_info.get("name", "") else "",
                "dob": patient_info.get("dob") or "1970-01-01",
                "gender": patient_info.get("gender") or "unknown",
                "insurance_plan": "Medicare Advantage",
                "member_id": f"MBR_{patient_id}"
            })
            db["patient_documents"].update_one(
                {"document_id": document_id},
                {"$set": {"patient_id": patient_id}}
            )
            
        # 5. Create or retrieve canonical PatientPriorAuthRequest
        request_id = doc.get("authorization_id")
        if not request_id:
            request_id = f"AUTH-DOC-{str(uuid.uuid4())[:6].upper()}"
            db["patient_documents"].update_one(
                {"document_id": document_id},
                {"$set": {"authorization_id": request_id}}
            )
            
        # Construct diagnosis list
        diag_codes = []
        for code in mapped_data["diagnosis_codes"]:
            diag_codes.append({
                "source_value": code,
                "canonical_value": code.replace(".", ""),
                "display_value": code
            })
            
        auth_request_doc = {
            "request_id": request_id,
            "patient_id": patient_id,
            "provider_id": mapped_data["provider_id"],
            "requested_procedure_code": {
                "source_value": mapped_data["requested_service"]["code"],
                "canonical_value": mapped_data["requested_service"]["code"],
                "display_value": mapped_data["requested_service"]["code"]
            },
            "diagnosis_code": diag_codes[0] if len(diag_codes) == 1 else diag_codes,
            "request_date": mapped_data["request_date"],
            "clinical_indication": mapped_data["clinical_indication"],
            "provider_justification": mapped_data["provider_justification"],
            "state_code": mapped_data["state_code"],
            "source": mapped_data["source"],
            "inserted_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Upsert auth request doc
        db["authorization_requests"].update_one(
            {"request_id": request_id},
            {"$set": auth_request_doc},
            upsert=True
        )
        
        # Log Document Attached audit event
        AuditLogService.log_event(
            authorization_id=request_id,
            event_type="DOCUMENT_ATTACHED_TO_AUTHORIZATION",
            actor_id=reviewer_id,
            actor_type="REVIEWER",
            metadata={"document_id": document_id}
        )
        
        # Add custom Manual vs Extracted provenance tags in document confirmation record
        for pr in extraction.get("provenance_records", []):
            fact_type = pr.get("fact_type")
            if fact_type == "requested_procedure_code" and is_hcpcs_manual:
                pr["source_text"] = "Manually entered by reviewer"
                pr["extraction_method"] = "MANUALLY_PROVIDED"
            elif fact_type == "geography" and is_state_manual:
                pr["source_text"] = "Manually entered by reviewer"
                pr["extraction_method"] = "MANUALLY_PROVIDED"
            elif fact_type == "date_of_service" and is_dos_manual:
                pr["source_text"] = "Manually entered by reviewer"
                pr["extraction_method"] = "MANUALLY_PROVIDED"
        
        db["document_extractions"].update_one(
            {"document_id": document_id},
            {"$set": {"provenance_records": extraction.get("provenance_records", [])}}
        )
        
        # Log Evaluation Started audit event
        AuditLogService.log_event(
            authorization_id=request_id,
            event_type="DOCUMENT_EVALUATION_STARTED",
            actor_id=reviewer_id,
            actor_type="REVIEWER",
            metadata={"document_id": document_id}
        )
        
        # 6. Route and Retrieve using existing services
        route_ret = PriorAuthorizationIntakeService.execute_route_and_retrieve(
            request_id=request_id,
            override_state=mapped_data["state_code"],
            override_date=mapped_data["request_date"]
        )
        
        # Log Policy Routed audit event
        AuditLogService.log_event(
            authorization_id=request_id,
            event_type="DOCUMENT_POLICY_ROUTED",
            actor_id=reviewer_id,
            actor_type="REVIEWER",
            metadata={"document_id": document_id}
        )
        
        # If no policy found, stop early
        routing_obj = route_ret.get("policy_routing")
        routing_status = getattr(routing_obj, "routing_status", None) if hasattr(routing_obj, "routing_status") else routing_obj.get("routing_status")
        
        # Helper to dump pydantic models
        def dump_model(val: Any) -> Any:
            if hasattr(val, "model_dump"):
                return val.model_dump()
            elif hasattr(val, "dict"):
                return val.dict()
            return val

        if routing_status == "NO_POLICY_FOUND":
            eval_bundle = {
                "evaluation_id": f"EVAL-NA-{str(uuid.uuid4())[:6].upper()}",
                "authorization_id": request_id,
                "requirements": [],
                "requirement_evaluations": [],
                "coding_validations": [],
                "administrative_validations": [],
                "missing_information": ["No active CMS policy coverage rules govern CPT code."],
                "warnings": ["NO_POLICY_FOUND"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            db["evaluations"].insert_one(eval_bundle)
            eval_bundle["_id"] = str(eval_bundle["_id"])
            
            decision = {
                "decision_id": f"DEC-NA-{str(uuid.uuid4())[:6].upper()}",
                "evaluation_id": eval_bundle["evaluation_id"],
                "authorization_id": request_id,
                "recommended_disposition": "DECISION_SUPPORT_UNAVAILABLE",
                "decision_certainty": "HIGH",
                "requires_human_review": True,
                "reason_codes": ["PA_POLICY_UNAVAILABLE"],
                "decision_factors": [],
                "missing_information": [],
                "rule_version": "1.0.0",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            db["decisions"].insert_one(decision)
            decision["_id"] = str(decision["_id"])
            
            explanation = {
                "summary": "Policy unavailable for requested service.",
                "why": ["The requested procedure code has no associated NCD, LCD or Article coverage policy mappings."],
                "policy_summary": [],
                "satisfied_requirements": [],
                "blocking_requirements": [],
                "missing_information": [],
                "generated_by": {"provider": "deterministic", "model": "rule_engine"}
            }
            
            res_payload = {
                "document": doc,
                "authorization_request": auth_request_doc,
                "clinical_evidence_packet": dump_model(route_ret["clinical_evidence_packet"]),
                "policy_routing": dump_model(route_ret["policy_routing"]),
                "policy_retrieval": route_ret.get("policy_retrieval", {}),
                "evaluation_bundle": eval_bundle,
                "decision_support": decision,
                "explanation": explanation
            }
            return clean_db_objects(res_payload)

        # 7. Evaluate using Volume 6 Evaluation Service
        eval_bundle = PriorAuthorizationEvaluationService.evaluate_request(
            request_id=request_id,
            override_state=mapped_data["state_code"],
            override_date=mapped_data["request_date"]
        )
        
        # Log Evaluation Created audit event
        AuditLogService.log_event(
            authorization_id=request_id,
            event_type="DOCUMENT_EVALUATION_CREATED",
            actor_id=reviewer_id,
            actor_type="REVIEWER",
            metadata={"document_id": document_id}
        )
        
        # 8. Decision Triage using Volume 7 Decision Service
        decision = PriorAuthorizationDecisionService.generate_decision(eval_bundle)
        
        # Log Decision Created audit event
        AuditLogService.log_event(
            authorization_id=request_id,
            event_type="DOCUMENT_DECISION_CREATED",
            actor_id=reviewer_id,
            actor_type="REVIEWER",
            metadata={"document_id": document_id}
        )
        
        # 9. Explanation using Volume 8 Explanation Service
        explanation = DecisionExplanationService.generate_explanation(decision, eval_bundle)
        
        # 10. Clean ObjectIds for response
        res = {
            "document": doc,
            "authorization_request": auth_request_doc,
            "clinical_evidence_packet": dump_model(route_ret["clinical_evidence_packet"]),
            "policy_routing": dump_model(route_ret["policy_routing"]),
            "policy_retrieval": route_ret.get("policy_retrieval", {}),
            "evaluation_bundle": dump_model(eval_bundle),
            "decision_support": dump_model(decision),
            "explanation": dump_model(explanation)
        }
        return clean_db_objects(res)
