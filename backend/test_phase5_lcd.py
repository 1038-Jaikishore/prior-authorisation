import os
import sys
import json
from dotenv import load_dotenv

load_dotenv('.env')
from app.models.patient import ClinicalEvidencePacket
from app.services.pipeline_orchestrator import PriorAuthPipelineOrchestrator
from app.services.ncd_evaluation_engine import NCDEvaluationEngine
from app.services.lcd_evaluation_engine import LCDEvaluationEngine

def run_test():
    print("=== VERIFYING PHASE 5 PIPELINE ORCHESTRATION ===")
    
    # We will simulate 3 Scenarios
    # Since the Orchestrator does database calls, we will just directly invoke the engines 
    # using the same logic as the Orchestrator to prove the state transitions.

    # Mock Law Data
    ncd_chunk_strict = {
        "document_type": "NCD",
        "document_id": "190",
        "section": "Coverage Indications",
        "text": "This item is NOT covered for patients with diabetes."
    }
    
    ncd_chunk_lenient = {
        "document_type": "NCD",
        "document_id": "190",
        "section": "Coverage Indications",
        "text": "This item is covered for patients with pressure ulcers."
    }

    lcd_chunk_strict = {
        "document_type": "LCD",
        "document_id": "L33312",
        "section": "Coverage Indications",
        "text": "This item is strictly NOT covered in Texas unless the patient is older than 60."
    }
    
    lcd_chunk_lenient = {
        "document_type": "LCD",
        "document_id": "L33312",
        "section": "Coverage Indications",
        "text": "This item is covered in Texas for patients with pressure ulcers."
    }

    def simulate_orchestrator(scenario_name: str, packet: ClinicalEvidencePacket, chunks: list):
        print(f"\n{scenario_name}")
        
        # 1. Evaluate NCD
        ncd_decision = NCDEvaluationEngine.evaluate_ncds(packet, chunks)
        print(f"[NCD PHASE 4] Output -> {ncd_decision.ncd_determination}")
        
        if ncd_decision.ncd_determination == "NOT COVERED":
            print(">>> PIPELINE EARLY EXIT (DENIED) <<<")
            print(f"Final Reason: Denied based on NCD. {ncd_decision.reasoning}")
            return
            
        print(">>> NCD PASSED OR NOT ADDRESSED. PROCEEDING TO LCD PHASE 5... <<<")
        
        # 2. Evaluate LCD
        lcd_decision = LCDEvaluationEngine.evaluate_lcds(packet, chunks)
        print(f"[LCD PHASE 5] Output -> {lcd_decision.lcd_determination}")
        
        if lcd_decision.lcd_determination == "NOT COVERED":
            print(">>> PIPELINE COMPLETED (DENIED) <<<")
            print(f"Final Reason: Denied based on LCD. {lcd_decision.reasoning}")
        elif lcd_decision.lcd_determination == "COVERED":
            print(">>> PIPELINE COMPLETED (APPROVED) <<<")
            print(f"Final Reason: Approved based on LCD. {lcd_decision.reasoning}")
        else:
            print(">>> PIPELINE COMPLETED (PENDING MANUAL REVIEW) <<<")
            print("Final Reason: Neither NCD nor LCD addressed this condition.")


    # --- SCENARIO A: NCD Fails (Early Exit Deny) ---
    packet_a = ClinicalEvidencePacket(
        authorization_id="AUTH-A", patient_id="PAT-A", requested_service={"code": "E2601", "description": "Wheelchair cushion"},
        diagnosis_codes=[], demographics={"age": 65, "gender": "M"}, conditions=[{"name": "diabetes"}],
        procedures=[], surgeries=[], medications=[], diagnostic_results=[], vital_signs=[], clinical_assessments=[], functional_status=[], allergies=[], medical_equipment=[], care_plans=[], social_history=[], family_history=[], referrals=[], encounters=[], prior_treatments=[], clinical_text=[], missing_information=[], provenance=[]
    )
    simulate_orchestrator("SCENARIO A: Patient has diabetes (NCD explicitly denies this). Should EARLY EXIT.", packet_a, [ncd_chunk_strict, lcd_chunk_lenient])

    # --- SCENARIO B: NCD Passes, LCD Fails ---
    packet_b = ClinicalEvidencePacket(
        authorization_id="AUTH-B", patient_id="PAT-B", requested_service={"code": "E2601", "description": "Wheelchair cushion"},
        diagnosis_codes=[], demographics={"age": 45, "gender": "M"}, conditions=[{"name": "pressure ulcer"}],
        procedures=[], surgeries=[], medications=[], diagnostic_results=[], vital_signs=[], clinical_assessments=[], functional_status=[], allergies=[], medical_equipment=[], care_plans=[], social_history=[], family_history=[], referrals=[], encounters=[], prior_treatments=[], clinical_text=[], missing_information=[], provenance=[]
    )
    simulate_orchestrator("SCENARIO B: Patient has pressure ulcer, but is 45 years old (LCD denies under 60 in Texas).", packet_b, [ncd_chunk_lenient, lcd_chunk_strict])

    # --- SCENARIO C: NCD Not Addressed, LCD Passes ---
    packet_c = ClinicalEvidencePacket(
        authorization_id="AUTH-C", patient_id="PAT-C", requested_service={"code": "E2601", "description": "Wheelchair cushion"},
        diagnosis_codes=[], demographics={"age": 65, "gender": "M"}, conditions=[{"name": "pressure ulcer"}],
        procedures=[], surgeries=[], medications=[], diagnostic_results=[], vital_signs=[], clinical_assessments=[], functional_status=[], allergies=[], medical_equipment=[], care_plans=[], social_history=[], family_history=[], referrals=[], encounters=[], prior_treatments=[], clinical_text=[], missing_information=[], provenance=[]
    )
    # Give it an NCD chunk about diabetes (so it returns NOT ADDRESSED for pressure ulcer), but an LCD chunk about pressure ulcer.
    simulate_orchestrator("SCENARIO C: NCD is about diabetes (Not Addressed), but LCD explicitly covers pressure ulcers.", packet_c, [ncd_chunk_strict, lcd_chunk_lenient])


if __name__ == "__main__":
    run_test()
