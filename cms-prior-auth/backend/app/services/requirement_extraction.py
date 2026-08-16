import json
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.db.connection import db_connection
from app.models.evaluation import PolicyRequirement
from app.services.llm import get_llm_provider

class PolicyRequirementExtractor:
    @classmethod
    def extract_requirements(
        cls, 
        retrieved_chunks: List[Dict[str, Any]], 
        policy_roles: Dict[str, str]
    ) -> List[PolicyRequirement]:
        """Extracts and deduplicates requirements from RAG policy text chunks."""
        db = db_connection.get_db()
        llm = get_llm_provider()
        
        extracted_list: List[PolicyRequirement] = []
        
        system_prompt = (
            "You are a professional medical policy analyst. Your task is to extract clinical requirements and criteria "
            "from the provided U.S. Medicare/CMS coverage document chunk.\n\n"
            "Critical Safety Instructions:\n"
            "1. Extract only requirements explicitly supported by the supplied CMS policy passage.\n"
            "2. Do not use outside medical knowledge or assume prerequisites.\n"
            "3. Do not infer requirements absent from the text.\n"
            "4. Do not make any prior authorization approval or denial recommendations.\n"
            "5. If wording is ambiguous, preserve that exact ambiguity in the extracted requirement.\n"
            "6. Classify each requirement type into exactly one of these categories:\n"
            "   DIAGNOSIS, SYMPTOM, DURATION, PRIOR_TREATMENT, FAILED_TREATMENT, MEDICATION, PROCEDURE, "
            "   DIAGNOSTIC_TEST, IMAGING, LAB, FUNCTIONAL_STATUS, AGE, FREQUENCY, QUANTITY, DOCUMENTATION, "
            "   CONTRAINDICATION, COMORBIDITY, EQUIPMENT, OTHER_CLINICAL, CODING, ADMINISTRATIVE.\n\n"
            "Return a JSON object exactly conforming to this schema:\n"
            "{\n"
            "  \"requirements\": [\n"
            "    {\n"
            "      \"requirement_text\": \"clinical condition description\",\n"
            "      \"requirement_type\": \"TYPE_FROM_LIST\",\n"
            "      \"mandatory\": true,\n"
            "      \"conditional\": false,\n"
            "      \"condition_text\": null,\n"
            "      \"source_quote_fragment\": \"precise raw quote from passage\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )
        
        for chunk in retrieved_chunks:
            doc_id = chunk["document_id"]
            doc_type = chunk.get("document_type", "LCD")
            doc_ver = chunk.get("document_version", "1")
            section = chunk.get("section", "indication")
            chunk_id = chunk.get("chunk_id", "")
            text = chunk.get("text", "")
            
            # Map policy role
            role = policy_roles.get(doc_id, "APPLICABLE")
            
            # Call LLM or mock to perform structured JSON extraction
            user_prompt = (
                f"Document Type: {doc_type}\n"
                f"Document ID: {doc_id}\n"
                f"Version: {doc_ver}\n"
                f"Section: {section}\n"
                f"Passage Content:\n\"\"\"\n{text}\n\"\"\""
            )
            
            raw_response = ""
            parsed_data = {"requirements": []}
            try:
                raw_response = llm.generate_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    json_mode=True,
                    temperature=0.0
                )
                parsed_data = json.loads(raw_response)
            except Exception as e:
                # Log extraction failure and keep moving rather than crashing
                db["requirement_extraction_failures"].insert_one({
                    "chunk_id": chunk_id,
                    "document_id": doc_id,
                    "error": str(e),
                    "raw_response": raw_response,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                continue
                
            # Log audit trail
            db["requirement_extraction_audit"].insert_one({
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "document_version": doc_ver,
                "section": section,
                "policy_role": role,
                "text": text,
                "raw_response": raw_response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            reqs = parsed_data.get("requirements", [])
            for idx, r in enumerate(reqs):
                req_text = r.get("requirement_text", "")
                if not req_text:
                    continue
                    
                # Create a stable requirement ID based on document and text content hash
                h = hashlib.md5(f"{doc_id}:{section}:{req_text}".encode("utf-8")).hexdigest()[:8]
                req_id = f"REQ-{doc_id}-{h}"
                
                req_obj = PolicyRequirement(
                    requirement_id=req_id,
                    document_type=doc_type,
                    document_id=doc_id,
                    document_version=doc_ver,
                    section=section,
                    citation=chunk_id or f"{doc_type}:{doc_id}:{doc_ver}:{section}:chunk_{idx}",
                    policy_role=role,
                    requirement_text=req_text,
                    requirement_type=r.get("requirement_type", "OTHER_CLINICAL"),
                    mandatory=r.get("mandatory", True),
                    conditional=r.get("conditional", False),
                    condition_text=r.get("condition_text"),
                    structured_constraints={},
                    extraction_method="LLM",
                    extraction_confidence=1.0
                )
                extracted_list.append(req_obj)
                
        # Deduplicate requirements by document_id, version, section, and normalized text
        deduplicated: List[PolicyRequirement] = []
        seen = set()
        
        for req in extracted_list:
            norm_text = "".join(c for c in req.requirement_text.lower() if c.isalnum())
            key = (req.document_id, req.document_version, req.section, norm_text)
            
            if key not in seen:
                seen.add(key)
                deduplicated.append(req)
                
        return deduplicated
