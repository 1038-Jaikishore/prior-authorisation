import os
import sys
import json
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

app = FastAPI(title="CMS Prior Auth API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For local testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        },
        timeout=15
    )
    content = response.json()["choices"][0]["message"]["content"]
    if content.startswith("```json"):
        content = content.strip("```json").strip("```").strip()
    return json.loads(content)


def get_mock_rules_for_text(text: str):
    text_lower = text.lower()
    
    # Asthma Rules (APPROVE scenario)
    if "asthma" in text_lower or "nebulizer" in text_lower:
        return (
            "E0570",
            [{"text": "Standard nebulizers are covered for severe persistent asthma when the patient has failed standard inhaler therapies and spirometry confirms severity.", "document_type": "NCD", "document_id": "NCD-ASTHMA"}],
            [{"text": "Coverage requires documented spirometry and failure of inhalers.", "document_type": "LCD", "document_id": "LCD-ASTHMA"}],
            [{"text": "E0570 is covered for severe persistent asthma. Diagnosis J45.50 is covered.", "document_type": "ARTICLE", "document_id": "ART-ASTHMA"}]
        )
    # Wheelchair Rules (PEND scenario)
    elif "wheelchair" in text_lower or "paraplegia" in text_lower:
        return (
            "K0005",
            [{"text": "Ultralight wheelchairs require a specialized PT/OT evaluation to prove the patient cannot use a standard wheelchair.", "document_type": "NCD", "document_id": "NCD-WHEEL"}],
            [{"text": "A standard wheelchair evaluation must have failed.", "document_type": "LCD", "document_id": "LCD-WHEEL"}],
            [{"text": "G82.20 is a covered code for K0005.", "document_type": "ARTICLE", "document_id": "ART-WHEEL"}]
        )
    # Experimental Rules (NURSE_REVIEW scenario)
    elif "experimental" in text_lower or "novel" in text_lower:
        return (
            "E9999",
            [{"text": "Coverage is considered on an individual basis by the medical director for rare and complex neurodegenerative presentations not otherwise specified.", "document_type": "NCD", "document_id": "NCD-EXPERIMENTAL"}],
            [{"text": "Experimental neural stimulators are evaluated individually due to clinical ambiguity.", "document_type": "LCD", "document_id": "LCD-EXPERIMENTAL"}],
            [{"text": "E9999 can be billed for experimental devices under individual consideration.", "document_type": "ARTICLE", "document_id": "ART-EXPERIMENTAL"}]
        )
    # Oxygen Rules (DENY scenario)
    else:
        return (
            "E0424",
            [{"text": "Stationary oxygen is covered for patients with severe hypoxemia documented by an ABG test.", "document_type": "NCD", "document_id": "NCD-240.2"}],
            [{"text": "Patient must have tried conservative therapy.", "document_type": "LCD", "document_id": "LCD-OXYGEN"}],
            [{"text": "R09.02 is an approved diagnosis code for E0424.", "document_type": "ARTICLE", "document_id": "ART-OXYGEN"}]
        )

@app.post("/api/v1/prior-auth/submit")
async def submit_prior_auth(file: UploadFile = File(...)):
    # Read PDF
    file_bytes = await file.read()
    
    # Phase 1: Extract Text
    raw_text = PdfExtractionService.extract_text_from_pdf(file_bytes)
    
    # Phase 2 & 3: Mock NER
    extracted_entities = mock_openrouter_ner(raw_text)
    
    demos = extracted_entities.get("Demographics", {})
    diseases = [d for d in extracted_entities.get("Disease_Disorder", [])]
    
    requested_code, ncd_chunks, lcd_chunks, art_chunks = get_mock_rules_for_text(raw_text)
    
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
    
    # Phase 4
    ncd_decision = NCDEvaluationEngine.evaluate_ncds(packet, ncd_chunks)
    
    # Phase 5
    lcd_decision = None
    if ncd_decision.ncd_determination != "NOT COVERED":
        lcd_decision = LCDEvaluationEngine.evaluate_lcds(packet, lcd_chunks)
        
    # Phase 6
    art_decision = ArticleEvaluationEngine.evaluate_articles(packet, art_chunks)
    
    # Phase 7
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
    
    # Phase 8
    final_markdown = ExplanationEngine.generate_explanation(pipeline_result)
    
    routing_data = {
        "requested_hcpcs": requested_code,
        "ncd_policies": [chunk["document_id"] for chunk in ncd_chunks],
        "lcd_policies": [chunk["document_id"] for chunk in lcd_chunks],
        "article_policies": [chunk["document_id"] for chunk in art_chunks]
    }
    
    details_dict = pipeline_result.dict()
    details_dict["phase3_routing"] = routing_data
    
    return {
        "status": pipeline_result.final_status,
        "confidence": phase7.overall_confidence_score,
        "recommendation": phase7.recommendation,
        "letter": final_markdown,
        "metrics": {
            "processing_time": 4.2 # mocked for UI
        },
        "details": details_dict
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
