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
        unrestricted: bool = False
    ) -> Dict[str, Any]:
        """Performs metadata-restricted hybrid vector search to retrieve relevant policy sections."""
        db = db_connection.get_db()
        provider = get_embedding_provider()
        warnings: List[str] = []
        
        # 1. Scope Validation
        ids = []
        if policy_scope:
            if policy_scope.get("ncd_ids"):
                ids.extend(policy_scope["ncd_ids"])
            if policy_scope.get("lcd_ids"):
                ids.extend(policy_scope["lcd_ids"])
            if policy_scope.get("article_ids"):
                ids.extend(policy_scope["article_ids"])
                
        # "If no policy scope is provided, the normal prior-auth pathway should reject or explicitly mark the retrieval as unrestricted/debug mode."
        if not ids and not unrestricted:
            raise ValueError(
                "RAG policy scope is empty. Prior-authorization retrieval must restrict vector search boundaries. "
                "Set unrestricted=True to run debug/unrestricted queries."
            )
            
        # 2. Generate Query Embedding
        query_vector = provider.get_embedding(query)
        
        # 3. Build Metadata Filters
        search_filter: Dict[str, Any] = {}
        if ids:
            # We match display document IDs (like L33942, A57311)
            search_filter["document_id"] = {"$in": ids}
            
        if sections:
            search_filter["section"] = {"$in": sections}
            
        # 4. Execute Vector Search (Attempting Atlas Search first)
        results = []
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": top_k * 10,
                    "limit": top_k,
                    "filter": search_filter
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "document_type": 1,
                    "document_id": 1,
                    "document_version": 1,
                    "title": 1,
                    "section": 1,
                    "chunk_order": 1,
                    "text": 1,
                    "source_field": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        try:
            results = list(db["policy_chunks"].aggregate(pipeline))
        except Exception as e:
            # Fall back to local cosine similarity calculation (extremely useful for tests and M0 tier setup)
            warnings.append(f"Atlas Search Index inactive, fell back to local similarity engine. Details: {str(e)}")
            
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
                    "document_version": cand.get("document_version"),
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
            doc_version = item.get("document_version", "1")
            doc_type = item["document_type"]
            
            # Version restricted filter check
            if document_versions and doc_id in document_versions:
                expected_ver = document_versions[doc_id]
                if doc_version != expected_ver:
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
