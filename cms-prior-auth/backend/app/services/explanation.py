import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.db.connection import db_connection
from app.services.llm import get_llm_provider
from app.services.audit import AuditLogService
from app.models.review import DecisionExplanation

class DecisionExplanationService:
    @classmethod
    def generate_deterministic_explanation(
        cls,
        decision_result: Dict[str, Any],
        evaluation_bundle: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generates a structured, fully grounded deterministic explanation from rule data."""
        disp = decision_result["recommended_disposition"]
        decision_id = decision_result["decision_id"]
        
        satisfied = []
        blocking = []
        missing = []
        coding_reasons = []
        policy_docs = []
        
        for fac in decision_result.get("decision_factors", []):
            desc = fac.get("description", "")
            effect = fac.get("effect", "")
            ftype = fac.get("factor_type", "")
            
            if effect == "SUPPORTS_APPROVAL":
                satisfied.append(desc)
            elif effect == "BLOCKING_FAILURE":
                blocking.append(desc)
            elif effect == "BLOCKING_MISSING_INFORMATION":
                missing.append(desc)
            elif ftype in ("CODING_VALIDATION", "ADMINISTRATIVE"):
                coding_reasons.append(f"{fac.get('factor_id')}: {desc} ({fac.get('status')})")
                
        # Policy summary
        policy_context = evaluation_bundle.get("policy_context", {})
        app_pols = policy_context.get("applicable_policies", [])
        rel_pols = policy_context.get("related_reference_policies", [])
        policy_docs = [f"Applicable LCD: {p}" for p in app_pols] + [f"Related Reference: {p}" for p in rel_pols]
        
        # Summary text
        if disp == "APPROVE":
            summary = "All CMS coverage rules and administrative criteria are satisfied. Approval is recommended."
        elif disp == "DENY":
            summary = f"Coverage recommendation is DENIED due to blocking failures: {'; '.join(blocking)}."
        elif disp == "PEND":
            summary = "Coverage evaluation is PENDING. Additional patient clinical documentation is required to establish medical necessity."
        elif disp == "NURSE_REVIEW":
            summary = "Manual review by a clinical nurse is required due to policy routing/applicability uncertainty or conflicting record parameters."
        else:
            summary = "Automated decision support is unavailable for this custom procedural request."
            
        why_list = []
        if disp == "PEND":
            why_list = ["Qualifying clinical documentation was not resolved in patient records."]
        elif disp == "DENY":
            why_list = ["Positive evidence indicates clinical criteria or coding conventions were not met."]
        elif disp == "APPROVE":
            why_list = ["All mandatory policy evaluations and administrative validations passed."]
        else:
            why_list = ["Case has been routed for manual clinical review."]
            
        exp = DecisionExplanation(
            decision_id=decision_id,
            recommended_disposition=disp,
            summary=summary,
            why=why_list,
            satisfied_requirements=satisfied,
            blocking_requirements=blocking,
            missing_information=missing if disp == "PEND" else [],
            coding_summary=coding_reasons,
            policy_summary=policy_docs,
            policy_citations=decision_result.get("policy_citations", []),
            patient_provenance=decision_result.get("patient_provenance", []),
            generated_by={
                "provider": "deterministic",
                "model": "rule_engine",
                "prompt_version": "v1"
            },
            created_at=datetime.now(timezone.utc).isoformat()
        )
        return exp.model_dump()

    @classmethod
    def generate_explanation(
        cls,
        decision_result: Dict[str, Any],
        evaluation_bundle: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attempts LLM synthesis with strict safety validations, failing back to deterministic on errors."""
        authorization_id = decision_result["authorization_id"]
        decision_id = decision_result["decision_id"]
        disp = decision_result["recommended_disposition"]
        
        # 1. Fall back if decision is unavailable
        if disp == "DECISION_SUPPORT_UNAVAILABLE":
            return cls.generate_deterministic_explanation(decision_result, evaluation_bundle)
            
        # 2. Try LLM Generation
        try:
            llm = get_llm_provider()
            
            # Prepare contextual parameters to send to LLM (excluding patient details/keys)
            system_prompt = (
                "You are an expert Medicare reviewer assistant. Summarize the prior authorization recommendation.\n"
                "You MUST return a JSON object with the following fields:\n"
                "{\n"
                "  \"summary\": \"Concise text summary (max 2 sentences)\",\n"
                "  \"why\": [\"List of key reasons why this recommendation was reached\"],\n"
                "  \"satisfied_requirements\": [\"List of requirements that are met\"],\n"
                "  \"blocking_requirements\": [\"List of blocking requirements if DENY or PEND\"],\n"
                "  \"missing_information\": [\"List of requested documents if PEND\"],\n"
                "  \"coding_summary\": [\"List of coding checks/conventions details\"],\n"
                "  \"policy_summary\": [\"Policy context description\"]\n"
                "}\n"
                "CRITICAL RULES:\n"
                "1. You MUST set the recommended disposition as PEND, DENY, APPROVE, or NURSE_REVIEW to match exactly the input.\n"
                "2. Do NOT change the decision.\n"
                "3. Do NOT invent outside facts or medical knowledge.\n"
                "4. All output must be strictly grounded in the decision factors provided.\n"
            )
            
            user_prompt = f"""
            Recommended Disposition: {disp}
            Decision ID: {decision_id}
            Reason Codes: {decision_result.get('reason_codes', [])}
            Citations: {decision_result.get('policy_citations', [])}
            
            Decision Factors:
            {json.dumps([{ 'id': f.get('factor_id'), 'status': f.get('status'), 'effect': f.get('effect'), 'description': f.get('description') } for f in decision_result.get('decision_factors', [])], indent=2)}
            
            Missing Information Requests:
            {json.dumps([{ 'desc': m.get('description') } for m in decision_result.get('missing_information', [])], indent=2)}
            """
            
            model_info = getattr(llm, "model", "mock_model")
            provider_info = "openrouter" if hasattr(llm, "api_key") else "mock"
            
            raw_res = llm.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_mode=True,
                temperature=0.0
            )
            
            parsed = json.loads(raw_res)
            
            # --- Strict Explanations Validations ---
            # Rule A: The LLM must not alter the disposition
            out_disp = parsed.get("recommended_disposition", disp)
            if out_disp != disp:
                raise ValueError(f"LLM tried to alter recommended disposition from {disp} to {out_disp}")
                
            # Compile valid outputs
            exp = DecisionExplanation(
                decision_id=decision_id,
                recommended_disposition=disp,
                summary=parsed.get("summary", ""),
                why=parsed.get("why", []),
                satisfied_requirements=parsed.get("satisfied_requirements", []),
                blocking_requirements=parsed.get("blocking_requirements", []),
                missing_information=parsed.get("missing_information", []),
                coding_summary=parsed.get("coding_summary", []),
                policy_summary=parsed.get("policy_summary", []),
                policy_citations=decision_result.get("policy_citations", []),
                patient_provenance=decision_result.get("patient_provenance", []),
                generated_by={
                    "provider": provider_info,
                    "model": model_info,
                    "prompt_version": "decision_explanation_v1"
                },
                created_at=datetime.now(timezone.utc).isoformat()
            )
            
            # Log successful generation event
            AuditLogService.log_event(
                authorization_id=authorization_id,
                event_type="EXPLANATION_GENERATED",
                related_object_id=decision_id,
                metadata={"provider": provider_info, "model": model_info}
            )
            
            # Save explanation
            db = db_connection.get_db()
            db["decision_explanations"].insert_one(exp.model_dump())
            return exp.model_dump()
            
        except Exception as e:
            # Fall back to deterministic explanation on LLM errors/timeouts
            AuditLogService.log_event(
                authorization_id=authorization_id,
                event_type="EXPLANATION_VALIDATION_FAILED",
                related_object_id=decision_id,
                metadata={"error": str(e)}
            )
            
            # Generate and persist deterministic explanation
            det_exp = cls.generate_deterministic_explanation(decision_result, evaluation_bundle)
            
            db = db_connection.get_db()
            db["decision_explanations"].insert_one(det_exp)
            return det_exp
            
    @classmethod
    def get_explanation(cls, decision_id: str) -> Optional[Dict[str, Any]]:
        """Fetches the computed explanation for a decision ID."""
        db = db_connection.get_db()
        doc = db["decision_explanations"].find_one({"decision_id": decision_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc
