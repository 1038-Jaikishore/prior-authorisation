import json
import os
import requests
from typing import Dict, Any, List
from app.models.decision import ArticleSemanticEvaluationResult
from app.models.patient import ClinicalEvidencePacket

class ArticleEvaluationEngine:
    @staticmethod
    def evaluate_articles(
        clinical_evidence: ClinicalEvidencePacket, 
        retrieval_result: List[Dict[str, Any]]
    ) -> ArticleSemanticEvaluationResult:
        """
        Evaluates clinical evidence against retrieved Billing & Coding Article chunks.
        Strict deterministic parsing of ICD-10 and HCPCS/CPT codes.
        """
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY is not set in environment.")

        # 1. Filter Retrieval Results for Articles only
        article_chunks = [
            chunk for chunk in retrieval_result 
            if chunk.get("document_type") == "ARTICLE"
        ]

        if not article_chunks:
            return ArticleSemanticEvaluationResult(
                article_determination="NOT ADDRESSED",
                administrative_match_score=0.0,
                validation_checklist={
                    "icd_10_cm": "NOT_APPLICABLE",
                    "icd_10_pcs": "NOT_APPLICABLE",
                    "cpt_hcpcs": "NOT_APPLICABLE",
                    "modifiers": "NOT_APPLICABLE",
                    "revenue_codes": "NOT_APPLICABLE",
                    "coding_rules": "NOT_APPLICABLE"
                },
                key_policy_excerpts=[],
                matching_codes=[],
                reasoning="No Billing & Coding Article paragraphs were retrieved for this request."
            )

        # 2. Build the LLM Context
        # Format Clinical Facts (Focus heavily on codes)
        facts = {
            "requested_service_code": clinical_evidence.requested_service.get("code") or "Not Provided",
            "requested_service_desc": clinical_evidence.requested_service.get("description") or "Not Provided",
            "diagnosis_codes_icd_10_cm": clinical_evidence.diagnosis_codes if clinical_evidence.diagnosis_codes else [],
            "procedure_codes_icd_10_pcs": clinical_evidence.icd_10_pcs_codes if (hasattr(clinical_evidence, 'icd_10_pcs_codes') and clinical_evidence.icd_10_pcs_codes) else [],
            "modifiers": clinical_evidence.modifiers if clinical_evidence.modifiers else [],
            "revenue_codes": clinical_evidence.revenue_codes if clinical_evidence.revenue_codes else [],
            "patient_age": clinical_evidence.demographics.get("age") or "Not Provided",
            "patient_gender": clinical_evidence.demographics.get("gender") or "Not Provided"
        }
        
        # Format Article Law Text
        law_texts = []
        for chunk in article_chunks:
            doc_id = chunk.get("document_id")
            section = chunk.get("section")
            text = chunk.get("text")
            law_texts.append(f"[ARTICLE {doc_id} | Section: {section}]\n{text}")
            
        law_context = "\n\n".join(law_texts)

        # 3. Construct Prompt
        system_prompt = """You are a highly precise Medicare Prior Authorization AI Agent performing Phase 6 Administrative Validation.
Your task is to compare the Patient's facts against the provided CMS Billing & Coding Article Text. 

You must perform ALL 6 of the following Deterministic Validation Checks:
1. Validate ICD-10-CM codes (Diagnosis)
2. Validate ICD-10-PCS codes (Inpatient Procedures - if applicable)
3. Validate CPT/HCPCS codes (Service Code)
4. Validate Modifiers & Modifier groups
5. Validate Revenue & Bill codes
6. Check Coding Rules & Dependencies (e.g., Age/Gender conflicts, mutually exclusive codes)

Output a JSON object exactly matching this structure:
{
  "article_determination": "COVERED" | "NOT COVERED" | "NOT ADDRESSED",
  "administrative_match_score": 0.0,
  "validation_checklist": {
    "icd_10_cm": "PASS" | "FAIL" | "NOT_APPLICABLE",
    "icd_10_pcs": "PASS" | "FAIL" | "NOT_APPLICABLE",
    "cpt_hcpcs": "PASS" | "FAIL" | "NOT_APPLICABLE",
    "modifiers": "PASS" | "FAIL" | "NOT_APPLICABLE",
    "revenue_codes": "PASS" | "FAIL" | "NOT_APPLICABLE",
    "coding_rules": "PASS" | "FAIL" | "NOT_APPLICABLE"
  },
  "matching_codes": ["List of the exact patient codes that matched lists or rules in the text"],
  "mismatched_codes": ["List of the exact patient codes that caused a FAIL condition, if any"],
  "key_policy_excerpts": ["Exact sentence from the text justifying the decision"],
  "reasoning": "A short paragraph explaining the decision based strictly on the 6 deterministic checks."
}

Rules:
1. ONLY use the provided Article Text. Do not use outside knowledge.
2. Look specifically for lists like "ICD-10 Codes that Support Medical Necessity" (Covered) or "ICD-10 Codes that DO NOT Support Medical Necessity" (Non-Covered).
3. **COVERED**: If the patient's exact diagnosis code, procedure code, or modifier is explicitly listed in a "Covered" or "Supports Medical Necessity" section, AND there are no Coding Rule violations (e.g. wrong age/gender), output COVERED.
4. **NOT COVERED**: If the patient's code is explicitly listed in a "Non-Covered" section, OR if there is a Coding Rule violation (e.g. code is only for females, but patient is male), you MUST output NOT COVERED.
5. **NOT ADDRESSED**: If the patient's codes are NOT mentioned anywhere in the text, or the text does not contain explicit covered/non-covered code lists related to the patient's codes, output NOT ADDRESSED.
7. CRITICAL INSTRUCTION: For every field in the `validation_checklist`, you MUST ONLY output the exact string "PASS", "FAIL", or "NOT_APPLICABLE". Do NOT output "NOT ADDRESSED", "UNKNOWN", or any other variations. If you cannot determine, output "NOT_APPLICABLE".
8. `administrative_match_score` must be a float between 0.0 and 1.0 representing the proportion of PASS/NOT_APPLICABLE items out of 6 (e.g., if 1 fails, score is 0.83).
9. Output ONLY valid, parsable JSON. No other text."""

        user_prompt = f"""### PATIENT BILLING/CODING FACTS ###
{json.dumps(facts, indent=2)}

### CMS ARTICLE TEXT ###
{law_context}
"""

        # 4. Call OpenRouter LLM
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openai/gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.0
                },
                timeout=30
            )
            response.raise_for_status()
            llm_output = response.json()["choices"][0]["message"]["content"]
            
            # Clean possible markdown formatting
            if llm_output.startswith("```json"):
                llm_output = llm_output.strip("```json").strip("```").strip()
                
            # Clean up LLM missing the underscore for enum compliance
            llm_output = llm_output.replace('"NOT APPLICABLE"', '"NOT_APPLICABLE"')
                
            parsed_data = json.loads(llm_output)
            
            return ArticleSemanticEvaluationResult(**parsed_data)
            
        except Exception as e:
            raise RuntimeError(f"Failed to parse AI output: {str(e)}")
