import json
import re
from typing import List, Dict, Any, Optional
from app.models.evaluation import PolicyRequirement, PatientEvidence, RequirementEvaluation
from app.services.llm import get_llm_provider

class PolicyEvidenceMatcher:
    @classmethod
    def match_evidence(
        cls, 
        requirements: List[PolicyRequirement], 
        evidence_packet: Any
    ) -> List[RequirementEvaluation]:
        """Compares patient evidence from the packet against policy requirements."""
        llm = get_llm_provider()
        
        # 1. Map packet objects to canonical PatientEvidence structures
        evidence_list = cls._compile_patient_evidence(evidence_packet)
        
        # Extra label leakage protection: check and filter out any accidental leakage fields
        leakage_fields = {
            "ai_reasoning", "threshold_met", "step_therapy_requirement_met",
            "necessity_evaluation_support", "duplicate_request_flag",
            "duplicate_service_flag", "status", "claim_status", "authorization_status"
        }
        evidence_list = [
            e for e in evidence_list 
            if not any(lf in e.value.lower() or lf in e.display_value.lower() for lf in leakage_fields)
        ]
        
        evaluations: List[RequirementEvaluation] = []
        
        for req in requirements:
            # First attempt structured matching for simple/explicit requirements
            eval_res = cls._attempt_structured_match(req, evidence_list, evidence_packet)
            
            # If structured matcher is UNCLEAR, attempt semantic/LLM matching for narrative clinical indications
            if eval_res.status == "UNCLEAR" and req.extraction_method in ("LLM", "RULE_OR_LLM"):
                eval_res = cls._attempt_llm_match(req, evidence_list, evidence_packet, llm)
                
            # Enforce safety rule: MET and NOT_MET evaluations must contain patient provenance
            if eval_res.status in ("MET", "NOT_MET") and not eval_res.patient_provenance:
                eval_res.patient_provenance = [{"collection": "authorization_requests", "record_id": evidence_packet.authorization_id}]
                
            evaluations.append(eval_res)
            
        return evaluations

    @classmethod
    def _compile_patient_evidence(cls, packet: Any) -> List[PatientEvidence]:
        """Translates ClinicalEvidencePacket clinical lists into list of PatientEvidence items."""
        evidence = []
        
        # Demographics
        demo = getattr(packet, "demographics", {})
        if "age" in demo:
            evidence.append(PatientEvidence(
                evidence_id="demo_age",
                fact_type="age",
                value=str(demo["age"]),
                display_value=f"Age {demo['age']}",
                source_collection="patients",
                source_record_id=packet.patient_id,
                source_field="age",
                evidence_quality="STRUCTURED"
            ))
            
        # Conditions
        for idx, cond in enumerate(getattr(packet, "conditions", [])):
            diag_node = cond.get("diagnosis_code", {})
            val = diag_node.get("canonical_value", "") if isinstance(diag_node, dict) else str(diag_node)
            disp = diag_node.get("display_value", "") if isinstance(diag_node, dict) else str(diag_node)
            evidence.append(PatientEvidence(
                evidence_id=f"conditions_{idx}",
                fact_type="diagnosis",
                value=val,
                display_value=disp,
                date=cond.get("onset_date") or cond.get("recorded_date"),
                source_collection="patient_conditions",
                source_record_id=cond.get("_id", f"cond_{idx}"),
                source_field="diagnosis_code",
                evidence_quality="STRUCTURED"
            ))
            
        # Medications
        for idx, med in enumerate(getattr(packet, "medications", [])):
            med_node = med.get("medication_code", {})
            val = med_node.get("canonical_value", "") if isinstance(med_node, dict) else med.get("drug_name", "")
            disp = med_node.get("display_value", "") if isinstance(med_node, dict) else med.get("drug_name", "")
            evidence.append(PatientEvidence(
                evidence_id=f"medications_{idx}",
                fact_type="medication",
                value=val,
                display_value=disp,
                date=med.get("start_date"),
                source_collection="patient_medications",
                source_record_id=med.get("_id", f"med_{idx}"),
                source_field="medication_code",
                evidence_quality="STRUCTURED"
            ))
            
        # Procedures
        for idx, proc in enumerate(getattr(packet, "procedures", [])):
            proc_node = proc.get("procedure_code", {})
            val = proc_node.get("canonical_value", "") if isinstance(proc_node, dict) else str(proc_node)
            disp = proc_node.get("display_value", "") if isinstance(proc_node, dict) else str(proc_node)
            evidence.append(PatientEvidence(
                evidence_id=f"procedures_{idx}",
                fact_type="procedure",
                value=val,
                display_value=disp,
                date=proc.get("performed_date") or proc.get("date"),
                source_collection="patient_procedures",
                source_record_id=proc.get("_id", f"proc_{idx}"),
                source_field="procedure_code",
                evidence_quality="STRUCTURED"
            ))
            
        # Surgeries
        for idx, surg in enumerate(getattr(packet, "surgeries", [])):
            surg_node = surg.get("surgery_code", {})
            val = surg_node.get("canonical_value", "") if isinstance(surg_node, dict) else str(surg_node)
            disp = surg_node.get("display_value", "") if isinstance(surg_node, dict) else str(surg_node)
            evidence.append(PatientEvidence(
                evidence_id=f"surgeries_{idx}",
                fact_type="procedure",
                value=val,
                display_value=disp,
                date=surg.get("performed_date") or surg.get("date"),
                source_collection="surgeries",
                source_record_id=surg.get("_id", f"surg_{idx}"),
                source_field="surgery_code",
                evidence_quality="STRUCTURED"
            ))
            
        # Medical Equipment
        for idx, equip in enumerate(getattr(packet, "medical_equipment", [])):
            equip_node = equip.get("equipment_code", {})
            val = equip_node.get("canonical_value", "") if isinstance(equip_node, dict) else str(equip_node)
            disp = equip_node.get("display_value", "") if isinstance(equip_node, dict) else str(equip_node)
            evidence.append(PatientEvidence(
                evidence_id=f"equipment_{idx}",
                fact_type="equipment",
                value=val,
                display_value=disp,
                date=equip.get("supplied_date"),
                source_collection="medical_equipment",
                source_record_id=equip.get("_id", f"equip_{idx}"),
                source_field="equipment_code",
                evidence_quality="STRUCTURED"
            ))

        # Clinical Justification Texts
        for idx, text in enumerate(getattr(packet, "clinical_text", [])):
            val = text.get("value", "")
            field = text.get("source_field", "justification")
            evidence.append(PatientEvidence(
                evidence_id=f"clinical_text_{idx}",
                fact_type="clinical_text",
                value=val,
                display_value=f"Narrative justification: {val[:60]}...",
                source_collection=text.get("source_collection", "authorization_requests"),
                source_record_id=text.get("source_record_id", "auth_req"),
                source_field=field,
                evidence_quality="PROVIDER_REPORTED"
            ))
            
        return evidence

    @classmethod
    def _attempt_structured_match(
        cls, 
        req: PolicyRequirement, 
        evidence_list: List[PatientEvidence],
        packet: Any
    ) -> RequirementEvaluation:
        """Determines clinical met/not_met statuses using clean code/demographic matchers."""
        req_type = req.requirement_type.upper()
        req_text = req.requirement_text.lower()
        
        # 1. DIAGNOSIS Matcher
        if req_type == "DIAGNOSIS":
            # Extract standard codes from requirement text (e.g. M17.11, M1711)
            codes_in_req = re.findall(r'[A-Z]\d{2,4}\.?\d{0,2}', req.requirement_text.upper())
            canonical_req_codes = ["".join(c.split(".")) for c in codes_in_req]
            
            matched = []
            for e in evidence_list:
                if e.fact_type == "diagnosis":
                    norm_val = "".join(e.value.split("."))
                    if norm_val in canonical_req_codes or any(c in e.display_value.upper() for c in codes_in_req):
                        matched.append(e)
                        
            if matched:
                return RequirementEvaluation(
                    requirement_id=req.requirement_id,
                    status="MET",
                    policy_requirement=req,
                    matching_evidence=matched,
                    rationale=f"Diagnoses {', '.join(m.value for m in matched)} found in patient condition history.",
                    policy_citation=req.citation,
                    patient_provenance=[{"collection": m.source_collection, "record_id": m.source_record_id} for m in matched]
                )
                
        # 2. AGE Matcher
        elif req_type == "AGE":
            # Extract age number and comparator
            num_match = re.search(r'\d+', req_text)
            if num_match:
                target_age = int(num_match.group())
                patient_age_ev = next((e for e in evidence_list if e.fact_type == "age"), None)
                if patient_age_ev:
                    patient_age = int(patient_age_ev.value)
                    
                    is_greater = ">=" in req_text or "greater" in req_text or "older" in req_text or "at least" in req_text
                    is_less = "<=" in req_text or "less" in req_text or "younger" in req_text or "under" in req_text
                    
                    met = False
                    if is_greater and patient_age >= target_age:
                        met = True
                    elif is_less and patient_age <= target_age:
                        met = True
                    elif not is_greater and not is_less and patient_age == target_age:
                        met = True
                        
                    if met:
                        return RequirementEvaluation(
                            requirement_id=req.requirement_id,
                            status="MET",
                            policy_requirement=req,
                            matching_evidence=[patient_age_ev],
                            rationale=f"Patient age ({patient_age}) satisfies the policy age requirement ({req.requirement_text}).",
                            policy_citation=req.citation,
                            patient_provenance=[{"collection": patient_age_ev.source_collection, "record_id": patient_age_ev.source_record_id}]
                        )
                    else:
                        return RequirementEvaluation(
                            requirement_id=req.requirement_id,
                            status="NOT_MET",
                            policy_requirement=req,
                            contradicting_evidence=[patient_age_ev],
                            rationale=f"Patient age ({patient_age}) does not satisfy the policy age requirement ({req.requirement_text}).",
                            policy_citation=req.citation,
                            patient_provenance=[{"collection": patient_age_ev.source_collection, "record_id": patient_age_ev.source_record_id}]
                        )
                        
        # 3. DURATION Check (e.g. failure of treatment for X months)
        elif req_type == "DURATION" or "duration" in req_text:
            # Check justification text or previous treatment durations
            # Look at authorization request fields
            duration_days = getattr(packet, "duration", None)
            if duration_days is not None:
                # Compare numeric months
                num_match = re.search(r'(\d+)\s+month', req_text)
                if num_match:
                    req_months = int(num_match.group(1))
                    patient_months = duration_days / 30.0
                    
                    if patient_months >= req_months:
                        return RequirementEvaluation(
                            requirement_id=req.requirement_id,
                            status="MET",
                            policy_requirement=req,
                            matching_evidence=[],
                            rationale=f"Requested duration {patient_months:.1f} months satisfies required {req_months} months.",
                            policy_citation=req.citation
                        )
                    else:
                        return RequirementEvaluation(
                            requirement_id=req.requirement_id,
                            status="NOT_MET",
                            policy_requirement=req,
                            rationale=f"Requested duration {patient_months:.1f} months is less than required {req_months} months.",
                            policy_citation=req.citation
                        )
                        
        # Default fallback to UNCLEAR for structured evaluation, proceeding to LLM semantic match if needed
        return RequirementEvaluation(
            requirement_id=req.requirement_id,
            status="UNCLEAR",
            policy_requirement=req,
            matching_evidence=[],
            rationale="Structured code matching could not definitively evaluate this requirement.",
            policy_citation=req.citation
        )

    @classmethod
    def _attempt_llm_match(
        cls, 
        req: PolicyRequirement, 
        evidence_list: List[PatientEvidence], 
        packet: Any,
        llm: Any
    ) -> RequirementEvaluation:
        """Runs a controlled LLM semantic matching prompt comparing a single clinical requirement with patient justification texts."""
        # 1. Compile relevant patient evidence descriptions
        patient_texts = []
        for ev in evidence_list:
            if ev.fact_type == "clinical_text":
                patient_texts.append(f"Justification ({ev.source_field}): \"{ev.value}\" [ID: {ev.evidence_id}]")
            elif ev.fact_type in ("medication", "procedure", "diagnosis"):
                patient_texts.append(f"Clinical record ({ev.fact_type}): {ev.display_value} ({ev.value}) [ID: {ev.evidence_id}]")
                
        evidence_context = "\n".join(patient_texts)
        
        system_prompt = (
            "You are a medical policy auditor. Compare the single provided clinical requirement with the patient evidence list.\n\n"
            "Safety Constraints:\n"
            "1. Do not use outside medical knowledge. Only match if the evidence text directly supports the requirement.\n"
            "2. Do not use outcome labels or assume authorization decisions.\n"
            "3. If evidence is absent, incomplete, or insufficient, you MUST return status 'UNCLEAR'. Do not automatically mark it as 'NOT_MET' unless the text explicitly contradicts it.\n"
            "4. Return matched and contradicting evidence IDs from the provided evidence list.\n"
            "5. Do not invent details or assume treatments occurred if they are not explicitly documented.\n\n"
            "Return a JSON object matching this schema:\n"
            "{\n"
            "  \"status\": \"MET / NOT_MET / UNCLEAR / NOT_APPLICABLE\",\n"
            "  \"matching_evidence_ids\": [\"evidence_id_1\"],\n"
            "  \"contradicting_evidence_ids\": [],\n"
            "  \"missing_information\": [\"what specific report or test is missing if UNCLEAR\"],\n"
            "  \"rationale\": \"explain match details exactly quoting evidence\"\n"
            "}"
        )
        
        user_prompt = (
            f"Policy Requirement:\n\"{req.requirement_text}\" [Type: {req.requirement_type}]\n\n"
            f"Patient Evidence:\n{evidence_context}\n"
        )
        
        try:
            raw_res = llm.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_mode=True,
                temperature=0.0
            )
            data = json.loads(raw_res)
            
            status = data.get("status", "UNCLEAR").upper()
            if status not in ("MET", "NOT_MET", "UNCLEAR", "NOT_APPLICABLE"):
                status = "UNCLEAR"
                
            match_ids = data.get("matching_evidence_ids", [])
            contra_ids = data.get("contradicting_evidence_ids", [])
            
            matching_ev = [e for e in evidence_list if e.evidence_id in match_ids]
            contradicting_ev = [e for e in evidence_list if e.evidence_id in contra_ids]
            
            return RequirementEvaluation(
                requirement_id=req.requirement_id,
                status=status,
                policy_requirement=req,
                matching_evidence=matching_ev,
                contradicting_evidence=contradicting_ev,
                missing_information=data.get("missing_information", []),
                rationale=data.get("rationale", "Semantic matching completed."),
                policy_citation=req.citation,
                patient_provenance=[{"collection": m.source_collection, "record_id": m.source_record_id} for m in matching_ev]
            )
            
        except Exception as e:
            return RequirementEvaluation(
                requirement_id=req.requirement_id,
                status="UNCLEAR",
                policy_requirement=req,
                matching_evidence=[],
                contradicting_evidence=[],
                missing_information=[f"LLM semantic matching failed: {str(e)}"],
                rationale=f"LLM match error: {str(e)}",
                policy_citation=req.citation
            )
