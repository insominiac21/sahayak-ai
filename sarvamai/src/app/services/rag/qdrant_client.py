from qdrant_client import QdrantClient
from app.core.config import settings

qdrant_client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY,
)

if __name__ == "__main__":
    print(qdrant_client.get_collections())
