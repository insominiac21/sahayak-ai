"""
Two-Stage Retrieval Pipeline: Hybrid Search + Cross-Encoder Reranking.

Complete Stage 1 pipeline for production-grade RAG:
    Stage 1a: Hybrid Search (Dense 60% + Sparse 40%) → 20 chunks (wide net)
    Stage 1b: Cross-Encoder Rerank (mmarco-MiniLMv2-L12-H384-v1) → 3-4 chunks (quality filter)

This architecture addresses key RAG failure modes:
    - Dense retriever bias → Mitigated by sparse keywords (BM25)
    - "Lost in the Middle" problem → Mitigated by cross-encoder reranking
    - Semantic similarity drift → Validated by 2nd-pass relevance check
    - Inference latency → Optimized: 20 hybrid searches << 40 cross-encoder pairs
    - Multilingual support → Both BGE-M3 and mmarco support Hindi + 100+ languages

Next stage (Phase 2): Send top-4 to LLM with full context
"""

from typing import List, Dict
import time

from app.services.rag.hybrid_retriever import HybridRetriever
from app.services.rag.cross_encoder_reranker import CrossEncoderReranker


class TwoStageRetriever:
    """
    Production-grade two-stage retrieval combining semantic + relevance signals.
    
    Stage 1a (Hybrid Search):
        - Dense: BGE-M3 embeddings + cosine similarity
        - Sparse: BM25 keyword matching
        - Weights: 60% dense + 40% sparse
        - Returns: Top 20 candidates
        
    Stage 1b (Reranking):
        - Model: BGE-Reranker-V2-M3 (cross-encoder)
        - Input: Query + each of 20 candidates
        - Output: Relevance scores [0, 1]
        - Returns: Top 3-4 by relevance
    
    Attributes:
        hybrid_retriever: HybridRetriever instance
        reranker: CrossEncoderReranker instance
    """
    
    def __init__(
        self,
        hybrid_top_k: int = 20,
        rerank_top_k: int = 4,
        dense_weight: float = 0.6
    ):
        """
        Initialize two-stage retriever.
        
        Args:
            hybrid_top_k: Candidates from Stage 1a (default 20)
            rerank_top_k: Final results from Stage 1b (default 3-4)
            dense_weight: Weight for dense search in hybrid (default 0.6)
        """
        self.hybrid_top_k = hybrid_top_k
        self.rerank_top_k = rerank_top_k
        self.dense_weight = dense_weight
        
        print("Initializing two-stage retriever...")
        self.hybrid_retriever = HybridRetriever(dense_weight=dense_weight)
        self.hybrid_retriever.setup()
        
        self.reranker = CrossEncoderReranker()
        print("[OK] Two-stage retriever ready\n")
    
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
            List of top-k reranked chunks with metadata and scores
        """
        # Stage 1a: Hybrid search
        start_stage1 = time.time()
        candidates = self.hybrid_retriever.retrieve(query, top_k=self.hybrid_top_k)
        time_stage1 = time.time() - start_stage1
        
        # Stage 1b: Cross-encoder rerank
        start_stage2 = time.time()
        reranked = self.reranker.rerank_payloads(
            query=query,
            chunks=candidates,
            top_k=self.rerank_top_k
        )
        time_stage2 = time.time() - start_stage2
        
        # Add timing if requested
        if return_full_pipeline:
            for chunk in reranked:
                chunk['_stage1a_time_ms'] = round(time_stage1 * 1000, 2)
                chunk['_stage1b_time_ms'] = round(time_stage2 * 1000, 2)
                chunk['_total_time_ms'] = round((time_stage1 + time_stage2) * 1000, 2)
                chunk['_candidates_evaluated'] = len(candidates)
        
        return reranked


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


# Global instance (lazy load)
_two_stage_instance = None

def get_two_stage_retriever() -> TwoStageRetriever:
    """
    Get or create global two-stage retriever instance.
    
    Returns:
        TwoStageRetriever singleton
    """
    global _two_stage_instance
    if _two_stage_instance is None:
        _two_stage_instance = TwoStageRetriever()
    return _two_stage_instance
