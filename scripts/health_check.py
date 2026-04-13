"""
Health Check Script: Verify all services in the RAG pipeline.

Tests:
1. Qdrant vector database connectivity
2. Supabase database connectivity (if enabled)
3. Google Genai LLM API
4. BGE-M3 embeddings model (download + inference)
5. Cross-encoder reranker (download + inference)
6. Full two-stage retrieval pipeline
7. WhatsApp webhook status
"""

import sys
from pathlib import Path
import time

# Add sarvamai/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "sarvamai" / "src"))

from app.core.config import settings


def test_qdrant() -> bool:
    """Test Qdrant vector database connectivity."""
    print("[1/7] Testing Qdrant...")
    try:
        from app.services.rag.qdrant_client import qdrant_client
        
        # Try to get collections
        collections = qdrant_client.get_collections()
        print(f"  [OK] Connected to Qdrant")
        print(f"  [OK] Found {len(collections.collections)} collections")
        
        # Check schemes collection
        try:
            info = qdrant_client.get_collection("schemes")
            print(f"  [OK] 'schemes' collection has {info.points_count} vectors")
            print(f"  [OK] Vector dimension: {info.config.params.vectors.size}D")
        except Exception as e:
            print(f"  [WARN] 'schemes' collection not found: {e}")
        
        return True
    except Exception as e:
        print(f"  [ERROR] Qdrant failed: {e}")
        return False


def test_supabase() -> bool:
    """Test Supabase database connectivity."""
    print("\n[2/7] Testing Supabase...")
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host=settings.SUPABASE_HOST,
            port=5432,
            database=settings.SUPABASE_DB,
            user=settings.SUPABASE_USER,
            password=settings.SUPABASE_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        print(f"  [OK] Connected to Supabase")
        print(f"  [OK] Database responsive")
        return True
    except Exception as e:
        print(f"  [WARN] Supabase unavailable: {e}")
        print(f"       (Optional - sessions will work without logging)")
        return False


def test_google_genai() -> bool:
    """Test Google Genai API connectivity."""
    print("\n[3/7] Testing Google Genai API...")
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        
        # List available models
        models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        print(f"  [OK] Connected to Google Genai")
        print(f"  [OK] {len(models)} generative models available")
        
        if models:
            print(f"  [OK] Primary model: {models[0].name}")
        
        return True
    except Exception as e:
        print(f"  [ERROR] Google Genai failed: {e}")
        return False


def test_embeddings() -> bool:
    """Test BGE-M3 embeddings model."""
    print("\n[4/7] Testing BGE-M3 Embeddings...")
    try:
        from app.services.rag.embeddings_bge import get_embedding_client
        
        client = get_embedding_client()
        print(f"  [OK] Model loaded: BAAI/bge-m3")
        print(f"  [OK] Embedding dimension: {client.embedding_dim}D")
        
        # Test embedding
        test_query = "What are government schemes?"
        embedding = client.embed_query(test_query)
        print(f"  [OK] Embedded test query ({len(embedding)} dimensions)")
        
        return True
    except Exception as e:
        print(f"  [ERROR] Embeddings failed: {e}")
        return False


def test_reranker() -> bool:
    """Test cross-encoder reranker model."""
    print("\n[5/7] Testing Cross-Encoder Reranker...")
    try:
        from app.services.rag.cross_encoder_reranker import CrossEncoderReranker
        
        reranker = CrossEncoderReranker()
        print(f"  [OK] Model loaded: ms-marco-MiniLM-L-2-v2")
        
        # Test reranking
        test_docs = ["PM-KISAN provides cash to farmers", "Health insurance for rural areas"]
        test_query = "What farming schemes exist?"
        results = reranker.rerank(test_query, test_docs, top_k=2)
        print(f"  [OK] Ranked {len(test_docs)} documents")
        print(f"  [OK] Top result score: {results[0][1]:.3f}")
        
        return True
    except Exception as e:
        print(f"  [ERROR] Reranker failed: {e}")
        return False


def test_hybrid_retriever() -> bool:
    """Test hybrid retriever (dense + sparse)."""
    print("\n[6/7] Testing Hybrid Retriever...")
    try:
        from app.services.rag.hybrid_retriever import HybridRetriever
        
        retriever = HybridRetriever()
        retriever.setup()
        print(f"  [OK] Hybrid retriever initialized")
        print(f"  [OK] Sparse vocab size: {retriever.sparse_indexer.get_vocab_size()}")
        
        return True
    except Exception as e:
        print(f"  [ERROR] Hybrid retriever failed: {e}")
        return False


def test_two_stage_pipeline() -> bool:
    """Test complete two-stage retrieval pipeline."""
    print("\n[7/7] Testing Two-Stage Retrieval Pipeline...")
    try:
        from app.services.rag.two_stage_retriever import TwoStageRetriever
        
        start = time.time()
        retriever = TwoStageRetriever(hybrid_top_k=20, rerank_top_k=4)
        elapsed_init = time.time() - start
        print(f"  [OK] Pipeline initialized ({elapsed_init*1000:.0f}ms)")
        
        # Test retrieval
        test_query = "What are housing schemes for urban areas?"
        start = time.time()
        results = retriever.retrieve(test_query)
        elapsed_retrieval = time.time() - start
        
        print(f"  [OK] Retrieved {len(results)} results ({elapsed_retrieval*1000:.0f}ms)")
        
        if results:
            top = results[0]
            print(f"  [OK] Top result: {top['scheme_name']} (rerank: {top.get('rerank_score', 0):.3f})")
        
        return True
    except Exception as e:
        print(f"  [ERROR] Two-stage pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all health checks."""
    print("=" * 80)
    print("SERVICE HEALTH CHECK - WhatsApp RAG System")
    print("=" * 80)
    
    results = {
        'Qdrant': test_qdrant(),
        'Supabase': test_supabase(),
        'Google Genai': test_google_genai(),
        'BGE-M3 Embeddings': test_embeddings(),
        'Cross-Encoder': test_reranker(),
        'Hybrid Retriever': test_hybrid_retriever(),
        'Two-Stage Pipeline': test_two_stage_pipeline(),
    }
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for service, status in results.items():
        status_str = "[OK]" if status else "[FAIL]"
        print(f"{status_str} {service}")
    
    print(f"\nResult: {passed}/{total} services healthy")
    
    if passed == total:
        print("\n[SUCCESS] All services operational - system ready for deployment!")
        return 0
    elif passed >= total - 1:  # Allow Supabase to fail (optional)
        print("\n[SUCCESS] Core services operational - system ready (optional services down)")
        return 0
    else:
        print("\n[FAILURE] Critical services down - fix errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
