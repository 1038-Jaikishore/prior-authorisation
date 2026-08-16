import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.db.connection import db_connection
from app.services.decision_engine import PriorAuthorizationDecisionService
from app.services.prior_auth_evaluation import PriorAuthorizationEvaluationService
from app.models.evaluation import PolicyRequirement, RequirementEvaluation, CodingValidation
from app.models.patient import ClinicalEvidencePacket

client = TestClient(app)

@pytest.fixture
def db():
    return db_connection.get_db()

def create_mock_evaluation(
    status="SUCCESS",
    applicable_policies=None,
    warnings=None,
    req_evals=None,
    coding_vals=None,
    admin_vals=None,
    intake_status="SUCCESS"
):
    return {
        "authorization_id": "AUTH_MOCK",
        "evaluation_id": "EVAL_MOCK_123",
        "policy_context": {
            "controlling_policies": [],
            "applicable_policies": applicable_policies or ["L33942"],
            "related_reference_policies": ["A57311"]
        },
        "requirements": [],
        "requirement_evaluations": req_evals or [],
        "coding_validations": coding_vals or [],
        "administrative_validations": admin_vals or [],
        "missing_information": [],
        "warnings": warnings or [],
        "provenance": {
            "evaluated_at": "2026-08-16T12:00:00Z",
            "intake_status": intake_status
        }
    }

# -------------------------------------------------------------
# 1. Golden Case A — APPROVAL PATH (All mandatory MET ➔ APPROVE)
# -------------------------------------------------------------
def test_decision_support_approve(db):
    req_evals = [
        {
            "status": "MET",
            "policy_requirement": {"requirement_id": "REQ-01", "requirement_text": "Must have referral", "policy_role": "APPLICABLE"},
            "patient_provenance": [{"collection": "referrals", "record_id": "ref1"}],
            "policy_citation": "L33942 Indication"
        }
    ]
    coding_vals = [
        {"validator": "ARTICLE_HCPCS", "status": "PASS", "reason": "CPT mapped"}
    ]
    bundle = create_mock_evaluation(req_evals=req_evals, coding_vals=coding_vals)
    res = PriorAuthorizationDecisionService.generate_decision(bundle)
    
    assert res["recommended_disposition"] == "APPROVE"
    assert res["decision_certainty"] == "HIGH"
    assert "PA_ALL_MANDATORY_CRITERIA_MET" in res["reason_codes"]
    assert res["requires_human_review"] is True
    
    db["decision_support_results"].delete_many({"authorization_id": "AUTH_MOCK"})

# -------------------------------------------------------------
# 2. Golden Case B — DENIAL PATH (Mandatory NOT_MET ➔ DENY)
# -------------------------------------------------------------
def test_decision_support_deny(db):
    req_evals = [
        {
            "status": "NOT_MET",
            "policy_requirement": {"requirement_id": "REQ-01", "requirement_text": "Must have referral", "policy_role": "APPLICABLE"},
            "patient_provenance": [],
            "policy_citation": "L33942 Indication"
        }
    ]
    bundle = create_mock_evaluation(req_evals=req_evals)
    res = PriorAuthorizationDecisionService.generate_decision(bundle)
    
    assert res["recommended_disposition"] == "DENY"
    assert res["decision_certainty"] == "HIGH"
    assert "PA_MANDATORY_CRITERION_NOT_MET" in res["reason_codes"]
    
    db["decision_support_results"].delete_many({"authorization_id": "AUTH_MOCK"})

# -------------------------------------------------------------
# 3. Golden Case C — PEND PATH (Mandatory UNCLEAR ➔ PEND)
# -------------------------------------------------------------
def test_decision_support_pend(db):
    req_evals = [
        {
            "status": "UNCLEAR",
            "policy_requirement": {"requirement_id": "REQ-01", "requirement_text": "Must have referral", "policy_role": "APPLICABLE"},
            "patient_provenance": [],
            "policy_citation": "L33942 Indication"
        }
    ]
    bundle = create_mock_evaluation(req_evals=req_evals)
    res = PriorAuthorizationDecisionService.generate_decision(bundle)
    
    assert res["recommended_disposition"] == "PEND"
    assert res["decision_certainty"] == "HIGH"
    assert "PA_MANDATORY_CRITERION_UNCLEAR" in res["reason_codes"]
    assert len(res["missing_information"]) == 1
    assert res["missing_information"][0]["requirement_id"] == "REQ-01"
    
    db["decision_support_results"].delete_many({"authorization_id": "AUTH_MOCK"})

# -------------------------------------------------------------
# 4. Golden Case D — NURSE_REVIEW PATH (Policy uncertainty ➔ NURSE_REVIEW)
# -------------------------------------------------------------
def test_decision_support_nurse_review(db):
    warnings = ["POLICY_APPLICABILITY_UNCERTAIN: Multiple matching LCDs"]
    bundle = create_mock_evaluation(warnings=warnings)
    res = PriorAuthorizationDecisionService.generate_decision(bundle)
    
    assert res["recommended_disposition"] == "NURSE_REVIEW"
    assert res["decision_certainty"] == "LOW"
    assert "PA_POLICY_UNCERTAIN" in res["reason_codes"]
    
    db["decision_support_results"].delete_many({"authorization_id": "AUTH_MOCK"})

# -------------------------------------------------------------
# 5. Warning non-blocking permits APPROVE
# -------------------------------------------------------------
def test_decision_nonblocking_warning(db):
    req_evals = [
        {
            "status": "MET",
            "policy_requirement": {"requirement_id": "REQ-01", "requirement_text": "Must have referral", "policy_role": "APPLICABLE"}
        }
    ]
    coding_vals = [
        {"validator": "ARTICLE_MODIFIER", "status": "UNKNOWN", "reason": "No modifiers"}
    ]
    bundle = create_mock_evaluation(req_evals=req_evals, coding_vals=coding_vals)
    res = PriorAuthorizationDecisionService.generate_decision(bundle)
    
    assert res["recommended_disposition"] == "APPROVE"
    assert res["decision_certainty"] == "MODERATE"
    assert "PA_NONBLOCKING_CODING_WARNING" in res["reason_codes"]
    
    db["decision_support_results"].delete_many({"authorization_id": "AUTH_MOCK"})

# -------------------------------------------------------------
# 6. LCD_HCPCS WARNING does not prevent APPROVE
# -------------------------------------------------------------
def test_decision_lcd_hcpcs_warning(db):
    req_evals = [
        {
            "status": "MET",
            "policy_requirement": {"requirement_id": "REQ-01", "requirement_text": "Must have referral", "policy_role": "APPLICABLE"}
        }
    ]
    coding_vals = [
        {"validator": "LCD_HCPCS", "status": "WARNING", "reason": "Mapped via article A57311"}
    ]
    bundle = create_mock_evaluation(req_evals=req_evals, coding_vals=coding_vals)
    res = PriorAuthorizationDecisionService.generate_decision(bundle)
    
    assert res["recommended_disposition"] == "APPROVE"
    assert res["decision_certainty"] == "MODERATE"
    
    db["decision_support_results"].delete_many({"authorization_id": "AUTH_MOCK"})

# -------------------------------------------------------------
# 7. Absent optional bill/revenue codes do not prevent APPROVE
# -------------------------------------------------------------
def test_decision_missing_optional_bill_revenue_codes(db):
    req_evals = [
        {
            "status": "MET",
            "policy_requirement": {"requirement_id": "REQ-01", "requirement_text": "Must have referral", "policy_role": "APPLICABLE"}
        }
    ]
    coding_vals = [
        {"validator": "ARTICLE_BILL_TYPE", "status": "NOT_EVALUATED", "reason": "Not provided"},
        {"validator": "ARTICLE_REVENUE_CODE", "status": "NOT_EVALUATED", "reason": "Not provided"}
    ]
    bundle = create_mock_evaluation(req_evals=req_evals, coding_vals=coding_vals)
    res = PriorAuthorizationDecisionService.generate_decision(bundle)
    
    assert res["recommended_disposition"] == "APPROVE"
    
    db["decision_support_results"].delete_many({"authorization_id": "AUTH_MOCK"})

# -------------------------------------------------------------
# 8. Unroutable/custom requests return DECISION_SUPPORT_UNAVAILABLE
# -------------------------------------------------------------
def test_decision_custom_code_unsupported(db):
    bundle = create_mock_evaluation(intake_status="POLICY_EVALUATION_UNAVAILABLE")
    res = PriorAuthorizationDecisionService.generate_decision(bundle)
    
    assert res["recommended_disposition"] == "DECISION_SUPPORT_UNAVAILABLE"
    assert res["decision_certainty"] == "LOW"
    assert "PA_POLICY_UNAVAILABLE" in res["reason_codes"]
    
    db["decision_support_results"].delete_many({"authorization_id": "AUTH_MOCK"})

# -------------------------------------------------------------
# 9. Precedence: DENY vs PEND
# -------------------------------------------------------------
def test_decision_precedence_deny_vs_pend(db):
    req_evals = [
        {
            "status": "NOT_MET",
            "policy_requirement": {"requirement_id": "REQ-01", "requirement_text": "Must be >= 65", "policy_role": "APPLICABLE"}
        },
        {
            "status": "UNCLEAR",
            "policy_requirement": {"requirement_id": "REQ-02", "requirement_text": "Therapy referral", "policy_role": "APPLICABLE"}
        }
    ]
    bundle = create_mock_evaluation(req_evals=req_evals)
    res = PriorAuthorizationDecisionService.generate_decision(bundle)
    
    assert res["recommended_disposition"] == "DENY"
    assert "PA_MANDATORY_CRITERION_NOT_MET" in res["reason_codes"]
    assert len(res["missing_information"]) == 1 # Still preserves PEND missing request!
    
    db["decision_support_results"].delete_many({"authorization_id": "AUTH_MOCK"})

# -------------------------------------------------------------
# 10. Precedence: NURSE_REVIEW vs DENY
# -------------------------------------------------------------
def test_decision_precedence_nurse_review_vs_deny(db):
    # Policy applicability is uncertain, so we escalete to NURSE_REVIEW even if a failure matches
    req_evals = [
        {
            "status": "NOT_MET",
            "policy_requirement": {"requirement_id": "REQ-01", "requirement_text": "Must be >= 65", "policy_role": "APPLICABLE"}
        }
    ]
    warnings = ["POLICY_APPLICABILITY_UNCERTAIN: Multiple matching LCDs"]
    bundle = create_mock_evaluation(req_evals=req_evals, warnings=warnings)
    res = PriorAuthorizationDecisionService.generate_decision(bundle)
    
    assert res["recommended_disposition"] == "NURSE_REVIEW"
    assert "PA_POLICY_UNCERTAIN" in res["reason_codes"]
    
    db["decision_support_results"].delete_many({"authorization_id": "AUTH_MOCK"})

# -------------------------------------------------------------
# 11. Related NCD/Article failure ignored for disposition
# -------------------------------------------------------------
def test_decision_related_ncd_failure_ignored(db):
    # Failure of a RELATED_REFERENCE requirement does not deny or pend
    req_evals = [
        {
            "status": "MET",
            "policy_requirement": {"requirement_id": "REQ-01", "requirement_text": "Must have referral", "policy_role": "APPLICABLE"}
        },
        {
            "status": "NOT_MET",
            "policy_requirement": {"requirement_id": "REQ-02", "requirement_text": "Related reference NCD rule", "policy_role": "RELATED_REFERENCE"}
        }
    ]
    bundle = create_mock_evaluation(req_evals=req_evals)
    res = PriorAuthorizationDecisionService.generate_decision(bundle)
    
    assert res["recommended_disposition"] == "APPROVE"
    
    db["decision_support_results"].delete_many({"authorization_id": "AUTH_MOCK"})

# -------------------------------------------------------------
# 12. Immutability & Audit properties
# -------------------------------------------------------------
def test_decision_immutability_and_audit(db):
    bundle = create_mock_evaluation()
    res1 = PriorAuthorizationDecisionService.generate_decision(bundle)
    res2 = PriorAuthorizationDecisionService.generate_decision(bundle)
    
    assert res1["decision_id"] != res2["decision_id"]
    assert res1["evaluation_id"] == bundle["evaluation_id"]
    assert res1["rule_version"] == "v1"
    
    assert db["decision_support_results"].count_documents({"decision_id": res1["decision_id"]}) == 1
    assert db["decision_support_results"].count_documents({"decision_id": res2["decision_id"]}) == 1
    
    db["decision_support_results"].delete_many({"authorization_id": "AUTH_MOCK"})

# -------------------------------------------------------------
# 13. Hard validator failure denies
# -------------------------------------------------------------
def test_decision_hard_validator_failure_denies(db):
    coding_vals = [
        {"validator": "ARTICLE_ICD10", "status": "FAIL", "reason": "Explicitly noncovered"}
    ]
    bundle = create_mock_evaluation(coding_vals=coding_vals)
    res = PriorAuthorizationDecisionService.generate_decision(bundle)
    
    assert res["recommended_disposition"] == "DENY"
    
    db["decision_support_results"].delete_many({"authorization_id": "AUTH_MOCK"})

# -------------------------------------------------------------
# 14. Real PT Fixture 97110 check
# -------------------------------------------------------------
def test_decision_real_pt_fixture_support(db):
    request_id = "AUTH_PT_FIXTURE_DECISION_TEST"
    
    # Setup patient & provider
    db["patients"].insert_one({
        "patient_id": "PT_PAT_DEC_TEST",
        "first_name": "Test",
        "last_name": "Patient",
        "dob": "1970-05-15",
        "gender": "female",
        "insurance_plan": "Medicare Advantage",
        "member_id": "MBR999"
    })
    db["providers"].insert_one({
        "provider_id": "PT_PROV_DEC_TEST",
        "provider_name": "Dr. Test",
        "facility_name": "Colorado Rehab Center CO"
    })
    db["authorization_requests"].insert_one({
        "request_id": request_id,
        "patient_id": "PT_PAT_DEC_TEST",
        "provider_id": "PT_PROV_DEC_TEST",
        "requested_procedure_code": {
            "source_value": "97110",
            "canonical_value": "97110",
            "display_value": "97110"
        },
        "diagnosis_code": {
            "source_value": "M17.11",
            "canonical_value": "M1711",
            "display_value": "M17.11"
        },
        "request_date": "2026-08-10",
        "clinical_indication": "Osteoarthritis knee joint impairment",
        "provider_justification": "Referred by specialist, conservative treatment B failed after 1 months.",
        "state_code": "CO"
    })
    
    try:
        # 1. Run evaluation first to store bundle
        eval_res = PriorAuthorizationEvaluationService.evaluate_request(request_id)
        
        # 2. Run decision
        dec = PriorAuthorizationDecisionService.generate_decision(eval_res)
        
        # Verify result is PEND because of UNCLEAR musculoskeletal diagnosis
        assert dec["recommended_disposition"] == "PEND"
        assert "PA_MANDATORY_CRITERION_UNCLEAR" in dec["reason_codes"]
        assert len(dec["missing_information"]) == 1
        assert "musculoskeletal" in dec["missing_information"][0]["description"]
        
    finally:
        db["authorization_requests"].delete_one({"request_id": request_id})
        db["patients"].delete_one({"patient_id": "PT_PAT_DEC_TEST"})
        db["providers"].delete_one({"provider_id": "PT_PROV_DEC_TEST"})
        db["evaluation_bundles"].delete_many({"authorization_id": request_id})
        db["decision_support_results"].delete_many({"authorization_id": request_id})

# -------------------------------------------------------------
# 15. API Endpoints check
# -------------------------------------------------------------
def test_decision_api_endpoints(db):
    request_id = "AUTH_PT_API_TEST"
    
    # Cleanup
    db["evaluation_bundles"].delete_many({"authorization_id": request_id})
    db["decision_support_results"].delete_many({"authorization_id": request_id})
    
    # Verify POST returns 404 if no evaluation exists
    post_res = client.post(f"/api/prior-auth/{request_id}/decision-support")
    assert post_res.status_code == 404
    
    # Store mock evaluation bundle in DB
    db["evaluation_bundles"].insert_one({
        "authorization_id": request_id,
        "evaluation_id": "EVAL_API_MOCK_123",
        "policy_context": {"applicable_policies": ["L33942"]},
        "requirement_evaluations": [],
        "coding_validations": [],
        "administrative_validations": [],
        "warnings": [],
        "provenance": {"evaluated_at": "2026-08-16T12:00:00Z", "intake_status": "SUCCESS"}
    })
    
    # POST decision
    post_res2 = client.post(f"/api/prior-auth/{request_id}/decision-support")
    assert post_res2.status_code == 200
    data = post_res2.json()
    assert data["recommended_disposition"] == "APPROVE" # No criteria ➔ all MET fallback
    
    # GET latest decision
    get_res = client.get(f"/api/prior-auth/{request_id}/decision-support")
    assert get_res.status_code == 200
    assert get_res.json()["decision_id"] == data["decision_id"]
    
    # GET decision by ID
    get_id_res = client.get(f"/api/decisions/{data['decision_id']}")
    assert get_id_res.status_code == 200
    
    # GET history
    hist_res = client.get(f"/api/prior-auth/{request_id}/decision-history")
    assert hist_res.status_code == 200
    assert len(hist_res.json()) >= 1
    
    # Cleanup
    db["evaluation_bundles"].delete_many({"authorization_id": request_id})
    db["decision_support_results"].delete_many({"authorization_id": request_id})
