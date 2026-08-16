import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.db.connection import db_connection
from app.models.decision import DecisionSupportResult, DecisionFactor, MissingInformationRequest

class PriorAuthorizationDecisionService:
    @classmethod
    def generate_decision(
        cls, 
        evaluation_bundle: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Runs the deterministic triage rules over the EvaluationBundle and returns versioned decision support."""
        db = db_connection.get_db()
        
        # 1. Normalize EvaluationBundle to dictionary
        if hasattr(evaluation_bundle, "model_dump"):
            bundle_dict = evaluation_bundle.model_dump()
        elif hasattr(evaluation_bundle, "dict"):
            bundle_dict = evaluation_bundle.dict()
        else:
            bundle_dict = dict(evaluation_bundle)
            
        authorization_id = bundle_dict["authorization_id"]
        evaluation_id = bundle_dict["evaluation_id"]
        
        policy_context = bundle_dict.get("policy_context", {})
        req_evals = bundle_dict.get("requirement_evaluations", [])
        coding_vals = bundle_dict.get("coding_validations", [])
        admin_vals = bundle_dict.get("administrative_validations", [])
        warnings = list(bundle_dict.get("warnings", []))
        missing_info_strings = list(bundle_dict.get("missing_information", []))
        provenance = bundle_dict.get("provenance", {})
        
        # Determine status flags
        intake_status = provenance.get("intake_status", "SUCCESS")
        
        # Initialize outputs
        recommended_disposition = "PEND"
        decision_certainty = "HIGH"
        reason_codes = []
        decision_factors = []
        missing_info_requests = []
        policy_citations = []
        patient_provenance = []
        
        # -------------------------------------------------------------
        # STEP 1: Parse and Map Decision Factors & Provenance
        # -------------------------------------------------------------
        
        # Helper to gather citations & patient provenance
        def add_provenance_and_citations(cit: Optional[str], prov_list: List[Dict[str, Any]]):
            if cit and cit not in policy_citations:
                policy_citations.append(cit)
            for p in prov_list:
                if p not in patient_provenance:
                    patient_provenance.append(p)
                    
        # Parse Clinical Requirement Evaluations
        has_mandatory_not_met = False
        has_mandatory_unclear = False
        
        for ev in req_evals:
            req = ev.get("policy_requirement", {})
            req_id = req.get("requirement_id", "REQ-UNK")
            req_text = req.get("requirement_text", "")
            role = req.get("policy_role", "APPLICABLE")
            status = ev.get("status", "UNCLEAR")
            rationale = ev.get("rationale", "")
            citation = ev.get("policy_citation")
            prov = ev.get("patient_provenance", [])
            
            # Map factors
            effect = "INFORMATIONAL"
            if role in ("CONTROLLING", "APPLICABLE"):
                if status == "MET":
                    effect = "SUPPORTS_APPROVAL"
                elif status == "NOT_MET":
                    effect = "BLOCKING_FAILURE"
                    has_mandatory_not_met = True
                elif status == "UNCLEAR":
                    effect = "BLOCKING_MISSING_INFORMATION"
                    has_mandatory_unclear = True
                elif status == "NOT_APPLICABLE":
                    effect = "INFORMATIONAL"
            else:
                # RELATED_REFERENCE requirements do NOT block
                if status == "MET":
                    effect = "INFORMATIONAL"
                elif status == "NOT_MET":
                    effect = "NON_BLOCKING_WARNING"
                elif status == "UNCLEAR":
                    effect = "INFORMATIONAL"
                    
            decision_factors.append(DecisionFactor(
                factor_id=f"FAC-{req_id}",
                factor_type="CLINICAL_REQUIREMENT",
                status=status,
                effect=effect,
                description=f"{req_text} (Role: {role}). Rationale: {rationale}",
                policy_citation=citation,
                patient_provenance=prov
            ))
            
            add_provenance_and_citations(citation, prov)
            
            # For UNCLEAR mandatory criteria, generate missing info request
            if role in ("CONTROLLING", "APPLICABLE") and status == "UNCLEAR":
                missing_info_requests.append(MissingInformationRequest(
                    request_type="CLINICAL_DOCUMENTATION",
                    requirement_id=req_id,
                    description=f"Provide documentation confirming compliance with requirement: {req_text}",
                    policy_citation=citation,
                    priority="REQUIRED"
                ))
                
        # Parse Coding and Administrative Validations
        has_blocking_fail = False
        has_coding_warnings = False
        
        for cv in (coding_vals + admin_vals):
            validator = cv.get("validator", "VALIDATOR")
            status = cv.get("status", "PASS")
            reason = cv.get("reason", "")
            doc_id = cv.get("policy_document")
            source_rec = cv.get("source_records", [])
            
            # Define severity mapping
            effect = "INFORMATIONAL"
            if status == "PASS":
                effect = "SUPPORTS_APPROVAL"
            elif status == "FAIL":
                # Explicit FAIL checks are BLOCKING
                effect = "BLOCKING_FAILURE"
                has_blocking_fail = True
            elif status in ("WARNING", "UNKNOWN"):
                # Missing optional elements or non-failing warnings are non-blocking
                effect = "NON_BLOCKING_WARNING"
                has_coding_warnings = True
            elif status == "NOT_EVALUATED":
                effect = "INFORMATIONAL"
                
            decision_factors.append(DecisionFactor(
                factor_id=f"FAC-VAL-{validator}",
                factor_type="ADMINISTRATIVE" if validator in ("JURISDICTION", "DATE_AND_VERSION") else "CODING_VALIDATION",
                status=status,
                effect=effect,
                description=reason,
                policy_citation=doc_id,
                patient_provenance=[{"collection": "cms_reference", "record_id": str(r.get("source_row"))} for r in source_rec if "source_row" in r]
            ))
            
            add_provenance_and_citations(doc_id, [])
            
        # -------------------------------------------------------------
        # STEP 2: Apply Precedence Rules & Recommended Disposition
        # -------------------------------------------------------------
        
        # Rule 1: POLICY_EVALUATION_UNAVAILABLE (Custom PROCxxxx / non-routable request)
        if intake_status == "POLICY_EVALUATION_UNAVAILABLE":
            recommended_disposition = "DECISION_SUPPORT_UNAVAILABLE"
            decision_certainty = "LOW"
            reason_codes.append("PA_POLICY_UNAVAILABLE")
            
        # Rule 2: POLICY_APPLICABILITY_UNCERTAIN (Ambiguous state geography or multiple conflicting LCDs)
        elif intake_status == "MISSING_ROUTING_GEOGRAPHY" or any("POLICY_APPLICABILITY_UNCERTAIN" in w for w in warnings):
            recommended_disposition = "NURSE_REVIEW"
            decision_certainty = "LOW"
            reason_codes.append("PA_POLICY_UNCERTAIN")
            
        # Rule 3: Deterministic Exclusions / Blocking Validation failures (ICD-10 noncovered, expired dates, incorrect MAC)
        elif has_blocking_fail:
            recommended_disposition = "DENY"
            decision_certainty = "HIGH"
            reason_codes.append("PA_CODING_BLOCKING_FAILURE")
            
        # Rule 4: Mandatory Clinical NOT_MET (positive evidence of failure)
        elif has_mandatory_not_met:
            recommended_disposition = "DENY"
            decision_certainty = "HIGH"
            reason_codes.append("PA_MANDATORY_CRITERION_NOT_MET")
            
        # Rule 5: Mandatory Clinical UNCLEAR / Blocking Clinical Missing Information (requires pending)
        elif has_mandatory_unclear:
            recommended_disposition = "PEND"
            decision_certainty = "HIGH"
            reason_codes.append("PA_MANDATORY_CRITERION_UNCLEAR")
            
        # Rule 6: All Mandatory requirements MET
        else:
            recommended_disposition = "APPROVE"
            # If warning or unknown status checks exist (e.g. modifier unknown, LCD_HCPCS warning), reduce certainty to MODERATE
            if has_coding_warnings or len(warnings) > 0:
                decision_certainty = "MODERATE"
                reason_codes.append("PA_NONBLOCKING_CODING_WARNING")
            else:
                decision_certainty = "HIGH"
                reason_codes.append("PA_ALL_MANDATORY_CRITERIA_MET")
                
        # Generate the structured explainability payload
        decision_id = f"DEC-{authorization_id}-{uuid.uuid4().hex[:8]}"
        
        bundle = DecisionSupportResult(
            decision_id=decision_id,
            evaluation_id=evaluation_id,
            authorization_id=authorization_id,
            recommended_disposition=recommended_disposition,
            decision_type="DECISION_SUPPORT",
            requires_human_review=True,
            reason_codes=reason_codes,
            decision_factors=decision_factors,
            missing_information=missing_info_requests,
            warnings=warnings,
            policy_citations=policy_citations,
            patient_provenance=patient_provenance,
            decision_certainty=decision_certainty,
            rule_version="v1",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Save decision support result to database
        db["decision_support_results"].insert_one(bundle.model_dump())
        return bundle.model_dump()
        
    @classmethod
    def get_latest_decision(cls, request_id: str) -> Optional[Dict[str, Any]]:
        """Fetches the latest completed decision support result for a request ID."""
        db = db_connection.get_db()
        doc = db["decision_support_results"].find_one(
            {"authorization_id": request_id},
            sort=[("created_at", -1)]
        )
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    @classmethod
    def get_decision_by_id(cls, decision_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a specific completed decision support result by its decision ID."""
        db = db_connection.get_db()
        doc = db["decision_support_results"].find_one({"decision_id": decision_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc
        
    @classmethod
    def get_decision_history(cls, request_id: str) -> List[Dict[str, Any]]:
        """Lists historical decision support entries computed for a request ID."""
        db = db_connection.get_db()
        docs = list(db["decision_support_results"].find(
            {"authorization_id": request_id},
            sort=[("created_at", -1)]
        ))
        for doc in docs:
            doc["_id"] = str(doc["_id"])
        return docs
