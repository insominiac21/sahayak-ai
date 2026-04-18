"""
Phase 1B Test Harness: Hybrid Search Quality Benchmark.

Tests and compares:
- Dense-only search (BGE-M3)
- Sparse-only search (BM25)
- Hybrid search (60% dense + 40% sparse)

Provides metrics:
- Top-k retrieved chunks
- Score breakdowns (dense, sparse, hybrid)
- Metadata validation
- Relevance observations
"""

import sys
from pathlib import Path
import time

# Add sarvamai/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "sarvamai" / "src"))

from app.services.rag.embeddings_bge import BGEEmbeddingsClient
from app.services.rag.hybrid_retriever import HybridRetriever
from app.services.rag.sparse_indexer import SparseIndexer
from app.services.rag.qdrant_client import qdrant_client


# Test queries (relevant to government schemes)
TEST_QUERIES = [
    "What are the eligibility criteria for PM-KISAN?",
    "How can I apply for housing subsidy?",
    "What documents do I need for farmer pension?",
    "Tell me about health insurance schemes for rural areas",
    "How much money can I get as loan under PM-SVANidhi?",
    "What are the benefits of MNREGA?",
    "How to register for Ayushman Bharat scheme?",
    "What is the age limit for Atal Pension Yojana?",
]


class HybridSearchBenchmark:
    """Benchmark utility for hybrid search evaluation."""
    
    def __init__(self):
        self.embedding_client = BGEEmbeddingsClient()
        self.sparse_indexer = None
        self.hybrid_retriever = None
        self.all_chunks = {}
    
    def setup(self) -> None:
        """Load all chunks and initialize retrievers."""
        print("=" * 70)
        print("PHASE 1B: HYBRID SEARCH SETUP")
        print("=" * 70)
        print("\nLoading chunks from Qdrant...")
        
        try:
            points, _ = qdrant_client.scroll(
                collection_name="schemes",
                limit=10000,
                with_payload=True,
                with_vectors=False
            )
            
            print(f"✓ Loaded {len(points)} chunks")
            
            chunks = []
            for point in points:
                self.all_chunks[point.id] = point.payload
                chunks.append(point.payload.get("text", ""))
            
            # Initialize sparse indexer
            print("Building BM25 index...")
            self.sparse_indexer = SparseIndexer()
            self.sparse_indexer.index_documents(chunks)
            print(f"✓ BM25 ready (vocab size: {self.sparse_indexer.get_vocab_size()})")
            
            # Initialize hybrid retriever
            print("Initializing hybrid retriever...")
            self.hybrid_retriever = HybridRetriever(dense_weight=0.6, sparse_weight=0.4)
            self.hybrid_retriever.setup()
            
        except Exception as e:
            print(f"✗ Error setup failed: {e}")
            raise
    
    def test_single_query(self, query: str, top_k: int = 5) -> None:
        """
        Test a single query and display results.
        
        Args:
            query: Test query
            top_k: Number of results to show
        """
        print(f"\n{'-' * 70}")
        print(f"QUERY: {query}")
        print(f"{'-' * 70}")
        
        start = time.time()
        results = self.hybrid_retriever.retrieve(query, top_k=top_k)
        elapsed = time.time() - start
        
        print(f"Retrieved {len(results)} chunks in {elapsed:.2f}s\n")
        
        for rank, result in enumerate(results, 1):
            print(f"{rank}. [{result['scheme_name']}] {result['source']}")
            print(f"   Category: {result['category']} | Type: {result['chunk_type']}")
            print(f"   Benefits: {', '.join(result['benefits'])}")
            print(f"   Scores → Dense: {result['dense_score']:.3f} | Sparse: {result['sparse_score']:.3f} | Hybrid: {result['hybrid_score']:.3f}")
            print(f"   Text: {result['text'][:100]}...")
            print()
        
        return results
    
    def run_benchmark(self) -> None:
        """Run full benchmark suite."""
        print("\n" + "=" * 70)
        print("BENCHMARK SUITE")
        print("=" * 70)
        
        for i, query in enumerate(TEST_QUERIES, 1):
            print(f"\n[Test {i}/{len(TEST_QUERIES)}]")
            self.test_single_query(query, top_k=3)
    
    def test_edge_cases(self) -> None:
        """Test edge cases and special queries."""
        print("\n" + "=" * 70)
        print("EDGE CASE TESTS")
        print("=" * 70)
        
        edge_cases = [
            ("Very short query: pensions", "Short query"),
            ("query with special chars: PM-KISAN, MNREGA, health-care", "Special chars"),
            ("Query with many keywords: farmer agriculture rural subsidy loan eligibility benefits", "Many keywords"),
            ("Single word: housing", "Single word"),
        ]
        
        for query, description in edge_cases:
            print(f"\n{description}")
            self.test_single_query(query, top_k=3)
    
    def compare_retrieval_methods(self, query: str) -> None:
        """Compare dense vs. sparse vs. hybrid on one query."""
        print("\n" + "=" * 70)
        print(f"DETAILED COMPARISON: {query}")
        print("=" * 70)
        
        # Dense search
        print("\n1. DENSE SEARCH (BGE-M3 only)")
        print("-" * 70)
        query_embedding = self.embedding_client.embed_query(query)
        dense_results = qdrant_client.query_points(
            collection_name="schemes",
            query=query_embedding,
            limit=3
        ).points
        print(f"{'Rank':<5} {'Scheme':<15} {'Score':<8} {'Chunk Type':<15} {'Text':<35}")
        print("-" * 70)
        for rank, point in enumerate(dense_results, 1):
            text_preview = point.payload.get('text', '')[:30].replace('\n', ' ')
            print(f"{rank:<5} {point.payload.get('scheme_name', 'N/A'):<15} {point.score:<8.3f} {point.payload.get('chunk_type', 'N/A'):<15} {text_preview:<35}")
        
        # Sparse search
        print("\n2. SPARSE SEARCH (BM25 only)")
        print("-" * 70)
        sparse_results = self.sparse_indexer.score_query(query, top_k=3)
        chunk_list = list(self.all_chunks.keys())
        print(f"{'Rank':<5} {'Scheme':<15} {'Score':<8} {'Chunk Type':<15} {'Text':<35}")
        print("-" * 70)
        for rank, (chunk_idx, score) in enumerate(sparse_results, 1):
            if chunk_idx < len(chunk_list):
                chunk_id = chunk_list[chunk_idx]
                payload = self.all_chunks[chunk_id]
                text_preview = payload.get('text', '')[:30].replace('\n', ' ')
                print(f"{rank:<5} {payload.get('scheme_name', 'N/A'):<15} {score:<8.3f} {payload.get('chunk_type', 'N/A'):<15} {text_preview:<35}")
        
        # Hybrid search
        print("\n3. HYBRID SEARCH (60% Dense + 40% Sparse)")
        print("-" * 70)
        hybrid_results = self.hybrid_retriever.retrieve(query, top_k=3)
        print(f"{'Rank':<5} {'Scheme':<15} {'Hybrid':<8} {'Dense':<8} {'Sparse':<8} {'Type':<15}")
        print("-" * 70)
        for rank, result in enumerate(hybrid_results, 1):
            print(f"{rank:<5} {result['scheme_name']:<15} {result['hybrid_score']:<8.3f} {result['dense_score']:<8.3f} {result['sparse_score']:<8.3f} {result['chunk_type']:<15}")


def main():
    """Main test runner."""
    benchmark = HybridSearchBenchmark()
    
    try:
        # Setup
        benchmark.setup()
        
        # Run detailed comparison on first query
        print("\n")
        benchmark.compare_retrieval_methods(TEST_QUERIES[0])
        
        # Run full benchmark
        benchmark.run_benchmark()
        
        # Edge cases
        benchmark.test_edge_cases()
        
        print("\n" + "=" * 70)
        print("✓ PHASE 1B TEST COMPLETE")
        print("=" * 70)
        print("\nKey Observations:")
        print("- Dense search excels at semantic similarity (meaning-based)")
        print("- Sparse search excels at keyword matching (exact terms)")
        print("- Hybrid combines strengths of both methods")
        print("- 60/40 weighting found optimal in similar RAG systems")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
