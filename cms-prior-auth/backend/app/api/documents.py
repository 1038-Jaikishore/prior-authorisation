import os
import uuid
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Path, Body
from app.db.connection import db_connection
from app.core.config import settings
from app.models.document import PatientDocument, ExtractedClinicalDocument, EditHistoryEntry
from app.services.document_parser import PdfClinicalDocumentParser, DocxClinicalDocumentParser, TextClinicalDocumentParser
from app.services.document_extractor import ClinicalDocumentExtractor
from app.services.audit import AuditLogService
from app.services.document_evaluation import DocumentPriorAuthEvaluationService

router = APIRouter(tags=["documents"])

# Ensure uploads directory exists
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def sanitize_filename(filename: str) -> str:
    """Sanitizes filename to prevent directory traversal and strip unsafe characters."""
    filename = os.path.basename(filename)
    return "".join(c for c in filename if c.isalnum() or c in "._-").strip()

@router.post("/api/documents/upload", response_model=Dict[str, Any])
def upload_document(file: UploadFile = File(...)):
    """Uploads a clinical patient document (PDF, DOCX, TXT) and validates format constraints."""
    db = db_connection.get_db()
    
    # 1. Validate file format and size
    filename = sanitize_filename(file.filename)
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    
    allowed_types = settings.allowed_document_types.split(",")
    if ext not in allowed_types:
        raise HTTPException(status_code=400, detail=f"File extension '.{ext}' is not supported.")
        
    # Check mime type
    mime_type = file.content_type
    valid_mimes = {
        "pdf": ["application/pdf"],
        "docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream"],
        "txt": ["text/plain"]
    }
    if ext in valid_mimes and mime_type not in valid_mimes[ext]:
        # Log warning but allow if extension matches to prevent client browser mime mismatches
        pass
        
    # Validate size limit
    file.file.seek(0, 2)
    size_bytes = file.file.tell()
    file.file.seek(0)
    
    if size_bytes == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(status_code=400, detail=f"File size exceeds maximum threshold of {settings.max_upload_mb} MB.")
        
    # 2. Store file safely in uploads folder
    doc_id = f"DOC-{str(uuid.uuid4())[:8].upper()}"
    stored_name = f"{doc_id}_{filename}"
    file_path = os.path.join(UPLOAD_DIR, stored_name)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file to disk: {str(e)}")
        
    # 3. Save metadata record in MongoDB (excluding local filesystem paths)
    doc_metadata = {
        "document_id": doc_id,
        "authorization_id": None,
        "patient_id": None,
        "filename": filename,
        "file_type": ext,
        "mime_type": mime_type,
        "upload_status": "UPLOADED",
        "extraction_status": "PENDING",
        "page_count": 0,
        "created_at": datetime.utcnow().isoformat(),
        "source_type": "UPLOADED_DOCUMENT",
        "stored_filename": stored_name
    }
    db["patient_documents"].insert_one(doc_metadata)
    
    # Audit log (use "SYSTEM" as auth ID since request isn't created yet)
    AuditLogService.log_event(
        authorization_id="SYSTEM",
        event_type="DOCUMENT_UPLOADED",
        actor_id="system",
        actor_type="SYSTEM",
        metadata={"document_id": doc_id, "filename": filename}
    )
    
    del doc_metadata["_id"]
    del doc_metadata["stored_filename"]
    return doc_metadata

@router.get("/api/documents/{document_id}", response_model=Dict[str, Any])
def get_document_metadata(document_id: str):
    """Retrieves patient document upload metadata."""
    db = db_connection.get_db()
    doc = db["patient_documents"].find_one({"document_id": document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document record not found.")
        
    doc["_id"] = str(doc["_id"])
    doc.pop("stored_filename", None)
    return doc

@router.post("/api/documents/{document_id}/extract", response_model=Dict[str, Any])
def extract_document_facts(document_id: str):
    """Triggers parsing and LLM structured extraction service for an uploaded document."""
    db = db_connection.get_db()
    
    doc = db["patient_documents"].find_one({"document_id": document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document record not found.")
        
    file_path = os.path.join(UPLOAD_DIR, doc["stored_filename"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Physical document file missing from server storage.")
        
    # 1. Parse document text page-by-page
    file_type = doc["file_type"]
    if file_type == "pdf":
        parser = PdfClinicalDocumentParser()
    elif file_type == "docx":
        parser = DocxClinicalDocumentParser()
    else:
        parser = TextClinicalDocumentParser()
        
    parsed_res = parser.parse(file_path, document_id)
    page_count = len(parsed_res["pages"])
    
    # Update parsed pages and counts
    db["patient_documents"].update_one(
        {"document_id": document_id},
        {
            "$set": {
                "upload_status": "PARSED",
                "page_count": page_count,
                "warnings": parsed_res.get("warnings", [])
            }
        }
    )
    
    # Audit log
    AuditLogService.log_event(
        authorization_id="SYSTEM",
        event_type="DOCUMENT_PARSED",
        actor_id="system",
        actor_type="SYSTEM",
        metadata={"document_id": document_id, "pages": page_count, "parser": parsed_res["parser"]}
    )
    
    # 2. Extract facts via ClinicalDocumentExtractor
    try:
        extracted_doc = ClinicalDocumentExtractor.extract_document(parsed_res)
    except Exception as e:
        db["patient_documents"].update_one(
            {"document_id": document_id},
            {"$set": {"upload_status": "EXTRACTION_FAILED"}}
        )
        raise HTTPException(status_code=522, detail=f"LLM Clinical Extraction execution failed: {str(e)}")
        
    # Store draft extraction in document_extractions collection
    db["document_extractions"].delete_many({"document_id": document_id})
    extracted_dict = extracted_doc.model_dump()
    db["document_extractions"].insert_one(extracted_dict)
    
    # Update status in metadata
    db["patient_documents"].update_one(
        {"document_id": document_id},
        {"$set": {"upload_status": "REVIEW_REQUIRED", "extraction_status": "COMPLETED"}}
    )
    
    # Audit log
    AuditLogService.log_event(
        authorization_id="SYSTEM",
        event_type="DOCUMENT_EXTRACTION_CREATED",
        actor_id="system",
        actor_type="SYSTEM",
        metadata={"document_id": document_id}
    )
    
    if "_id" in extracted_dict:
        extracted_dict["_id"] = str(extracted_dict["_id"])
    return extracted_dict

@router.get("/api/documents/{document_id}/extraction", response_model=Dict[str, Any])
def get_document_extraction(document_id: str):
    """Retrieves the draft clinical extraction facts for editing."""
    db = db_connection.get_db()
    extraction = db["document_extractions"].find_one({"document_id": document_id})
    if not extraction:
        raise HTTPException(status_code=404, detail="Document extraction draft not found.")
        
    extraction["_id"] = str(extraction["_id"])
    return extraction

@router.patch("/api/documents/{document_id}/extraction", response_model=Dict[str, Any])
def edit_document_extraction(
    document_id: str,
    update_data: Dict[str, Any] = Body(...),
    reviewer_id: str = Query("demo_reviewer", description="ID of reviewing nurse or specialist")
):
    """Allows a reviewer to edit, add, or remove clinical facts, saving edit histories."""
    db = db_connection.get_db()
    
    current = db["document_extractions"].find_one({"document_id": document_id})
    if not current:
        raise HTTPException(status_code=404, detail="Document extraction record not found.")
        
    # Build edit logs
    edit_logs = current.get("edit_history", [])
    new_version = current.get("version", 1) + 1
    
    for field_k, new_val in update_data.items():
        if field_k in ["document_id", "version", "edit_history"]:
            continue
        orig_val = current.get(field_k)
        if orig_val != new_val:
            edit_logs.append({
                "original_value": orig_val,
                "new_value": new_val,
                "reviewer_id": reviewer_id,
                "timestamp": datetime.utcnow().isoformat(),
                "edit_reason": "Manual reviewer corrections during confirmation"
            })
            
    # Update draft payload
    update_fields = {k: v for k, v in update_data.items() if k not in ["_id", "document_id", "version", "edit_history"]}
    update_fields["version"] = new_version
    update_fields["edit_history"] = edit_logs
    
    db["document_extractions"].update_one(
        {"document_id": document_id},
        {"$set": update_fields}
    )
    
    # Audit log
    AuditLogService.log_event(
        authorization_id="SYSTEM",
        event_type="DOCUMENT_EXTRACTION_EDITED",
        actor_id=reviewer_id,
        actor_type="REVIEWER",
        metadata={"document_id": document_id, "new_version": new_version}
    )
    
    updated_doc = db["document_extractions"].find_one({"document_id": document_id})
    updated_doc["_id"] = str(updated_doc["_id"])
    return updated_doc

@router.post("/api/documents/{document_id}/confirm", response_model=Dict[str, Any])
def confirm_document_extraction(
    document_id: str,
    reviewer_id: str = Query("demo_reviewer")
):
    """Confirms the extracted patient clinical evidence facts, locking modifications."""
    db = db_connection.get_db()
    
    extraction = db["document_extractions"].find_one({"document_id": document_id})
    if not extraction:
        raise HTTPException(status_code=404, detail="Document extraction draft not found.")
        
    # Update status to confirmed
    db["document_extractions"].update_one(
        {"document_id": document_id},
        {"$set": {"status": "CONFIRMED"}}
    )
    db["patient_documents"].update_one(
        {"document_id": document_id},
        {"$set": {"upload_status": "CONFIRMED"}}
    )
    
    # Audit log
    AuditLogService.log_event(
        authorization_id="SYSTEM",
        event_type="DOCUMENT_EXTRACTION_CONFIRMED",
        actor_id=reviewer_id,
        actor_type="REVIEWER",
        metadata={"document_id": document_id}
    )
    
    return {"status": "success", "document_id": document_id, "extraction_status": "CONFIRMED"}

@router.post("/api/prior-auth/from-document", response_model=Dict[str, Any])
def create_prior_auth_from_document(
    document_id: str = Query(...),
    hcpcs_override: Optional[str] = Query(None),
    state_override: Optional[str] = Query(None),
    dos_override: Optional[str] = Query(None),
    reviewer_id: str = Query("demo_reviewer")
):
    """Generates a PatientPriorAuthRequest request record from confirmed document facts."""
    db = db_connection.get_db()
    
    doc = db["patient_documents"].find_one({"document_id": document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document record not found.")
        
    extraction = db["document_extractions"].find_one({"document_id": document_id})
    if not extraction:
        raise HTTPException(status_code=404, detail="Document extraction draft not found.")
        
    # Enforce confirmation before prior auth generation
    if extraction.get("status") != "CONFIRMED":
        raise HTTPException(status_code=400, detail="Cannot run prior authorization. Reviewer must confirm extracted facts first.")
        
    # Extract HCPCS/CPT and check for overrides
    req_service = extraction.get("requested_service", {})
    hcpcs = hcpcs_override or req_service.get("code")
    
    # Extract geography and check overrides
    geography = extraction.get("geography", {})
    state = state_override or geography.get("state")
    
    # Extract Date of Service
    dos = dos_override or req_service.get("date_of_service")
    if not dos:
        # Fallback to current request date
        dos = datetime.utcnow().strftime("%Y-%m-%d")
        
    # Require routing keys
    if not hcpcs or not state:
        raise HTTPException(
            status_code=400,
            detail=f"Missing mandatory policy routing fields: hcpcs={hcpcs}, state={state}. Prompts manual input."
        )
        
    # Resolve Patient
    patient = extraction.get("patient", {})
    patient_id = doc.get("patient_id")
    if not patient_id:
        patient_id = f"PT_DOC_{str(uuid.uuid4())[:6].upper()}"
        db["patients"].insert_one({
            "patient_id": patient_id,
            "first_name": patient.get("name", "Unknown").split(" ")[0],
            "last_name": patient.get("name", "Unknown").split(" ")[-1] if " " in patient.get("name", "") else "",
            "dob": patient.get("dob") or "1970-01-01",
            "gender": patient.get("gender") or "unknown",
            "insurance_plan": "Medicare Advantage",
            "member_id": f"MBR_{patient_id}"
        })
        db["patient_documents"].update_one(
            {"document_id": document_id},
            {"$set": {"patient_id": patient_id}}
        )
        
    # Create request
    request_id = f"AUTH-DOC-{str(uuid.uuid4())[:6].upper()}"
    
    # Get diagnoses codes list
    diag_codes = []
    for d in extraction.get("diagnoses", []):
        if d.get("code"):
            diag_codes.append({
                "source_value": d["code"],
                "canonical_value": d["code"].replace(".", ""),
                "display_value": d["code"]
            })
            
    if not diag_codes:
        diag_codes = [{"source_value": "M17.11", "canonical_value": "M1711", "display_value": "M17.11"}]
        
    auth_request = {
        "request_id": request_id,
        "patient_id": patient_id,
        "provider_id": extraction.get("provider", {}).get("npi") or "PROV_MOCK",
        "requested_procedure_code": {
            "source_value": hcpcs,
            "canonical_value": hcpcs,
            "display_value": hcpcs
        },
        "diagnosis_code": diag_codes[0] if len(diag_codes) == 1 else diag_codes,
        "request_date": dos,
        "clinical_indication": extraction.get("clinical_indication") or "",
        "provider_justification": extraction.get("provider_justification") or "",
        "state_code": state,
        "source": f"uploaded_document_{document_id}"
    }
    
    db["authorization_requests"].insert_one(auth_request)
    
    # Update document link
    db["patient_documents"].update_one(
        {"document_id": document_id},
        {"$set": {"authorization_id": request_id}}
    )
    
    # Audit log
    AuditLogService.log_event(
        authorization_id=request_id,
        event_type="DOCUMENT_ATTACHED_TO_AUTHORIZATION",
        actor_id=reviewer_id,
        actor_type="REVIEWER",
        metadata={"document_id": document_id}
    )
    
    auth_request["_id"] = str(auth_request["_id"])
    return auth_request

@router.post("/api/prior-auth/{authorization_id}/documents", response_model=Dict[str, Any])
def attach_document_to_authorization(
    authorization_id: str,
    document_id: str = Query(...),
    reviewer_id: str = Query("demo_reviewer")
):
    """Attaches an uploaded document to an existing prior authorization case."""
    db = db_connection.get_db()
    
    req = db["authorization_requests"].find_one({"request_id": authorization_id})
    if not req:
        raise HTTPException(status_code=404, detail="Authorization request not found.")
        
    doc = db["patient_documents"].find_one({"document_id": document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document record not found.")
        
    db["patient_documents"].update_one(
        {"document_id": document_id},
        {"$set": {"authorization_id": authorization_id, "patient_id": req["patient_id"]}}
    )
    
    # Audit log
    AuditLogService.log_event(
        authorization_id=authorization_id,
        event_type="DOCUMENT_ATTACHED_TO_AUTHORIZATION",
        actor_id=reviewer_id,
        actor_type="REVIEWER",
        metadata={"document_id": document_id}
    )
    
    return {"status": "success", "authorization_id": authorization_id, "document_id": document_id}

@router.post("/api/documents/{document_id}/evaluate", response_model=Dict[str, Any])
def evaluate_document_endpoint(
    document_id: str,
    hcpcs_override: Optional[str] = Query(None),
    state_override: Optional[str] = Query(None),
    dos_override: Optional[str] = Query(None),
    reviewer_id: str = Query("demo_reviewer")
):
    """Triggers the full orchestration service for a confirmed document, returning evaluations and decisions."""
    try:
        return DocumentPriorAuthEvaluationService.evaluate_document(
            document_id=document_id,
            hcpcs_override=hcpcs_override,
            state_override=state_override,
            dos_override=dos_override,
            reviewer_id=reviewer_id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
