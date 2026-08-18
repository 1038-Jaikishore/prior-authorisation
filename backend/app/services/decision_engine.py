import json
import os
import requests
from typing import Optional
from app.models.decision import (
    NCDSemanticEvaluationResult,
    LCDSemanticEvaluationResult,
    ArticleSemanticEvaluationResult,
    Phase7DecisionOutput
)
from app.models.patient import ClinicalEvidencePacket

class ConfidenceDecisionEngine:
    @staticmethod
    def compute_decision(
        clinical_evidence: ClinicalEvidencePacket,
        ncd_decision: Optional[NCDSemanticEvaluationResult],
        lcd_decision: Optional[LCDSemanticEvaluationResult],
        article_decision: Optional[ArticleSemanticEvaluationResult]
    ) -> Phase7DecisionOutput:
        
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY is not set in environment.")

        # Prepare Payload
        payload = {
            "ncd_determination": ncd_decision.ncd_determination if ncd_decision else "NOT EVALUATED",
            "ncd_reasoning": ncd_decision.reasoning if ncd_decision else "",
            "lcd_determination": lcd_decision.lcd_determination if lcd_decision else "NOT EVALUATED",
            "lcd_reasoning": lcd_decision.reasoning if lcd_decision else "",
            "article_determination": article_decision.article_determination if article_decision else "NOT EVALUATED",
            "article_reasoning": article_decision.reasoning if article_decision else "",
            "validation_checklist": article_decision.validation_checklist.dict() if article_decision else {},
            "ncd_pathways": [p.dict() for p in ncd_decision.pathways_evaluated] if ncd_decision and ncd_decision.pathways_evaluated else [],
            "lcd_pathways": [p.dict() for p in lcd_decision.pathways_evaluated] if lcd_decision and lcd_decision.pathways_evaluated else []
        }

        system_prompt = """You are the Phase 7 Confidence & Decision Engine for a Medicare Prior Authorization pipeline.
Your job is to aggregate the outputs from the NCD (National), LCD (Local), and Article (Administrative) engines to make a deterministic final decision.

You must output a raw JSON object matching exactly this structure:
{
  "overall_confidence_score": 0.0,
  "evidence_summary": "A brief summary of the clinical and administrative evidence provided.",
  "gap_analysis": "What evidence or coding is missing or contradictory (if applicable).",
  "recommendation": "APPROVE" | "DENY" | "PEND" | "NURSE_REVIEW"
}

Decision Rules:
1. Distinguish between FAILED requirements and MISSING evidence:
   - FAILED: The EHR contains evidence that directly violates an applicable coverage threshold or exclusion.
   - MISSING: A mandatory clinical test, document, or data point required by the policy is simply not present in the EHR.
2. If the OVERALL determination for ANY policy (NCD, LCD, or Article) is explicitly 'NOT COVERED', output DENY.
3. If all applicable policies return 'COVERED' (and administrative validation passes), output APPROVE.
4. If ANY policy is 'NOT ADDRESSED' due to an AMBIGUOUS pathway, output NURSE_REVIEW.
5. If ANY policy is 'NOT ADDRESSED' due to a MISSING pathway (and there is no AMBIGUOUS pathway), output PEND.
6. NEVER output DENY if there is an AMBIGUOUS or MISSING pathway that caused the policy to be 'NOT ADDRESSED'. Do NOT output DENY just because an alternative pathway (like Group I) failed, if another pathway (like Group II) is AMBIGUOUS or MISSING.
7. Any required administrative validation FAIL (e.g., ICD-10-CM FAIL) that strictly prevents coverage should result in DENY.
8. Output ONLY valid, parsable JSON without markdown wrappers."""

        user_prompt = f"""### PHASE 4, 5, 6 DETERMINATIONS & REASONING ###
{json.dumps(payload, indent=2)}

Please compute the final Phase 7 decision based on the above rules.
"""

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
            
            if llm_output.startswith("```json"):
                llm_output = llm_output.strip("```json").strip("```").strip()
                
            parsed_data = json.loads(llm_output)
            return Phase7DecisionOutput(**parsed_data)
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate Phase 7 output: {str(e)}")
