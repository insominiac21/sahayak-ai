"""
Retrieval Pipeline: Hybrid Search (Dense + Sparse).

Simplified Stage 1 pipeline for memory-constrained environments (512MB Render free tier):
    Stage 1: Hybrid Search (Dense 60% + Sparse 40%) → top-4 chunks directly
    
Uses HuggingFace Inference API for embeddings (saves 500MB local model).
Skips cross-encoder reranking (saves 62MB) since quality still good with hybrid search.

Architecture addresses key RAG failure modes:
    - Dense retriever bias → Mitigated by sparse keywords (BM25)
    - Multilingual support → BGE-M3 via HF API supports 100+ languages
    - Low memory footprint → No local model loads
    - Thread-safe singleton pattern prevents race conditions with concurrent requests

Next stage (Phase 3): Add agentic tools (web search, eligibility calculator)
"""

from typing import List, Dict
import time
import threading

from app.services.rag.hybrid_retriever import HybridRetriever


class TwoStageRetriever:
    """
    Production hybrid search combining semantic + keyword signals.
    
    Stage 1 (Hybrid Search):
        - Dense: BGE-M3 embeddings (via HF API) + cosine similarity
        - Sparse: BM25 keyword matching
        - Weights: 60% dense + 40% sparse
        - Returns: Top 4 candidates directly (no reranking to save RAM)
    
    Attributes:
        hybrid_retriever: HybridRetriever instance
    """
    
    def __init__(
        self,
        hybrid_top_k: int = 20,
        rerank_top_k: int = 4,
        dense_weight: float = 0.6
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            hybrid_top_k: Candidates from hybrid search (default 20, not all used)
            rerank_top_k: Final results to return (default 4)
            dense_weight: Weight for dense search in hybrid (default 0.6)
        """
        self.hybrid_top_k = hybrid_top_k
        self.rerank_top_k = rerank_top_k
        self.dense_weight = dense_weight
        
        self.hybrid_retriever = HybridRetriever(dense_weight=dense_weight)
        # No cross-encoder reranker (saves 62MB model)
    
    def retrieve(
        self, 
        query: str, 
        return_full_pipeline: bool = False
    ) -> List[Dict]:
        """
        Execute complete two-stage retrieval.
        
        Args:
            query: User query
            return_full_pipeline: Include timing + intermediate results
            
        Returns:
            List of top-k chunks with metadata and scores
        """
        # Hybrid retriever's setup() is thread-safe and returns early if already initialized
        self.hybrid_retriever.setup()
        
        # Stage 1: Hybrid search (dense 60% + sparse 40%)
        # Skip Stage 2 reranking to save 62MB cross-encoder model
        start_time = time.time()
        results = self.hybrid_retriever.retrieve(query, top_k=self.rerank_top_k)
        elapsed = time.time() - start_time
        
        # Add timing if requested
        if return_full_pipeline:
            for chunk in results:
                chunk['_hybrid_search_time_ms'] = round(elapsed * 1000, 2)
        
        return results


def create_two_stage_retriever(
    hybrid_top_k: int = 20,
    rerank_top_k: int = 4
) -> TwoStageRetriever:
    """
    Factory function to create and initialize a two-stage retriever.
    
    Args:
        hybrid_top_k: Number of candidates to retrieve in Stage 1a
        rerank_top_k: Number of final results from Stage 1b
        
    Returns:
        Initialized TwoStageRetriever
    """
    return TwoStageRetriever(
        hybrid_top_k=hybrid_top_k,
        rerank_top_k=rerank_top_k
    )


# Global instance (lazy load with thread safety)
_two_stage_instance = None
_two_stage_lock = threading.Lock()

def get_two_stage_retriever() -> TwoStageRetriever:
    """
    Get or create global two-stage retriever instance (thread-safe singleton).
    
    Uses double-checked locking pattern to prevent race conditions
    when multiple concurrent requests try to initialize simultaneously.
    
    Returns:
        TwoStageRetriever singleton
    """
    global _two_stage_instance
    
    # First check (without lock) for performance
    if _two_stage_instance is None:
        with _two_stage_lock:
            # Second check (with lock) to prevent race condition
            if _two_stage_instance is None:
                _two_stage_instance = TwoStageRetriever()
    
    return _two_stage_instance
