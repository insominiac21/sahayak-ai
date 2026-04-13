"""
Embedding models for RAG.
Uses BGE-M3 (sentence-transformers) for efficient, accurate embeddings.
"""

import os
from typing import List
import numpy as np


class BGEEmbeddingsClient:
    """
    BGE-M3 embeddings client (Bi-Encoder for asymmetric retrieval).
    Multilingual, optimized for Q&D pairs, production-grade.
    """

    def __init__(self):
        """Initialize BGE-M3 embedding model."""
        try:
            from sentence_transformers import SentenceTransformer
            
            model_name = "BAAI/bge-m3"
            print(f"Loading {model_name}...")
            self.model = SentenceTransformer(model_name)
            self.embedding_dim = 1024  # BGE-M3 dimension
            print(f"Model loaded. Embedding dimension: {self.embedding_dim}")
            
        except ImportError:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load BGE-M3 model: {e}")

    def embed_query(self, query: str) -> List[float]:
        """
        Embed a query (optimized for short questions).
        
        Args:
            query: Query text
        
        Returns:
            Embedding vector (1024 dimensions)
        """
        embedding = self.model.encode(
            query,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        return embedding.tolist()

    def embed_document(self, document: str) -> List[float]:
        """
        Embed a document chunk (optimized for longer documents).
        
        Args:
            document: Document chunk text
        
        Returns:
            Embedding vector (1024 dimensions)
        """
        embedding = self.model.encode(
            document,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        return embedding.tolist()

    def embed_batch_documents(self, documents: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Embed multiple documents efficiently.
        
        Args:
            documents: List of document texts
            batch_size: Batch size for processing
        
        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(
            documents,
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        return [e.tolist() for e in embeddings]

    def embed_batch_queries(self, queries: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Embed multiple queries efficiently.
        
        Args:
            queries: List of query texts
            batch_size: Batch size for processing
        
        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(
            queries,
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        return [e.tolist() for e in embeddings]


# Global client instance (lazy loaded)
_embedding_client = None


def get_embedding_client() -> BGEEmbeddingsClient:
    """
    Get or initialize the global embedding client.
    
    Returns:
        BGEEmbeddingsClient instance
    """
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = BGEEmbeddingsClient()
    return _embedding_client


def embed_query(query: str) -> List[float]:
    """
    Embed a single query using the global client.
    
    Args:
        query: Query text
    
    Returns:
        Embedding vector
    """
    client = get_embedding_client()
    return client.embed_query(query)


def embed_document(document: str) -> List[float]:
    """
    Embed a single document using the global client.
    
    Args:
        document: Document text
    
    Returns:
        Embedding vector
    """
    client = get_embedding_client()
    return client.embed_document(document)
