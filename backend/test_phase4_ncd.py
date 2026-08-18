import os
import sys
import json
from dotenv import load_dotenv

load_dotenv('.env')
from app.models.patient import ClinicalEvidencePacket
from app.services.ncd_evaluation_engine import NCDEvaluationEngine

def run_scenarios():
    print("=== VERIFYING AI DETERMINATION STATUSES ===")
    
    # The CMS Law Chunk (Constant)
    law_chunks = [{
        "document_type": "NCD",
        "document_id": "190",
        "section": "Coverage Indications",
        "text": "A wheelchair seat cushion is covered for a patient who has a current pressure ulcer on the area of contact with the seating surface AND has a prior physical therapy assessment."
    }]

    # Scenario 1: COVERED (Patient meets ALL conditions)
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

    # Scenario 2: NOT ADDRESSED (Patient has pressure ulcer but is MISSING the PT assessment data)
    packet_not_addressed_missing = ClinicalEvidencePacket(
        authorization_id="AUTH-2",
        patient_id="PAT-2",
        requested_service={"code": "E2601", "description": "Wheelchair seat cushion"},
        diagnosis_codes=[],
        demographics={"age": 65, "gender": "M"},
        conditions=[{"name": "pressure ulcer"}],
        procedures=[], surgeries=[], medications=[], diagnostic_results=[], vital_signs=[],
        clinical_assessments=[], functional_status=[], allergies=[], medical_equipment=[],
        care_plans=[], social_history=[], family_history=[], referrals=[], encounters=[],
        prior_treatments=[], clinical_text=[], missing_information=[], provenance=[]
    )

    # Scenario 3: NOT ADDRESSED (Patient has diabetes - no determination resolving this)
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

    # Scenario 4: NOT ADDRESSED (Patient has lung cancer)
    packet_not_addressed_2 = ClinicalEvidencePacket(
        authorization_id="AUTH-4",
        patient_id="PAT-4",
        requested_service={"code": "E2601", "description": "Wheelchair seat cushion"},
        diagnosis_codes=[],
        demographics={"age": 65, "gender": "M"},
        conditions=[{"name": "stage 4 lung cancer"}],
        procedures=[], surgeries=[], medications=[], diagnostic_results=[], vital_signs=[],
        clinical_assessments=[], functional_status=[], allergies=[], medical_equipment=[],
        care_plans=[], social_history=[], family_history=[], referrals=[], encounters=[],
        prior_treatments=[], clinical_text=[], missing_information=[], provenance=[]
    )

    scenarios = [
        ("SCENARIO 1: Expecting COVERED", packet_covered),
        ("SCENARIO 2: Expecting NOT ADDRESSED (Missing PT data)", packet_not_addressed_missing),
        ("SCENARIO 3: Expecting NOT ADDRESSED (Diabetes)", packet_not_addressed),
        ("SCENARIO 4: Expecting NOT ADDRESSED (Lung Cancer)", packet_not_addressed_2)
    ]

    for title, packet in scenarios:
        print(f"\n{title}")
        print(f"Patient Condition: {packet.conditions[0]['name']}")
        decision = NCDEvaluationEngine.evaluate_ncds(
            clinical_evidence=packet,
            retrieval_result=law_chunks
        )
        print(f"AI Output -> {decision.ncd_determination}")
        print(f"Reasoning: {decision.reasoning}")

if __name__ == "__main__":
    run_scenarios()
