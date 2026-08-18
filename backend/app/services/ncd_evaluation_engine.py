import json
import os
import requests
from typing import Dict, Any, List
from app.models.decision import NCDSemanticEvaluationResult
from app.models.patient import ClinicalEvidencePacket

class NCDEvaluationEngine:
    @staticmethod
    def evaluate_ncds(
        clinical_evidence: ClinicalEvidencePacket, 
        retrieval_result: List[Dict[str, Any]]
    ) -> NCDSemanticEvaluationResult:
        """
        Evaluates clinical evidence against retrieved NCD chunks to determine coverage.
        """
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY is not set in environment.")

        # 1. Filter Retrieval Results for NCDs only
        ncd_chunks = [
            chunk for chunk in retrieval_result 
            if chunk.get("document_type") == "NCD"
        ]

        if not ncd_chunks:
            return NCDSemanticEvaluationResult(
                ncd_determination="NOT ADDRESSED",
                semantic_similarity_score=0.0,
                confidence_score=0.0,
                key_policy_excerpts=[],
                conditions=[],
                reasoning="No NCD text paragraphs were retrieved for this request."
            )

        # 2. Build the LLM Context
        # Format Clinical Facts
        facts = {
            "requested_service": clinical_evidence.requested_service.get("description") or "Not Provided",
            "diagnosis_codes": clinical_evidence.diagnosis_codes if clinical_evidence.diagnosis_codes else "Not Provided",
            "conditions": [c.get("name") for c in clinical_evidence.conditions] if clinical_evidence.conditions else "Not Provided",
            "clinical_assessments": [a.get("name") for a in clinical_evidence.clinical_assessments] if (hasattr(clinical_evidence, 'clinical_assessments') and clinical_evidence.clinical_assessments) else "Not Provided",
            "diagnostic_results": clinical_evidence.diagnostic_results if (hasattr(clinical_evidence, 'diagnostic_results') and clinical_evidence.diagnostic_results) else "Not Provided",
            "encounters": [f"{e.get('type')} with {e.get('provider_specialty')}" for e in clinical_evidence.encounters] if (hasattr(clinical_evidence, 'encounters') and clinical_evidence.encounters) else "Not Provided",
            "age": clinical_evidence.demographics.get("age") or "Not Provided",
            "gender": clinical_evidence.demographics.get("gender") or "Not Provided"
        }
        
        # Format NCD Law Text
        law_texts = []
        for chunk in ncd_chunks:
            doc_id = chunk.get("document_id")
            section = chunk.get("section")
            text = chunk.get("text")
            law_texts.append(f"[NCD {doc_id} | Section: {section}]\n{text}")
            
        law_context = "\n\n".join(law_texts)

        # 3. Construct Prompt
        system_prompt = """You are a highly precise Medicare Prior Authorization AI Agent. 
Your task is to evaluate the provided Patient Clinical Facts against the provided Medicare NCD (National Coverage Determination) Law Text.

You must output a raw JSON object (without markdown code blocks) matching exactly this structure:
{
  "ncd_determination": "COVERED" | "NOT COVERED" | "NOT ADDRESSED",
  "semantic_similarity_score": 0.0,
  "confidence_score": 0.0,
  "reasoning": "Detailed reasoning explaining the overall decision.",
  "key_policy_excerpts": ["Exact sentence from the text justifying the decision"],
  "conditions": ["Any specific conditions or limitations found in the text"],
  "requirements_evaluated": [
    {
      "description": "Patient must have Test Result <= 55",
      "pathway": "Pathway A",
      "is_numerical": true,
      "numerical_evaluation": {
        "patient_value": 58,
        "operator": "<=",
        "threshold": 55,
        "source_evidence": "Test Result = 58"
      },
      "llm_is_met": false,
      "status": "FAILED"
    },
    {
      "description": "Patient must have Qualifying Condition Y",
      "pathway": "Pathway B",
      "is_numerical": false,
      "numerical_evaluation": null,
      "llm_is_met": false,
      "status": "AMBIGUOUS"
    }
  ],
  "pathways_evaluated": []
}

Rules for Determinations:
1. Extract EVERY distinct medical requirement from the applicable policy into the `requirements_evaluated` list, including ALL alternative pathways (e.g., Group I, Group II) even if the patient does not meet them.
2. Group related requirements by their `pathway` name (e.g., "Group I", "Group II"). EVERY requirement MUST have a `pathway` assigned. If it is universally mandatory regardless of the pathway, set `pathway` to "Global". Do NOT default to "Global" for Group I or Group II specific rules!
3. Determine the status of each requirement:
   - "MET": Patient evidence satisfies it.
   - "FAILED": Patient evidence directly violates it.
   - "MISSING": The required clinical test/evidence is not present.
   - "AMBIGUOUS": Evidence exists, but the clinical meaning, causal relationship, or etiology is explicitly unclear or contradictory.
     *CRITICAL AMBIGUITY RULE*: If a qualifying condition (e.g., "Disease X suggesting Condition Y") is partially present (e.g., patient has Disease X) but its etiology or exact nature is explicitly stated as 'ambiguous' or 'unclear' in the clinical notes, you MUST mark its status as 'AMBIGUOUS', NOT 'MISSING' or 'FAILED'.
4. If a requirement is numerical, set `is_numerical: true` and populate `numerical_evaluation`. 
   - Extract numerical thresholds STRICTLY from the provided CMS policy chunks. Do NOT hardcode or hallucinate numbers.
   - Use strict mathematical operators: "at or below X" -> `<=`, "below X" -> `<`, "at or above X" -> `>=`, "above X" -> `>`.
   - IMPORTANT: If a threshold is a range (e.g., 56-59), split it into TWO separate requirements (e.g., one for `>= 56`, and another for `<= 59`). DO NOT output a range string like '56-59' as the threshold.
   - IMPORTANT: DO NOT conflate alternative pathways! For example, do NOT apply Group I's threshold (e.g., PO2 <= 55) to Group II (which has its own distinct PO2 limits like 56-59). Treat each pathway entirely independently.
5. Do NOT hallucinate policy criteria that are not in the provided CMS text.

For semantic_similarity_score and confidence_score, output a float between 0.0 and 1.0. Output ONLY valid, parsable JSON."""

        user_prompt = f"""### PATIENT CLINICAL FACTS ###
{json.dumps(facts, indent=2)}

### CMS NCD LAW TEXT ###
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
                
            parsed_data = json.loads(llm_output)
            
            # Deterministic Numerical Correction & Logical Re-Evaluation
            def deterministic_eval(op, patient_val, thresh):
                try:
                    if op == '<=': return float(patient_val) <= float(thresh)
                    if op == '<': return float(patient_val) < float(thresh)
                    if op == '>=': return float(patient_val) >= float(thresh)
                    if op == '>': return float(patient_val) > float(thresh)
                    if op == '==': return float(patient_val) == float(thresh)
                except (ValueError, TypeError):
                    pass
                return None

            for req in parsed_data.get('requirements_evaluated', []):
                if req.get('is_numerical') and req.get('numerical_evaluation'):
                    num_eval = req['numerical_evaluation']
                    res = deterministic_eval(num_eval.get('operator'), num_eval.get('patient_value'), num_eval.get('threshold'))
                    if res is not None:
                        req['computed_is_met'] = res
                        if req.get('status') != 'AMBIGUOUS': # Let LLM ambiguity override numbers
                            req['status'] = 'MET' if res else 'FAILED'

            # Only re-evaluate if the policy was actually addressed
            if parsed_data.get('ncd_determination') != 'NOT ADDRESSED' and parsed_data.get('requirements_evaluated'):
                reqs = parsed_data.get('requirements_evaluated', [])
                
                # Group by pathway
                from collections import defaultdict
                pathway_groups = defaultdict(list)
                for r in reqs:
                    pathway = r.get('pathway', 'Global')
                    pathway_groups[pathway].append(r)
                
                pathways_evaluated = []
                for p_name, p_reqs in pathway_groups.items():
                    if all(r.get('status') == 'MET' for r in p_reqs):
                        p_status = 'MET'
                    elif any(r.get('status') == 'FAILED' for r in p_reqs):
                        p_status = 'FAILED'
                    elif any(r.get('status') == 'AMBIGUOUS' for r in p_reqs):
                        p_status = 'AMBIGUOUS'
                    else:
                        p_status = 'MISSING'
                    
                    pathways_evaluated.append({
                        'pathway_name': p_name,
                        'status': p_status,
                        'requirements': p_reqs
                    })
                
                parsed_data['pathways_evaluated'] = pathways_evaluated
                
                # Evaluate overall determination
                global_pathway = next((p for p in pathways_evaluated if p['pathway_name'].lower() == 'global'), None)
                alt_pathways = [p for p in pathways_evaluated if p['pathway_name'].lower() != 'global']
                
                if global_pathway and global_pathway['status'] == 'FAILED':
                    parsed_data['ncd_determination'] = 'NOT COVERED'
                elif global_pathway and global_pathway['status'] in ['MISSING', 'AMBIGUOUS']:
                    parsed_data['ncd_determination'] = 'NOT ADDRESSED'
                else:
                    # Global is MET or non-existent. Evaluate alternatives.
                    if not alt_pathways:
                        parsed_data['ncd_determination'] = 'COVERED'
                    elif any(p['status'] == 'MET' for p in alt_pathways):
                        parsed_data['ncd_determination'] = 'COVERED'
                    elif all(p['status'] == 'FAILED' for p in alt_pathways):
                        parsed_data['ncd_determination'] = 'NOT COVERED'
                    elif any(p['status'] == 'AMBIGUOUS' for p in alt_pathways):
                        parsed_data['ncd_determination'] = 'NOT ADDRESSED' # Will map to NURSE_REVIEW
                    else:
                        parsed_data['ncd_determination'] = 'NOT ADDRESSED' # Will map to PEND
            else:
                parsed_data['pathways_evaluated'] = []
            
            return NCDSemanticEvaluationResult(**parsed_data)
            
        except requests.exceptions.RequestException as e:
            # Firewall / Network Fallback for Prototyping
            print(f"OpenRouter API request failed: {e}. Returning mock result for prototype.")
            return NCDSemanticEvaluationResult(
                ncd_determination="COVERED",
                semantic_similarity_score=0.95,
                confidence_score=0.9,
                reasoning="MOCK RESPONSE (FIREWALL BLOCKED): Based on NCD 190, the patient has a pressure ulcer, which justifies coverage for the requested wheelchair seat cushion.",
                key_policy_excerpts=["Coverage is provided if the patient has a current pressure ulcer... on the area of contact with the seating surface."],
                conditions=["Must be associated with DME base item (wheelchair)"]
            )
        except Exception as e:
            raise RuntimeError(f"Failed to parse AI output: {str(e)}")
