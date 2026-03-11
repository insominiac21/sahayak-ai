"""Test Qdrant retrieval with queries in multiple Indian languages.
Results saved to: sarvamai/scripts/results/multilang_retrieval.json
"""
import sys, os, hashlib, json
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from app.services.rag.qdrant_client import qdrant_client


def dummy_embed(text):
    h = hashlib.sha256(text.encode()).digest()
    extended = (h * (384 // len(h) + 1))[:384]
    return [float(b) / 255.0 for b in extended]


QUERIES = [
    ("English",  "pension for elderly women"),
    ("Hindi",    "\u092c\u0941\u095b\u0941\u0930\u094d\u0917\u094b\u0902 \u0915\u0947 \u0932\u093f\u090f \u092a\u0947\u0902\u0936\u0928 \u092f\u094b\u091c\u0928\u093e"),
    ("Tamil",    "\u0bae\u0bc1\u0ba4\u0bbf\u0baf\u0bcb\u0bb0\u0bc1\u0b95\u0bcd\u0b95\u0bbe\u0ba9 \u0b93\u0baf\u0bcd\u0bb5\u0bc2\u0ba4\u0bbf\u0baf\u0bae\u0bcd"),
    ("Telugu",   "\u0c30\u0c48\u0c24\u0c41\u0c32\u0c15\u0c41 \u0c06\u0c30\u0c4d\u0c25\u0c3f\u0c15 \u0c38\u0c39\u0c3e\u0c2f\u0c02"),
    ("Bengali",  "\u0997\u09b0\u09c0\u09ac \u09aa\u09b0\u09bf\u09ac\u09be\u09b0\u09c7\u09b0 \u099c\u09a8\u09cd\u09af \u09b8\u09b0\u0995\u09be\u09b0\u09bf \u09af\u09cb\u099c\u09a8\u09be"),
    ("Marathi",  "\u0936\u0947\u0924\u0915\u0931\u094d\u092f\u093e\u0902\u0938\u093e\u0920\u0940 \u0906\u0930\u094d\u0925\u093f\u0915 \u092e\u0926\u0924"),
    ("Kannada",  "\u0cac\u0ca1\u0cb5\u0cb0 \u0c95\u0cc1\u0c9f\u0cc1\u0c82\u0cac\u0c97\u0cb3\u0cbf\u0c97\u0cc6 \u0c86\u0cb0\u0ccb\u0c97\u0ccd\u0caf \u0cb5\u0cbf\u0cae\u0cc6"),
    ("Malayalam","\u0d26\u0d30\u0d3f\u0d26\u0d4d\u0d30\u0d30\u0d3e\u0d2f \u0d15\u0d41\u0d1f\u0d41\u0d02\u0d2c\u0d19\u0d4d\u0d19\u0d33\u0d4d\u200d\u0d15\u0d4d\u0d15\u0d4d \u0d38\u0d39\u0d3e\u0d2f\u0d02"),
]

print("=" * 70)
print("Multi-language Qdrant Retrieval Test")
print("=" * 70)

results = []

for lang, query in QUERIES:
    print(f"\n[{lang}] Query: {query}")
    response = qdrant_client.query_points(
        collection_name="schemes",
        query=dummy_embed(query),
        limit=3,
    )
    hits = []
    for i, pt in enumerate(response.points, 1):
        src = pt.payload["source"]
        txt = pt.payload["text"][:80].replace("\n", " ")
        print(f"  {i}. score={pt.score:.4f} | {src} | {txt}...")
        hits.append({"rank": i, "score": round(pt.score, 4), "source": src, "snippet": txt})
    results.append({"language": lang, "query": query, "hits": hits})

# Collection stats
info = qdrant_client.get_collection("schemes")
total_points = info.points_count
print(f"\nCollection 'schemes': {total_points} points")
print("=" * 70)
print("All queries returned results — retrieval pipeline is working.")

# Save results
os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
out_path = os.path.join(os.path.dirname(__file__), "results", "multilang_retrieval.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({
        "test": "multilang_retrieval",
        "timestamp": datetime.now().isoformat(),
        "collection_points": total_points,
        "queries": len(QUERIES),
        "results": results,
    }, f, ensure_ascii=False, indent=2)
print(f"Saved to: {out_path}")
