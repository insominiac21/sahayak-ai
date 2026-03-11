import os
import re
import sys
from typing import List

# Ensure src is importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from app.services.rag.qdrant_client import qdrant_client
from app.services.rag.embeddings import embed_batch, EMBEDDING_DIM
from app.core.config import settings

from qdrant_client.models import PointStruct, VectorParams, Distance

VECTOR_SIZE = EMBEDDING_DIM
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





def extract_scheme_name(text: str, fname: str) -> str:
    """Extract the human-readable scheme name from the first markdown heading."""
    first_line = text.split('\n', 1)[0]
    # Match: # Scheme N — Name
    m = re.match(r'^#\s*Scheme\s*\d+\s*[—–-]\s*(.+)$', first_line)
    if m:
        return m.group(1).strip()
    # Fallback: use heading text without '#'
    if first_line.startswith('#'):
        return first_line.lstrip('# ').strip()
    return fname


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
        scheme_name = extract_scheme_name(text, fname)
        chunks = chunk_text(text)
        embeddings = embed_batch(chunks)
        points = [
            PointStruct(
                id=point_id + i,
                vector=emb,
                payload={"text": chunk, "source": scheme_name},
            )
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
        ]
        point_id += len(chunks)
        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)
        print(f"  Ingested {len(chunks)} chunks from {fname} ({scheme_name})")

    print(f"\nDone — {point_id} total points in '{COLLECTION_NAME}'")


if __name__ == "__main__":
    ingest_docs()
