import json
import uuid
from typing import Dict, Any, List
from app.models.document import ExtractedClinicalDocument, DocumentEvidenceProvenance, DiagnosisItem, PriorTreatmentItem, DiagnosticResultItem
from app.services.llm import get_llm_provider

class ClinicalDocumentExtractor:
    @classmethod
    def extract_document(cls, parsed_doc: Dict[str, Any]) -> ExtractedClinicalDocument:
        """Invokes the LLM provider under versioned prompt clinical_document_extraction_v1 to extract structured clinical facts from parsed document text."""
        document_id = parsed_doc["document_id"]
        full_text = parsed_doc["full_text"]
        pages = parsed_doc["pages"]
        
        # Prepare pages list with contents for the prompt context
        pages_context = ""
        for p in pages:
            pages_context += f"--- START OF PAGE {p['page_number']} ---\n{p['text']}\n--- END OF PAGE {p['page_number']} ---\n\n"
            
        system_prompt = """You are extracting structured facts from a patient clinical document under versioned prompt clinical_document_extraction_v1.
        
        Strictly adhere to the following rules:
        1. Use ONLY the supplied document text. Do not use outside clinical knowledge to fill missing facts.
        2. Do not infer undocumented diagnoses, procedures, durations, treatments, or results.
        3. Preserve exact clinical codes (such as CPT or ICD-10) when explicitly present.
        4. If a diagnosis or code itself is NOT documented in the text, do NOT assign it. Instead, return code as null, and set code_status to "NOT_DOCUMENTED".
        5. Every extracted fact must identify the supporting page number and exact source text quote fragment.
        6. Do not make coverage or authorization decisions.
        7. Ignore prior authorization outcomes (e.g. "prior authorization approved" or "meets policy criteria") or AI-generated recommendation text as patient evidence.
        8. Return the output strictly in the requested JSON format.
        """
        
        user_prompt = f"""Extract clinical information from the pages context:
        
        {pages_context}
        
        Respond with a JSON object containing:
        - patient: object with keys: name (string), dob (string or null), age (integer or null), gender (string or null)
        - requested_service: object with keys: code (string CPT or null), code_system (string "CPT"), description (string or null)
        - diagnoses: array of objects with keys: code (string ICD-10 or null), code_system (string "ICD-10-CM"), description (string or null), code_status (string "DOCUMENTED" if code was explicitly present in text, else "NOT_DOCUMENTED")
        - prior_treatments: array of objects with keys: treatment_type (string), name (string), duration (string or null), status (string or null), treatment_response (string or null), failed (boolean or null)
        - diagnostic_results: array of objects with keys: test_name (string), result (string), date (string or null)
        - clinical_indication: string or null
        - provider_justification: string or null
        - provider: object with keys: name (string or null), provider_type (string or null), facility (string or null), npi (string or null)
        - geography: object with keys: state (string or null), zip (string or null)
        - missing_fields: array of strings containing fields that are missing or not documented
        - provenance_records: array of objects with keys: fact_type (string), value (string), page_number (integer), source_text (string)
        """
        
        llm = get_llm_provider()
        raw_response = llm.generate_completion(system_prompt, user_prompt, json_mode=True)
        
        try:
            extracted_json = json.loads(raw_response)
        except Exception:
            # Re-try or raise error
            raise ValueError("Failed to parse clinical extraction output as JSON.")
            
        # Parse Pydantic entities
        patient_data = extracted_json.get("patient", {})
        service_data = extracted_json.get("requested_service", {})
        
        diagnoses = []
        for diag in extracted_json.get("diagnoses", []):
            diagnoses.append(DiagnosisItem(
                code=diag.get("code"),
                code_system=diag.get("code_system", "ICD-10-CM"),
                description=diag.get("description"),
                code_status=diag.get("code_status", "DOCUMENTED")
            ))
            
        prior_treatments = []
        for pt in extracted_json.get("prior_treatments", []):
            prior_treatments.append(PriorTreatmentItem(
                treatment_type=pt.get("treatment_type"),
                name=pt.get("name"),
                duration=pt.get("duration"),
                status=pt.get("status"),
                treatment_response=pt.get("treatment_response"),
                failed=pt.get("failed")
            ))
            
        diagnostic_results = []
        for dr in extracted_json.get("diagnostic_results", []):
            diagnostic_results.append(DiagnosticResultItem(
                test_name=dr.get("test_name"),
                result=dr.get("result"),
                date=dr.get("date")
            ))
            
        prov_records = []
        for pr in extracted_json.get("provenance_records", []):
            prov_records.append(DocumentEvidenceProvenance(
                fact_id=f"FACT-{str(uuid.uuid4())[:8]}",
                fact_type=pr.get("fact_type"),
                value=str(pr.get("value")),
                document_id=document_id,
                page_number=pr.get("page_number", 1),
                source_text=pr.get("source_text", ""),
                extraction_method="LLM",
                extractor_model=getattr(llm, "model", "mock_extractor")
            ))
            
        return ExtractedClinicalDocument(
            document_id=document_id,
            version=1,
            status="DRAFT_EXTRACTION",
            patient=patient_data,
            requested_service=service_data,
            diagnoses=diagnoses,
            prior_treatments=prior_treatments,
            diagnostic_results=diagnostic_results,
            clinical_indication=extracted_json.get("clinical_indication"),
            provider_justification=extracted_json.get("provider_justification"),
            provider=extracted_json.get("provider", {}),
            geography=extracted_json.get("geography", {}),
            missing_fields=extracted_json.get("missing_fields", []),
            provenance_records=prov_records,
            metadata={
                "extractor_provider": llm.__class__.__name__,
                "extractor_model": getattr(llm, "model", "rule_engine"),
                "extraction_prompt_version": "clinical_document_extraction_v1"
            }
        )
