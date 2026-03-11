import os
import sys
import hashlib
from typing import List

# Ensure src is importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from app.services.rag.qdrant_client import qdrant_client
from app.core.config import settings

from qdrant_client.models import PointStruct, VectorParams, Distance

VECTOR_SIZE = 384
COLLECTION_NAME = "schemes"


def chunk_text(text: str, chunk_size: int = 512) -> List[str]:
    """Chunk text into paragraphs or fixed-size blocks."""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    for para in paragraphs:
        while len(para) > chunk_size:
            chunks.append(para[:chunk_size])
            para = para[chunk_size:]
        chunks.append(para)
    return chunks


def dummy_embed(text: str) -> List[float]:
    """Deterministic 384-dim embedding from SHA-256 hash (replace with Sarvam embedding later)."""
    h = hashlib.sha256(text.encode()).digest()
    # Repeat hash bytes to fill 384 dims
    extended = (h * (384 // len(h) + 1))[:384]
    return [float(b) / 255.0 for b in extended]


def ingest_docs():
    """Read Markdown files, chunk, embed, upsert to Qdrant vector DB."""
    seed_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/seed_docs/'))
    # Create collection if not exists
    if not qdrant_client.collection_exists(COLLECTION_NAME):
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        print(f"Created collection '{COLLECTION_NAME}'")
    else:
        print(f"Collection '{COLLECTION_NAME}' already exists")

    point_id = 0
    for fname in sorted(os.listdir(seed_dir)):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(seed_dir, fname)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        chunks = chunk_text(text)
        points = []
        for chunk in chunks:
            embedding = dummy_embed(chunk)
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={"text": chunk, "source": fname},
                )
            )
            point_id += 1
        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)
        print(f"  Ingested {len(chunks)} chunks from {fname}")

    print(f"\nDone — {point_id} total points in '{COLLECTION_NAME}'")


if __name__ == "__main__":
    ingest_docs()
