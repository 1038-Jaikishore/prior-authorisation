import json
import os
from dotenv import load_dotenv
load_dotenv()

from app.models.patient import ClinicalEvidencePacket
from app.services.ncd_evaluation_engine import NCDEvaluationEngine
from app.services.lcd_evaluation_engine import LCDEvaluationEngine

def main():
    print("=== RUNNING COMBINED EVALUATION FOR A NEW DISEASE (OXYGEN THERAPY) ===")

    # Mock Patient: COPD, PO2 of 52 mm Hg, seen by Pulmonologist
    packet = ClinicalEvidencePacket(
        authorization_id="AUTH-999",
        patient_id="PAT-OXYGEN",
        requested_service={"code": "E0424", "description": "Stationary compressed gaseous oxygen system"},
        diagnosis_codes=["J44.9"], # COPD
        demographics={"age": 72, "gender": "F"},
        conditions=[{"name": "Severe chronic obstructive pulmonary disease (COPD)"}],
        diagnostic_results=[{"name": "Arterial Blood Gas", "value": "PO2 52 mm Hg"}],
        encounters=[{"provider_specialty": "Pulmonology", "type": "face-to-face evaluation"}]
    )

    # Mock NCD Law Text for Oxygen
    ncd_chunks = [{
        "text": "National Coverage Determination (NCD) 240.2 (Home Use of Oxygen): Coverage is provided for patients with significant hypoxemia in the chronic stable state, provided the patient has an arterial PO2 at or below 55 mm Hg.",
        "document_type": "NCD",
        "document_id": "NCD-240.2",
        "section": "Indications and Limitations of Coverage"
    }]

    # Mock LCD Law Text for Oxygen
    lcd_chunks = [{
        "text": "Local Coverage Determination (LCD) L33797: In addition to the NCD requirements for PO2 levels, the patient must have had a face-to-face evaluation with a pulmonologist within 30 days prior to the initial certification.",
        "document_type": "LCD",
        "document_id": "LCD-L33797",
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
