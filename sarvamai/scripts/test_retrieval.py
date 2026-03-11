import sys, os, hashlib
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from app.services.rag.qdrant_client import qdrant_client

def dummy_embed(text):
    h = hashlib.sha256(text.encode()).digest()
    extended = (h * (384 // len(h) + 1))[:384]
    return [float(b) / 255.0 for b in extended]

response = qdrant_client.query_points(
    collection_name="schemes",
    query=dummy_embed("pension for elderly women"),
    limit=3,
)
for r in response.points:
    src = r.payload["source"]
    txt = r.payload["text"][:120]
    print(f"Score: {r.score:.4f} | Source: {src}")
    print(f"  {txt}...")
    print()

info = qdrant_client.get_collection("schemes")
print(f"Collection: points={info.points_count}")
