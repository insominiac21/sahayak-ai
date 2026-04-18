import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
from app.services.rag.retrieve import retrieve_chunks

queries = [
    ("Pension", "How can an elderly person apply for old age pension?"),
    ("Housing", "I want to get a house under government housing scheme"),
    ("SC/ST Loan", "I am a SC/ST woman and want to start a business, what loan can I get?"),
    ("LPG", "How to get free LPG gas connection for poor family?"),
    ("Health", "What is the government health insurance scheme for poor people?"),
]

for label, query in queries:
    print(f"\n=== {label} ===")
    results = retrieve_chunks(query, top_k=3)
    for r in results:
        score = r["score"]
        source = r["source"]
        text = r["text"][:100].replace("\n", " ")
        print(f"  [{score:.4f}] {source}: {text}...")
