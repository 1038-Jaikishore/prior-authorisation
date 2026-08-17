import os
import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.connection import db_connection
from app.services.document_parser import PdfClinicalDocumentParser, DocxClinicalDocumentParser, TextClinicalDocumentParser
from app.services.document_extractor import ClinicalDocumentExtractor
from app.services.prior_auth_intake import PriorAuthorizationIntakeService
from app.services.prior_auth_evaluation import PriorAuthorizationEvaluationService
from app.services.decision_engine import PriorAuthorizationDecisionService
from app.services.explanation import DecisionExplanationService

client = TestClient(app)
FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

@pytest.fixture
def db():
    return db_connection.get_db()

# -------------------------------------------------------------
# 1-6. Document Upload & File Validation Tests
# -------------------------------------------------------------
def test_pdf_upload(db):
    path = os.path.join(FIXTURE_DIR, "native_text.pdf")
    with open(path, "rb") as f:
        res = client.post("/api/documents/upload", files={"file": ("native_text.pdf", f, "application/pdf")})
    assert res.status_code == 200
    data = res.json()
    assert data["document_id"].startswith("DOC-")
    assert data["filename"] == "native_text.pdf"
    assert data["file_type"] == "pdf"
    assert data["upload_status"] == "UPLOADED"
    
    # Cleanup database
    db["patient_documents"].delete_one({"document_id": data["document_id"]})

def test_docx_upload(db):
    path = os.path.join(FIXTURE_DIR, "complete_approve.docx")
    with open(path, "rb") as f:
        res = client.post("/api/documents/upload", files={"file": ("complete_approve.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert res.status_code == 200
    data = res.json()
    assert data["file_type"] == "docx"
    db["patient_documents"].delete_one({"document_id": data["document_id"]})

def test_txt_upload(db):
    path = os.path.join(FIXTURE_DIR, "not_met.txt")
    with open(path, "rb") as f:
        res = client.post("/api/documents/upload", files={"file": ("not_met.txt", f, "text/plain")})
    assert res.status_code == 200
    data = res.json()
    assert data["file_type"] == "txt"
    db["patient_documents"].delete_one({"document_id": data["document_id"]})

def test_unsupported_type_rejected():
    res = client.post("/api/documents/upload", files={"file": ("malicious.exe", io.BytesIO(b"binary"), "application/x-msdownload")})
    assert res.status_code == 400
    assert "not supported" in res.json()["detail"]

def test_oversized_file_rejected():
    # Simulate a file larger than 10MB
    large_stream = io.BytesIO(b"0" * (11 * 1024 * 1024))
    res = client.post("/api/documents/upload", files={"file": ("large.pdf", large_stream, "application/pdf")})
    assert res.status_code == 400
    assert "size exceeds" in res.json()["detail"]

def test_filename_sanitization(db):
    res = client.post("/api/documents/upload", files={"file": ("../../etc/passwd.txt", io.BytesIO(b"content"), "text/plain")})
    assert res.status_code == 200
    data = res.json()
    # Path traversal characters should be stripped or basename extracted
    assert ".." not in data["filename"]
    assert "etc" not in data["filename"]
    assert data["filename"] == "passwd.txt"
    db["patient_documents"].delete_one({"document_id": data["document_id"]})

# -------------------------------------------------------------
# 7-9. Document Text Extraction Tests
# -------------------------------------------------------------
def test_pdf_native_text_parsing():
    path = os.path.join(FIXTURE_DIR, "native_text.pdf")
    parser = PdfClinicalDocumentParser()
    res = parser.parse(path, "DOC_TEST_PDF")
    assert res["document_id"] == "DOC_TEST_PDF"
    assert len(res["pages"]) >= 1
    assert "97110" in res["full_text"]
    assert not res["ocr_used"]
    assert not res["warnings"]

def test_docx_text_parsing():
    path = os.path.join(FIXTURE_DIR, "complete_approve.docx")
    parser = DocxClinicalDocumentParser()
    res = parser.parse(path, "DOC_TEST_DOCX")
    assert len(res["pages"]) >= 1
    assert "Complete Patient" in res["full_text"] or "Approve" in res["full_text"]

def test_txt_text_parsing():
    path = os.path.join(FIXTURE_DIR, "not_met.txt")
    parser = TextClinicalDocumentParser()
    res = parser.parse(path, "DOC_TEST_TXT")
    assert len(res["pages"]) == 1
    assert "NotMet Patient" in res["full_text"]

# -------------------------------------------------------------
# 10-18. LLM Extraction & Safety Validation Tests
# -------------------------------------------------------------
def test_clinical_extraction_json_schema(db):
    path = os.path.join(FIXTURE_DIR, "native_text.pdf")
    parser = PdfClinicalDocumentParser()
    parsed_res = parser.parse(path, "DOC_TEST")
    
    extracted = ClinicalDocumentExtractor.extract_document(parsed_res)
    assert extracted.document_id == "DOC_TEST"
    assert extracted.patient is not None
    assert extracted.requested_service is not None
    assert len(extracted.diagnoses) >= 1
    assert len(extracted.provenance_records) >= 1

def test_missing_fields_retained_null():
    # Mock extractor output with user_prompt "missing"
    parsed_res = {"document_id": "DOC_MISS", "full_text": "absent fields document", "pages": [{"page_number": 1, "text": "absent fields"}]}
    extracted = ClinicalDocumentExtractor.extract_document(parsed_res)
    assert extracted.requested_service.code is None
    assert extracted.geography.state is None

def test_no_hallucinated_diagnosis_code():
    # Mock text containing diagnosis description but no ICD-10 code
    parsed_res = {"document_id": "DOC_NO_CODE", "full_text": "osteoarthritis of right knee", "pages": [{"page_number": 1, "text": "osteoarthritis of right knee"}]}
    extracted = ClinicalDocumentExtractor.extract_document(parsed_res)
    diag = extracted.diagnoses[0]
    assert diag.code is None
    assert diag.code_status == "NOT_DOCUMENTED"

def test_documented_icd_retained_exactly():
    parsed_res = {"document_id": "DOC_ICD", "full_text": "Osteoarthritis M17.11", "pages": [{"page_number": 1, "text": "Osteoarthritis M17.11"}]}
    extracted = ClinicalDocumentExtractor.extract_document(parsed_res)
    assert extracted.diagnoses[0].code == "M17.11"
    assert extracted.diagnoses[0].code_status == "DOCUMENTED"

def test_documented_hcpcs_retained_exactly():
    parsed_res = {"document_id": "DOC_CPT", "full_text": "CPT Code: 97110", "pages": [{"page_number": 1, "text": "CPT Code: 97110"}]}
    extracted = ClinicalDocumentExtractor.extract_document(parsed_res)
    assert extracted.requested_service.code == "97110"

def test_provenance_page_and_text_retained():
    parsed_res = {"document_id": "DOC_PROV", "full_text": "Diagnosis M17.11", "pages": [{"page_number": 1, "text": "Diagnosis M17.11"}]}
    extracted = ClinicalDocumentExtractor.extract_document(parsed_res)
    prov = next(p for p in extracted.provenance_records if p.fact_type == "diagnosis_code")
    assert prov.page_number == 1
    assert "Diagnosis" in prov.source_text

def test_outcome_leakage_ignored():
    # User prompt containing prior authorization approved outcome text
    parsed_res = {"document_id": "DOC_LEAK", "full_text": "Prior authorization approved. Meets policy criteria.", "pages": [{"page_number": 1, "text": "Prior authorization approved. Meets policy"}]}
    extracted = ClinicalDocumentExtractor.extract_document(parsed_res)
    # The output metadata and status shouldn't contain precomputed conclusions
    assert "approved" not in extracted.status.lower()

# -------------------------------------------------------------
# 19-21. Edit History & Confirmation Workflow Tests
# -------------------------------------------------------------
def test_edit_history_retained(db):
    doc_id = "DOC_EDIT_TEST"
    db["document_extractions"].delete_many({"document_id": doc_id})
    db["document_extractions"].insert_one({
        "document_id": doc_id,
        "version": 1,
        "patient": {"name": "Old Name", "dob": "1970-05-15"},
        "edit_history": []
    })
    
    # PATCH endpoint
    res = client.patch(
        f"/api/documents/{doc_id}/extraction",
        json={"patient": {"name": "New Name", "dob": "1970-05-15"}},
        params={"reviewer_id": "rev_test_1"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["version"] == 2
    assert len(data["edit_history"]) == 1
    assert data["edit_history"][0]["original_value"]["name"] == "Old Name"
    assert data["edit_history"][0]["new_value"]["name"] == "New Name"
    assert data["edit_history"][0]["reviewer_id"] == "rev_test_1"
    
    db["document_extractions"].delete_many({"document_id": doc_id})

def test_unconfirmed_evidence_cannot_enter_evaluation(db):
    doc_id = "DOC_UNCONFIRMED"
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["patient_documents"].insert_one({
        "document_id": doc_id,
        "stored_filename": "native_text.pdf",
        "file_type": "pdf"
    })
    db["document_extractions"].delete_many({"document_id": doc_id})
    db["document_extractions"].insert_one({
        "document_id": doc_id,
        "status": "DRAFT_EXTRACTION"
    })
    
    # Generate request should fail
    res = client.post(f"/api/prior-auth/from-document?document_id={doc_id}")
    assert res.status_code == 400
    assert "Reviewer must confirm" in res.json()["detail"]
    
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["document_extractions"].delete_many({"document_id": doc_id})

# -------------------------------------------------------------
# 22-26. Merging, Conflicts & Missing Inputs Tests
# -------------------------------------------------------------
def test_confirmed_evidence_packet_mapping_and_merge(db):
    doc_id = "DOC_MERGE_TEST"
    req_id = "REQ_MERGE_TEST"
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["patient_documents"].insert_one({
        "document_id": doc_id,
        "authorization_id": req_id,
        "patient_id": "PT_MOCK_1",
        "upload_status": "CONFIRMED"
    })
    db["document_extractions"].delete_many({"document_id": doc_id})
    db["document_extractions"].insert_one({
        "document_id": doc_id,
        "status": "CONFIRMED",
        "patient": {"name": "John Doe", "dob": "1970-05-15"},
        "requested_service": {"code": "97110"},
        "diagnoses": [{"code": "M17.11", "description": "Osteoarthritis", "code_status": "DOCUMENTED"}],
        "prior_treatments": [{"treatment_type": "medication", "name": "Drug A", "duration": "1 month"}],
        "provenance_records": [{"fact_type": "requested_procedure_code", "value": "97110", "page_number": 1, "source_text": "CPT 97110"}]
    })
    
    # Mock base auth request
    db["authorization_requests"].delete_many({"request_id": req_id})
    db["authorization_requests"].insert_one({
        "request_id": req_id,
        "patient_id": "PT_MOCK_1",
        "provider_id": "PROV_MOCK_1",
        "requested_procedure_code": {"display_value": "97110"},
        "diagnosis_code": {"display_value": "M17.11"}
    })
    
    # Compile
    res = PriorAuthorizationIntakeService.compile_evidence_packet(req_id)
    packet = res["packet"]
    
    # Confirmed document condition should be merged
    assert len(packet.conditions) >= 1
    assert packet.conditions[0]["source"] == "EXTRACTED_FROM_DOCUMENT"
    assert packet.conditions[0]["document_id"] == doc_id
    
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["document_extractions"].delete_many({"document_id": doc_id})
    db["authorization_requests"].delete_many({"request_id": req_id})

def test_conflicting_evidence_flagged(db):
    doc_id = "DOC_CONFLICT_TEST"
    req_id = "REQ_CONFLICT_TEST"
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["patient_documents"].insert_one({
        "document_id": doc_id,
        "authorization_id": req_id,
        "patient_id": "PT_CONFLICT",
        "upload_status": "CONFIRMED"
    })
    db["patients"].delete_one({"patient_id": "PT_CONFLICT"})
    db["patients"].insert_one({
        "patient_id": "PT_CONFLICT",
        "dob": "1954-03-20"
    })
    db["document_extractions"].delete_many({"document_id": doc_id})
    db["document_extractions"].insert_one({
        "document_id": doc_id,
        "status": "CONFIRMED",
        "patient": {"name": "Conflict Doe", "dob": "1955-03-20"}, # DOB Mismatch!
        "requested_service": {"code": "97110"},
        "diagnoses": []
    })
    db["authorization_requests"].delete_many({"request_id": req_id})
    db["authorization_requests"].insert_one({
        "request_id": req_id,
        "patient_id": "PT_CONFLICT",
        "provider_id": "PROV_MOCK",
        "requested_procedure_code": {"display_value": "97110"},
        "diagnosis_code": {"display_value": "M17.11"}
    })
    
    res = PriorAuthorizationIntakeService.compile_evidence_packet(req_id)
    assert len(res["warnings"]) >= 1
    assert "CONFLICTING_DOCUMENT_EVIDENCE" in res["warnings"][0]
    
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["document_extractions"].delete_many({"document_id": doc_id})
    db["patients"].delete_one({"patient_id": "PT_CONFLICT"})
    db["authorization_requests"].delete_many({"request_id": req_id})

def test_missing_routing_fields_rejected(db):
    doc_id = "DOC_MISSING_ROUTE"
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["patient_documents"].insert_one({
        "document_id": doc_id,
        "upload_status": "CONFIRMED"
    })
    db["document_extractions"].delete_many({"document_id": doc_id})
    db["document_extractions"].insert_one({
        "document_id": doc_id,
        "status": "CONFIRMED",
        "patient": {"name": "Missing Doe"},
        "requested_service": {"code": None}, # Missing CPT
        "geography": {"state": None} # Missing State
    })
    
    res = client.post(f"/api/prior-auth/from-document?document_id={doc_id}")
    assert res.status_code == 400
    assert "Missing mandatory policy routing fields" in res.json()["detail"]
    
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["document_extractions"].delete_many({"document_id": doc_id})

# -------------------------------------------------------------
# 27-33. End-to-End Pipeline Integration Tests
# -------------------------------------------------------------
def test_document_intake_to_prior_auth_decision_flow(db):
    doc_id = "DOC_E2E_MOCK"
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["patient_documents"].insert_one({
        "document_id": doc_id,
        "upload_status": "CONFIRMED"
    })
    db["document_extractions"].delete_many({"document_id": doc_id})
    db["document_extractions"].insert_one({
        "document_id": doc_id,
        "status": "CONFIRMED",
        "patient": {"name": "E2E Approve Patient", "dob": "1954-03-20"},
        "requested_service": {"code": "97110"},
        "diagnoses": [{"code": "M17.11", "description": "Osteoarthritis"}],
        "prior_treatments": [{"treatment_type": "physical_therapy", "name": "Conservative treatment B", "failed": True, "duration": "6 months"}],
        "provenance_records": [{"fact_type": "requested_procedure_code", "value": "97110", "page_number": 1, "source_text": "97110"}]
    })
    
    # 1. Create prior auth request
    res_req = client.post(f"/api/prior-auth/from-document?document_id={doc_id}&hcpcs_override=97110&state_override=CO")
    assert res_req.status_code == 200
    req_data = res_req.json()
    req_id = req_data["request_id"]
    
    # 2. Run Intake Routing & RAG Retrieval
    res_intake = client.post(f"/api/prior-auth/{req_id}/route-and-retrieve")
    assert res_intake.status_code == 200
    
    # 3. Run Clinical Evaluation
    res_eval = client.post(f"/api/prior-auth/{req_id}/evaluate")
    assert res_eval.status_code == 200
    
    # 4. Generate Decision Support
    res_dec = client.post(f"/api/prior-auth/{req_id}/decision-support")
    assert res_dec.status_code == 200
    dec_data = res_dec.json()
    assert dec_data["recommended_disposition"] == "APPROVE"
    
    # 5. Generate Explanation
    res_exp = client.post(f"/api/review/cases/{req_id}/explain")
    assert res_exp.status_code == 200
    assert res_exp.json()["recommended_disposition"] == "APPROVE"
    
    # Cleanup
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["document_extractions"].delete_many({"document_id": doc_id})
    db["authorization_requests"].delete_many({"request_id": req_id})
    db["evaluations"].delete_many({"authorization_id": req_id})
    db["decisions"].delete_many({"authorization_id": req_id})
    db["decision_explanations"].delete_many({"decision_id": {"$regex": f"DEC-{req_id}"}})
    db["audit_events"].delete_many({"authorization_id": req_id})

# -------------------------------------------------------------
# Post-Volume-8: Orchestrated Evaluation & Safety Tests
# -------------------------------------------------------------
def test_unconfirmed_extraction_cannot_evaluate(db):
    doc_id = "DOC_UNCONFIRMED_EVAL"
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["patient_documents"].insert_one({
        "document_id": doc_id,
        "upload_status": "REVIEW_REQUIRED"
    })
    db["document_extractions"].delete_many({"document_id": doc_id})
    db["document_extractions"].insert_one({
        "document_id": doc_id,
        "status": "DRAFT_EXTRACTION"
    })

    res = client.post(f"/api/documents/{doc_id}/evaluate")
    assert res.status_code == 400
    assert res.json()["detail"] == "DOCUMENT_EXTRACTION_NOT_CONFIRMED"

    # Cleanup
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["document_extractions"].delete_many({"document_id": doc_id})

def test_missing_state_requires_manual_completion(db):
    doc_id = "DOC_MISSING_STATE_EVAL"
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["patient_documents"].insert_one({
        "document_id": doc_id,
        "upload_status": "CONFIRMED"
    })
    db["document_extractions"].delete_many({"document_id": doc_id})
    db["document_extractions"].insert_one({
        "document_id": doc_id,
        "status": "CONFIRMED",
        "patient": {"name": "Missing State Patient"},
        "requested_service": {"code": "97110", "date_of_service": "2026-08-10"},
        "geography": {"state": None} # Missing state
    })

    # Evaluates fails with MISSING_ROUTING_GEOGRAPHY
    res = client.post(f"/api/documents/{doc_id}/evaluate")
    assert res.status_code == 400
    assert "MISSING_ROUTING_GEOGRAPHY" in res.json()["detail"]

    # Succeeds when state_override is manually provided
    res_ok = client.post(f"/api/documents/{doc_id}/evaluate?state_override=CO")
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["policy_routing"]["routing_status"] in ["CO_ACTIVE_POLICIES", "PARTIAL_POLICY_DATA"]
    assert data["authorization_request"]["state_code"] == "CO"

    # Cleanup
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["document_extractions"].delete_many({"document_id": doc_id})
    req_id = data["authorization_request"]["request_id"]
    db["authorization_requests"].delete_many({"request_id": req_id})
    db["evaluations"].delete_many({"authorization_id": req_id})
    db["decisions"].delete_many({"authorization_id": req_id})

def test_no_policy_document_ends_safely(db):
    doc_id = "DOC_NO_POLICY_EVAL"
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["patient_documents"].insert_one({
        "document_id": doc_id,
        "upload_status": "CONFIRMED"
    })
    db["document_extractions"].delete_many({"document_id": doc_id})
    db["document_extractions"].insert_one({
        "document_id": doc_id,
        "status": "CONFIRMED",
        "patient": {"name": "No Policy Patient"},
        "requested_service": {"code": "PROC6042", "date_of_service": "2026-08-10"},
        "geography": {"state": "CO"}
    })

    res = client.post(f"/api/documents/{doc_id}/evaluate")
    assert res.status_code == 200
    data = res.json()
    assert data["policy_routing"]["routing_status"] == "NO_POLICY_FOUND"
    assert data["decision_support"]["recommended_disposition"] == "DECISION_SUPPORT_UNAVAILABLE"
    
    # Verify no unrestricted RAG occurs
    assert len(data["policy_retrieval"].get("retrieved_chunks", [])) == 0

    # Cleanup
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["document_extractions"].delete_many({"document_id": doc_id})
    req_id = data["authorization_request"]["request_id"]
    db["authorization_requests"].delete_many({"request_id": req_id})
    db["evaluations"].delete_many({"authorization_id": req_id})
    db["decisions"].delete_many({"authorization_id": req_id})

def test_document_fact_affects_matching_and_provenance(db):
    doc_id = "DOC_PT_FACTS_EVAL"
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["patient_documents"].insert_one({
        "document_id": doc_id,
        "upload_status": "CONFIRMED"
    })
    
    # Scenario A: Extracted document contains conservative therapy failed after 6 months
    db["document_extractions"].delete_many({"document_id": doc_id})
    db["document_extractions"].insert_one({
        "document_id": doc_id,
        "status": "CONFIRMED",
        "patient": {"name": "PT Fact Patient", "dob": "1954-03-20"},
        "requested_service": {"code": "97110", "date_of_service": "2026-08-10"},
        "diagnoses": [{"code": "M17.11", "description": "Osteoarthritis"}],
        "prior_treatments": [
            {"treatment_type": "physical_therapy", "name": "Conservative therapeutic exercise", "duration": "6 months", "failed": True}
        ],
        "provenance_records": [
            {
                "fact_type": "prior_treatments",
                "value": "Conservative therapeutic exercise",
                "page_number": 2,
                "source_text": "Patient completed 6 months of conservative therapeutic exercise without response."
            }
        ]
    })

    res_met = client.post(f"/api/documents/{doc_id}/evaluate?state_override=CO")
    assert res_met.status_code == 200
    data_met = res_met.json()
    
    # Requirement evaluation should be MET
    eval_bundle = data_met["evaluation_bundle"]
    pt_eval = next((ev for ev in eval_bundle["requirement_evaluations"] if "conservative" in ev["requirement_id"].lower() or "therapy" in ev["requirement_id"].lower()), None)
    
    # Verify MET status & Document Provenance survival into evaluation
    if pt_eval:
        assert pt_eval["status"] == "MET"
        prov = pt_eval["patient_provenance"][0]
        assert prov["collection"] == "patient_documents"
        assert prov["record_id"] == doc_id

    # Verify provenance survival into decision factors
    dec_factors = data_met["decision_support"]["decision_factors"]
    assert len(dec_factors) > 0
    for factor in dec_factors:
        if factor.get("patient_provenance"):
            f_prov = factor["patient_provenance"][0]
            assert f_prov["collection"] in [
                "patient_documents", "patients", "authorization_requests", 
                "patient_conditions", "patient_procedures", "patient_medications", 
                "surgeries", "cms_reference"
            ]

    # Scenario B: Remove conservative therapy facts from document extraction
    db["document_extractions"].update_one(
        {"document_id": doc_id},
        {"$set": {"prior_treatments": [], "provenance_records": []}}
    )
    
    # Run evaluation again
    res_unclear = client.post(f"/api/documents/{doc_id}/evaluate?state_override=CO")
    assert res_unclear.status_code == 200
    data_unclear = res_unclear.json()
    pt_eval_unclear = next((ev for ev in data_unclear["evaluation_bundle"]["requirement_evaluations"] if "conservative" in ev["requirement_id"].lower() or "therapy" in ev["requirement_id"].lower()), None)
    if pt_eval_unclear:
        assert pt_eval_unclear["status"] == "UNCLEAR"

    # Scenario C: Contradictory conservative therapy duration of 2 months
    db["document_extractions"].update_one(
        {"document_id": doc_id},
        {"$set": {
            "prior_treatments": [
                {"treatment_type": "physical_therapy", "name": "Conservative therapy", "duration": "2 months", "failed": True}
            ],
            "provenance_records": [
                {
                    "fact_type": "prior_treatments",
                    "value": "Conservative therapy",
                    "page_number": 2,
                    "source_text": "Completed 2 months of therapy."
                }
            ]
        }}
    )
    
    # Run evaluation again
    res_not_met = client.post(f"/api/documents/{doc_id}/evaluate?state_override=CO")
    assert res_not_met.status_code == 200
    data_not_met = res_not_met.json()
    pt_eval_not_met = next((ev for ev in data_not_met["evaluation_bundle"]["requirement_evaluations"] if "conservative" in ev["requirement_id"].lower() or "therapy" in ev["requirement_id"].lower()), None)
    if pt_eval_not_met:
        # Note: L33942 PT conservative therapy requires >=3 months or >=6 months. 2 months is NOT_MET.
        assert pt_eval_not_met["status"] == "NOT_MET"

    # Cleanup
    db["patient_documents"].delete_many({"document_id": doc_id})
    db["document_extractions"].delete_many({"document_id": doc_id})
    req_id = data_met["authorization_request"]["request_id"]
    db["authorization_requests"].delete_many({"request_id": req_id})
    db["evaluations"].delete_many({"authorization_id": req_id})
    db["decisions"].delete_many({"authorization_id": req_id})
