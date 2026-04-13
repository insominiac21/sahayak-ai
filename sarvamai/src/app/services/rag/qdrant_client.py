from qdrant_client import QdrantClient
from app.core.config import settings

# Lazy-load Qdrant client to avoid blocking app startup
_qdrant_client = None

def get_qdrant_client() -> QdrantClient:
    """
    Get or create Qdrant client singleton (lazy initialization).
    
    This defers the Qdrant connection until first use, preventing
    app startup from hanging if Qdrant is slow or misconfigured.
    """
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
    return _qdrant_client


class LazyQdrantClientProxy:
    """Proxy object that defers Qdrant connection until first method call."""
    def __getattr__(self, name):
        return getattr(get_qdrant_client(), name)


# Backward compatibility: expose as module-level attribute
qdrant_client = LazyQdrantClientProxy()

if __name__ == "__main__":
    client = get_qdrant_client()
    print(client.get_collections())
