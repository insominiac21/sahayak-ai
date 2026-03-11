"""Basic Qdrant retrieval test — single English query.
Results saved to: sarvamai/scripts/results/retrieval_basic.json
"""
import sys, os, hashlib, json
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from app.services.rag.qdrant_client import qdrant_client

def dummy_embed(text):
    h = hashlib.sha256(text.encode()).digest()
    extended = (h * (384 // len(h) + 1))[:384]
    return [float(b) / 255.0 for b in extended]

query = "pension for elderly women"
response = qdrant_client.query_points(
    collection_name="schemes",
    query=dummy_embed(query),
    limit=3,
)
hits = []
for r in response.points:
    src = r.payload["source"]
    txt = r.payload["text"][:120]
    print(f"Score: {r.score:.4f} | Source: {src}")
    print(f"  {txt}...")
    print()
    hits.append({"score": round(r.score, 4), "source": src, "snippet": txt})

info = qdrant_client.get_collection("schemes")
print(f"Collection: points={info.points_count}")

os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
out_path = os.path.join(os.path.dirname(__file__), "results", "retrieval_basic.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({
        "test": "retrieval_basic",
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "collection_points": info.points_count,
        "hits": hits,
    }, f, ensure_ascii=False, indent=2)
print(f"Saved to: {out_path}")
