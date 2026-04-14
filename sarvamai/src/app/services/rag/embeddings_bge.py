"""
Embedding models for RAG.
Uses HuggingFace Inference API for BGE-M3 embeddings (saves ~500MB RAM).
Thread-safe singleton pattern to prevent race conditions with concurrent requests.
"""

import os
import threading
from typing import List
from huggingface_hub import InferenceClient


class BGEEmbeddingsClient:
    """
    BGE-M3 embeddings client using HuggingFace Inference API.
    - No local model load (saves 500MB RAM)
    - Trade-off: ~300ms latency vs 50ms local
    - Multilingual, optimized for Q&D pairs
    - Thread-safe singleton pattern
    """
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Implement thread-safe singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking: check again after acquiring lock
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize HF Inference client for BGE-M3 (only once)."""
        # Prevent re-initialization if already done
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            api_token = os.getenv("HF_TOKEN")
            if not api_token:
                raise RuntimeError(
                    "HF_TOKEN environment variable not set. "
                    "Get one at https://huggingface.co/settings/tokens"
                )
            
            self.client = InferenceClient(api_key=api_token)
            self.model_name = "BAAI/bge-m3"
            self.embedding_dim = 1024  # BGE-M3 dimension
            print(f"Using HF Inference API for {self.model_name}")
            print(f"Embedding dimension: {self.embedding_dim}\n")
            self._initialized = True

    def embed_query(self, query: str) -> List[float]:
        """
        Embed a query via HF Inference API.
        
        Args:
            query: Query text
        
        Returns:
            Embedding vector (1024 dimensions)
        """
        try:
            response = self.client.feature_extraction(
                text=query,
                model=self.model_name
            )
            # HF returns list of floats directly
            return response
        except Exception as e:
            raise RuntimeError(f"Failed to embed query: {e}")

    def embed_document(self, document: str) -> List[float]:
        """
        Embed a document chunk via HF Inference API.
        
        Args:
            document: Document chunk text
        
        Returns:
            Embedding vector (1024 dimensions)
        """
        try:
            response = self.client.feature_extraction(
                text=document,
                model=self.model_name
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Failed to embed document: {e}")

    def embed_batch_documents(self, documents: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Embed multiple documents via HF Inference API.
        
        Args:
            documents: List of document texts
            batch_size: Batch size for processing (ignored for HF API)
        
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for doc in documents:
            try:
                embedding = self.client.feature_extraction(
                    text=doc,
                    model=self.model_name
                )
                embeddings.append(embedding)
            except Exception as e:
                print(f"Warning: Failed to embed document: {e}")
                # Return zero vector on failure (will have low matches in Qdrant)
                embeddings.append([0.0] * self.embedding_dim)
        return embeddings

    def embed_batch_queries(self, queries: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Embed multiple queries via HF Inference API.
        
        Args:
            queries: List of query texts
            batch_size: Batch size for processing (ignored for HF API)
        
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for query in queries:
            try:
                embedding = self.client.feature_extraction(
                    text=query,
                    model=self.model_name
                )
                embeddings.append(embedding)
            except Exception as e:
                print(f"Warning: Failed to embed query: {e}")
                embeddings.append([0.0] * self.embedding_dim)
        return embeddings


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
