from typing import List
from app.services.rag.two_stage_retriever import get_two_stage_retriever


def retrieve_chunks(query: str, top_k: int = 4) -> List[dict]:
    """
    Retrieve top-k chunks using two-stage pipeline.
    
    Stage 1a: Hybrid search (dense 60% + sparse 40%) → 20 candidates
    Stage 1b: Cross-encoder reranking → top 4 final results
    
    Args:
        query: User query
        top_k: Number of final results (default 4 for optimal TTFT on WhatsApp)
        
    Returns:
        List of reranked chunks with metadata and relevance scores
    """
    retriever = get_two_stage_retriever()
    results = retriever.retrieve(query)
    
    return [
        {
            "id": r.get("id"),
            "text": r.get("text", ""),
            "source": r.get("source", ""),
            "scheme_name": r.get("scheme_name", ""),
            "category": r.get("category", ""),
            "chunk_type": r.get("chunk_type", ""),
            "benefits": r.get("benefits", []),
            "applicability": r.get("applicability", []),
            "hybrid_score": r.get("hybrid_score", 0),
            "rerank_score": r.get("rerank_score", 0),
        }
        for r in results[:top_k]
    ]
