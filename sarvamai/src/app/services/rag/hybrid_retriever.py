"""
Hybrid Search Retriever combining Dense (60%) + Sparse (40%) vectors.

This module implements asymmetric two-stage retrieval:
- Stage 1: Hybrid search (dense 60% + BM25 sparse 40%) → 20 chunks
- (Stage 2 will be cross-encoder reranking in Phase 1D)
"""

from typing import List, Dict, Tuple
from app.services.rag.qdrant_client import get_qdrant_client
from app.services.rag.embeddings_bge import BGEEmbeddingsClient
from app.services.rag.sparse_indexer import SparseIndexer


class HybridRetriever:
    """
    Hybrid search combining dense embeddings (BGE-M3) + sparse BM25.
    
    Weighting: 60% dense + 40% sparse
    Top-K Stage 1: 20 chunks (wide net for next stage reranking)
    
    Workflow:
        1. Dense search: Query embedding vs. all document embeddings (Qdrant)
        2. Sparse search: BM25 scores vs. all documents (locally)
        3. Normalize scores to [0, 1]
        4. Combine: 0.6 * dense_score + 0.4 * sparse_score
        5. Return top-k by combined score
    """
    
    def __init__(self, dense_weight: float = 0.6, sparse_weight: float = 0.4):
        """
        Initialize hybrid retriever.
        
        Args:
            dense_weight: Weight for dense search (0-1)
            sparse_weight: Weight for sparse search (0-1)
        """
        assert dense_weight + sparse_weight == 1.0, "Weights must sum to 1.0"
        
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.embedding_client = BGEEmbeddingsClient()
        self.sparse_indexer = None
        self.collection_name = "schemes"
        self.all_chunks = {}  # chunk_id -> payload
    
    def setup(self, collection_name: str = "schemes") -> None:
        """
        Initialize retrievers by loading all chunks from Qdrant.
        
        Must be called once before retrieval.
        
        Args:
            collection_name: Qdrant collection name
        """
        self.collection_name = collection_name
        
        # Load all chunks from Qdrant
        print(f"Loading all chunks from Qdrant collection '{collection_name}'...")
        try:
            # Scroll through all points
            points, _ = get_qdrant_client().scroll(
                collection_name=collection_name,
                limit=10000,  # Adjust if more chunks
                with_payload=True,
                with_vectors=False
            )
            
            # Extract chunks for BM25 indexing
            extract_text_list = []
            for point in points:
                self.all_chunks[point.id] = point.payload
                extract_text_list.append(point.payload.get("text", ""))
            
            print(f"  Loaded {len(points)} chunks")
            
            # Initialize BM25 sparse indexer
            print(f"Building BM25 sparse index...")
            self.sparse_indexer = SparseIndexer()
            self.sparse_indexer.index_documents(extract_text_list)
            print(f"  Vocabulary size: {self.sparse_indexer.get_vocab_size()}")
            print(f"  [OK] Hybrid retriever ready\n")
            
        except Exception as e:
            print(f"  Error loading chunks: {e}")
            raise
    
    def retrieve(self, query: str, top_k: int = 20) -> List[Dict]:
        """
        Retrieve chunks using hybrid search.
        
        Args:
            query: User query
            top_k: Number of chunks to return (default 20 for Stage 1)
            
        Returns:
            List of dicts with keys: text, source, scheme_name, dense_score, 
                                     sparse_score, hybrid_score
        """
        if not self.sparse_indexer:
            raise ValueError("Must call setup() first")
        
        # 1. Dense search (Qdrant)
        query_embedding = self.embedding_client.embed_query(query)
        dense_results = get_qdrant_client().query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=top_k * 2  # Get extra candidates for hybrid combination
        ).points
        
        dense_scores = {point.id: point.score for point in dense_results}
        
        # 2. Sparse search (BM25)
        sparse_results = self.sparse_indexer.score_query(query, top_k=top_k * 2)
        
        # Format sparse scores: {chunk_id: score}
        # Note: sparse_results are (chunk_idx, score) from the ordered list
        sparse_scores = {}
        for chunk_idx, score in sparse_results:
            # Get chunk_id from all_chunks dict
            chunk_list = list(self.all_chunks.keys())
            if chunk_idx < len(chunk_list):
                chunk_id = chunk_list[chunk_idx]
                sparse_scores[chunk_id] = score
        
        # 3. Normalize scores to [0, 1]
        dense_scores_norm = self._normalize_scores(dense_scores)
        sparse_scores_norm = self._normalize_scores(sparse_scores)
        
        # 4. Combine scores
        combined_scores = {}
        all_chunk_ids = set(dense_scores_norm.keys()) | set(sparse_scores_norm.keys())
        
        for chunk_id in all_chunk_ids:
            dense = dense_scores_norm.get(chunk_id, 0.0)
            sparse = sparse_scores_norm.get(chunk_id, 0.0)
            combined = (self.dense_weight * dense) + (self.sparse_weight * sparse)
            combined_scores[chunk_id] = {
                'dense': dense,
                'sparse': sparse,
                'hybrid': combined
            }
        
        # 5. Sort by combined score and return top-k
        sorted_results = sorted(
            combined_scores.items(),
            key=lambda x: x[1]['hybrid'],
            reverse=True
        )[:top_k]
        
        # Build result dicts
        results = []
        for chunk_id, scores in sorted_results:
            payload = self.all_chunks[chunk_id]
            results.append({
                'id': chunk_id,
                'text': payload.get('text', ''),
                'source': payload.get('source', ''),
                'scheme_name': payload.get('scheme_name', ''),
                'category': payload.get('category', ''),
                'chunk_type': payload.get('chunk_type', ''),
                'benefits': payload.get('benefits', []),
                'dense_score': scores['dense'],
                'sparse_score': scores['sparse'],
                'hybrid_score': scores['hybrid'],
            })
        
        return results
    
    def _normalize_scores(self, scores: Dict[int, float]) -> Dict[int, float]:
        """
        Normalize scores to [0, 1] range.
        
        Args:
            scores: Dict of {chunk_id: score}
            
        Returns:
            Dict of normalized scores
        """
        if not scores:
            return {}
        
        max_score = max(scores.values()) if scores.values() else 1.0
        
        if max_score == 0:
            return {k: 0.0 for k in scores.keys()}
        
        return {k: v / max_score for k, v in scores.items()}


def create_hybrid_retriever(dense_weight: float = 0.6) -> HybridRetriever:
    """
    Factory function to create and initialize a hybrid retriever.
    
    Args:
        dense_weight: Weight for dense search (default 0.6)
        
    Returns:
        Initialized HybridRetriever
    """
    retriever = HybridRetriever(dense_weight=dense_weight)
    retriever.setup()
    return retriever
