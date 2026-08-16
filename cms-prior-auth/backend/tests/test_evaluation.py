import pytest
from unittest.mock import patch, MagicMock
from app.db.connection import db_connection
from app.models.patient import ClinicalEvidencePacket, EvidenceProvenance
from app.models.evaluation import PolicyRequirement, PatientEvidence, RequirementEvaluation, CodingValidation, EvaluationBundle
from app.services.requirement_extraction import PolicyRequirementExtractor
from app.services.evidence_matching import PolicyEvidenceMatcher
from app.services.coding_validation import CodingValidationService
from app.services.prior_auth_evaluation import PriorAuthorizationEvaluationService

# -------------------------------------------------------------
# Test Fixture Helper
# -------------------------------------------------------------
@pytest.fixture
def db():
    return db_connection.get_db()

@pytest.fixture(autouse=True)
def mock_llm_provider():
    from app.services.llm import MockLLMProvider
    with patch("app.services.evidence_matching.get_llm_provider", return_value=MockLLMProvider()), \
         patch("app.services.requirement_extraction.get_llm_provider", return_value=MockLLMProvider()):
        yield

# -------------------------------------------------------------
# 1. Policy Requirement Extraction Tests
# -------------------------------------------------------------
def test_requirement_extraction_from_chunk():
    # Test 1: Extract requirements from LCD chunk
    mock_chunks = [{
        "document_type": "LCD",
        "document_id": "L33942",
        "document_version": "50",
        "section": "indication",
        "chunk_id": "LCD:L33942:v50:indication:chunk_01",
        "text": "The patient must be referred for physical therapy by a physician."
    }]
    policy_roles = {"L33942": "APPLICABLE"}
    
    reqs = PolicyRequirementExtractor.extract_requirements(mock_chunks, policy_roles)
    assert len(reqs) > 0
    assert reqs[0].document_id == "L33942"
    assert reqs[0].section == "indication"

def test_requirement_extraction_citation_preserved():
    # Test 2: Requirement extraction citation preserved
    mock_chunks = [{
        "document_type": "LCD",
        "document_id": "L33942",
        "document_version": "50",
        "section": "indication",
        "chunk_id": "LCD:L33942:v50:indication:chunk_01",
        "text": "The patient must be referred for physical therapy by a physician."
    }]
    policy_roles = {"L33942": "APPLICABLE"}
    
    reqs = PolicyRequirementExtractor.extract_requirements(mock_chunks, policy_roles)
    assert reqs[0].citation == "LCD:L33942:v50:indication:chunk_01"

def test_duplicate_requirement_removal():
    # Test 3: Duplicate requirement removal
    mock_chunks = [
        {
            "document_type": "LCD",
            "document_id": "L33942",
            "document_version": "50",
            "section": "indication",
            "chunk_id": "LCD:L33942:v50:indication:chunk_01",
            "text": "The patient must be referred for physical therapy by a physician."
        },
        {
            "document_type": "LCD",
            "document_id": "L33942",
            "document_version": "50",
            "section": "indication",
            "chunk_id": "LCD:L33942:v50:indication:chunk_02",
            "text": "The patient must be referred for physical therapy by a physician."
        }
    ]
    policy_roles = {"L33942": "APPLICABLE"}
    
    reqs = PolicyRequirementExtractor.extract_requirements(mock_chunks, policy_roles)
    # Deduplicator should collapse identical texts under the same document/section (each chunk maps to 3 requirements, duplicates removed leaves 3)
    assert len(reqs) == 3

# -------------------------------------------------------------
# 2. Evidence Matching Status Tests
# -------------------------------------------------------------
def test_diagnosis_match_met():
    # Test 4: Diagnosis MET
    req = PolicyRequirement(
        requirement_id="REQ-01", document_type="LCD", document_id="L33942", document_version="50",
        section="indication", citation="cit-01", policy_role="APPLICABLE",
        requirement_text="Patient has a diagnosis of Osteoarthritis knee (M17.11)",
        requirement_type="DIAGNOSIS"
    )
    
    packet = ClinicalEvidencePacket(
        authorization_id="AUTH001", patient_id="PAT01",
        requested_service={"code": "97110", "display": "PT"},
        diagnosis_codes=["M17.11"],
        conditions=[{"diagnosis_code": {"canonical_value": "M1711", "display_value": "M17.11"}, "_id": "c1"}]
    )
    
    res = PolicyEvidenceMatcher.match_evidence([req], packet)
    assert res[0].status == "MET"
    assert len(res[0].matching_evidence) > 0

def test_diagnosis_match_not_met():
    # Test 5: Diagnosis NOT_MET (when age criteria directly fails)
    req = PolicyRequirement(
        requirement_id="REQ-02", document_type="LCD", document_id="L33942", document_version="50",
        section="indication", citation="cit-01", policy_role="APPLICABLE",
        requirement_text="Patient age is at least 65 years",
        requirement_type="AGE"
    )
    
    packet = ClinicalEvidencePacket(
        authorization_id="AUTH001", patient_id="PAT01",
        requested_service={"code": "97110", "display": "PT"},
        demographics={"age": 52, "dob": "1974-01-01"}
    )
    
    res = PolicyEvidenceMatcher.match_evidence([req], packet)
    assert res[0].status == "NOT_MET"

def test_missing_imaging_unclear():
    # Test 6: Missing evidence/imaging result is UNCLEAR, not NOT_MET
    req = PolicyRequirement(
        requirement_id="REQ-03", document_type="LCD", document_id="L33942", document_version="50",
        section="indication", citation="cit-01", policy_role="APPLICABLE",
        requirement_text="Imaging confirmation of structural impairment (MRI or X-ray)",
        requirement_type="IMAGING"
    )
    
    packet = ClinicalEvidencePacket(
        authorization_id="AUTH001", patient_id="PAT01",
        requested_service={"code": "97110", "display": "PT"},
        diagnostic_results=[] # empty
    )
    
    res = PolicyEvidenceMatcher.match_evidence([req], packet)
    assert res[0].status == "UNCLEAR"

def test_numeric_duration_not_met():
    # Test 7: Duration requirement NOT_MET
    req = PolicyRequirement(
        requirement_id="REQ-04", document_type="LCD", document_id="L33942", document_version="50",
        section="indication", citation="cit-01", policy_role="APPLICABLE",
        requirement_text="Failed conservative treatment B for at least 6 months",
        requirement_type="DURATION",
        extraction_method="LLM"
    )
    
    packet = ClinicalEvidencePacket(
        authorization_id="AUTH001", patient_id="PAT01",
        requested_service={"code": "97110", "display": "PT"},
        clinical_text=[{"value": "Treatment B received for 1 months"}]
    )
    
    res = PolicyEvidenceMatcher.match_evidence([req], packet)
    assert res[0].status == "NOT_MET"

def test_conditional_requirement_not_applicable():
    # Test 8: Conditional requirement resolves to NOT_APPLICABLE if condition doesn't match
    # Since our semantic LLM matcher evaluates conditions, we test LLM provider matching logic
    req = PolicyRequirement(
        requirement_id="REQ-05", document_type="LCD", document_id="L33942", document_version="50",
        section="indication", citation="cit-01", policy_role="APPLICABLE",
        requirement_text="Patient has failed conservative treatment",
        requirement_type="FAILED_TREATMENT",
        conditional=True,
        condition_text="if condition is chronic impairment"
    )
    
    packet = ClinicalEvidencePacket(
        authorization_id="AUTH001", patient_id="PAT01",
        requested_service={"code": "97110", "display": "PT"},
        clinical_text=[{"value": "Patient is undergoing oxygen titration (acute episode)"}]
    )
    
    with patch("app.services.llm.MockLLMProvider.generate_completion") as mock_gen:
        mock_gen.return_value = '{"status": "NOT_APPLICABLE", "matching_evidence_ids": [], "contradicting_evidence_ids": [], "rationale": "Condition is acute, not chronic."}'
        res = PolicyEvidenceMatcher.match_evidence([req], packet)
        assert res[0].status == "NOT_APPLICABLE"

def test_prior_treatment_structured_match():
    # Test 9: Prior treatment structured match
    req = PolicyRequirement(
        requirement_id="REQ-06", document_type="LCD", document_id="L33942", document_version="50",
        section="indication", citation="cit-01", policy_role="APPLICABLE",
        requirement_text="Patient must be under care of specialist physician",
        requirement_type="PROCEDURE"
    )
    
    packet = ClinicalEvidencePacket(
        authorization_id="AUTH001", patient_id="PAT01",
        requested_service={"code": "97110", "display": "PT"},
        clinical_text=[{"value": "Patient is referred under care of oncology physician."}]
    )
    
    res = PolicyEvidenceMatcher.match_evidence([req], packet)
    assert res[0].status == "MET"

def test_narrative_evidence_match():
    # Test 10: Narrative evidence match
    req = PolicyRequirement(
        requirement_id="REQ-07", document_type="LCD", document_id="L33942", document_version="50",
        section="indication", citation="cit-01", policy_role="APPLICABLE",
        requirement_text="Patient has failed conservative therapy",
        requirement_type="FAILED_TREATMENT",
        extraction_method="LLM"
    )
    
    packet = ClinicalEvidencePacket(
        authorization_id="AUTH001", patient_id="PAT01",
        requested_service={"code": "97110", "display": "PT"},
        clinical_text=[{"value": "Conservative treatments failed, escalating care required."}]
    )
    
    res = PolicyEvidenceMatcher.match_evidence([req], packet)
    assert res[0].status == "MET"

# -------------------------------------------------------------
# 3. Label Leakage Protection Tests
# -------------------------------------------------------------
def test_label_leakage_protection_ai_reasoning():
    # Test 11: ai_reasoning is excluded from matched patient evidence
    req = PolicyRequirement(
        requirement_id="REQ-08", document_type="LCD", document_id="L33942", document_version="50",
        section="indication", citation="cit-01", policy_role="APPLICABLE",
        requirement_text="Indication text check",
        requirement_type="OTHER_CLINICAL"
    )
    
    packet = ClinicalEvidencePacket(
        authorization_id="AUTH001", patient_id="PAT01",
        requested_service={"code": "97110", "display": "PT"},
        clinical_text=[
            {"value": "ai_reasoning: Approved based on manual review."},
            {"value": "Patient requires physical therapy due to gait dysfunction."}
        ]
    )
    
    res = PolicyEvidenceMatcher.match_evidence([req], packet)
    # The record containing "ai_reasoning" must be stripped and not matched
    assert not any("ai_reasoning" in m.value for m in res[0].matching_evidence)

def test_label_leakage_protection_outcome_status():
    # Test 12: authorization_status is excluded from matched evidence
    req = PolicyRequirement(
        requirement_id="REQ-09", document_type="LCD", document_id="L33942", document_version="50",
        section="indication", citation="cit-01", policy_role="APPLICABLE",
        requirement_text="Indication checking",
        requirement_type="OTHER_CLINICAL"
    )
    
    packet = ClinicalEvidencePacket(
        authorization_id="AUTH001", patient_id="PAT01",
        requested_service={"code": "97110", "display": "PT"},
        clinical_text=[
            {"value": "status: APPROVED"},
            {"value": "threshold_met: True"}
        ]
    )
    
    res = PolicyEvidenceMatcher.match_evidence([req], packet)
    assert len(res[0].matching_evidence) == 0

def test_missing_evidence_never_automatically_not_met():
    # Test 13: Missing evidence matches remain UNCLEAR
    req = PolicyRequirement(
        requirement_id="REQ-10", document_type="LCD", document_id="L33942", document_version="50",
        section="indication", citation="cit-01", policy_role="APPLICABLE",
        requirement_text="MRI of knee structural findings",
        requirement_type="IMAGING"
    )
    
    packet = ClinicalEvidencePacket(
        authorization_id="AUTH001", patient_id="PAT01",
        requested_service={"code": "97110", "display": "PT"}
    )
    
    res = PolicyEvidenceMatcher.match_evidence([req], packet)
    assert res[0].status == "UNCLEAR"

# -------------------------------------------------------------
# 4. Deterministic Coding Validation Tests
# -------------------------------------------------------------
def test_covered_icd_mapping_pass(db):
    # Test 14: Covered ICD code returns PASS
    res = CodingValidationService.validate_icd10(
        diagnosis_code="C00.0",
        article_id="A58679"
    )
    assert res.status == "PASS"

def test_noncovered_icd_mapping_fail(db):
    # Test 15: Noncovered ICD code returns FAIL
    res = CodingValidationService.validate_icd10(
        diagnosis_code="N17.0",
        article_id="A60155"
    )
    assert res.status == "FAIL"

def test_absent_icd_mapping_unknown(db):
    # Test 16: Absent ICD code returns UNKNOWN
    res = CodingValidationService.validate_icd10(
        diagnosis_code="Z99.9",
        article_id="A58679"
    )
    assert res.status == "UNKNOWN"

def test_lcd_hcpcs_validation(db):
    # Test 17: CPT code matched to LCD
    res = CodingValidationService.validate_hcpcs(
        hcpcs_code="A4223",
        lcd_id="L33610",
        article_id=None
    )
    # Check that LCD mapping validator passes
    lcd_val = next(v for v in res if v.validator == "LCD_HCPCS")
    assert lcd_val.status == "PASS"

def test_article_hcpcs_validation(db):
    # Test 18: CPT code matched to Article
    res = CodingValidationService.validate_hcpcs(
        hcpcs_code="97110",
        lcd_id=None,
        article_id="A57311"
    )
    art_val = next(v for v in res if v.validator == "ARTICLE_HCPCS")
    assert art_val.status == "PASS"

def test_modifier_validation(db):
    # Test 19: Modifiers validated against article mapping
    res = CodingValidationService.validate_modifier(
        modifiers=["59"],
        article_id="A58565"
    )
    assert res.status == "PASS"

def test_missing_modifier_not_falsely_fail(db):
    # Test 20: Missing modifiers returns UNKNOWN (not FAIL)
    res = CodingValidationService.validate_modifier(
        modifiers=[],
        article_id="A58565"
    )
    assert res.status == "UNKNOWN"

def test_bill_type_validation(db):
    # Test 21: Bill type validated against article
    res = CodingValidationService.validate_bill_type(
        bill_type="999",
        article_id="A57414"
    )
    assert res.status == "PASS"

def test_missing_bill_type_not_evaluated(db):
    # Test 22: Missing bill type returns NOT_EVALUATED
    res = CodingValidationService.validate_bill_type(
        bill_type=None,
        article_id="A57414"
    )
    assert res.status == "NOT_EVALUATED"

def test_revenue_code_validation(db):
    # Test 23: Revenue code validated against article
    res = CodingValidationService.validate_revenue_code(
        revenue_code="0409",
        article_id="A57071"
    )
    assert res.status == "PASS"

def test_jurisdiction_mac_validation(db):
    # Test 24: MAC jurisdiction validates successfully
    res = CodingValidationService.validate_jurisdiction(
        state_code="CO",
        lcd_id="L33942"
    )
    assert res.status == "PASS"

def test_date_version_validation():
    # Test 25: Date window check passes or fails appropriately
    policy_doc = {
        "lcd_id": "L33942",
        "effective_date": "2026-08-06",
        "end_date": None
    }
    
    # 2026-08-10 is after effective date -> PASS
    res_pass = CodingValidationService.validate_dates_and_version("2026-08-10", "L33942", policy_doc)
    assert res_pass.status == "PASS"
    
    # 2026-07-11 is before effective date -> FAIL
    res_fail = CodingValidationService.validate_dates_and_version("2026-07-11", "L33942", policy_doc)
    assert res_fail.status == "FAIL"

# -------------------------------------------------------------
# 5. Prior Authorization Evaluation Engine Tests
# -------------------------------------------------------------
def test_broken_policy_reference_warning_preserved(db):
    # Test 26: Broken master records in LCD/Article mappings result in warnings
    mock_routing = {
        "routing_status": "RESOLVED",
        "applicable_ncds": [],
        "applicable_lcds": [{"lcd_id": "L99999", "title": "Missing LCD", "version": "1"}],
        "candidate_ncds": [],
        "candidate_lcds": [],
        "related_articles": []
    }
    mock_retrieval = {"results": []}
    
    with patch("app.services.prior_auth_intake.PriorAuthorizationIntakeService.execute_route_and_retrieve") as mock_intake:
        mock_intake.return_value = {
            "clinical_evidence_packet": ClinicalEvidencePacket(
                authorization_id="AUTH001", patient_id="PAT01",
                requested_service={"code": "97110", "display": "PT"}
            ),
            "policy_routing": mock_routing,
            "policy_retrieval": mock_retrieval,
            "warnings": ["LCD L99999 master record missing from MongoDB."]
        }
        
        res = PriorAuthorizationEvaluationService.evaluate_request("AUTH001")
        assert any("missing" in w.lower() or "partial" in w.lower() for w in res["warnings"])

def test_related_ncd_not_automatically_controlling(db):
    # Test 27: Related reference NCD is not automatically controlling
    mock_routing = {
        "routing_status": "RESOLVED",
        "applicable_ncds": [], # none controlling
        "applicable_lcds": [{"lcd_id": "L33942", "title": "PT", "version": "50"}],
        "candidate_ncds": [],
        "candidate_lcds": [],
        "related_articles": [{"article_id": "A57311", "title": "PT Article"}]
    }
    
    # Mock RAG result returning chunk from related Article A57311
    mock_retrieval = {
        "results": [{
            "document_type": "Article",
            "document_id": "A57311",
            "document_version": "35",
            "section": "coding",
            "chunk_id": "Art:A57311:v35:coding:chunk_01",
            "text": "Article mapping requirements details."
        }]
    }
    
    with patch("app.services.prior_auth_intake.PriorAuthorizationIntakeService.execute_route_and_retrieve") as mock_intake:
        mock_intake.return_value = {
            "clinical_evidence_packet": ClinicalEvidencePacket(
                authorization_id="AUTH001", patient_id="PAT01",
                requested_service={"code": "97110", "display": "PT"}
            ),
            "policy_routing": mock_routing,
            "policy_retrieval": mock_retrieval,
            "warnings": []
        }
        
        res = PriorAuthorizationEvaluationService.evaluate_request("AUTH001")
        # Article requirements should be listed as RELATED_REFERENCE
        assert res["requirements"][0]["policy_role"] == "RELATED_REFERENCE"

def test_custom_proc_code_evaluation_unavailable(db):
    # Test 28: Custom procedure code yields evaluation unavailable
    # Mock intake to return NO_POLICY_FOUND
    with patch("app.services.prior_auth_intake.PriorAuthorizationIntakeService.execute_route_and_retrieve") as mock_intake:
        mock_intake.return_value = {
            "clinical_evidence_packet": ClinicalEvidencePacket(
                authorization_id="AUTH00001", patient_id="PAT014",
                requested_service={"code": "PROC6042", "display": "PROC6042"}
            ),
            "policy_routing": {
                "routing_status": "NO_POLICY_FOUND",
                "applicable_ncds": [], "applicable_lcds": [], "candidate_ncds": [], "candidate_lcds": [], "related_articles": []
            },
            "policy_retrieval": {"results": []},
            "warnings": ["NO_POLICY_FOUND"]
        }
        
        res = PriorAuthorizationEvaluationService.evaluate_request("AUTH00001")
        assert any("unavailable" in w.lower() for w in res["warnings"])
        assert len(res["requirements"]) == 0

def test_provenance_retained(db):
    # Test 29: Evaluation bundle contains provenance mapping tracking matching versions
    with patch("app.services.prior_auth_intake.PriorAuthorizationIntakeService.execute_route_and_retrieve") as mock_intake:
        mock_intake.return_value = {
            "clinical_evidence_packet": ClinicalEvidencePacket(
                authorization_id="AUTH001", patient_id="PAT01",
                requested_service={"code": "97110", "display": "PT"}
            ),
            "policy_routing": {
                "routing_status": "RESOLVED",
                "applicable_ncds": [], "applicable_lcds": [{"lcd_id": "L33942", "title": "PT", "version": "50"}], "candidate_ncds": [], "candidate_lcds": [], "related_articles": []
            },
            "policy_retrieval": {"results": []},
            "warnings": []
        }
        
        res = PriorAuthorizationEvaluationService.evaluate_request("AUTH001")
        assert "evaluated_at" in res["provenance"]
        assert "matching_engine_version" in res["provenance"]

def test_evaluation_bundle_summary_counts(db):
    # Test 30: Evaluation bundle summary counts match expectations
    mock_routing = {
        "routing_status": "RESOLVED",
        "applicable_ncds": [],
        "applicable_lcds": [{"lcd_id": "L33942", "title": "PT", "version": "50"}],
        "candidate_ncds": [],
        "candidate_lcds": [],
        "related_articles": []
    }
    
    # RAG results containing 2 chunks matching PT requirements
    mock_retrieval = {
        "results": [
            {
                "document_type": "LCD",
                "document_id": "L33942",
                "document_version": "50",
                "section": "indication",
                "chunk_id": "LCD:L33942:v50:indication:chunk_02",
                "text": "The patient must be referred for therapy services by a physician."
            },
            {
                "document_type": "LCD",
                "document_id": "L33942",
                "document_version": "50",
                "section": "indication",
                "chunk_id": "LCD:L33942:v50:indication:chunk_03",
                "text": "failed conservative management for at least 6 months"
            }
        ]
    }
    
    with patch("app.services.prior_auth_intake.PriorAuthorizationIntakeService.execute_route_and_retrieve") as mock_intake:
        mock_intake.return_value = {
            "clinical_evidence_packet": ClinicalEvidencePacket(
                authorization_id="AUTH_TEST", patient_id="PAT014",
                requested_service={"code": "97110", "display": "PT"},
                clinical_text=[
                    {"value": "referred by physician specialist"},
                    {"value": "Treatment B received for 1 months"}
                ]
            ),
            "policy_routing": mock_routing,
            "policy_retrieval": mock_retrieval,
            "warnings": []
        }
        
        res = PriorAuthorizationEvaluationService.evaluate_request("AUTH_TEST")
        # 1 met (referral) + 1 not_met (duration/months) -> total = 2 clinical requirements evaluated
        assert res["summary"]["requirements_total"] == 3
        # Assert MET count and NOT_MET count are tracked
        assert res["summary"]["met"] == 1
        assert res["summary"]["not_met"] == 1

# -------------------------------------------------------------
# 6. API Endpoint & Persistence Verification Tests
# -------------------------------------------------------------
def test_evaluation_api_endpoints(db):
    # Test 31: POST /evaluate endpoint returns evaluation details
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    
    mock_routing = {
        "routing_status": "RESOLVED",
        "applicable_ncds": [],
        "applicable_lcds": [{"lcd_id": "L33942", "title": "PT", "version": "50"}],
        "candidate_ncds": [],
        "candidate_lcds": [],
        "related_articles": []
    }
    
    with patch("app.services.prior_auth_intake.PriorAuthorizationIntakeService.execute_route_and_retrieve") as mock_intake:
        mock_intake.return_value = {
            "clinical_evidence_packet": ClinicalEvidencePacket(
                authorization_id="AUTH00001", patient_id="PAT014",
                requested_service={"code": "97110", "display": "PT"}
            ),
            "policy_routing": mock_routing,
            "policy_retrieval": {"results": []},
            "warnings": []
        }
        
        # Test evaluation trigger endpoint
        res = client.post("/api/prior-auth/AUTH00001/evaluate?override_state=CO")
        assert res.status_code == 200
        data = res.json()
        assert "evaluation_id" in data
        assert data["authorization_id"] == "AUTH00001"
        
        # Test latest evaluation fetch endpoint
        latest_res = client.get("/api/prior-auth/AUTH00001/evaluation")
        assert latest_res.status_code == 200
        assert latest_res.json()["evaluation_id"] == data["evaluation_id"]

def test_historical_evaluation_persistence_and_versioning(db):
    # Test 32: Evaluations are persisted in DB, and can be queried by ID
    mock_routing = {
        "routing_status": "RESOLVED",
        "applicable_ncds": [],
        "applicable_lcds": [{"lcd_id": "L33942", "title": "PT", "version": "50"}],
        "candidate_ncds": [],
        "candidate_lcds": [],
        "related_articles": []
    }
    
    with patch("app.services.prior_auth_intake.PriorAuthorizationIntakeService.execute_route_and_retrieve") as mock_intake:
        mock_intake.return_value = {
            "clinical_evidence_packet": ClinicalEvidencePacket(
                authorization_id="AUTH001", patient_id="PAT01",
                requested_service={"code": "97110", "display": "PT"}
            ),
            "policy_routing": mock_routing,
            "policy_retrieval": {"results": []},
            "warnings": []
        }
        
        # Trigger two evaluations to verify they don't overwrite each other (persistence of historical entries)
        res1 = PriorAuthorizationEvaluationService.evaluate_request("AUTH001")
        res2 = PriorAuthorizationEvaluationService.evaluate_request("AUTH001")
        
        assert res1["evaluation_id"] != res2["evaluation_id"]
        
        # Verify both exist separately in MongoDB
        assert db["evaluation_bundles"].count_documents({"evaluation_id": res1["evaluation_id"]}) == 1
        assert db["evaluation_bundles"].count_documents({"evaluation_id": res2["evaluation_id"]}) == 1
        
        # Clean up database entries
        db["evaluation_bundles"].delete_many({"authorization_id": "AUTH001"})

def test_real_physical_therapy_fixture_resolution(db):
    # Test 33: Real Physical Therapy 97110 Colorado fixture resolution
    request_id = "AUTH_PT_FIXTURE_TEST"
    
    # Cleanup
    db["authorization_requests"].delete_one({"request_id": request_id})
    db["patients"].delete_one({"patient_id": "PT_PAT_TEST"})
    db["providers"].delete_one({"provider_id": "PT_PROV_TEST"})
    
    # Setup patient & provider
    db["patients"].insert_one({
        "patient_id": "PT_PAT_TEST",
        "first_name": "Test",
        "last_name": "Patient",
        "dob": "1970-05-15",
        "gender": "female",
        "insurance_plan": "Medicare Advantage",
        "member_id": "MBR999"
    })
    db["providers"].insert_one({
        "provider_id": "PT_PROV_TEST",
        "provider_name": "Dr. Test",
        "facility_name": "Colorado Rehab Center CO"
    })
    db["authorization_requests"].insert_one({
        "request_id": request_id,
        "patient_id": "PT_PAT_TEST",
        "provider_id": "PT_PROV_TEST",
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
        res = PriorAuthorizationEvaluationService.evaluate_request(request_id)
        
        # Verify LCD and Article resolution
        assert "L33942" in res["policy_context"]["applicable_policies"]
        assert "A57311" in res["policy_context"]["related_reference_policies"]
        
        # Verify LCD_HCPCS is WARNING (not FAIL) when mapped via companion Article
        lcd_hcpcs_val = next(v for v in res["coding_validations"] if v["validator"] == "LCD_HCPCS")
        assert lcd_hcpcs_val["status"] == "WARNING"
        assert "A57311" in lcd_hcpcs_val["reason"]
        
        # Verify ARTICLE_HCPCS is PASS
        art_hcpcs_val = next(v for v in res["coding_validations"] if v["validator"] == "ARTICLE_HCPCS")
        assert art_hcpcs_val["status"] == "PASS"
        
        # Verify coding validations status details
        icd_val = next(v for v in res["coding_validations"] if v["validator"] == "ARTICLE_ICD10")
        assert icd_val["status"] == "PASS"
        
        # Verify geography alone does not make an LCD applicable (L34049 is candidate but geography mismatch in CO)
        assert "L34049" in res["policy_context"]["candidate_policies"]
        assert "L34049" not in res["policy_context"]["geography_compatible_policies"]
        
        # Verify L33631 is candidate but geography mismatch in CO
        assert "L33631" in res["policy_context"]["candidate_policies"]
        assert "L33631" not in res["policy_context"]["geography_compatible_policies"]
        
        # Verify L33942 is geography compatible and final applicable LCD
        assert "L33942" in res["policy_context"]["geography_compatible_policies"]
        assert "L33942" in res["policy_context"]["applicable_policies"]
        
        # Verify only final applicable policies contribute mandatory requirements (summary requirements_total is 3)
        assert res["summary"]["requirements_total"] == 3
        
        # Verify administrative jurisdiction check passes
        jur_val = next(v for v in res["administrative_validations"] if v["validator"] == "JURISDICTION")
        assert jur_val["status"] == "PASS"
        
    finally:
        # Cleanup
        db["authorization_requests"].delete_one({"request_id": request_id})
        db["patients"].delete_one({"patient_id": "PT_PAT_TEST"})
        db["providers"].delete_one({"provider_id": "PT_PROV_TEST"})
        db["evaluation_bundles"].delete_many({"authorization_id": request_id})
