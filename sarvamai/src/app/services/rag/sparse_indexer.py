"""
BM25 Sparse Vector Indexing for Hybrid Search.

This module implements BM25 keyword matching for sparse vector representation,
enabling hybrid search (dense + sparse) in Qdrant.
"""

from typing import List, Dict
import json
from pathlib import Path
from rank_bm25 import BM25Okapi


class SparseIndexer:
    """
    Manages BM25 sparse vectors for all chunks.
    
    BM25 is a probabilistic relevance framework that scores documents
    based on keyword frequency and inverse document frequency (IDF).
    
    Usage:
        indexer = SparseIndexer()
        indexer.index_documents(chunks)  # Build BM25 index
        sparse_vecs = indexer.get_sparse_vectors()  # Get as (idx, value) pairs
    """
    
    def __init__(self):
        """Initialize BM25 indexer."""
        self.bm25 = None
        self.chunks = []
        self.tokenized_chunks = []
        self.vocab_to_idx = {}  # vocab_word -> vocab_index
        self.idx_to_vocab = {}  # vocab_index -> vocab_word
        self.sparse_vectors = []  # List of sparse vectors as (idx, value) pairs
        
    def tokenize(self, text: str) -> List[str]:
        """Simple tokenization: lowercase, split on whitespace/punctuation."""
        import re
        # Convert to lowercase and split on non-alphanumeric
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def index_documents(self, chunks: List[str]) -> None:
        """
        Build BM25 index from chunks.
        
        Args:
            chunks: List of text chunks to index
        """
        self.chunks = chunks
        
        # Tokenize all chunks
        self.tokenized_chunks = [self.tokenize(chunk) for chunk in chunks]
        
        # Create BM25 index
        self.bm25 = BM25Okapi(self.tokenized_chunks)
        
        # Build vocabulary
        self._build_vocabulary()
        
        # Precompute sparse vectors for all chunks
        self._compute_sparse_vectors()
    
    def _build_vocabulary(self) -> None:
        """Build vocabulary mapping from all chunks."""
        vocab_idx = 0
        for tokens in self.tokenized_chunks:
            for token in tokens:
                if token not in self.vocab_to_idx:
                    self.vocab_to_idx[token] = vocab_idx
                    self.idx_to_vocab[vocab_idx] = token
                    vocab_idx += 1
    
    def _compute_sparse_vectors(self) -> None:
        """
        Compute sparse BM25 vectors for all chunks.
        
        Sparse vector format: [(vocab_idx, score), ...]
        Only non-zero scores are stored.
        """
        self.sparse_vectors = []
        
        for chunk_idx, tokens in enumerate(self.tokenized_chunks):
            # BM25 scores for this chunk
            sparse_vec = {}  # vocab_idx -> score
            
            for token in set(tokens):
                vocab_idx = self.vocab_to_idx[token]
                # BM25 score for this token in this document
                score = self.bm25.get_scores(tokens)[chunk_idx] if hasattr(self.bm25, 'get_scores') else 1.0
                
                # Use IDF-weighted frequency instead
                # Simpler approach: use term frequency + IDF
                tf = tokens.count(token)
                idf = self.bm25.idf.get(token, 0)
                sparse_vec[vocab_idx] = float(tf * idf)
            
            # Store as sparse format (only non-zero entries)
            self.sparse_vectors.append(sparse_vec)
    
    def score_query(self, query: str, top_k: int = None) -> List[tuple]:
        """
        Score chunks against a query using BM25.
        
        Args:
            query: Query text
            top_k: Return top k results (None = all)
            
        Returns:
            List of (chunk_idx, score) sorted by score descending
        """
        if self.bm25 is None:
            raise ValueError("Must call index_documents first")
        
        query_tokens = self.tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        
        # Sort by score descending
        results = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        
        if top_k:
            results = results[:top_k]
        
        return results
    
    def get_sparse_vectors(self) -> List[Dict[int, float]]:
        """
        Get sparse vectors in Qdrant format.
        
        Returns:
            List of dicts mapping vocab_idx -> score
        """
        return self.sparse_vectors
    
    def get_vocab_size(self) -> int:
        """Get total vocabulary size."""
        return len(self.vocab_to_idx)


def create_sparse_indexer_from_chunks(chunks: List[str]) -> SparseIndexer:
    """
    Factory function to create and initialize a sparse indexer.
    
    Args:
        chunks: List of text chunks
        
    Returns:
        Initialized SparseIndexer
    """
    indexer = SparseIndexer()
    indexer.index_documents(chunks)
    return indexer
