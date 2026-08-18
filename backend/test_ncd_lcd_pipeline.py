import json
import os
from dotenv import load_dotenv
load_dotenv()

from app.models.patient import ClinicalEvidencePacket
from app.services.ncd_evaluation_engine import NCDEvaluationEngine
from app.services.lcd_evaluation_engine import LCDEvaluationEngine

def main():
    print("=== RUNNING COMBINED NCD & LCD EVALUATION ===")

    # Mock Patient: Pressure Ulcer, PT Assessment, Age 65
    packet = ClinicalEvidencePacket(
        authorization_id="AUTH-123",
        patient_id="PAT-456",
        requested_service={"code": "E0192", "description": "Wheelchair seat cushion"},
        diagnosis_codes=["L89.15"],
        demographics={"age": 65, "gender": "M"},
        conditions=[{"name": "pressure ulcer"}],
        clinical_assessments=[{"name": "physical therapy assessment"}]
    )

    # Mock NCD Law Text
    ncd_chunks = [{
        "text": "National Coverage Determination (NCD) 280.1: A wheelchair seat cushion is covered if the patient has a documented pressure ulcer.",
        "document_type": "NCD",
        "document_id": "NCD-280.1",
        "section": "Coverage"
    }]

    # Mock LCD Law Text
    lcd_chunks = [{
        "text": "Local Coverage Determination (LCD) L33312: In addition to NCD requirements, the patient must have a prior physical therapy assessment and be older than 60.",
        "document_type": "LCD",
        "document_id": "LCD-L33312",
        "section": "Coverage"
    }]

    print("\n[PHASE 4: NCD EVALUATION]")
    ncd_decision = NCDEvaluationEngine.evaluate_ncds(
        clinical_evidence=packet,
        retrieval_result=ncd_chunks
    )
    print(ncd_decision.model_dump_json(indent=2))

    print("\n[PHASE 5: LCD EVALUATION]")
    lcd_decision = LCDEvaluationEngine.evaluate_lcds(
        clinical_evidence=packet,
        retrieval_result=lcd_chunks
    )
    print(lcd_decision.model_dump_json(indent=2))

if __name__ == "__main__":
    main()
