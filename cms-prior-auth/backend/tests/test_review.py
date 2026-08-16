import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.db.connection import db_connection
from app.services.audit import AuditLogService
from app.services.decision_engine import PriorAuthorizationDecisionService
from app.services.explanation import DecisionExplanationService
from app.services.review import PriorAuthorizationReviewCaseService
from app.services.prior_auth_evaluation import PriorAuthorizationEvaluationService

client = TestClient(app)

@pytest.fixture
def db():
    return db_connection.get_db()

def create_base_decision_result(disposition="PEND"):
    return {
        "decision_id": "DEC_TEST_123",
        "evaluation_id": "EVAL_TEST_123",
        "authorization_id": "AUTH_TEST_123",
        "recommended_disposition": disposition,
        "decision_certainty": "HIGH",
        "requires_human_review": True,
        "reason_codes": ["PA_MANDATORY_CRITERION_UNCLEAR"],
        "policy_citations": ["L33942"],
        "patient_provenance": [{"collection": "conditions", "record_id": "cond_1"}],
        "warnings": [],
        "decision_factors": [
            {
                "factor_id": "FAC-REQ-1",
                "factor_type": "CLINICAL_REQUIREMENT",
                "status": "MET",
                "effect": "SUPPORTS_APPROVAL",
                "description": "Physician referral documented."
            },
            {
                "factor_id": "FAC-REQ-2",
                "factor_type": "CLINICAL_REQUIREMENT",
                "status": "UNCLEAR",
                "effect": "BLOCKING_MISSING_INFORMATION",
                "description": "Joint impairment diagnosis missing."
            }
        ],
        "missing_information": [
            {
                "request_type": "CLINICAL_DOCUMENTATION",
                "requirement_id": "REQ-2",
                "description": "Provide joint impairment documentation.",
                "priority": "REQUIRED"
            }
        ]
    }

# -------------------------------------------------------------
# 1. Deterministic Explanation Generation
# -------------------------------------------------------------
def test_deterministic_explanation_generation():
    dec = create_base_decision_result("PEND")
    eval_bundle = {"policy_context": {"applicable_policies": ["L33942"], "related_reference_policies": ["A57311"]}}
    
    exp = DecisionExplanationService.generate_deterministic_explanation(dec, eval_bundle)
    assert exp["recommended_disposition"] == "PEND"
    assert "PENDING" in exp["summary"]
    assert "L33942" in exp["policy_citations"]
    assert len(exp["satisfied_requirements"]) == 1
    assert len(exp["missing_information"]) == 1
    assert exp["generated_by"]["provider"] == "deterministic"

# -------------------------------------------------------------
# 2. LLM explanation validation prevents disposition alteration
# -------------------------------------------------------------
def test_llm_explanation_validation_prevents_disposition_change():
    dec = create_base_decision_result("PEND")
    eval_bundle = {"policy_context": {"applicable_policies": ["L33942"], "related_reference_policies": ["A57311"]}}
    
    # Mock LLM trying to change disposition to APPROVE
    with patch("app.services.explanation.get_llm_provider") as mock_get_llm:
        class FakeLLM:
            model = "mock-model"
            def generate_completion(self, *args, **kwargs):
                return '{"recommended_disposition": "APPROVE", "summary": "LLM approved case"}'
        mock_get_llm.return_value = FakeLLM()
        
        # Trigger generation, it should fail validation and fall back to deterministic (PEND)
        res = DecisionExplanationService.generate_explanation(dec, eval_bundle)
        assert res["recommended_disposition"] == "PEND"
        assert res["generated_by"]["provider"] == "deterministic"

# -------------------------------------------------------------
# 3. LLM failure falls back to deterministic explanation
# -------------------------------------------------------------
def test_llm_failure_falls_back_to_deterministic():
    dec = create_base_decision_result("PEND")
    eval_bundle = {"policy_context": {"applicable_policies": ["L33942"], "related_reference_policies": ["A57311"]}}
    
    with patch("app.services.explanation.get_llm_provider") as mock_get_llm:
        mock_get_llm.side_effect = RuntimeError("OpenRouter timeout")
        
        res = DecisionExplanationService.generate_explanation(dec, eval_bundle)
        assert res["recommended_disposition"] == "PEND"
        assert res["generated_by"]["provider"] == "deterministic"

# -------------------------------------------------------------
# 4. Reviewer actions and override validation
# -------------------------------------------------------------
def test_reviewer_action_and_override_rules(db):
    auth_id = "AUTH_REVIEW_TEST"
    
    # Seed mock dec result
    db["decision_support_results"].delete_many({"authorization_id": auth_id})
    db["reviewer_actions"].delete_many({"authorization_id": auth_id})
    
    db["decision_support_results"].insert_one({
        "decision_id": "DEC_VAL_999",
        "evaluation_id": "EVAL_VAL_999",
        "authorization_id": auth_id,
        "recommended_disposition": "PEND",
        "requires_human_review": True
    })
    
    # 1. Submit ACCEPT action
    action1 = PriorAuthorizationReviewCaseService.record_action(
        authorization_id=auth_id,
        reviewer_id="reviewer_alice",
        action="ACCEPT_RECOMMENDATION",
        reason="Consistent with CMS LCD"
    )
    assert action1["action"] == "ACCEPT_RECOMMENDATION"
    
    # 2. Submit OVERRIDE action
    action2 = PriorAuthorizationReviewCaseService.record_action(
        authorization_id=auth_id,
        reviewer_id="reviewer_bob",
        action="OVERRIDE_RECOMMENDATION",
        reason="Clinical review overrides conservative trial duration.",
        intended_disposition="APPROVE"
    )
    assert action2["action"] == "OVERRIDE_RECOMMENDATION"
    assert action2["intended_disposition"] == "APPROVE"
    
    # Verify original recommendation remains intact
    latest_dec = db["decision_support_results"].find_one({"authorization_id": auth_id})
    assert latest_dec["recommended_disposition"] == "PEND"
    
    # Cleanup
    db["decision_support_results"].delete_many({"authorization_id": auth_id})
    db["reviewer_actions"].delete_many({"authorization_id": auth_id})
    db["audit_events"].delete_many({"authorization_id": auth_id})

# -------------------------------------------------------------
# 5. Review history immutability
# -------------------------------------------------------------
def test_review_history_immutability(db):
    auth_id = "AUTH_IMMUTE_TEST"
    db["reviewer_actions"].delete_many({"authorization_id": auth_id})
    db["decision_support_results"].delete_many({"authorization_id": auth_id})
    
    db["decision_support_results"].insert_one({
        "decision_id": "DEC_IMM",
        "evaluation_id": "EVAL_IMM",
        "authorization_id": auth_id,
        "recommended_disposition": "DENY"
    })
    
    # Log two actions
    PriorAuthorizationReviewCaseService.record_action(auth_id, "rev_1", "ESCALATE", "Needs second opinion")
    PriorAuthorizationReviewCaseService.record_action(auth_id, "rev_1", "OVERRIDE_RECOMMENDATION", "Override to PEND", "PEND")
    
    history = db["reviewer_actions"].count_documents({"authorization_id": auth_id})
    assert history == 2
    
    # Cleanup
    db["reviewer_actions"].delete_many({"authorization_id": auth_id})
    db["decision_support_results"].delete_many({"authorization_id": auth_id})
    db["audit_events"].delete_many({"authorization_id": auth_id})

# -------------------------------------------------------------
# 6. Audit logs generated for milestones
# -------------------------------------------------------------
def test_audit_logs_milestones(db):
    auth_id = "AUTH_AUDIT_TEST"
    db["audit_events"].delete_many({"authorization_id": auth_id})
    
    AuditLogService.log_event(auth_id, "REQUEST_CREATED")
    AuditLogService.log_event(auth_id, "POLICY_ROUTED")
    
    events = AuditLogService.get_events(auth_id)
    assert len(events) == 2
    assert events[0]["event_type"] == "REQUEST_CREATED"
    assert events[1]["event_type"] == "POLICY_ROUTED"
    
    db["audit_events"].delete_many({"authorization_id": auth_id})

# -------------------------------------------------------------
# 7. Custom code request decision unavailable
# -------------------------------------------------------------
def test_custom_code_explanation_unavailable():
    dec = {
        "decision_id": "DEC_CUST",
        "evaluation_id": "EVAL_CUST",
        "authorization_id": "AUTH_CUST",
        "recommended_disposition": "DECISION_SUPPORT_UNAVAILABLE",
        "decision_factors": [],
        "policy_citations": [],
        "patient_provenance": []
    }
    eval_bundle = {"policy_context": {}}
    
    exp = DecisionExplanationService.generate_explanation(dec, eval_bundle)
    assert exp["recommended_disposition"] == "DECISION_SUPPORT_UNAVAILABLE"
    assert "unavailable" in exp["summary"].lower()

# -------------------------------------------------------------
# 8. Real PT case PEND resolution remains
# -------------------------------------------------------------
def test_real_pt_case_pend_resolution(db):
    request_id = "AUTH_PT_FIXTURE_DEC_E2E"
    
    db["patients"].delete_one({"patient_id": "PT_PAT_E2E"})
    db["providers"].delete_one({"provider_id": "PT_PROV_E2E"})
    db["authorization_requests"].delete_one({"request_id": request_id})
    db["evaluation_bundles"].delete_many({"authorization_id": request_id})
    db["decision_support_results"].delete_many({"authorization_id": request_id})
    db["decision_explanations"].delete_many({"decision_id": {"$regex": f"DEC-{request_id}"}})
    
    db["patients"].insert_one({
        "patient_id": "PT_PAT_E2E",
        "first_name": "Test",
        "last_name": "Patient",
        "dob": "1970-05-15",
        "gender": "female",
        "insurance_plan": "Medicare Advantage",
        "member_id": "MBR999"
    })
    db["providers"].insert_one({
        "provider_id": "PT_PROV_E2E",
        "provider_name": "Dr. Test",
        "facility_name": "Colorado Rehab Center CO"
    })
    db["authorization_requests"].insert_one({
        "request_id": request_id,
        "patient_id": "PT_PAT_E2E",
        "provider_id": "PT_PROV_E2E",
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
        # Run pipeline
        eval_res = PriorAuthorizationEvaluationService.evaluate_request(request_id)
        dec_res = PriorAuthorizationDecisionService.generate_decision(eval_res)
        
        # Verify recommended disposition is PEND
        assert dec_res["recommended_disposition"] == "PEND"
        
        # Run explanation synthesis
        exp_res = DecisionExplanationService.generate_explanation(dec_res, eval_res)
        assert exp_res["recommended_disposition"] == "PEND"
        assert len(exp_res["missing_information"]) >= 1
        
    finally:
        db["patients"].delete_one({"patient_id": "PT_PAT_E2E"})
        db["providers"].delete_one({"provider_id": "PT_PROV_E2E"})
        db["authorization_requests"].delete_one({"request_id": request_id})
        db["evaluation_bundles"].delete_many({"authorization_id": request_id})
        db["decision_support_results"].delete_many({"authorization_id": request_id})
        db["decision_explanations"].delete_many({"decision_id": {"$regex": f"DEC-{request_id}"}})

# -------------------------------------------------------------
# 9. API routes validations
# -------------------------------------------------------------
def test_review_api_endpoints(db):
    auth_id = "AUTH_API_REV_TEST"
    db["authorization_requests"].delete_many({"request_id": auth_id})
    db["evaluation_bundles"].delete_many({"authorization_id": auth_id})
    db["decision_support_results"].delete_many({"authorization_id": auth_id})
    db["reviewer_actions"].delete_many({"authorization_id": auth_id})
    
    # Seed mock request
    db["authorization_requests"].insert_one({
        "request_id": auth_id,
        "patient_id": "PT_API_TEST",
        "provider_id": "PROV_API_TEST",
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
        "state_code": "CO"
    })
    
    # Seed mock data
    db["evaluation_bundles"].insert_one({
        "authorization_id": auth_id,
        "evaluation_id": "EVAL_MOCK_API",
        "policy_context": {"applicable_policies": ["L33942"]},
        "requirement_evaluations": [],
        "coding_validations": [],
        "administrative_validations": [],
        "warnings": [],
        "provenance": {"evaluated_at": "2026-08-16T12:00:00Z", "intake_status": "SUCCESS"}
    })
    db["decision_support_results"].insert_one({
        "decision_id": "DEC_MOCK_API",
        "evaluation_id": "EVAL_MOCK_API",
        "authorization_id": auth_id,
        "recommended_disposition": "PEND",
        "missing_information": []
    })
    
    # GET cases list
    res_list = client.get("/api/review/cases")
    assert res_list.status_code == 200
    
    # POST explain
    res_exp = client.post(f"/api/review/cases/{auth_id}/explain")
    assert res_exp.status_code == 200
    assert res_exp.json()["recommended_disposition"] == "PEND"
    
    # GET case details
    res_details = client.get(f"/api/review/cases/{auth_id}")
    assert res_details.status_code == 200
    assert res_details.json()["decision_explanation"] is not None
    
    # POST reviewer action
    res_action = client.post(
        f"/api/review/cases/{auth_id}/action",
        params={
            "action": "ACCEPT_RECOMMENDATION",
            "reason": "Passed coding and clinical review",
            "reviewer_id": "tester_1"
        }
    )
    assert res_action.status_code == 200
    
    # GET history
    res_hist = client.get(f"/api/review/cases/{auth_id}/history")
    assert res_hist.status_code == 200
    assert len(res_hist.json()) >= 1
    
    # GET audit
    res_audit = client.get(f"/api/review/cases/{auth_id}/audit")
    assert res_audit.status_code == 200
    
    # Cleanup
    db["authorization_requests"].delete_many({"request_id": auth_id})
    db["evaluation_bundles"].delete_many({"authorization_id": auth_id})
    db["decision_support_results"].delete_many({"authorization_id": auth_id})
    db["reviewer_actions"].delete_many({"authorization_id": auth_id})
    db["audit_events"].delete_many({"authorization_id": auth_id})
    db["decision_explanations"].delete_many({"decision_id": "DEC_MOCK_API"})
