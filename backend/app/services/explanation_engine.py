import json
import os
import requests
from typing import Dict, Any
from app.models.decision import PipelineDecisionResult

class ExplanationEngine:
    @staticmethod
    def generate_explanation(pipeline_result: PipelineDecisionResult) -> str:
        """
        Generates the final Phase 8 markdown explanation based on the exact
        templates for APPROVE, DENY, PEND, and NURSE_REVIEW.
        """
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY is not set in environment.")

        # Serialize the pipeline results to feed to the LLM
        payload_str = pipeline_result.json()
        payload = json.loads(payload_str)
        # Remove the final_explanation field since that's what we are generating
        payload.pop("final_explanation", None)

        rec = payload.get("phase7_decision", {}).get("recommendation", "NURSE_REVIEW")
        
        ncd_det = payload.get("ncd_decision", {}).get("ncd_determination", "NOT EVALUATED") if payload.get("ncd_decision") else "SKIPPED"
        lcd_det = payload.get("lcd_decision", {}).get("lcd_determination", "NOT EVALUATED") if payload.get("lcd_decision") else "SKIPPED"
        
        ncd_pathways = payload.get("ncd_decision", {}).get("pathways_evaluated", []) if payload.get("ncd_decision") else []
        pathway_strs = [f"{p['pathway_name']} -> {p['status']}" for p in ncd_pathways]
        pathway_section = "PATHWAYS EVALUATED:\n" + "\n".join(pathway_strs) if pathway_strs else "PATHWAYS EVALUATED: None"

        policy_eval_section = f"NCD: {ncd_det}\nLCD: {lcd_det}"
        if ncd_det == "NOT COVERED" and lcd_det == "NOT ADDRESSED":
            policy_eval_section = f"NCD: {ncd_det}"

        if rec == "APPROVE":
            template = """--- TEMPLATE: APPROVE ---
FINAL DECISION: APPROVE

DECISION SUMMARY:
[Why the request satisfies the applicable requirements.]

POLICY EVALUATION:
{policy_eval_section}

{pathway_section}

REQUIREMENT ANALYSIS:
- MET: [Requirement met]

PATIENT EVIDENCE:
- [Patient clinical evidence]

POLICY EVIDENCE:
- [Extracted policy text and rule]

ADMINISTRATIVE VALIDATION:
ICD-10-CM: [PASS/FAIL/NOT_APPLICABLE]
CPT/HCPCS: [PASS/FAIL/NOT_APPLICABLE]
Coding Rules: [PASS/FAIL/NOT_APPLICABLE]

POLICY CITATIONS:
- [Actual policy ID + section]

CONFIDENCE:
[Phase 7 Confidence Score]

NEXT STEP:
Authorization may proceed."""
        elif rec == "DENY":
            template = """--- TEMPLATE: DENY ---
FINAL DECISION: DENY

DECISION SUMMARY:
[Why coverage is not satisfied.]

POLICY EVALUATION:
{policy_eval_section}

{pathway_section}

FAILED REQUIREMENT:
[Exact failed requirement.]

PATIENT EVIDENCE:
[Evidence showing requirement was not satisfied.]

POLICY EVIDENCE:
[Exact retrieved policy evidence.]

ADMINISTRATIVE VALIDATION:
ICD-10-CM: [PASS/FAIL/NOT_APPLICABLE]
CPT/HCPCS: [PASS/FAIL/NOT_APPLICABLE]
Coding Rules: [PASS/FAIL/NOT_APPLICABLE]

POLICY CITATIONS:
[Actual NCD/LCD/Article ID + section]

CONFIDENCE:
[Phase 7 Confidence Score]

NEXT STEP:
[Appropriate next step.]"""
        elif rec == "PEND":
            template = """--- TEMPLATE: PEND ---
FINAL DECISION: PEND

DECISION SUMMARY:
Additional information is required to complete the evaluation.

POLICY EVALUATION:
{policy_eval_section}

{pathway_section}

REQUIREMENT ANALYSIS:
- MET: [Requirement met]
- MISSING: [Requirement missing]

MISSING INFORMATION:
1. [Numbered list of missing documents]

WHY IT IS REQUIRED:
[Explain based on actual policy evidence.]

PATIENT EVIDENCE:
[Patient facts provided]

POLICY EVIDENCE:
[Extracted policy text]

POLICY CITATION:
[Actual source ID + section]

ADMINISTRATIVE VALIDATION:
ICD-10-CM: [PASS/FAIL/NOT_APPLICABLE]
CPT/HCPCS: [PASS/FAIL/NOT_APPLICABLE]
Coding Rules: [PASS/FAIL/NOT_APPLICABLE]

CONFIDENCE:
[Phase 7 Confidence Score]

NEXT STEP:
Submit the missing documentation."""
        else:
            template = """--- TEMPLATE: NURSE_REVIEW ---
FINAL DECISION: NURSE_REVIEW

DECISION SUMMARY:
Available evidence is insufficient or ambiguous for reliable automated adjudication.

POLICY EVALUATION:
{policy_eval_section}

{pathway_section}

KEY CLINICAL FINDINGS:
[Summarize complex or unlisted findings]

POLICY REQUIREMENTS:
[Summarize relevant policy limitations]

AREAS REQUIRING CLINICAL REVIEW:
1. [Area requiring review]

SUPPORTING PATIENT EVIDENCE:
[Patient facts provided]

SUPPORTING POLICY EVIDENCE:
[Extracted policy text]

POLICY CITATIONS:
[Relevant Policy IDs]

CONFIDENCE:
[Phase 7 Confidence Score]

REVIEW ACTION:
Route to nurse/medical reviewer for clinical assessment."""

        template = template.format(policy_eval_section=policy_eval_section, pathway_section=pathway_section)

        system_prompt = f"""You are the Phase 8 Explanation Generation Engine for a Medicare Prior Authorization pipeline.
Your job is to read the detailed Pipeline Decision Result (which contains NCD, LCD, Article, and Phase 7 scores) and generate a final markdown formatted summary.

You MUST complete the following template exactly as structured. The NCD and LCD determinations have already been securely populated to prevent hallucinations.
Fill in ONLY the bracketed/placeholder information using the data provided in the payload. Do not invent citations or clinical facts.

CRITICAL RULES AGAINST HALLUCINATION:
1. You MUST NEVER infer the source of a requirement. 
2. Every requirement, missing evidence, and failed criterion you write MUST carry its exact source type and policy ID from the payload.
3. The explanation MUST cite the exact source document ID (NCD/LCD/Article) provided in the structured outputs. If a document ID isn't provided for a specific rule, attribute it to the general "Policy" but never fabricate an NCD/LCD label.

Output ONLY the markdown text. Do not wrap it in JSON.

{template}
"""

        user_prompt = f"""### PIPELINE DECISION RESULT PAYLOAD ###
{json.dumps(payload, indent=2)}
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
            
            # Clean possible markdown formatting from LLM response if it wrapped it
            if llm_output.startswith("```markdown"):
                llm_output = llm_output.strip("```markdown").strip("```").strip()
            elif llm_output.startswith("```"):
                llm_output = llm_output.strip("```").strip()
                
            return llm_output
            
        except requests.exceptions.RequestException as e:
            print(f"OpenRouter API request failed: {e}. Returning mock result for prototype.")
            return f"**[MOCK EXPLANATION - LLM UNAVAILABLE]**\n\n{template}"
        except Exception as e:
            raise RuntimeError(f"Failed to generate Phase 8 Explanation: {str(e)}")
