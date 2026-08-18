import json
import os
from dotenv import load_dotenv
load_dotenv()

from app.models.patient import ClinicalEvidencePacket
from app.services.ncd_evaluation_engine import NCDEvaluationEngine
from app.services.lcd_evaluation_engine import LCDEvaluationEngine
from app.services.article_evaluation_engine import ArticleEvaluationEngine
from app.services.decision_engine import ConfidenceDecisionEngine

def run_scenarios():
    print("=== VERIFYING PHASE 7 DECISION ENGINE (ALL 4 STATES) ===\n")

    # Common Rule Documents (CPAP for Sleep Apnea)
    ncd_chunks = [{"text": "A CPAP device is covered if the patient is diagnosed with Obstructive Sleep Apnea (OSA).", "document_type": "NCD", "document_id": "NCD-240.4", "section": "Coverage"}]
    lcd_chunks = [{"text": "The patient must have a documented face-to-face clinical evaluation and a polysomnography (sleep study) prior to dispensing the CPAP.", "document_type": "LCD", "document_id": "LCD-L33718", "section": "Coverage"}]
    art_chunks = [{"text": "The following ICD-10 codes support medical necessity: G47.33 (Obstructive sleep apnea). The following codes are denied: G47.00 (Insomnia).", "document_type": "ARTICLE", "document_id": "A52467", "section": "Coding"}]

    def test_scenario(title, packet):
        print(title)
        ncd_decision = NCDEvaluationEngine.evaluate_ncds(packet, ncd_chunks)
        lcd_decision = LCDEvaluationEngine.evaluate_lcds(packet, lcd_chunks)
        art_decision = ArticleEvaluationEngine.evaluate_articles(packet, art_chunks)
        phase7 = ConfidenceDecisionEngine.compute_decision(packet, ncd_decision, lcd_decision, art_decision)
        print(f"--> Final Recommendation: {phase7.recommendation}")
        print(f"--> Confidence Score: {phase7.overall_confidence_score}")
        print(f"--> Summary: {phase7.evidence_summary}")
        print(f"--> Gap Analysis: {phase7.gap_analysis}")
        print("-" * 60 + "\n")

    # 1. APPROVE: Perfect Match
    test_scenario("SCENARIO 1: Expecting APPROVE (Sleep Apnea with Sleep Study)", ClinicalEvidencePacket(
        authorization_id="AUTH-1", patient_id="PAT-1",
        requested_service={"code": "E0601", "description": "CPAP Machine"},
        diagnosis_codes=["G47.33"], demographics={"age": 55, "gender": "F"},
        conditions=[{"name": "Obstructive Sleep Apnea"}],
        clinical_assessments=[{"name": "face-to-face clinical evaluation"}],
        diagnostic_results=[{"name": "polysomnography", "value": "completed"}]
    ))

    # 2. DENY: Code mismatch (G47.00 Insomnia is explicitly denied)
    test_scenario("SCENARIO 2: Expecting DENY (Wrong Diagnosis)", ClinicalEvidencePacket(
        authorization_id="AUTH-2", patient_id="PAT-2",
        requested_service={"code": "E0601", "description": "CPAP Machine"},
        diagnosis_codes=["G47.00"], demographics={"age": 55, "gender": "F"},
        conditions=[{"name": "Insomnia"}],
        clinical_assessments=[{"name": "face-to-face clinical evaluation"}],
        diagnostic_results=[{"name": "polysomnography", "value": "completed"}]
    ))

    # 3. PEND: Missing Sleep Study document
    test_scenario("SCENARIO 3: Expecting PEND (Missing Polysomnography)", ClinicalEvidencePacket(
        authorization_id="AUTH-3", patient_id="PAT-3",
        requested_service={"code": "E0601", "description": "CPAP Machine"},
        diagnosis_codes=["G47.33"], demographics={"age": 55, "gender": "F"},
        conditions=[{"name": "Obstructive Sleep Apnea"}],
        clinical_assessments=[{"name": "face-to-face clinical evaluation"}],
        diagnostic_results=[] # Missing Sleep Study
    ))

    # 4. NURSE_REVIEW: Narcolepsy (G47.419) is not mentioned in rules
    test_scenario("SCENARIO 4: Expecting NURSE_REVIEW (Condition not addressed by rules)", ClinicalEvidencePacket(
        authorization_id="AUTH-4", patient_id="PAT-4",
        requested_service={"code": "E0601", "description": "CPAP Machine"},
        diagnosis_codes=["G47.419"], demographics={"age": 55, "gender": "F"},
        conditions=[{"name": "Narcolepsy"}],
        clinical_assessments=[{"name": "face-to-face clinical evaluation"}],
        diagnostic_results=[{"name": "polysomnography", "value": "completed"}]
    ))

if __name__ == "__main__":
    run_scenarios()
