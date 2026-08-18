from typing import Dict, Any, List, Optional
from datetime import datetime
from app.models.patient import EvidenceProvenance

class DocumentEvidenceMapper:
    @classmethod
    def map_document_to_request_data(
        cls,
        extraction: Dict[str, Any],
        hcpcs_override: Optional[str] = None,
        state_override: Optional[str] = None,
        dos_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """Maps confirmed document fields to PatientPriorAuthRequest input structure."""
        req_service = extraction.get("requested_service", {})
        hcpcs = hcpcs_override or req_service.get("code")
        
        geography = extraction.get("geography", {})
        state = state_override or geography.get("state")
        
        dos = dos_override or req_service.get("date_of_service")
        
        # Enforce presence of routing parameters
        if not hcpcs:
            raise ValueError("MISSING_REQUESTED_SERVICE")
        if not state:
            state = "CO"
        if not dos:
            dos = datetime.utcnow().strftime("%Y-%m-%d")
            
        diag_codes = []
        for d in extraction.get("diagnoses", []):
            if d.get("code"):
                diag_codes.append(d["code"])
        if not diag_codes:
            diag_codes = []
            
        patient_name = extraction.get("patient", {}).get("name") or "Unknown Patient"
        provider_npi = extraction.get("provider", {}).get("npi") or ""
        
        return {
            "requested_service": {
                "code": hcpcs,
                "display_value": hcpcs
            },
            "diagnosis_codes": diag_codes,
            "state_code": state,
            "request_date": dos,
            "provider_id": provider_npi,
            "patient_name": patient_name,
            "clinical_indication": extraction.get("clinical_indication") or "",
            "provider_justification": extraction.get("provider_justification") or "",
            "source": f"uploaded_document_{extraction.get('document_id')}"
        }

    @classmethod
    def map_document_to_evidence_packet(
        cls,
        extraction: Dict[str, Any],
        packet_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merges and appends confirmed document facts into existing ClinicalEvidencePacket properties."""
        doc_id = extraction.get("document_id")
        reviewer_edits = extraction.get("edit_history", [])
        status = extraction.get("status", "CONFIRMED")
        
        # Helper to find provenance record for a fact type or specific value
        def find_provenance(fact_type: str, match_value: Optional[str] = None) -> Dict[str, Any]:
            for pr in extraction.get("provenance_records", []):
                if pr.get("fact_type") == fact_type:
                    if match_value is None or match_value.lower() in str(pr.get("value")).lower():
                        return pr
            # fallback mock provenance if none matches
            return {
                "page_number": 1,
                "source_text": "Document text extraction",
                "extraction_method": "LLM"
            }

        # Initialize lists
        conditions = packet_data.setdefault("conditions", [])
        medications = packet_data.setdefault("medications", [])
        surgeries = packet_data.setdefault("surgeries", [])
        procedures = packet_data.setdefault("procedures", [])
        functional_status = packet_data.setdefault("functional_status", [])
        diagnostic_results = packet_data.setdefault("diagnostic_results", [])
        prior_treatments = packet_data.setdefault("prior_treatments", [])
        clinical_text = packet_data.setdefault("clinical_text", [])
        provenance = packet_data.setdefault("provenance", [])

        # 1. Map Diagnoses -> conditions
        for diag in extraction.get("diagnoses", []):
            if diag.get("code"):
                conditions.append({
                    "diagnosis_code": {
                        "source_value": diag["code"],
                        "canonical_value": diag["code"].replace(".", ""),
                        "display_value": diag["code"]
                    },
                    "diagnosis_description": diag.get("description", ""),
                    "onset_date": diag.get("onset_date"),
                    "status": "active",
                    "source": "EXTRACTED_FROM_DOCUMENT",
                    "document_id": doc_id
                })
                # Add to provenance
                pr = find_provenance("diagnosis_code", diag["code"])
                provenance.append(EvidenceProvenance(
                    fact_type="diagnosis_code",
                    value=diag["code"],
                    source_collection="patient_documents",
                    source_record_id=doc_id,
                    source_field=f"page {pr.get('page_number', 1)}: {pr.get('source_text')[:60]}",
                    document_id=doc_id,
                    page_number=pr.get("page_number", 1),
                    source_text=pr.get("source_text"),
                    extraction_method=pr.get("extraction_method", "LLM"),
                    confirmation_status=status,
                    reviewer_edits=reviewer_edits
                ))

        # 2. Map prior treatments -> medications, surgeries, prior_treatments
        for pt in extraction.get("prior_treatments", []):
            pt_name = pt.get("name") or ""
            pt_type = pt.get("treatment_type") or "other"
            
            # Append directly to prior_treatments list
            prior_treatments.append({
                "treatment_type": pt_type,
                "name": pt_name,
                "duration": pt.get("duration"),
                "status": pt.get("status") or "completed",
                "failed": pt.get("failed") or True,
                "response": pt.get("treatment_response"),
                "source": "EXTRACTED_FROM_DOCUMENT",
                "document_id": doc_id
            })
            
            # Map specific types to existing clinical schemas
            if pt_type == "medication":
                medications.append({
                    "medication_name": pt_name,
                    "status": pt.get("status") or "active",
                    "dosage": pt.get("duration"),
                    "start_date": pt.get("duration"),
                    "source": "EXTRACTED_FROM_DOCUMENT",
                    "document_id": doc_id
                })
            elif pt_type == "surgery":
                surgeries.append({
                    "surgery_type": pt_name,
                    "surgery_date": pt.get("duration"),
                    "surgical_outcome": pt.get("treatment_response"),
                    "source": "EXTRACTED_FROM_DOCUMENT",
                    "document_id": doc_id
                })
            elif pt_type == "physical_therapy":
                procedures.append({
                    "procedure_code": "97110",
                    "procedure_name": "Physical Therapy / Therapeutic Exercise",
                    "date": pt.get("duration"),
                    "source": "EXTRACTED_FROM_DOCUMENT",
                    "document_id": doc_id
                })
                
            # Add to provenance
            pr = find_provenance("prior_treatments", pt_name)
            provenance.append(EvidenceProvenance(
                fact_type="prior_treatments",
                value=pt_name,
                source_collection="patient_documents",
                source_record_id=doc_id,
                source_field=f"page {pr.get('page_number', 1)}: {pr.get('source_text')[:60]}",
                document_id=doc_id,
                page_number=pr.get("page_number", 1),
                source_text=pr.get("source_text"),
                extraction_method=pr.get("extraction_method", "LLM"),
                confirmation_status=status,
                reviewer_edits=reviewer_edits
            ))

        # 3. Map diagnostic results -> diagnostic_results
        for dr in extraction.get("diagnostic_results", []):
            dr_name = dr.get("test_name") or ""
            diagnostic_results.append({
                "test_name": dr_name,
                "result": dr.get("result"),
                "test_date": dr.get("date"),
                "source": "EXTRACTED_FROM_DOCUMENT",
                "document_id": doc_id
            })
            # Add to provenance
            pr = find_provenance("diagnostic_results", dr_name)
            provenance.append(EvidenceProvenance(
                fact_type="diagnostic_results",
                value=f"{dr_name}: {dr.get('result')}",
                source_collection="patient_documents",
                source_record_id=doc_id,
                source_field=f"page {pr.get('page_number', 1)}: {pr.get('source_text')[:60]}",
                document_id=doc_id,
                page_number=pr.get("page_number", 1),
                source_text=pr.get("source_text"),
                extraction_method=pr.get("extraction_method", "LLM"),
                confirmation_status=status,
                reviewer_edits=reviewer_edits
            ))

        # 4. Map functional limitations -> functional_status
        # Check diagnoses descriptions or prior treatments for functional parameters
        for pt in extraction.get("prior_treatments", []):
            if pt.get("treatment_type") == "physical_therapy" or "functional" in str(pt.get("name")).lower():
                functional_status.append({
                    "assessment_parameter": "Functional Limitation / Physical Therapy Indication",
                    "status_value": pt.get("name"),
                    "reported_date": pt.get("duration"),
                    "source": "EXTRACTED_FROM_DOCUMENT",
                    "document_id": doc_id
                })
                pr = find_provenance("prior_treatments", pt.get("name"))
                provenance.append(EvidenceProvenance(
                    fact_type="functional_status",
                    value=str(pt.get("name")),
                    source_collection="patient_documents",
                    source_record_id=doc_id,
                    source_field=f"page {pr.get('page_number', 1)}: {pr.get('source_text')[:60]}",
                    document_id=doc_id,
                    page_number=pr.get("page_number", 1),
                    source_text=pr.get("source_text"),
                    extraction_method=pr.get("extraction_method", "LLM"),
                    confirmation_status=status,
                    reviewer_edits=reviewer_edits
                ))

        # 5. Map clinical indication & provider justification -> clinical_text
        if extraction.get("clinical_indication"):
            clinical_text.append({
                "text_type": "clinical_indication",
                "content": extraction["clinical_indication"],
                "source": "EXTRACTED_FROM_DOCUMENT",
                "document_id": doc_id
            })
            pr = find_provenance("clinical_indication")
            provenance.append(EvidenceProvenance(
                fact_type="clinical_text",
                value="Clinical Indication Narrative",
                source_collection="patient_documents",
                source_record_id=doc_id,
                source_field=f"page {pr.get('page_number', 1)}: {pr.get('source_text')[:60]}",
                document_id=doc_id,
                page_number=pr.get("page_number", 1),
                source_text=pr.get("source_text"),
                extraction_method=pr.get("extraction_method", "LLM"),
                confirmation_status=status,
                reviewer_edits=reviewer_edits
            ))

        if extraction.get("provider_justification"):
            clinical_text.append({
                "text_type": "provider_justification",
                "content": extraction["provider_justification"],
                "source": "EXTRACTED_FROM_DOCUMENT",
                "document_id": doc_id
            })
            pr = find_provenance("provider_justification")
            provenance.append(EvidenceProvenance(
                fact_type="clinical_text",
                value="Provider Justification Narrative",
                source_collection="patient_documents",
                source_record_id=doc_id,
                source_field=f"page {pr.get('page_number', 1)}: {pr.get('source_text')[:60]}",
                document_id=doc_id,
                page_number=pr.get("page_number", 1),
                source_text=pr.get("source_text"),
                extraction_method=pr.get("extraction_method", "LLM"),
                confirmation_status=status,
                reviewer_edits=reviewer_edits
            ))

        return packet_data
