import os
import sys
from dotenv import load_dotenv

load_dotenv('.env')
from app.models.patient import ClinicalEvidencePacket
from app.services.lcd_evaluation_engine import LCDEvaluationEngine

def run_scenarios():
    print("=== VERIFYING PHASE 5 LCD EVALUATION STATUSES ===\n")

    # The CMS LCD Law Chunk (Constant)
    # Testing age constraint and required PT assessment.
    lcd_chunks = [{
        "document_type": "LCD",
        "document_id": "L33312",
        "section": "Coverage Indications",
        "text": "A wheelchair seat cushion is covered in Texas for a patient who has a current pressure ulcer AND has a prior physical therapy assessment AND is older than 60."
    }]

    # Scenario 1: COVERED (Patient meets ALL conditions and is 65)
    packet_covered = ClinicalEvidencePacket(
        authorization_id="AUTH-1",
        patient_id="PAT-1",
        requested_service={"code": "E2601", "description": "Wheelchair seat cushion"},
        diagnosis_codes=[],
        demographics={"age": 65, "gender": "M"},
        conditions=[{"name": "pressure ulcer"}],
        procedures=[], surgeries=[], medications=[], diagnostic_results=[], vital_signs=[],
        clinical_assessments=[{"name": "physical therapy assessment"}], functional_status=[], allergies=[], medical_equipment=[],
        care_plans=[], social_history=[], family_history=[], referrals=[], encounters=[],
        prior_treatments=[], clinical_text=[], missing_information=[], provenance=[]
    )

    # Scenario 2: NOT COVERED (Patient is 45 years old - fails explicit age requirement)
    packet_not_covered = ClinicalEvidencePacket(
        authorization_id="AUTH-2",
        patient_id="PAT-2",
        requested_service={"code": "E2601", "description": "Wheelchair seat cushion"},
        diagnosis_codes=[],
        demographics={"age": 45, "gender": "M"},
        conditions=[{"name": "pressure ulcer"}],
        procedures=[], surgeries=[], medications=[], diagnostic_results=[], vital_signs=[],
        clinical_assessments=[{"name": "physical therapy assessment"}], functional_status=[], allergies=[], medical_equipment=[],
        care_plans=[], social_history=[], family_history=[], referrals=[], encounters=[],
        prior_treatments=[], clinical_text=[], missing_information=[], provenance=[]
    )

    # Scenario 3: NOT ADDRESSED (Patient has Diabetes, LCD only talks about Pressure Ulcers)
    packet_not_addressed = ClinicalEvidencePacket(
        authorization_id="AUTH-3",
        patient_id="PAT-3",
        requested_service={"code": "E2601", "description": "Wheelchair seat cushion"},
        diagnosis_codes=[],
        demographics={"age": 65, "gender": "M"},
        conditions=[{"name": "diabetes"}],
        procedures=[], surgeries=[], medications=[], diagnostic_results=[], vital_signs=[],
        clinical_assessments=[], functional_status=[], allergies=[], medical_equipment=[],
        care_plans=[], social_history=[], family_history=[], referrals=[], encounters=[],
        prior_treatments=[], clinical_text=[], missing_information=[], provenance=[]
    )

    scenarios = [
        ("SCENARIO 1: Expecting COVERED", packet_covered),
        ("SCENARIO 2: Expecting NOT COVERED (Under 60)", packet_not_covered),
        ("SCENARIO 3: Expecting NOT ADDRESSED (Diabetes - Irrelevant Disease)", packet_not_addressed)
    ]

    for title, packet in scenarios:
        print(f"{title}")
        print(f"Patient Condition: {packet.conditions}")
        print(f"Patient Age: {packet.demographics.get('age')}")
        print(f"Patient Assessments: {packet.clinical_assessments}")
        decision = LCDEvaluationEngine.evaluate_lcds(
            clinical_evidence=packet,
            retrieval_result=lcd_chunks
        )
        print(f"AI Output -> {decision.lcd_determination}")
        print(f"Reasoning: {decision.reasoning}\n")

if __name__ == "__main__":
    run_scenarios()
