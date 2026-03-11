import sys, os
sys.path.insert(0, r'A:\internships\interview prep\puch-ai\whatsapp-RAG\sarvamai\src')
from dotenv import load_dotenv
load_dotenv(r'A:\internships\interview prep\puch-ai\whatsapp-RAG\sarvamai\.env')
from google import genai

for i in range(1, 7):
    key = os.getenv(f'GEMINI_API_KEY{i}', '').strip().strip('"')
    try:
        c = genai.Client(api_key=key)
        r = c.models.generate_content(model='gemini-2.5-flash', contents='Say OK')
        print(f'KEY{i}: ALIVE - {r.text.strip()[:20]}')
    except Exception as e:
        print(f'KEY{i}: FAILED - {str(e)[:80]}')

from qdrant_client import QdrantClient
qc = QdrantClient(url=os.getenv('QDRANT_URL'), api_key=os.getenv('QDRANT_API_KEY'))
print(f'Qdrant: ALIVE - {qc.get_collections()}')
