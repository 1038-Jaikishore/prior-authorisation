import json
import os
from dotenv import load_dotenv
load_dotenv()

from app.models.patient import ClinicalEvidencePacket
from app.services.article_evaluation_engine import ArticleEvaluationEngine

def run_scenarios():
    print("=== VERIFYING PHASE 6 ARTICLE EVALUATION ===\n")

    # Mock Article Text with explicit covered/non-covered lists
    article_chunks = [{
        "text": "The following ICD-10-CM codes support medical necessity and are covered for HCPCS code E2601:\nL89.15 (Pressure ulcer)\nL89.20 (Pressure ulcer of unspecified heel)\n\nThe following ICD-10-CM codes DO NOT support medical necessity and will be denied:\nE11.9 (Type 2 diabetes mellitus without complications)",
        "document_type": "ARTICLE",
        "document_id": "A52467",
        "section": "Coding Information"
    }]

    # Scenario 1: COVERED (Patient has L89.15)
    packet_covered = ClinicalEvidencePacket(
        authorization_id="AUTH-ART-1",
        patient_id="PAT-1",
        requested_service={"code": "E2601", "description": "Wheelchair seat cushion"},
        diagnosis_codes=["L89.15"],
        demographics={"age": 65},
    )

    # Scenario 2: NOT COVERED (Patient has E11.9)
    packet_denied = ClinicalEvidencePacket(
        authorization_id="AUTH-ART-2",
        patient_id="PAT-2",
        requested_service={"code": "E2601", "description": "Wheelchair seat cushion"},
        diagnosis_codes=["E11.9"],
        demographics={"age": 65},
    )

    # Scenario 3: NOT ADDRESSED (Patient has J44.9 - COPD, which is not mentioned)
    packet_silent = ClinicalEvidencePacket(
        authorization_id="AUTH-ART-3",
        patient_id="PAT-3",
        requested_service={"code": "E2601", "description": "Wheelchair seat cushion"},
        diagnosis_codes=["J44.9"],
        demographics={"age": 65},
    )

    scenarios = [
        ("SCENARIO 1: Expecting COVERED (Code L89.15 is on the Covered list)", packet_covered),
        ("SCENARIO 2: Expecting NOT COVERED (Code E11.9 is on the Non-Covered list)", packet_denied),
        ("SCENARIO 3: Expecting NOT ADDRESSED (Code J44.9 is not mentioned)", packet_silent)
    ]

    for title, packet in scenarios:
        print(title)
        decision = ArticleEvaluationEngine.evaluate_articles(
            clinical_evidence=packet,
            retrieval_result=article_chunks
        )
        print(decision.model_dump_json(indent=2))
        print("-" * 50 + "\n")

if __name__ == "__main__":
    run_scenarios()
