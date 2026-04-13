"""
Migration script to re-embed scheme documents with BGE-M3 and add metadata.
Run this ONCE to upgrade from old Gemini embeddings to new BGE-M3 + metadata system.

Usage:
    python scripts/migrate_to_bge_m3.py
"""

import os
import json
import sys
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm

# Add sarvamai/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "sarvamai" / "src"))

from app.services.rag.semantic_chunker import SemanticChunker
from app.services.rag.metadata_extractor import SchemeMetadataExtractor
from app.services.rag.embeddings_bge import BGEEmbeddingsClient
from app.services.rag.qdrant_client import qdrant_client
from qdrant_client.models import VectorParams, Distance, PointStruct


def load_documents_from_markdown(data_dir: str) -> Dict[str, str]:
    """
    Load markdown documents from directory.
    
    Args:
        data_dir: Directory containing .md files
    
    Returns:
        Dict mapping filename to content
    """
    documents = {}
    data_path = Path(data_dir)
    
    if not data_path.exists():
        print(f"Data directory not found: {data_dir}")
        return documents
    
    for md_file in data_path.glob("*.md"):
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                documents[md_file.stem] = f.read()
                print(f"Loaded: {md_file.name}")
        except Exception as e:
            print(f"Error loading {md_file.name}: {e}")
    
    return documents


def migrate_documents(
    data_dir: str = None,
    qdrant_url: str = None,
    qdrant_key: str = None,
    collection_name: str = "schemes",
    recreate_collection: bool = False
):
    """
    Main migration function.
    
    Args:
        data_dir: Directory with markdown files (default: ./data)
        qdrant_url: Qdrant URL (default from env)
        qdrant_key: Qdrant API key (default from env)
        collection_name: Qdrant collection name
        recreate_collection: Whether to recreate the collection (CAUTION: deletes all data)
    """
    
    # Defaults
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "seed_docs")
    if qdrant_url is None:
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    if qdrant_key is None:
        qdrant_key = os.getenv("QDRANT_API_KEY", "")
    
    print(f"\n{'='*60}")
    print(f"MIGRATION: Gemini (3072D) → BGE-M3 (1024D) + Metadata")
    print(f"{'='*60}")
    print(f"Data dir: {data_dir}")
    print(f"Qdrant URL: {qdrant_url}")
    print(f"Collection: {collection_name}")
    print(f"Recreate: {recreate_collection}\n")
    
    # 1. Load documents
    print("Step 1: Loading documents...")
    documents = load_documents_from_markdown(data_dir)
    print(f"Loaded {len(documents)} documents\n")
    
    if not documents:
        print("No documents found! Exiting.")
        return
    
    # 2. Initialize clients
    print("Step 2: Initializing clients...")
    chunker = SemanticChunker(target_chunk_tokens=250, max_chunk_tokens=300)
    metadata_extractor = SchemeMetadataExtractor()
    embedding_client = BGEEmbeddingsClient()
    print(f"BGE-M3 ready (dimension: {embedding_client.embedding_dim})\n")
    
    # 3. Recreate collection if requested
    if recreate_collection:
        print(f"Step 3: Recreating collection '{collection_name}'...")
        try:
            qdrant_client.delete_collection(collection_name)
            print(f"Deleted old collection\n")
        except:
            pass
        
        # Create new collection with BGE-M3 dimensions
        qdrant_client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=embedding_client.embedding_dim,
                distance=Distance.COSINE
            )
        )
        print(f"Created new collection with {embedding_client.embedding_dim}D vectors\n")
    else:
        print("Step 3: (Skipping collection recreation)\n")
    
    # 4. Process documents
    print("Step 4: Chunking, extracting metadata, and embedding...")
    
    all_chunks = []
    chunk_id = 1
    
    for doc_name, doc_content in documents.items():
        print(f"\nProcessing: {doc_name}")
        
        # Chunk the document
        chunks = chunker.chunk(doc_content)
        print(f"  Chunks: {len(chunks)}")
        
        # For each chunk, extract metadata and embed
        chunk_embeddings = embedding_client.embed_batch_documents(chunks, batch_size=16)
        
        for i, (chunk_text, embedding) in enumerate(zip(chunks, chunk_embeddings)):
            # Extract metadata
            metadata = metadata_extractor.extract_all(chunk_text, source=doc_name, chunk_number=i)
            
            # Create Qdrant point
            point = PointStruct(
                id=chunk_id,
                vector=embedding,
                payload={
                    "text": chunk_text,
                    "scheme_name": metadata["scheme_name"],
                    "category": metadata["category"],
                    "applicability": metadata["applicability"],
                    "income_limit": metadata["income_limit"],
                    "benefits": metadata["benefits"],
                    "chunk_type": metadata["chunk_type"],
                    "source": metadata["source"],
                }
            )
            all_chunks.append(point)
            chunk_id += 1
    
    print(f"\n✓ Created {len(all_chunks)} total chunks\n")
    
    # 5. Upload to Qdrant
    print("Step 5: Uploading to Qdrant...")
    
    batch_size = 100
    for i in tqdm(range(0, len(all_chunks), batch_size), desc="Uploading"):
        batch = all_chunks[i:i + batch_size]
        qdrant_client.upsert(
            collection_name=collection_name,
            points=batch
        )
    
    print(f"\n✓ Successfully uploaded {len(all_chunks)} points to Qdrant\n")
    
    # 6. Verify
    print("Step 6: Verification...")
    collection_info = qdrant_client.get_collection(collection_name)
    print(f"Collection '{collection_name}':")
    print(f"  Points: {collection_info.points_count}")
    print(f"  Vector size: {collection_info.config.params.vectors.size}")
    print(f"  Distance metric: {collection_info.config.params.vectors.distance}")
    
    # Sample a chunk to verify metadata
    sample = qdrant_client.scroll(collection_name, limit=1)[0][0]
    print(f"\nSample chunk metadata:")
    for key, value in sample.payload.items():
        if key != "text":
            print(f"  {key}: {value}")
    
    print(f"\n{'='*60}")
    print(f"✓ MIGRATION COMPLETE")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Run migration
    # NOTE: Set recreate_collection=True ONLY on first run
    migrate_documents(recreate_collection=True)
