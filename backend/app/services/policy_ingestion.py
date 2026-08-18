import re
from typing import List, Dict, Any
from app.db.connection import db_connection
from app.services.cms_api_service import CMSApiService
from app.services.embedding import get_embedding_provider

class PolicyIngestionService:
    @staticmethod
    def chunk_text(text: str, max_words: int = 150) -> List[str]:
        """Splits text into chunks of approximately max_words."""
        if not text:
            return []
            
        words = text.split()
        chunks = []
        current_chunk = []
        
        for word in words:
            current_chunk.append(word)
            if len(current_chunk) >= max_words:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks

    @classmethod
    def self_heal_document(cls, doc_type: str, doc_id: str, hcpcs_code: str = None, keywords: List[str] = None) -> None:
        """
        Fetches the missing document from the CMS API, pre-filters the text based on requested codes/keywords,
        chunks the relevant text, generates embeddings, and stores them in the policy_chunks collection.
        """
        print(f"[{doc_type} {doc_id}] Self-Healing Triggered: Fetching document from CMS API...")
        
        raw_doc = None
        if doc_type == "NCD":
            raw_doc = CMSApiService.fetch_ncd_document(doc_id)
        elif doc_type == "LCD":
            raw_doc = CMSApiService.fetch_lcd_document(doc_id)
        elif doc_type == "ARTICLE":
            raw_doc = CMSApiService.fetch_article_document(doc_id)
            
        if not raw_doc:
            print(f"[{doc_type} {doc_id}] Failed to fetch document from API. Skipping self-heal.")
            return
            
        cls.ingest_document(doc_type, doc_id, raw_doc, hcpcs_code, keywords)

    @classmethod
    def ingest_document(cls, doc_type: str, doc_id: str, raw_doc: dict, hcpcs_code: str = None, keywords: List[str] = None) -> None:
        """Ingests a raw CMS document into the vector store."""
        db = db_connection.get_db()
        provider = get_embedding_provider()
        
        fields_to_extract = []
        if doc_type == "NCD":
            fields_to_extract = ["indications_limitations", "item_service_description", "other_text"]
        elif doc_type == "LCD":
            fields_to_extract = ["indication", "cms_cov_policy", "doc_reqs", "summary_of_evidence", "analysis_of_evidence"]
        elif doc_type == "ARTICLE":
            fields_to_extract = ["article_text", "article_guidance", "cms_cov_policy"]
            
        strict_terms = [hcpcs_code.lower()] if hcpcs_code else []
        broad_terms = [k.lower() for k in keywords if k] if keywords else []
        coverage_terms = [
            "covered", "coverage", "coverage criteria", "indication", "limitation", 
            "documentation", "medical necessity", "non-covered", "not covered", 
            "requirement", "qualifying", "clinical", "diagnosis"
        ]
        
        all_terms = strict_terms + broad_terms + coverage_terms
        
        # 1. Collect all paragraphs by field
        field_paragraphs = {}
        total_paragraphs_count = 0
        for field in fields_to_extract:
            text = raw_doc.get(field, "")
            if not text:
                continue
                
            text_with_newlines = re.sub(r'</p>|<br/?>|</li>', '\n', text)
            clean_text = re.sub(r'<[^>]+>', ' ', text_with_newlines)
            paragraphs = [re.sub(r'\s+', ' ', p).strip() for p in clean_text.split('\n')]
            paragraphs = [p for p in paragraphs if len(p) > 10]
            
            if paragraphs:
                field_paragraphs[field] = paragraphs
                total_paragraphs_count += len(paragraphs)
                
        # 2. Targeted filtering with context window
        retained_by_field = {}
        direct_matches_count = 0
        context_paragraphs_count = 0
        
        for field, paragraphs in field_paragraphs.items():
            matched_indices = set()
            field_direct = 0
            
            for i, p in enumerate(paragraphs):
                p_lower = p.lower()
                # Check for match
                if any(t in p_lower for t in all_terms):
                    field_direct += 1
                    # Add context window: 2 before, 2 after
                    for j in range(max(0, i-2), min(len(paragraphs), i+3)):
                        matched_indices.add(j)
                        
            direct_matches_count += field_direct
            context_paragraphs_count += (len(matched_indices) - field_direct)
            
            if matched_indices:
                retained_by_field[field] = [paragraphs[i] for i in sorted(matched_indices)]
                
        # 3. Fallback logic
        if direct_matches_count == 0:
            print(f"[{doc_type} {doc_id}] Strict filtering produced 0 matches. Falling back to full document ingestion.")
            retained_by_field = field_paragraphs
            
        # 4. Chunking and Embedding
        import uuid
        from datetime import datetime
        
        chunks_to_insert = []
        chunk_order = 1
        
        policy_version = raw_doc.get("document_version") or raw_doc.get("article_version") or raw_doc.get("lcd_version") or "1"
        effective_date = raw_doc.get("rev_eff_date") or raw_doc.get("effective_date") or ""
        
        for field, paragraphs in retained_by_field.items():
            filtered_text = " ".join(paragraphs)
            if not filtered_text:
                continue
                
            text_chunks = cls.chunk_text(filtered_text, max_words=150)
            
            for chunk in text_chunks:
                print(f"[{doc_type} {doc_id}] Generating embedding for chunk {chunk_order}...")
                embedding = provider.get_embedding(chunk)
                
                chunks_to_insert.append({
                    "chunk_id": str(uuid.uuid4()),
                    "document_id": doc_id,
                    "document_type": doc_type,
                    "policy_id": doc_id,
                    "section": field,
                    "subsection": "",
                    "text": chunk,
                    "embedding": embedding,
                    "effective_date": effective_date,
                    "policy_version": policy_version,
                    "source": "CMS_API",
                    "retrieved_at": datetime.utcnow().isoformat(),
                    "chunk_order": chunk_order
                })
                chunk_order += 1
                
        # Log Ingestion Statistics
        print(f"--- Ingestion Statistics for {doc_type} {doc_id} ---")
        print(f"Total paragraphs: {total_paragraphs_count}")
        print(f"Direct matches: {direct_matches_count}")
        print(f"Context paragraphs added: {context_paragraphs_count}")
        print(f"Final paragraphs retained: {sum(len(p) for p in retained_by_field.values())}")
        print(f"Chunks created: {len(chunks_to_insert)}")
        print(f"--------------------------------------------------")
        
        if chunks_to_insert:
            db["policy_chunks"].insert_many(chunks_to_insert)
        else:
            print(f"[{doc_type} {doc_id}] No extractable text found in document.")
