import json
import re
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.core.config import settings

class LLMProvider(ABC):
    @abstractmethod
    def generate_completion(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        json_mode: bool = False, 
        temperature: float = 0.0
    ) -> str:
        """Generates a text completion from the LLM model."""
        pass

class MockLLMProvider(LLMProvider):
    def generate_completion(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        json_mode: bool = False, 
        temperature: float = 0.0
    ) -> str:
        # Check if the prompt is for clinical document extraction
        if "clinical_document_extraction_v1" in system_prompt or "extraction" in system_prompt.lower():
            # Isolate the document text between page boundaries to avoid schema keyword clashes
            matches = re.findall(r"--- START OF PAGE \d+ ---\n(.*?)\n--- END OF PAGE \d+ ---", user_prompt, re.DOTALL)
            doc_text = "\n".join(matches).lower() if matches else user_prompt.lower()
            
            name = "John Doe"
            dob = "1970-05-15"
            age = 56
            gender = "male"
            cpt = "97110"
            state = "CO"
            icd = "M17.11"
            icd_status = "DOCUMENTED"
            failed_treatments = [{"treatment_type": "physical_therapy", "name": "Treatment B", "failed": True, "duration": "1 month"}]
            referral = "referred for therapy services by a physician"
            
            if "notmet" in doc_text or "not_met" in doc_text or "age: 52" in doc_text or "age = 52" in doc_text:
                name = "TXT NotMet Patient"
                dob = "1974-08-10"
                age = 52
                cpt = "97110"
                state = "CO"
                icd = "M17.11"
            elif "approve-like" in doc_text or "docx approve" in doc_text or "complete_approve" in doc_text or "conservative treatment b failed after 6" in doc_text:
                name = "DOCX Approve Patient"
                dob = "1954-03-20"
                age = 72
                cpt = "97110"
                state = "CO"
                icd = "M17.11"
                failed_treatments = [{"treatment_type": "physical_therapy", "name": "Conservative treatment B", "failed": True, "duration": "6 months"}]
            elif "absent fields" in doc_text or "absent" in doc_text:
                name = "Missing Params Patient"
                cpt = None
                state = None
                icd = "M17.11"
            elif "approved" in doc_text or "leakage" in doc_text or "meets policy" in doc_text:
                name = "Leakage Protected Patient"
                cpt = "97110"
                state = "CO"
                icd = "M17.11"
            elif "conflict" in doc_text or "dob: 1955" in doc_text:
                name = "Conflicting Patient"
                dob = "1955-03-20"
                cpt = "97110"
                state = "CO"
                icd = "M17.11"
            elif "osteoarthritis" in doc_text and "m17.11" not in doc_text:
                icd = None
                icd_status = "NOT_DOCUMENTED"
                
            return json.dumps({
                "patient": {
                    "name": name,
                    "dob": dob,
                    "age": age,
                    "gender": gender
                },
                "requested_service": {
                    "code": cpt,
                    "code_system": "CPT",
                    "description": "Therapeutic exercises" if cpt == "97110" else None
                },
                "diagnoses": [
                    {
                        "code": icd,
                        "code_system": "ICD-10-CM",
                        "description": "Osteoarthritis of knee" if icd else "Osteoarthritis of right knee",
                        "code_status": icd_status
                    }
                ],
                "prior_treatments": failed_treatments,
                "diagnostic_results": [],
                "clinical_indication": "Knee pain and stiffness",
                "provider_justification": referral,
                "provider": {
                    "name": "Dr. Smith",
                    "provider_type": "MD",
                    "facility": "Denver Medical Center",
                    "npi": "1234567890"
                },
                "geography": {
                    "state": state,
                    "zip": "80202"
                },
                "missing_fields": [],
                "provenance_records": [
                    {
                        "fact_type": "requested_procedure_code",
                        "value": cpt if cpt else "not_documented",
                        "page_number": 1,
                        "source_text": f"Requested therapy: {cpt}" if cpt else "Requested therapy"
                    },
                    {
                        "fact_type": "diagnosis_code",
                        "value": icd if icd else "Osteoarthritis",
                        "page_number": 1,
                        "source_text": "Diagnosis: Osteoarthritis right knee"
                    }
                ]
            })

        # Check if the prompt is for requirement extraction
        if "extract" in system_prompt.lower() or "analyst" in system_prompt.lower():
            # Check keywords in user prompt to return appropriate mock requirements
            if "oximetry" in user_prompt.lower() or "L33405" in user_prompt:
                return json.dumps({
                    "requirements": [
                        {
                            "requirement_text": "Patient has a diagnosis of chronic obstructive pulmonary disease or other respiratory disease",
                            "requirement_type": "DIAGNOSIS",
                            "mandatory": True,
                            "conditional": False,
                            "condition_text": None,
                            "source_quote_fragment": "covered for indications including respiratory disease",
                            "citation": "LCD:L33405:v50:indication:chunk_01"
                        },
                        {
                            "requirement_text": "Patient has failed conservative therapy or is undergoing oxygen titration",
                            "requirement_type": "PRIOR_TREATMENT",
                            "mandatory": True,
                            "conditional": True,
                            "condition_text": "if oxygen titration is not performed",
                            "source_quote_fragment": "titration of oxygen or failure of conservative management",
                            "citation": "LCD:L33405:v50:indication:chunk_02"
                        }
                    ]
                })
            elif "physical therapy" in user_prompt.lower() or "L33942" in user_prompt or "home health" in user_prompt.lower():
                return json.dumps({
                    "requirements": [
                        {
                            "requirement_text": "The patient must be under the care of and referred for therapy services by a physician",
                            "requirement_type": "PROCEDURE",
                            "mandatory": True,
                            "conditional": False,
                            "condition_text": None,
                            "source_quote_fragment": "referred for therapy services by a physician",
                            "citation": "LCD:L33942:v50:indication:chunk_02"
                        },
                        {
                            "requirement_text": "The patient must have a documented diagnosis of joint or musculoskeletal impairment",
                            "requirement_type": "DIAGNOSIS",
                            "mandatory": True,
                            "conditional": False,
                            "condition_text": None,
                            "source_quote_fragment": "rehabilitative therapy for musculoskeletal conditions",
                            "citation": "LCD:L33942:v50:indication:chunk_01"
                        },
                        {
                            "requirement_text": "Patient must show progress and have at least 6 months failed conservative treatment if chronic",
                            "requirement_type": "FAILED_TREATMENT",
                            "mandatory": False,
                            "conditional": True,
                            "condition_text": "if condition is classified as chronic impairment",
                            "source_quote_fragment": "failed conservative management for at least 6 months",
                            "citation": "LCD:L33942:v50:indication:chunk_03"
                        }
                    ]
                })
            else:
                # Default generic mock requirements
                return json.dumps({
                    "requirements": [
                        {
                            "requirement_text": "Patient must have a documented clinical indication supporting the requested service.",
                            "requirement_type": "DIAGNOSIS",
                            "mandatory": True,
                            "conditional": False,
                            "condition_text": None,
                            "source_quote_fragment": "medically necessary indication",
                            "citation": "LCD:L99999:v1:description:chunk_00"
                        }
                    ]
                })
        
        # Check if the prompt is for evidence matching
        elif "compare" in system_prompt.lower() or "auditor" in system_prompt.lower():
            lower_prompt = user_prompt.lower()
            
            # Segment which requirement is being evaluated based on requirement portion of user_prompt
            req_part = lower_prompt.split("patient evidence")[0]
            is_referral = "referred" in req_part or "physician" in req_part or "care of" in req_part
            is_diagnosis = "musculoskeletal" in req_part or "joint" in req_part or "diagnosis of" in req_part
            is_duration = "6 months" in req_part or "failed conservative" in req_part or "conservative treatment" in req_part
            
            if is_referral:
                # Referred by physician - MET
                return json.dumps({
                    "status": "MET",
                    "matching_evidence_ids": ["encounters_0"],
                    "contradicting_evidence_ids": [],
                    "missing_information": [],
                    "rationale": "Patient's encounter record confirms they are under the active care of an oncology specialist physician.",
                    "evidence_quotes": ["Active oncology referral details found in providers/encounters."]
                })
            elif is_diagnosis:
                if "osteoarthritis" in lower_prompt or "m17" in lower_prompt:
                    return json.dumps({
                        "status": "MET",
                        "matching_evidence_ids": ["conditions_0"],
                        "contradicting_evidence_ids": [],
                        "missing_information": [],
                        "rationale": "Patient has a documented diagnosis of Osteoarthritis (M17.11) which is a musculoskeletal condition.",
                        "evidence_quotes": ["M17.11 Osteoarthritis of knee"]
                    })
                else:
                    return json.dumps({
                        "status": "UNCLEAR",
                        "matching_evidence_ids": [],
                        "contradicting_evidence_ids": [],
                        "missing_information": ["Documented musculoskeletal diagnosis is missing."],
                        "rationale": "No musculoskeletal diagnosis is present in patient clinical records.",
                        "evidence_quotes": []
                    })
            elif is_duration:
                if "2 months" in lower_prompt or "1 months" in lower_prompt:
                    # NOT_MET: Patient only has 1 month conservative treatment B
                    return json.dumps({
                        "status": "NOT_MET",
                        "matching_evidence_ids": [],
                        "contradicting_evidence_ids": ["authorization_requests_0"],
                        "missing_information": [],
                        "rationale": "The policy requires 6 months of conservative therapy. The patient's record shows they only received Treatment B for 1 month.",
                        "evidence_quotes": ["Treatment B received for 1 months"]
                    })
                elif "unclear" in lower_prompt or "imaging" in lower_prompt or "mri" in lower_prompt:
                    # UNCLEAR: Missing imaging
                    return json.dumps({
                        "status": "UNCLEAR",
                        "matching_evidence_ids": [],
                        "contradicting_evidence_ids": [],
                        "missing_information": ["Qualifying MRI or diagnostic imaging report confirming structural joint damage."],
                        "rationale": "The requirement mandates diagnostic imaging confirmation, but no diagnostic results or imaging reports are present in the clinical evidence packet.",
                        "evidence_quotes": []
                    })
                else:
                    return json.dumps({
                        "status": "MET",
                        "matching_evidence_ids": ["authorization_requests_0"],
                        "contradicting_evidence_ids": [],
                        "missing_information": [],
                        "rationale": "The patient justification text states conservative treatments have failed.",
                        "evidence_quotes": ["Conservative treatments failed"]
                    })
            else:
                return json.dumps({
                    "status": "UNCLEAR",
                    "matching_evidence_ids": [],
                    "contradicting_evidence_ids": [],
                    "missing_information": ["Documented clinical evidence matching this specific policy requirement."],
                    "rationale": "No matching clinical findings or structured records exist in the patient clinical history.",
                    "evidence_quotes": []
                })

        # Check if the prompt is for decision explanation
        elif "explain" in system_prompt.lower() or "explanation" in system_prompt.lower() or "why" in system_prompt.lower():
            disp = "PEND"
            if "APPROVE" in user_prompt:
                disp = "APPROVE"
            elif "DENY" in user_prompt:
                disp = "DENY"
            elif "NURSE_REVIEW" in user_prompt:
                disp = "NURSE_REVIEW"
            elif "DECISION_SUPPORT_UNAVAILABLE" in user_prompt:
                disp = "DECISION_SUPPORT_UNAVAILABLE"
                
            return json.dumps({
                "decision_id": "DEC_MOCK_123",
                "recommended_disposition": disp,
                "summary": f"Mock synthesis summary explaining recommended disposition: {disp}.",
                "why": [f"Mock reason for triage status {disp}."],
                "satisfied_requirements": ["Physician referral documented.", "Conservative treatment failed documented."],
                "blocking_requirements": ["Musculoskeletal diagnosis not found."] if disp in ("DENY", "PEND") else [],
                "missing_information": ["Clinical documentation confirming joint impairment."] if disp == "PEND" else [],
                "coding_summary": ["CPT 97110 is mapped in companion Article A57311, yielding warning at LCD level but passing at Article level."],
                "policy_summary": ["Governed under Colorado active LCD L33942 and Article A57311."],
                "policy_citations": ["L33942", "A57311"],
                "patient_provenance": [{"collection": "authorization_requests", "record_id": "MOCK_REQ_ID"}]
            })

        return "{}"

class OpenRouterLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "meta-llama/llama-3-8b-instruct:free"):
        self.api_key = api_key
        self.model = model
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def generate_completion(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        json_mode: bool = False, 
        temperature: float = 0.0
    ) -> str:
        if not self.api_key:
            raise ValueError("OpenRouter API key is missing. Please set OPENROUTER_API_KEY in .env")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/1038-Jaikishore/prior-authorisation.git",
            "X-Title": "CMS Prior Auth Decision Support"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=45)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                raise RuntimeError(f"OpenRouter returned error details: {data['error']}")

            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"OpenRouter LLM request failed: {str(e)}")

def get_llm_provider() -> LLMProvider:
    # Read LLM settings or fall back to embedding keys
    provider_name = getattr(settings, "llm_provider", "mock").lower().strip()
    
    if provider_name == "openrouter":
        key = settings.openrouter_api_key or getattr(settings, "llm_api_key", "")
        model = getattr(settings, "llm_model", "meta-llama/llama-3-8b-instruct:free")
        return OpenRouterLLMProvider(api_key=key, model=model)
    else:
        return MockLLMProvider()
