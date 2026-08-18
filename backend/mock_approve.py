import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Ensure backend path is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from app.models.decision import Phase7DecisionOutput
from app.services.explanation_engine import ExplanationEngine

def main():
    # Mock the Phase 7 output for a perfect APPROVE
    mock_decision = Phase7DecisionOutput(
        overall_confidence_score=0.98,
        evidence_summary="Patient presents with Severe Persistent Asthma (J45.50). Requested service is Standard Nebulizer (E0570). Clinical documentation includes spirometry confirming severity and failure of standard inhaler therapies.",
        gap_analysis="None. All requirements met.",
        recommendation="APPROVE",
        ncd_determination="COVERED",
        lcd_determination="COVERED",
        article_determination="COVERED",
        met_requirements=[
            "Documented spirometry confirming asthma severity",
            "Documented failure of standard inhaler therapies",
            "Valid diagnosis code J45.50 for requested service E0570"
        ],
        missing_requirements=[],
        patient_evidence=[
            "Clinical notes state: Patient has failed standard inhaler therapies.",
            "Diagnostic procedure: Spirometry confirming asthma severity."
        ],
        policy_evidence=[
            "NCD-ASTHMA Section 1.2: Standard nebulizers are covered for severe persistent asthma when the patient has failed standard inhaler therapies and spirometry confirms severity.",
            "LCD-ASTHMA L33333: Coverage requires documented spirometry and failure of inhalers."
        ],
        mismatched_codes=[],
        matching_codes=["J45.50", "E0570"]
    )
    
    # Run Phase 8
    print("================================================================================")
    print("GENERATING PHASE 8 APPROVE LETTER...")
    print("================================================================================\n")
    
    letter = ExplanationEngine.generate_explanation(mock_decision)
    print(letter)

if __name__ == "__main__":
    main()
