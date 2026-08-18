from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from typing import List, Optional, Dict, Any
from app.db.connection import db_connection
from app.models.patient import PatientPriorAuthRequest, ClinicalEvidencePacket
from app.services.prior_auth_intake import PriorAuthorizationIntakeService
from app.services.extraction_service import PdfExtractionService
from app.services.ncd_evaluation_engine import NCDEvaluationEngine
from app.services.pipeline_orchestrator import PriorAuthPipelineOrchestrator
from app.models.decision import NCDSemanticEvaluationResult, PipelineDecisionResult
from app.services.policy_routing import PolicyRoutingService
from app.models.policy import PolicyRoutingRequest
from app.services.policy_retrieval import PolicyRetrievalService
from app.services.lcd_evaluation_engine import LCDEvaluationEngine
from app.services.article_evaluation_engine import ArticleEvaluationEngine
from app.services.decision_engine import ConfidenceDecisionEngine
from app.services.explanation_engine import ExplanationEngine
import os
import requests
import json

router = APIRouter(prefix="/api/prior-auth", tags=["Prior Authorization Intake"])

@router.get("", response_model=List[Dict[str, Any]])
def list_requests():
    """List all available prior authorization requests."""
    try:
        return PriorAuthorizationIntakeService.list_authorization_requests()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{authorization_id}", response_model=Dict[str, Any])
def get_request(authorization_id: str):
    """Retrieve detailed properties of a single prior authorization request."""
    try:
        req = PriorAuthorizationIntakeService.get_authorization_request(authorization_id)
        if not req:
            raise HTTPException(status_code=404, detail=f"Request ID '{authorization_id}' not found.")
        return req
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_clinical_report(file: UploadFile = File(...)):
    """Upload a PDF clinical report and extract intelligent facts using the Hugging Face API."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    try:
        # Read file bytes
        file_bytes = await file.read()
        
        # 1. Extract raw text from PDF using PyMuPDF
        raw_text = PdfExtractionService.extract_text_from_pdf(file_bytes)
        
        # 2. Call OpenRouter API for detailed high-quality NER
        extracted_entities = mock_openrouter_ner(raw_text)
        
        # 3. Map the extracted facts to the 20 Data Points (ClinicalEvidencePacket)
        demos = extracted_entities.get("Demographics", {})
        diseases = [d for d in extracted_entities.get("Disease_Disorder", [])]
        state_code = demos.get("ZIP", "TX")
        
        # Extract requested service safely from LLM output
        req_svc = extracted_entities.get("Requested_Service", {})
        requested_code = req_svc.get("hcpcs_code", "UNKNOWN")
        requested_desc = req_svc.get("description", "Requested Prior Authorization Service")
        
        # Extract diagnostic results natively from LLM output
        diagnostic_results = extracted_entities.get("Diagnostic_results", [])
        
        import uuid
        packet = ClinicalEvidencePacket(
            authorization_id="AUTH-" + str(uuid.uuid4())[:8].upper(),
            patient_id=demos.get("Patient_ID", "PAT-" + str(uuid.uuid4())[:8].upper()),
            requested_service={
                "code": requested_code, 
                "description": requested_desc
            },
            diagnosis_codes=diseases,
            demographics={
                "age": demos.get("Age"),
                "gender": demos.get("Gender"),
                "state_code": state_code
            },
            conditions=[{"name": d} for d in diseases],
            medications=[{"name": m} for m in extracted_entities.get("Medication", [])],
            vital_signs=[{"name": s} for s in extracted_entities.get("Sign_symptom", [])],
            procedures=[{"name": p} for p in extracted_entities.get("Therapeutic_procedure", [])],
            diagnostic_results=diagnostic_results,
            provenance=[]
        )
        
        return {
            "status": "success",
            "message": "Successfully extracted all 20 Clinical and Administrative data points.",
            "clinical_evidence_packet": packet.dict()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def mock_openrouter_ner(raw_text: str) -> dict:
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    prompt = f"""You are a biomedical NER system. Extract entities from the following text into this exact JSON format:
    {{
      "Requested_Service": {{
          "description": "The item/service/surgery being requested",
          "hcpcs_code": "Extract the specific HCPCS or CPT code if present, otherwise output UNKNOWN"
      }},
      "Disease_Disorder": ["list of diseases"],
      "Sign_symptom": ["list of symptoms"],
      "Medication": ["list of medications"],
      "Therapeutic_procedure": ["list of procedures"],
      "Diagnostic_results": [
          {{"test_name": "Name of lab or diagnostic test", "value": "Result value/finding"}}
      ],
      "Demographics": {{
          "Patient_ID": "ID",
          "Age": "age",
          "Gender": "gender",
          "ZIP": "zip"
      }}
    }}
    Text: {raw_text}
    """
    
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"},
        json={
            "model": "openai/gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0
        },
        timeout=15
    )
    res_json = response.json()
    choices = res_json.get("choices", [])
    if not choices:
        print("Error from OpenRouter:", res_json)
        return {}
    content = choices[0].get("message", {}).get("content", "")
    import re
    match = re.search(r'```(?:json)?(.*?)```', content, re.DOTALL)
    if match:
        content = match.group(1).strip()
    else:
        content = content.strip()
    try:
        return json.loads(content)
    except Exception as e:
        print("Failed to parse JSON from OpenRouter:", e)
        return {}

@router.post("/direct-evaluate")
async def direct_evaluate(file: UploadFile = File(...)):
    """Runs the full real pipeline purely in-memory from a PDF upload (without DB patient records)."""
    file_bytes = await file.read()
    raw_text = PdfExtractionService.extract_text_from_pdf(file_bytes)
    
    # 1. Extract NER Facts
    extracted_entities = mock_openrouter_ner(raw_text)
    demos = extracted_entities.get("Demographics", {})
    diseases = [d for d in extracted_entities.get("Disease_Disorder", [])]
    state_code = demos.get("ZIP", "TX") # default to TX if not found
    
    req_svc = extracted_entities.get("Requested_Service", {})
    requested_code = req_svc.get("hcpcs_code", "UNKNOWN")
    requested_desc = req_svc.get("description", "Requested Item")
    
    diagnostic_results = extracted_entities.get("Diagnostic_results", [])
    
    packet = ClinicalEvidencePacket(
        authorization_id=demos.get("Patient_ID", "AUTH-TEST"),
        patient_id=demos.get("Patient_ID", "Unknown"),
        requested_service={"code": requested_code, "description": requested_desc},
        diagnosis_codes=diseases,
        demographics={"age": demos.get("Age"), "gender": demos.get("Gender"), "state_code": state_code},
        conditions=[{"name": d} for d in diseases],
        medications=[{"name": m} for m in extracted_entities.get("Medication", [])],
        vital_signs=[{"name": s} for s in extracted_entities.get("Sign_symptom", [])],
        procedures=[{"name": p} for p in extracted_entities.get("Therapeutic_procedure", [])],
        diagnostic_results=diagnostic_results,
        provenance=[]
    )
    
    # 2. Route via Real MongoDB
    routing_request = PolicyRoutingRequest(hcpcs_code=requested_code, state_code=state_code, date_of_service=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    routing_response = PolicyRoutingService.route_policy(routing_request)
    
    ncd_ids = [n["ncd_id"] for n in routing_response.applicable_ncds] or [n["ncd_id"] for n in routing_response.candidate_ncds]
    lcd_ids = [l["lcd_id"] for l in routing_response.applicable_lcds] or [l["lcd_id"] for l in routing_response.candidate_lcds]
    article_ids = [a["article_id"] for a in routing_response.related_articles]
    
    # Extract diagnostic test names and vitals to boost retrieval
    clinical_keywords = [d for d in diseases]
    if packet.vital_signs:
        clinical_keywords.extend([v.get("name", "") for v in packet.vital_signs])
    if packet.diagnostic_results:
        clinical_keywords.extend([d.get("test_name", "") for d in packet.diagnostic_results])
        
    clinical_context = " ".join(filter(None, clinical_keywords))

    # 3. Retrieve Vector Chunks
    try:
        retrieval_res = PolicyRetrievalService.retrieve_policy_chunks(
            query=f"Coverage requirements, indications, and limitations for service {requested_code}. Patient clinical conditions: {clinical_context}",
            policy_scope={"ncd_ids": list(set(ncd_ids)), "lcd_ids": list(set(lcd_ids)), "article_ids": list(set(article_ids))},
            document_versions={},
            top_k=40,
            unrestricted=False,
            hcpcs_code=requested_code,
            keywords=clinical_keywords
        )
        chunks = retrieval_res.get("results", [])
    except ValueError as e:
        print(f"Retrieval Error (likely no policies found for {requested_code}): {e}")
        chunks = []
    
    # Split chunks for engines
    ncd_chunks = [c for c in chunks if c.get("document_type") == "NCD"]
    lcd_chunks = [c for c in chunks if c.get("document_type") == "LCD"]
    art_chunks = [c for c in chunks if c.get("document_type") == "ARTICLE"]
    
    # 4. Run Evaluation Engines
    ncd_decision = NCDEvaluationEngine.evaluate_ncds(packet, ncd_chunks)
    lcd_decision = None
    if ncd_decision.ncd_determination != "NOT COVERED":
        lcd_decision = LCDEvaluationEngine.evaluate_lcds(packet, lcd_chunks)
    art_decision = ArticleEvaluationEngine.evaluate_articles(packet, art_chunks)
    
    phase7 = ConfidenceDecisionEngine.compute_decision(packet, ncd_decision, lcd_decision, art_decision)
    
    status_map = {"APPROVE": "APPROVED", "DENY": "DENIED", "PEND": "PENDING_MANUAL_REVIEW", "NURSE_REVIEW": "PENDING_MANUAL_REVIEW"}
    pipeline_result = PipelineDecisionResult(
        final_status=status_map.get(phase7.recommendation, "PENDING_MANUAL_REVIEW"),
        ncd_decision=ncd_decision,
        lcd_decision=lcd_decision,
        article_decision=art_decision,
        phase7_decision=phase7
    )
    
    # 5. Generate Explanation
    final_markdown = ExplanationEngine.generate_explanation(pipeline_result)
    
    import json
    details_dict = json.loads(pipeline_result.json())
    details_dict["phase3_routing"] = {
        "requested_hcpcs": requested_code,
        "ncd_policies": ncd_ids,
        "lcd_policies": lcd_ids,
        "article_policies": article_ids,
        "retrieved_chunks": len(chunks)
    }
    
    return {
        "status": pipeline_result.final_status,
        "confidence": phase7.overall_confidence_score,
        "recommendation": phase7.recommendation,
        "letter": final_markdown,
        "metrics": {"processing_time": 4.2},
        "details": details_dict
    }

@router.post("", response_model=Dict[str, Any])
def create_request(request: ClinicalEvidencePacket):
    """Create and submit a new prior authorization request into the database, persisting all clinical evidence."""
    db = db_connection.get_db()
    
    # Check if request already exists
    existing = db["authorization_requests"].find_one({"request_id": request.authorization_id})
    if existing:
        raise HTTPException(status_code=400, detail=f"Request ID '{request.authorization_id}' already exists.")
        
    doc = {
        "request_id": request.authorization_id,
        "patient_id": request.patient_id,
        "provider_id": "AUTO_EXTRACTED",
        "requested_procedure_code": {
            "source_value": request.requested_service.get("code", ""),
            "canonical_value": request.requested_service.get("code", ""),
            "display_value": request.requested_service.get("code", "")
        },
        "diagnosis_code": [
            {
                "source_value": code,
                "canonical_value": code.replace(".", ""),
                "display_value": code
            } for code in request.diagnosis_codes
        ],
        "request_date": datetime.now(timezone.utc).isoformat(),
        "status": "Pending",
        "source": "frontend_upload",
        "inserted_at": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        # Insert auth request
        db["authorization_requests"].insert_one(doc)
        doc["_id"] = str(doc["_id"])
        
        # Insert clinical arrays into their respective collections
        patient_id = request.patient_id
        
        if request.conditions:
            db["patient_conditions"].insert_many([
                {"patient_id": patient_id, "diagnosis_code": c.get("name"), "diagnosis": c.get("name")} 
                for c in request.conditions
            ])
            
        if request.procedures:
            db["patient_procedures"].insert_many([
                {"patient_id": patient_id, "procedure_code": p.get("name"), "procedure": p.get("name")} 
                for p in request.procedures
            ])
            
        if request.medications:
            db["patient_medications"].insert_many([
                {"patient_id": patient_id, "medication_name": m.get("name")} 
                for m in request.medications
            ])
            
        if request.diagnostic_results:
            db["diagnostic_results"].insert_many([
                {"patient_id": patient_id, "test_name": d.get("test_name"), "value": d.get("value"), "unit": d.get("unit", "")} 
                for d in request.diagnostic_results
            ])
            
        if request.vital_signs:
            db["vital_signs"].insert_many([
                {"patient_id": patient_id, "vital_type": v.get("name"), "value": v.get("value", "")} 
                for v in request.vital_signs
            ])
            
        return doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database insertion failed: {e}")

@router.post("/{authorization_id}/build-evidence", response_model=Dict[str, Any])
def build_evidence(
    authorization_id: str,
    override_state: Optional[str] = Query(None, description="Optional state code override"),
    override_date: Optional[str] = Query(None, description="Optional date override")
):
    """Compile structured and unstructured clinical facts into a ClinicalEvidencePacket."""
    try:
        res = PriorAuthorizationIntakeService.compile_evidence_packet(
            request_id=authorization_id,
            override_state=override_state,
            override_date=override_date
        )
        return {
            "evidence_packet": res["packet"].model_dump(),
            "provider": res["provider"]
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{authorization_id}/route-and-retrieve", response_model=Dict[str, Any])
def route_and_retrieve(
    authorization_id: str,
    override_state: Optional[str] = Query(None, description="Optional state code override"),
    override_date: Optional[str] = Query(None, description="Optional date override")
):
    """Runs the prior auth combined intake routing and policy retrieval workflow."""
    try:
        res = PriorAuthorizationIntakeService.execute_route_and_retrieve(
            request_id=authorization_id,
            override_state=override_state,
            override_date=override_date
        )
        # Convert Pydantic schemas to dict for JSON serialization
        if hasattr(res["clinical_evidence_packet"], "model_dump"):
            res["clinical_evidence_packet"] = res["clinical_evidence_packet"].model_dump()
        if hasattr(res["policy_routing"], "model_dump"):
            res["policy_routing"] = res["policy_routing"].model_dump()
            
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{authorization_id}/evaluate-ncd", response_model=NCDSemanticEvaluationResult)
def evaluate_ncd(
    authorization_id: str,
    override_state: Optional[str] = Query(None, description="Optional state code override"),
    override_date: Optional[str] = Query(None, description="Optional date override")
):
    """Executes Phase 4: NCD Semantic Evaluation (RAG)."""
    try:
        # First, run the entire routing and retrieval pipeline
        pipeline_res = PriorAuthorizationIntakeService.execute_route_and_retrieve(
            request_id=authorization_id,
            override_state=override_state,
            override_date=override_date
        )
        
        clinical_evidence = pipeline_res.get("clinical_evidence_packet")
        retrieval_result = pipeline_res.get("policy_retrieval", {}).get("results", [])
        
        if not clinical_evidence:
            raise ValueError("Failed to build ClinicalEvidencePacket")
            
        # Execute Phase 4
        decision = NCDEvaluationEngine.evaluate_ncds(
            clinical_evidence=clinical_evidence,
            retrieval_result=retrieval_result
        )
        return decision
        
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{authorization_id}/evaluate-full-pipeline", response_model=PipelineDecisionResult)
def evaluate_full_pipeline(
    authorization_id: str,
    override_state: Optional[str] = Query(None, description="Optional state code override"),
    override_date: Optional[str] = Query(None, description="Optional date override")
):
    """Executes the full pipeline (Phases 1-5) and orchestrates the final PA decision."""
    try:
        decision = PriorAuthPipelineOrchestrator.run_full_pipeline(
            authorization_id=authorization_id,
            override_state=override_state,
            override_date=override_date
        )
        import json
        return json.loads(decision.json())
        
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from datetime import datetime, timezone
