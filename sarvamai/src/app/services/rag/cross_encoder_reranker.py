"""
Cross-Encoder Reranker for semantic relevance ranking.

This module uses BGE Reranker V2 M3 (multilingual cross-encoder)
to rerank retrieved chunks based on query-document relevance.

Model: cross-encoder/bge-reranker-v2-m3
- Input: (query, document) pairs
- Output: Relevance score [0.0, 1.0]
- Size: ~200MB
- Supports: 100+ languages including Hindi
- Inference: <10ms per pair on CPU

Usage in two-stage pipeline:
    Stage 1: Hybrid search → 20 chunks
    Stage 2: Cross-encoder rerank → 3-4 chunks (Phase 1D)
    Stage 3: Send to LLM with reranked context (Phase 2)
"""

from typing import List, Tuple, Dict, Callable
from sentence_transformers import CrossEncoder


class CrossEncoderReranker:
    """
    Semantic relevance reranker using multilingual cross-encoder.
    
    Cross-encoder directly scores query-document pairs,
    avoiding the "Lost in the Middle" problem where middle documents
    are scored lower by dense retrievers.
    
    Model: cross-encoder/mmarco-MiniLMv2-L12-H384-v1
        - Multilingual (supports Hindi + 100+ languages)
        - Fast (MiniLM = ~150MB)
        - High quality cross-encoder reranking
        - <10ms per pair on CPU
    
    Attributes:
        model_name: Hugging Face model identifier
        model: Loaded CrossEncoder instance
        batch_size: Process multiple pairs simultaneously
    """
    
    MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-2-v2"
    
    def __init__(self, model_name: str = None, batch_size: int = 32):
        """
        Initialize cross-encoder reranker.
        
        Args:
            model_name: Hugging Face model ID (default: BGE Reranker V2 M3)
            batch_size: Batch processing size for efficiency
        """
        self.model_name = model_name or self.MODEL_NAME
        self.batch_size = batch_size
        self.model = None
        self._model_loaded = False
    
    def _ensure_model_loaded(self) -> None:
        """Lazy-load cross-encoder model on first use (saves 62MB at startup)."""
        if self._model_loaded:
            return
        print(f"Loading {self.model_name}...")
        try:
            self.model = CrossEncoder(self.model_name)
            self._model_loaded = True
            print(f"[OK] Cross-encoder ready\n")
        except Exception as e:
            print(f"[ERROR] Error loading model: {e}")
            raise
    
    def rerank(
        self, 
        query: str, 
        documents: List[str],
        top_k: int = 4
    ) -> List[Tuple[int, float, str]]:
        """
        Rerank documents by query relevance.
        
        Args:
            query: User query
            documents: List of document texts to rerank
            top_k: Number of top results to return (default 4 for Phase 1D)
            
        Returns:
            List of (original_index, score, text) tuples, sorted by score descending
        """
        if not documents:
            return []
        
        self._ensure_model_loaded()  # Lazy load on first call
        
        # Create query-document pairs
        pairs = [[query, doc] for doc in documents]
        
        # Score all pairs
        scores = self.model.predict(pairs, batch_size=self.batch_size)
        
        # Create ranking (index, score, text)
        rankings = [
            (i, float(score), documents[i])
            for i, score in enumerate(scores)
        ]
        
        # Sort by score descending
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        # Return top-k
        return rankings[:top_k]
    
    def rerank_payloads(
        self,
        query: str,
        chunks: List[Dict],
        top_k: int = 4
    ) -> List[Dict]:
        """
        Rerank chunks (with metadata) by relevance.
        
        Args:
            query: User query
            chunks: List of chunk dicts with 'text' key
            top_k: Number of results to return
            
        Returns:
            Reranked chunk dicts with added 'rerank_score' field
        """
        if not chunks:
            return []
        
        self._ensure_model_loaded()  # Lazy load on first call
        
        documents = [c.get('text', '') for c in chunks]
        rankings = self.rerank(query, documents, top_k=top_k)
        
        # Map back to original chunk dicts
        result = []
        for orig_idx, score, _ in rankings:
            chunk = chunks[orig_idx].copy()
            chunk['rerank_score'] = score
            result.append(chunk)
        
        return result


def create_reranker(top_k: int = 4) -> Callable:
    """
    Factory function to create a reranker function.
    
    Args:
        top_k: Default number of results to return
        
    Returns:
        Reranking function that matches the rerank_payloads signature
    """
    reranker = CrossEncoderReranker()
    
    def rerank_fn(query: str, chunks: List[Dict]) -> List[Dict]:
        return reranker.rerank_payloads(query, chunks, top_k=top_k)
    
    return rerank_fn


# Global singleton
_reranker_instance = None

def get_reranker() -> CrossEncoderReranker:
    """
    Get or create global reranker instance.
    
    Returns:
        CrossEncoderReranker singleton
    """
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = CrossEncoderReranker()
    return _reranker_instance
