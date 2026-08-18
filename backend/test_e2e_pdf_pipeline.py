import os
import sys
from dotenv import load_dotenv
load_dotenv()

from app.models.patient import ClinicalEvidencePacket
from app.services.extraction_service import PdfExtractionService
from app.services.ncd_evaluation_engine import NCDEvaluationEngine
from app.services.lcd_evaluation_engine import LCDEvaluationEngine
from app.services.article_evaluation_engine import ArticleEvaluationEngine
from app.services.decision_engine import ConfidenceDecisionEngine
from app.services.explanation_engine import ExplanationEngine
from app.models.decision import PipelineDecisionResult
from app.db.connection import db_connection
import requests
import json
import os

def mock_openrouter_ner(raw_text: str) -> dict:
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    prompt = f"""You are a biomedical NER system. Extract entities from the following text into this exact JSON format:
    {{
      "Disease_Disorder": ["list of diseases"],
      "Sign_symptom": ["list of symptoms"],
      "Medication": ["list of medications"],
      "Diagnostic_procedure": ["list of procedures"],
      "Demographics": {{
          "Patient_ID": "ID",
          "Age": "age",
          "Gender": "gender",
          "ZIP": "zip"
      }}
    }}
    Text: {raw_text}
    """
    
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"},
        json={
            "model": "openai/gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0
        }
    )
    content = response.json()["choices"][0]["message"]["content"]
    if content.startswith("```json"):
        content = content.strip("```json").strip("```").strip()
    return json.loads(content)

def run_e2e_test(scenario_name, pdf_filename, expected_outcome, ncd_chunks, lcd_chunks, art_chunks, requested_code):
    print(f"\n{'='*80}\nRUNNING E2E TEST: {scenario_name}\n{'='*80}")
    
    # PHASE 1: Intake & OCR Extraction
    print(f"[Phase 1] Extracting data from {pdf_filename}...")
    with open(pdf_filename, "rb") as f:
        file_bytes = f.read()
        
    raw_text = PdfExtractionService.extract_text_from_pdf(file_bytes)
    print("  -> Text extracted successfully. Running OpenRouter NER...")
    
    extracted_entities = mock_openrouter_ner(raw_text)
    
    demos = extracted_entities.get("Demographics", {})
    diseases = [d for d in extracted_entities.get("Disease_Disorder", [])]
    
    packet = ClinicalEvidencePacket(
        authorization_id=demos.get("Patient_ID", "AUTH-TEST"),
        patient_id=demos.get("Patient_ID", "Unknown"),
        requested_service={
            "code": requested_code,
            "description": "Requested Item"
        },
        diagnosis_codes=diseases,
        demographics={
            "age": demos.get("Age"),
            "gender": demos.get("Gender"),
            "state_code": demos.get("ZIP")
        },
        conditions=[{"name": d} for d in diseases],
        medications=[{"name": m} for m in extracted_entities.get("Medication", [])],
        vital_signs=[{"name": s} for s in extracted_entities.get("Sign_symptom", [])],
        procedures=[{"name": p} for p in extracted_entities.get("Diagnostic_procedure", [])],
        provenance=[]
    )
    print("  -> Built Clinical Evidence Packet!")
    
    # PHASE 4: NCD Evaluation
    print(f"[Phase 4] Evaluating National Coverage Determination...")
    ncd_decision = NCDEvaluationEngine.evaluate_ncds(packet, ncd_chunks)
    
    lcd_decision = None
    if ncd_decision.ncd_determination != "NOT COVERED":
        # PHASE 5: LCD Evaluation
        print(f"[Phase 5] Evaluating Local Coverage Determination...")
        lcd_decision = LCDEvaluationEngine.evaluate_lcds(packet, lcd_chunks)
    else:
        print(f"[Phase 5] SKIPPING LCD Evaluation (NCD Explicitly Denied)...")
        
    # PHASE 6: Article Evaluation
    print(f"[Phase 6] Evaluating Administrative Articles...")
    art_decision = ArticleEvaluationEngine.evaluate_articles(packet, art_chunks)
    
    # PHASE 7: Decision Engine
    print(f"[Phase 7] Computing Final Decision...")
    phase7 = ConfidenceDecisionEngine.compute_decision(packet, ncd_decision, lcd_decision, art_decision)
    
    status_map = {
        "APPROVE": "APPROVED",
        "DENY": "DENIED",
        "PEND": "PENDING_MANUAL_REVIEW",
        "NURSE_REVIEW": "PENDING_MANUAL_REVIEW"
    }

    pipeline_result = PipelineDecisionResult(
        final_status=status_map.get(phase7.recommendation, "PENDING_MANUAL_REVIEW"),
        ncd_decision=ncd_decision,
        lcd_decision=lcd_decision,
        article_decision=art_decision,
        phase7_decision=phase7
    )

    # PHASE 8: Explanation Generation
    print(f"[Phase 8] Generating Formal Letter...")
    final_markdown = ExplanationEngine.generate_explanation(pipeline_result)
    
    print("\n--- FINAL PHASE 8 OUTPUT LETTER ---")
    print(final_markdown.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding))
    print(f"--- END OF {scenario_name} ---")


if __name__ == "__main__":
    db_connection.connect()
    
    # Scenario 1: Oxygen
    run_e2e_test(
        "SCENARIO 1: Oxygen Therapy (Hypoxemia)",
        "scenario1_oxygen.pdf",
        "APPROVE",
        [{"text": "Stationary oxygen is covered for patients with severe hypoxemia documented by an ABG test.", "document_type": "NCD", "document_id": "NCD-240.2"}],
        [{"text": "Patient must have tried conservative therapy.", "document_type": "LCD", "document_id": "LCD-OXYGEN"}],
        [{"text": "R09.02 is an approved diagnosis code for E0424.", "document_type": "ARTICLE", "document_id": "ART-OXYGEN"}],
        "E0424"
    )
    
    # Scenario 2: Prosthesis
    run_e2e_test(
        "SCENARIO 2: Prosthetic Limb (Amputation)",
        "scenario2_prosthesis.pdf",
        "PEND",
        [{"text": "Prosthetics are covered for patients with amputations.", "document_type": "NCD", "document_id": "NCD-PROS"}],
        [{"text": "Coverage requires a detailed surgical report of the amputation date and outcome.", "document_type": "LCD", "document_id": "LCD-PROS"}],
        [{"text": "Z89.419 is covered for L5613.", "document_type": "ARTICLE", "document_id": "ART-PROS"}],
        "L5613"
    )
    
    # Scenario 3: Wheelchair
    run_e2e_test(
        "SCENARIO 3: Ultralight Wheelchair (Paraplegia) -> PEND",
        "scenario3_wheelchair.pdf",
        "PEND",
        [{"text": "Ultralight wheelchairs require a specialized PT/OT evaluation to prove the patient cannot use a standard wheelchair.", "document_type": "NCD", "document_id": "NCD-WHEEL"}],
        [{"text": "A standard wheelchair evaluation must have failed.", "document_type": "LCD", "document_id": "LCD-WHEEL"}],
        [{"text": "G82.20 is a covered code for K0005.", "document_type": "ARTICLE", "document_id": "ART-WHEEL"}],
        "K0005"
    )
    
    # Scenario 4: Experimental (Rare Disease) -> NURSE_REVIEW
    run_e2e_test(
        "SCENARIO 4: Experimental Device (Novel Syndrome X) -> NURSE_REVIEW",
        "scenario4_experimental.pdf",
        "NURSE_REVIEW",
        [{"text": "Coverage is considered on an individual basis by the medical director for rare and complex neurodegenerative presentations not otherwise specified.", "document_type": "NCD", "document_id": "NCD-EXPERIMENTAL"}],
        [{"text": "Experimental neural stimulators are evaluated individually due to clinical ambiguity.", "document_type": "LCD", "document_id": "LCD-EXPERIMENTAL"}],
        [{"text": "E9999 can be billed for experimental devices under individual consideration.", "document_type": "ARTICLE", "document_id": "ART-EXPERIMENTAL"}],
        "E9999"
    )
    
    # Scenario 5: Asthma Nebulizer -> APPROVE
    run_e2e_test(
        "SCENARIO 5: Standard Nebulizer (Asthma) -> APPROVE",
        "scenario5_asthma.pdf",
        "APPROVE",
        [{"text": "Standard nebulizers are covered for severe persistent asthma when the patient has failed standard inhaler therapies and spirometry confirms severity.", "document_type": "NCD", "document_id": "NCD-ASTHMA"}],
        [{"text": "Coverage requires documented spirometry and failure of inhalers.", "document_type": "LCD", "document_id": "LCD-ASTHMA"}],
        [{"text": "E0570 is covered for severe persistent asthma. Diagnosis J45.50 is covered.", "document_type": "ARTICLE", "document_id": "ART-ASTHMA"}],
        "E0570"
    )
