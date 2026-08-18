import math
from typing import Dict, Any, List, Optional
from app.db.connection import db_connection
from app.core.config import settings
from app.services.embedding import get_embedding_provider

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes the cosine similarity between two vectors."""
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude1 = math.sqrt(sum(a * a for a in v1))
    magnitude2 = math.sqrt(sum(b * b for b in v2))
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)

class PolicyRetrievalService:
    @staticmethod
    def retrieve_policy_chunks(
        query: str,
        policy_scope: Optional[Dict[str, List[str]]] = None,
        document_versions: Optional[Dict[str, str]] = None,
        sections: Optional[List[str]] = None,
        top_k: int = 8,
        unrestricted: bool = False,
        hcpcs_code: str = None,
        keywords: List[str] = None
    ) -> Dict[str, Any]:
        """Performs metadata-restricted hybrid vector search to retrieve relevant policy sections."""
        db = db_connection.get_db()
        provider = get_embedding_provider()
        warnings: List[str] = []
        
        # 1. Scope Validation
        ids = []
        clean_ncd_ids = []
        clean_lcd_ids = []
        clean_article_ids = []
        
        if policy_scope:
            if policy_scope.get("ncd_ids"):
                for ncd in policy_scope["ncd_ids"]:
                    clean_id = str(ncd).strip()
                    clean_ncd_ids.append(clean_id)
                    ids.append(clean_id)
            if policy_scope.get("lcd_ids"):
                for lcd in policy_scope["lcd_ids"]:
                    clean_id = str(lcd).lstrip('L').lstrip('l').strip()
                    clean_lcd_ids.append(clean_id)
                    ids.extend([clean_id, f"L{clean_id}"])
            if policy_scope.get("article_ids"):
                for art in policy_scope["article_ids"]:
                    clean_id = str(art).lstrip('A').lstrip('a').strip()
                    clean_article_ids.append(clean_id)
                    ids.extend([clean_id, f"A{clean_id}"])
                
        # "If no policy scope is provided, the normal prior-auth pathway should reject or explicitly mark the retrieval as unrestricted/debug mode."
        if not ids and not unrestricted:
            raise ValueError(
                "RAG policy scope is empty. Prior-authorization retrieval must restrict vector search boundaries. "
                "Set unrestricted=True to run debug/unrestricted queries."
            )
            
        # 1.5 Self-Heal Missing Policies
        from app.services.policy_ingestion import PolicyIngestionService
        if policy_scope:
            for ncd_id in clean_ncd_ids:
                if db["policy_chunks"].count_documents({"document_id": {"$in": [ncd_id]}}) == 0:
                    PolicyIngestionService.self_heal_document("NCD", ncd_id, hcpcs_code, keywords)
            for lcd_id in clean_lcd_ids:
                if db["policy_chunks"].count_documents({"document_id": {"$in": [lcd_id, f"L{lcd_id}"]}}) == 0:
                    PolicyIngestionService.self_heal_document("LCD", lcd_id, hcpcs_code, keywords)
            for art_id in clean_article_ids:
                if db["policy_chunks"].count_documents({"document_id": {"$in": [art_id, f"A{art_id}"]}}) == 0:
                    PolicyIngestionService.self_heal_document("ARTICLE", art_id, hcpcs_code, keywords)
            
        # 2. Generate Query Embedding
        query_vector = provider.get_embedding(query)
        
        # 3. Build Metadata Filters
        search_filter: Dict[str, Any] = {}
        if ids:
            # We match display document IDs (like L33942, A57311)
            search_filter["document_id"] = {"$in": ids}
            
        if sections:
            search_filter["section"] = {"$in": sections}
            
        # 4. Execute standard MongoDB find and calculate cosine similarity in app layer
        candidates = list(db["policy_chunks"].find(search_filter))
        
        scored_candidates = []
        for cand in candidates:
            cand_emb = cand.get("embedding")
            if cand_emb:
                similarity = cosine_similarity(query_vector, cand_emb)
                scored_candidates.append((cand, similarity))
                
        # Sort candidates by similarity descending
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = scored_candidates[:top_k]
        
        results = []
        for cand, score in top_candidates:
            results.append({
                "document_type": cand["document_type"],
                "document_id": cand["document_id"],
                "document_version": str(cand.get("policy_version") or cand.get("document_version")),
                "title": cand.get("title"),
                "section": cand.get("section"),
                "chunk_order": cand.get("chunk_order", 0),
                "text": cand.get("text"),
                "source_field": cand.get("source_field"),
                "score": score
            })

        # 5. Filter version boundaries & generate citations
        filtered_results = []
        for item in results:
            doc_id = item["document_id"]
            doc_version = item["document_version"]
            doc_type = item["document_type"]
            
            # Version restricted filter check
            if document_versions and doc_id in document_versions:
                expected_ver = str(document_versions[doc_id])
                if str(doc_version) != expected_ver:
                    warnings.append(f"VERSION_NOT_INDEXED: Chunk from {doc_type} {doc_id} has version {doc_version}, but requested {expected_ver}.")
                    continue
                    
            # Generate stable citation format: LCD:L40330:v8:Coverage_Indications:chunk_03
            clean_section = re.sub(r'[^A-Za-z0-9]', '_', item["section"])
            chunk_order_str = f"chunk_{item['chunk_order']:02d}"
            citation_str = f"{doc_type.upper()}:{doc_id}:v{doc_version or '1'}:{clean_section}:{chunk_order_str}"
            
            item["citation"] = {
                "document_id": doc_id,
                "section": item["section"],
                "chunk_id": citation_str
            }
            
            # Score rename check
            item["score"] = float(item["score"])
            filtered_results.append(item)

        return {
            "results": filtered_results,
            "warnings": list(set(warnings))
        }
import re
