from typing import List
from app.services.rag.qdrant_client import qdrant_client
from app.services.rag.embeddings import embed_text


def retrieve_chunks(query: str, top_k: int = 5) -> List[dict]:
    """Retrieve top-k chunks from Qdrant based on query embedding."""
    response = qdrant_client.query_points(
        collection_name="schemes",
        query=embed_text(query),
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
