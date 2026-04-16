"""
Embedding models for RAG.
Uses HuggingFace Inference API for BGE-M3 embeddings (saves ~500MB RAM).
Thread-safe singleton pattern to prevent race conditions with concurrent requests.
Includes retry logic for transient 503/504 errors (exponential backoff, max 4 attempts).
"""

import os
import logging
import threading
from typing import List
from huggingface_hub import InferenceClient
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    RetryError,
)

logger = logging.getLogger(__name__)


def _should_retry_hf_error(exception: Exception) -> bool:
    """
    Determine if an HF Inference API error is retryable.
    
    Retries on:
    - 503 Service Unavailable (model warming up, temporary overload)
    - 504 Gateway Timeout (transient network issue)
    - Connection errors (temporary network issue)
    
    Does NOT retry on:
    - 400 Bad Request (malformed request, our fault)
    - 401 Unauthorized (invalid API key, our fault)
    
    Args:
        exception: The exception that was raised
    
    Returns:
        True if we should retry, False otherwise
    """
    error_str = str(exception).lower()
    
    # Retry on 503/504 HTTP errors
    if "503" in error_str or "504" in error_str:
        return True
    
    # Retry on connection/timeout errors
    if "timeout" in error_str or "connection" in error_str:
        return True
    
    # Do NOT retry on 400/401 errors (client errors, our fault)
    if "400" in error_str or "401" in error_str:
        return False
    
    # For other unexpected errors, don't retry (fail fast)
    return False


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
        Embed a query via HF Inference API with retry logic.
        
        Uses exponential backoff (2-10s) for transient 503/504 errors.
        Max 4 attempts before raising RuntimeError.
        
        Args:
            query: Query text
        
        Returns:
            Embedding vector (1024 dimensions)
            
        Raises:
            RuntimeError: If all retries exhausted or non-retryable error occurs
        """
        @retry(
            stop=stop_after_attempt(4),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception(_should_retry_hf_error),
            reraise=True,
        )
        def _call_hf_api():
            """Make the actual HF API call (wrapped for retries)."""
            return self.client.feature_extraction(
                text=query,
                model=self.model_name
            )
        
        try:
            response = _call_hf_api()
            return response
        except RetryError as e:
            error_msg = f"Failed to embed query after 4 retries: {e.last_attempt.exception}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Failed to embed query (non-retryable error): {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def embed_document(self, document: str) -> List[float]:
        """
        Embed a document chunk via HF Inference API with retry logic.
        
        Uses exponential backoff (2-10s) for transient 503/504 errors.
        Max 4 attempts before raising RuntimeError.
        
        Args:
            document: Document chunk text
        
        Returns:
            Embedding vector (1024 dimensions)
            
        Raises:
            RuntimeError: If all retries exhausted or non-retryable error occurs
        """
        @retry(
            stop=stop_after_attempt(4),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception(_should_retry_hf_error),
            reraise=True,
        )
        def _call_hf_api():
            """Make the actual HF API call (wrapped for retries)."""
            return self.client.feature_extraction(
                text=document,
                model=self.model_name
            )
        
        try:
            response = _call_hf_api()
            return response
        except RetryError as e:
            error_msg = f"Failed to embed document after 4 retries: {e.last_attempt.exception}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Failed to embed document (non-retryable error): {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def embed_batch_documents(self, documents: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Embed multiple documents via HF Inference API with retry logic.
        
        Each document gets up to 4 retries with exponential backoff (2-10s).
        On final failure, logs error and returns zero vector.
        
        Args:
            documents: List of document texts
            batch_size: Batch size for processing (ignored for HF API)
        
        Returns:
            List of embedding vectors (zero vectors for failed documents)
        """
        @retry(
            stop=stop_after_attempt(4),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception(_should_retry_hf_error),
            reraise=True,
        )
        def _call_hf_api_for_doc(doc):
            """Make the actual HF API call for one document (wrapped for retries)."""
            return self.client.feature_extraction(
                text=doc,
                model=self.model_name
            )
        
        embeddings = []
        for i, doc in enumerate(documents):
            try:
                embedding = _call_hf_api_for_doc(doc)
                embeddings.append(embedding)
            except RetryError as e:
                error_msg = f"Failed to embed document {i} after 4 retries: {e.last_attempt.exception}"
                logger.error(error_msg)
                # Return zero vector on failure (will have low matches in Qdrant)
                embeddings.append([0.0] * self.embedding_dim)
            except Exception as e:
                error_msg = f"Failed to embed document {i} (non-retryable error): {e}"
                logger.error(error_msg)
                embeddings.append([0.0] * self.embedding_dim)
        
        return embeddings

    def embed_batch_queries(self, queries: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Embed multiple queries via HF Inference API with retry logic.
        
        Each query gets up to 4 retries with exponential backoff (2-10s).
        On final failure, logs error and returns zero vector.
        
        Args:
            queries: List of query texts
            batch_size: Batch size for processing (ignored for HF API)
        
        Returns:
            List of embedding vectors (zero vectors for failed queries)
        """
        @retry(
            stop=stop_after_attempt(4),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception(_should_retry_hf_error),
            reraise=True,
        )
        def _call_hf_api_for_query(q):
            """Make the actual HF API call for one query (wrapped for retries)."""
            return self.client.feature_extraction(
                text=q,
                model=self.model_name
            )
        
        embeddings = []
        for i, query in enumerate(queries):
            try:
                embedding = _call_hf_api_for_query(query)
                embeddings.append(embedding)
            except RetryError as e:
                error_msg = f"Failed to embed query {i} after 4 retries: {e.last_attempt.exception}"
                logger.error(error_msg)
                embeddings.append([0.0] * self.embedding_dim)
            except Exception as e:
                error_msg = f"Failed to embed query {i} (non-retryable error): {e}"
                logger.error(error_msg)
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
