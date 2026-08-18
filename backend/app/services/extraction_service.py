import os
import fitz  # PyMuPDF
import requests
import json
from typing import Dict, Any, List

class PdfExtractionService:
    HF_API_URL = "https://api-inference.huggingface.co/models/d4data/biomedical-ner-all"
    
    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> str:
        """Extracts text from a PDF preserving reading order via PyMuPDF."""
        text = ""
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                text += page.get_text("text") + "\n"
        except Exception as e:
            raise ValueError(f"Failed to extract PDF text: {str(e)}")
        return text

    @staticmethod
    def run_ner_extraction(text: str) -> Dict[str, Any]:
        """Calls the Hugging Face Inference API to perform biomedical NER."""
        api_token = os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
        if not api_token:
            raise ValueError("Hugging Face API token is missing in .env")

        headers = {"Authorization": f"Bearer {api_token}"}
        
        # Truncate text if too long for the API model limits
        payload = {"inputs": text[:4000]}
        
        response = requests.post(
            PdfExtractionService.HF_API_URL, 
            headers=headers, 
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"HF API Error: {response.text}")
            
        ner_results = response.json()
        
        # Parse the raw NER tokens into grouped categories
        extracted_data = {
            "Disease_Disorder": [],
            "Sign_symptom": [],
            "Medication": [],
            "Diagnostic_procedure": [],
            "Therapeutic_procedure": []
        }
        
        for entity in ner_results:
            group = entity.get("entity_group")
            word = entity.get("word", "").strip()
            # Clean up ## tokens from WordPiece tokenization
            word = word.replace("##", "")
            
        # Extract Administrative / Demographic points using Regex
        import re
        admin_data = {
            "Patient_ID": re.search(r"(?i)(Patient ID|MRN|DOB)[:\-]?\s*([a-zA-Z0-9\-\/]+)", text),
            "Age": re.search(r"(?i)(\d{1,3})\s*(?:yo|y/o|years old|year old)", text),
            "Gender": re.search(r"(?i)\b(male|female|man|woman|boy|girl)\b", text),
            "ZIP": re.search(r"(?i)\b\d{5}(?:-\d{4})?\b", text),
            "NPI": re.search(r"(?i)(NPI)[:\-]?\s*(\d{10})", text),
            "Facility": re.search(r"(?i)(Facility|Clinic|Hospital)[:\-]?\s*([a-zA-Z\s]+)", text),
            "Date": re.search(r"(?i)(Date)[:\-]?\s*([\d\/\-]+)", text),
        }
        
        extracted_data["Demographics"] = {
            k: v.group(1) if v and len(v.groups()) == 1 else (v.group(2) if v else "Not Found")
            for k, v in admin_data.items()
        }
                    
        return extracted_data

    @staticmethod
    def validate_against_db(extracted_entities: Dict[str, Any], db) -> Dict[str, Any]:
        """Maps extracted diseases to candidate ICD-10 codes using MongoDB."""
        candidate_codes = []
        
        diseases = extracted_entities.get("Disease_Disorder", [])
        
        # Simple exact match or text search lookup for demonstration
        for disease in diseases:
            # Query the ICD-10 Covered Articles collection to find a matching description
            # This is a naive text search. In production, an Atlas Vector Search on the description is ideal.
            matching_code = db["icd10_covered_articles"].find_one(
                {"description": {"$regex": disease, "$options": "i"}}
            )
            
            if matching_code:
                candidate_codes.append({
                    "code": matching_code.get("icd10_code"),
                    "description": matching_code.get("description"),
                    "confidence": "High (DB Match)"
                })
                
        return candidate_codes
