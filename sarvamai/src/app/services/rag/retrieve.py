import hashlib
from typing import List
from app.services.rag.qdrant_client import qdrant_client
from app.core.config import settings


def _dummy_embed(text: str) -> list[float]:
    """SHA-256 deterministic embedding (384-dim). Replace with Sarvam embeddings in v2."""
    h = hashlib.sha256(text.encode()).digest()
    extended = (h * (384 // len(h) + 1))[:384]
    return [float(b) / 255.0 for b in extended]


def retrieve_chunks(query: str, top_k: int = 5) -> List[dict]:
    """Retrieve top-k chunks from Qdrant based on query embedding."""
    response = qdrant_client.query_points(
        collection_name="schemes",
        query=_dummy_embed(query),
        limit=top_k,
    )
    return [
        {
            "text": pt.payload["text"],
            "source": pt.payload["source"],
            "score": pt.score,
        }
        for pt in response.points
    ]
