from typing import Dict, Any, List, Optional
from datetime import datetime
from bson import ObjectId
from app.db.connection import db_connection
from app.models.patient import ClinicalEvidencePacket, EvidenceProvenance, PatientPriorAuthRequest
from app.models.policy import PolicyRoutingRequest
from app.services.policy_routing import PolicyRoutingService
from app.services.policy_retrieval import PolicyRetrievalService

class PriorAuthorizationIntakeService:
    @staticmethod
    def get_authorization_request(request_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves prior authorization request document from MongoDB."""
        db = db_connection.get_db()
        doc = db["authorization_requests"].find_one({"request_id": request_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    @staticmethod
    def list_authorization_requests() -> List[Dict[str, Any]]:
        """Lists all prior authorization requests in the database."""
        db = db_connection.get_db()
        docs = list(db["authorization_requests"].find().limit(100))
        for doc in docs:
            doc["_id"] = str(doc["_id"])
        return docs

    @classmethod
    def compile_evidence_packet(
        cls,
        request_id: str,
        override_state: Optional[str] = None,
        override_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compiles structured and unstructured clinical facts into a ClinicalEvidencePacket with audit provenance."""
        db = db_connection.get_db()
        
        # 1. Fetch Auth Request
        req_doc = db["authorization_requests"].find_one({"request_id": request_id})
        if not req_doc:
            raise ValueError(f"Authorization request ID '{request_id}' not found.")
            
        patient_id = req_doc["patient_id"]
        provider_id = req_doc["provider_id"]
        
        # 2. Fetch Patient Demographics
        pat_doc = db["patients"].find_one({"patient_id": patient_id})
        demographics = {}
        if pat_doc:
            demographics = {
                "first_name": pat_doc.get("first_name"),
                "last_name": pat_doc.get("last_name"),
                "dob": pat_doc.get("dob"),
                "age": pat_doc.get("age"),
                "gender": pat_doc.get("gender"),
                "insurance_plan": pat_doc.get("insurance_plan"),
                "member_id": pat_doc.get("member_id"),
                "summary": pat_doc.get("summary_card_text")
            }
            
        # 3. Resolve Geography (State Code)
        # Check providers for facility details
        state_code = override_state
        prov_doc = db["providers"].find_one({"provider_id": provider_id})
        if prov_doc:
            prov_doc["_id"] = str(prov_doc["_id"])
        
        if not state_code and prov_doc:
            facility = prov_doc.get("facility_name", "")
            # Heuristics: extract 2-letter state abbreviation if present or check full name
            if "colorado" in facility.lower() or " CO" in facility:
                state_code = "CO"
            elif "texas" in facility.lower() or " TX" in facility:
                state_code = "TX"
            # Fall back to checking network status address if mapped
            
        demographics["state_code"] = state_code
        
        # 4. Fetch Clinical tables and build provenance list
        provenance_list: List[EvidenceProvenance] = []
        warnings = []
        missing = []
        
        # Helper to query collection and attach provenance
        def fetch_clinical_records(coll_name: str, fact_type: str, code_field: str) -> List[Dict[str, Any]]:
            records = list(db[coll_name].find({"patient_id": patient_id}))
            output = []
            for r in records:
                r["_id"] = str(r["_id"])
                output.append(r)
                
                # Capture provenance
                val = r.get(code_field, "")
                # If code is normalized dict structure
                if isinstance(val, dict) and "display_value" in val:
                    val_str = val["display_value"]
                else:
                    val_str = str(val)
                    
                provenance_list.append(EvidenceProvenance(
                    fact_type=fact_type,
                    value=val_str,
                    source_collection=coll_name,
                    source_record_id=r["_id"],
                    source_field=code_field
                ))
            return output

        # Fetch entities
        conditions = fetch_clinical_records("patient_conditions", "diagnosis", "diagnosis_code")
        procedures = fetch_clinical_records("patient_procedures", "procedure", "procedure_code")
        medications = fetch_clinical_records("patient_medications", "medication", "medication_name")
        diagnostic_results = fetch_clinical_records("diagnostic_results", "lab_result", "test_name")
        vital_signs = fetch_clinical_records("vital_signs", "vital_sign", "vital_type")
        allergies = fetch_clinical_records("allergies", "allergy", "allergen_name")
        care_plans = fetch_clinical_records("care_plans", "care_plan", "current_treatment_plan")
        surgeries = fetch_clinical_records("surgeries", "surgery", "surgery_type")
        functional_status = fetch_clinical_records("functional_status", "functional_status", "physical_functional_status")
        clinical_assessments = fetch_clinical_records("clinical_assessments", "clinical_assessment", "assessment_type")
        family_history = fetch_clinical_records("family_history", "family_history", "condition")
        referrals = fetch_clinical_records("referrals", "referral", "specialty_required")
        encounters = fetch_clinical_records("encounters", "encounter", "encounter_type")
        medical_equipment = fetch_clinical_records("medical_equipment", "medical_equipment", "equipment_type")
        social_history = fetch_clinical_records("social_history", "social_history", " smoking_status") # space checking
        if not social_history:
            # Fall back to strip key
            social_history = fetch_clinical_records("social_history", "social_history", "smoking_status")

        # 5. Extract Free Text Narratives and append provenance
        clinical_text_blocks = []
        for field in ["clinical_indication", "medical_necessity", "provider_justification", "previous_treatment_info"]:
            text_val = req_doc.get(field, "")
            if text_val:
                clinical_text_blocks.append({
                    "field": field,
                    "text": text_val
                })
                provenance_list.append(EvidenceProvenance(
                    fact_type=field,
                    value=text_val[:60] + "...", # snippet value
                    source_collection="authorization_requests",
                    source_record_id=str(req_doc["_id"]),
                    source_field=field
                ))
                
        # 6. Prior Treatments compilation
        # Combine clinical text descriptions and structured medication records
        prior_treatments = []
        for med in medications:
            prior_treatments.append({
                "treatment_type": "medication",
                "name": med.get("medication_name"),
                "status": med.get("status"),
                "dosage": med.get("dosage"),
                "start_date": med.get("start_date")
            })
        for surg in surgeries:
            prior_treatments.append({
                "treatment_type": "surgery",
                "name": surg.get("surgery_type"),
                "date": surg.get("surgery_date"),
                "outcome": surg.get("surgical_outcome")
            })
            
        # Parse previous treatment info string
        prev_tx_text = req_doc.get("previous_treatment_info", "")
        if prev_tx_text:
            prior_treatments.append({
                "treatment_type": "narrative_reported",
                "description": prev_tx_text
            })

        # 7. Check for Gaps / Missing Information (Do Not Hallucinate)
        if not diagnostic_results:
            missing.append("Diagnostic lab results are completely missing.")
        if not medications:
            missing.append("Prior conservative medication therapy treatments are missing.")
        if not surgeries:
            missing.append("Prior surgical history information is missing.")
            
        # Format requested service
        req_svc_code = req_doc["requested_procedure_code"]["display_value"]
        # Look up procedure name from CPT reference or procedural records
        req_svc_desc = "Requested Procedure"
        # Find description matching code if possible
        ref_proc = db["article_hcpcs"].find_one({"hcpcs_code.canonical_value": req_svc_code})
        if ref_proc:
            req_svc_desc = ref_proc.get("description", "Requested Procedure")
            
        # Get requested diagnosis codes list
        req_diag = req_doc["diagnosis_code"]
        requested_diagnoses = []
        if isinstance(req_diag, list):
            requested_diagnoses = [d["display_value"] for d in req_diag]
        elif isinstance(req_diag, dict) and "display_value" in req_diag:
            requested_diagnoses = [req_diag["display_value"]]
        else:
            requested_diagnoses = [str(req_diag)]

        packet = ClinicalEvidencePacket(
            authorization_id=request_id,
            patient_id=patient_id,
            requested_service={"code": req_svc_code, "description": req_svc_desc},
            diagnosis_codes=requested_diagnoses,
            demographics=demographics,
            conditions=conditions,
            procedures=procedures,
            surgeries=surgeries,
            medications=medications,
            diagnostic_results=diagnostic_results,
            vital_signs=vital_signs,
            clinical_assessments=clinical_assessments,
            functional_status=functional_status,
            allergies=allergies,
            medical_equipment=medical_equipment,
            care_plans=care_plans,
            social_history=social_history,
            family_history=family_history,
            referrals=referrals,
            encounters=encounters,
            prior_treatments=prior_treatments,
            clinical_text=clinical_text_blocks,
            missing_information=missing,
            provenance=provenance_list
        )
        
        return {
            "packet": packet,
            "provider": prov_doc
        }

    @classmethod
    def execute_route_and_retrieve(
        cls,
        request_id: str,
        override_state: Optional[str] = None,
        override_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Runs the combined Prior Auth Intake workflow: compiles evidence, routes, and retrieves policies."""
        db = db_connection.get_db()
        warnings = []
        
        # 1. Compile ClinicalEvidencePacket
        comp_res = cls.compile_evidence_packet(request_id, override_state, override_date)
        packet = comp_res["packet"]
        
        # 2. Geography validation check
        state_code = packet.demographics.get("state_code")
        if not state_code:
            return {
                "authorization_request": cls.get_authorization_request(request_id),
                "clinical_evidence_packet": packet,
                "policy_routing": {
                    "routing_status": "MISSING_ROUTING_GEOGRAPHY",
                    "applicable_ncds": [],
                    "applicable_lcds": [],
                    "candidate_ncds": [],
                    "candidate_lcds": [],
                    "related_articles": [],
                    "warnings": ["Geography state code is missing. Please provide a state code manually."]
                },
                "policy_retrieval": {
                    "results": [],
                    "warnings": ["Skipped retrieval because routing geography state is missing."]
                },
                "warnings": ["MISSING_ROUTING_GEOGRAPHY: Please provide state_code manual override."]
            }
            
        # 3. Resolve Request Dates
        req_doc = db["authorization_requests"].find_one({"request_id": request_id})
        date_val = override_date or req_doc.get("request_date")
        if not date_val:
            date_val = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
        # 4. Build PolicyRoutingRequest
        # Map target HCPCS and first diagnosis code for deterministic Volume 3 lookup
        hcpcs_code = packet.requested_service["code"]
        first_diag = packet.diagnosis_codes[0] if packet.diagnosis_codes else "None"
        
        # Route logic
        routing_request = PolicyRoutingRequest(
            hcpcs_code=hcpcs_code,
            state_code=state_code,
            date_of_service=date_val
        )
        
        # Execute Volume 3 routing
        routing_response = PolicyRoutingService.route_policy(routing_request)
        
        # 5. Extract resolved candidate IDs and call Volume 4 retrieval
        ncd_ids = [n["ncd_id"] for n in routing_response.applicable_ncds] or [n["ncd_id"] for n in routing_response.candidate_ncds]
        lcd_ids = [l["lcd_id"] for l in routing_response.applicable_lcds] or [l["lcd_id"] for l in routing_response.candidate_lcds]
        article_ids = [a["article_id"] for a in routing_response.related_articles]
        
        policy_scope = {
            "ncd_ids": list(set(ncd_ids)),
            "lcd_ids": list(set(lcd_ids)),
            "article_ids": list(set(article_ids))
        }
        
        # Extract specific versions
        document_versions = {}
        for n in (routing_response.applicable_ncds or routing_response.candidate_ncds):
            document_versions[n["ncd_id"]] = n.get("version")
        for l in (routing_response.applicable_lcds or routing_response.candidate_lcds):
            document_versions[l["lcd_id"]] = l.get("version")
        for a in routing_response.related_articles:
            document_versions[a["article_id"]] = a.get("article_version")
            
        # Retrieve chunks (with cosign fallback or Atlas search)
        scope_has_records = any(policy_scope.values())
        unrestricted_flag = not scope_has_records
        
        if unrestricted_flag:
            warnings.append("Resolved policy scope is empty. Executing unrestricted/debug retrieval.")
            
        retrieval_res = PolicyRetrievalService.retrieve_policy_chunks(
            query=f"Coverage requirements, indications, and limitations for service {hcpcs_code} and diagnosis {first_diag}",
            policy_scope=policy_scope,
            document_versions=document_versions,
            top_k=8,
            unrestricted=unrestricted_flag
        )
        
        # Map final results
        warnings.extend(retrieval_res["warnings"])
        warnings.extend(routing_response.warnings)
        
        return {
            "authorization_request": cls.get_authorization_request(request_id),
            "clinical_evidence_packet": packet,
            "policy_routing": routing_response,
            "policy_retrieval": {
                "results": retrieval_res["results"],
                "warnings": retrieval_res["warnings"]
            },
            "warnings": list(set(warnings))
        }
