import os
import pytest
from unittest.mock import patch, MagicMock
from app.db.connection import db_connection
from app.models.patient import PatientPriorAuthRequest, ClinicalEvidencePacket
from app.models.policy import PolicyRoutingRequest, PolicyRoutingResponse
from app.services.prior_auth_intake import PriorAuthorizationIntakeService
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(scope="module")
def db():
    return db_connection.get_db()

# -------------------------------------------------------------
# Ingestion / Audit Verification Tests (1-8)
# -------------------------------------------------------------
def test_audited_reports_exist():
    # Test 1: Confirm audit files generated
    assert os.path.exists("reports/patient_dataset_audit.md")
    assert os.path.exists("reports/patient_data_dictionary.json")
    assert os.path.exists("reports/patient_relationship_report.md")
    assert os.path.exists("reports/patient_data_quality_report.json")
    assert os.path.exists("reports/patient_field_role_map.md")

def test_patient_joins(db):
    # Test 2, 3, 4: Patient -> conditions/procedures/encounters join checks
    cond = db["patient_conditions"].find_one()
    if cond:
        patient_id = cond["patient_id"]
        patient = db["patients"].find_one({"patient_id": patient_id})
        assert patient is not None, f"Condition patient ID '{patient_id}' not found in patients."

    proc = db["patient_procedures"].find_one()
    if proc:
        patient_id = proc["patient_id"]
        patient = db["patients"].find_one({"patient_id": patient_id})
        assert patient is not None, f"Procedure patient ID '{patient_id}' not found in patients."

    enc = db["encounters"].find_one()
    if enc:
        patient_id = enc["patient_id"]
        patient = db["patients"].find_one({"patient_id": patient_id})
        assert patient is not None, f"Encounter patient ID '{patient_id}' not found in patients."

def test_auth_request_joins(db):
    # Test 5, 6: Authorization -> patient/provider join checks
    req = db["authorization_requests"].find_one()
    if req:
        patient_id = req["patient_id"]
        provider_id = req["provider_id"]
        patient = db["patients"].find_one({"patient_id": patient_id})
        provider = db["providers"].find_one({"provider_id": provider_id})
        assert patient is not None
        assert provider is not None

def test_idempotent_ingestion(db):
    # Test 7: Verify running ingestion twice updates rows without duplicates
    # Fetch initial count
    initial_count = db["patients"].count_documents({})
    
    # Run mock ingestion again
    from scripts.ingest_patient_data import ingest_data
    ingest_data(full_rebuild=False)
    
    post_count = db["patients"].count_documents({})
    assert initial_count == post_count, "Idempotent ingestion failed: duplicated patient records created."

def test_label_leakage_classification():
    # Test 8: Verify role map excludes AI reasoning from facts
    assert os.path.exists("reports/patient_field_role_map.md")
    with open("reports/patient_field_role_map.md", "r") as f:
        content = f.read()
    assert "ai_reasoning" in content
    assert "AI_GENERATED_LABEL" in content

# -------------------------------------------------------------
# Evidence Packet Verification Tests (9-15)
# -------------------------------------------------------------
def test_evidence_packet_inclusion(db):
    # Test 9, 10, 11, 12: Correct inclusion of clinical tables
    req = db["authorization_requests"].find_one()
    if not req:
        pytest.skip("No authorization requests present.")
        
    res = PriorAuthorizationIntakeService.compile_evidence_packet(req["request_id"])
    packet = res["packet"]
    
    # Check conditions
    cond_db = list(db["patient_conditions"].find({"patient_id": req["patient_id"]}))
    assert len(packet.conditions) == len(cond_db)
    
    # Check procedures
    proc_db = list(db["patient_procedures"].find({"patient_id": req["patient_id"]}))
    assert len(packet.procedures) == len(proc_db)
    
    # Check diagnostic results
    diag_db = list(db["diagnostic_results"].find({"patient_id": req["patient_id"]}))
    assert len(packet.diagnostic_results) == len(diag_db)
    
    # Check allergies
    allergy_db = list(db["allergies"].find({"patient_id": req["patient_id"]}))
    assert len(packet.allergies) == len(allergy_db)

def test_evidence_provenance(db):
    # Test 13: Provenance retained
    req = db["authorization_requests"].find_one()
    if req:
        res = PriorAuthorizationIntakeService.compile_evidence_packet(req["request_id"])
        packet = res["packet"]
        assert len(packet.provenance) > 0
        for prov in packet.provenance:
            assert prov.fact_type is not None
            assert prov.source_collection is not None
            assert prov.source_record_id is not None
            assert prov.source_field is not None

def test_no_clinical_fabrication(db):
    # Test 14: Missing evidence is recorded, not fabricated
    req = db["authorization_requests"].find_one()
    if req:
        # Fetch with clean patient that has missing diagnostic results
        res = PriorAuthorizationIntakeService.compile_evidence_packet(req["request_id"])
        packet = res["packet"]
        # If the patient has no vital signs in DB, it shouldn't have them in the packet
        vitals_db = list(db["vital_signs"].find({"patient_id": req["patient_id"]}))
        assert len(packet.vital_signs) == len(vitals_db)

def test_precomputed_labels_exclusion(db):
    # Test 15: AI precomputed outcomes excluded from evidence logic
    req = db["authorization_requests"].find_one()
    if req:
        res = PriorAuthorizationIntakeService.compile_evidence_packet(req["request_id"])
        packet = res["packet"]
        
        # Verify that ai_reasoning values are NOT loaded into the packet clinical fields
        for prov in packet.provenance:
            assert prov.source_field != "ai_reasoning", "AI reasoning label leaked into packet evidence."

# -------------------------------------------------------------
# Integration / Mapping Verification Tests (16-20)
# -------------------------------------------------------------
def test_auth_to_routing_request(db):
    # Test 16: Check mapping from request details to routing request properties
    req = db["authorization_requests"].find_one()
    if req:
        res = PriorAuthorizationIntakeService.compile_evidence_packet(req["request_id"])
        packet = res["packet"]
        
        hcpcs_code = packet.requested_service["code"]
        first_diag = packet.diagnosis_codes[0] if packet.diagnosis_codes else "None"
        
        routing_req = PolicyRoutingRequest(
            hcpcs_code=hcpcs_code,
            state_code="CO",
            date_of_service=req["request_date"]
        )
        assert routing_req.hcpcs_code == req["requested_procedure_code"]["canonical_value"]
        assert routing_req.date_of_service == req["request_date"]

def test_routing_and_retrieval_integration(db):
    # Test 17, 18: Prior auth -> Volume 3 router -> Volume 4 RAG
    # Look up Colorado request
    # AUTH00001 maps to L33942 during ingestion checks
    from app.services.policy_routing import PolicyRoutingService
    
    mock_response = PolicyRoutingResponse(
        routing_status="RESOLVED",
        applicable_ncds=[],
        applicable_lcds=[{
            "lcd_id": "L33942",
            "title": "Non-Invasive Ear or Pulse Oximetry",
            "version": "50",
            "effective_date": "2020-01-01"
        }],
        candidate_ncds=[],
        candidate_lcds=[],
        related_articles=[{
            "article_id": "A57311",
            "title": "Billing and Coding: Non-Invasive Ear or Pulse Oximetry",
            "article_version": "1",
            "effective_date": "2020-01-01"
        }],
        warnings=[],
        normalized_request={},
        routing_confidence=1.0
    )
    
    req = db["authorization_requests"].find_one({"request_id": "AUTH00001"})
    if req:
        with patch.object(PolicyRoutingService, "route_policy", return_value=mock_response):
            res = PriorAuthorizationIntakeService.execute_route_and_retrieve(
                request_id="AUTH00001",
                override_state="CO"
            )
            # Should resolve policy routing NCDs/LCDs
            assert res["policy_routing"].routing_status == "RESOLVED"
            # Should resolve vector search policy chunks
            assert len(res["policy_retrieval"]["results"]) > 0

def test_missing_geography_handling(db):
    # Test 19: Missing state geography triggers MISSING_ROUTING_GEOGRAPHY status
    req = db["authorization_requests"].find_one()
    if req:
        # Set state_code override to None
        res = PriorAuthorizationIntakeService.execute_route_and_retrieve(
            request_id=req["request_id"],
            override_state=None
        )
        # Verify status flag returns missing geography
        assert res["policy_routing"]["routing_status"] == "MISSING_ROUTING_GEOGRAPHY"

def test_broken_reference_warning(db):
    # Test 20: Broken reference warnings preserved
    # Map a mock broken article relationship
    db["lcd_article_relationships"].insert_one({
        "lcd_id_numeric": "33942",
        "lcd_version": "50",
        "article_id_numeric": "99999", # missing
        "article_version": "1",
        "source_file": "lcd_article_relationship.csv"
    })
    
    from app.services.policy_routing import PolicyRoutingService
    
    mock_response = PolicyRoutingResponse(
        routing_status="RESOLVED",
        applicable_ncds=[],
        applicable_lcds=[{
            "lcd_id": "L33942",
            "title": "Non-Invasive Ear or Pulse Oximetry",
            "version": "50",
            "effective_date": "2020-01-01"
        }],
        candidate_ncds=[],
        candidate_lcds=[],
        related_articles=[{
            "article_id": "A99999",
            "title": "Billing and Coding: Broken Reference",
            "article_version": "1",
            "effective_date": "2020-01-01"
        }],
        warnings=["Some relationship references point to master documents missing from the database."],
        normalized_request={},
        routing_confidence=1.0
    )
    
    try:
        # Route AUTH00001 (which maps to L33942)
        with patch.object(PolicyRoutingService, "route_policy", return_value=mock_response):
            res = PriorAuthorizationIntakeService.execute_route_and_retrieve(
                request_id="AUTH00001",
                override_state="CO"
            )
            assert any("missing" in w.lower() or "unresolved" in w.lower() or "partial" in w.lower() or "not indexed" in w.lower() for w in res["warnings"])
    finally:
        db["lcd_article_relationships"].delete_one({"lcd_id_numeric": "33942", "article_id_numeric": "99999"})

# -------------------------------------------------------------
# API Endpoints Verification Tests (21-23)
# -------------------------------------------------------------
def test_api_list_requests():
    # Test 21: GET /api/prior-auth
    res = client.get("/api/prior-auth")
    assert res.status_code == 200
    assert len(res.json()) > 0

def test_api_build_evidence():
    # Test 22: POST /api/prior-auth/{id}/build-evidence
    res = client.post("/api/prior-auth/AUTH00001/build-evidence")
    assert res.status_code == 200
    data = res.json()
    assert "evidence_packet" in data
    
    db = db_connection.get_db()
    req = db["authorization_requests"].find_one({"request_id": "AUTH00001"})
    assert data["evidence_packet"]["patient_id"] == req["patient_id"]

def test_api_route_and_retrieve_endpoint():
    # Test 23: POST /api/prior-auth/{id}/route-and-retrieve
    res = client.post("/api/prior-auth/AUTH00001/route-and-retrieve?override_state=CO")
    assert res.status_code == 200
    data = res.json()
    assert "policy_routing" in data
    assert "policy_retrieval" in data
