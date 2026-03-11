"""
Embedding module using Google's gemini-embedding-001 model.
Shared by both ingestion and retrieval pipelines.
"""
import os
import logging
from google import genai

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 3072

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY1", "").strip().strip('"')
        if not key:
            raise RuntimeError("GEMINI_API_KEY1 not set — needed for embeddings")
        _client = genai.Client(api_key=key)
    return _client


def embed_text(text: str) -> list[float]:
    """Generate a 3072-dim embedding for a single text string."""
    client = _get_client()
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
    )
    return list(response.embeddings[0].values)


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts in one API call."""
    client = _get_client()
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
    )
    return [list(e.values) for e in response.embeddings]
