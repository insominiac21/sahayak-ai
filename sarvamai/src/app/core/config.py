import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from sarvamai root (two levels up from core/)
env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=env_path)

# LLM and service API keys from .env
GEMINI_API_KEYS = [os.getenv(f"GEMINI_API_KEY{i}", "") for i in range(1, 8)]
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
# Supabase Postgres connection string
POSTGRES_URL = os.getenv("POSTGRES_URL")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
WHATSAPP_WEBHOOK_SECRET = os.getenv("WHATSAPP_WEBHOOK_SECRET")
# Sarvam AI config
from pydantic_settings import BaseSettings



# Settings for dependency injection (if needed)
class Settings(BaseSettings):
    # Twilio WhatsApp Integration
    TWILIO_AUTH_TOKEN: str
    TWILIO_ACCOUNT_SID: str
    TWILIO_WHATSAPP_NUMBER: str
    
    # LLM & Vector Search APIs
    HF_TOKEN: str | None = None  # HuggingFace Inference API (embeddings)
    GOOGLE_API_KEY: str | None = None  # Google Gemini API (legacy, single key)
    SARVAM_API_KEY: str | None = None  # Sarvam AI (STT, translation)
    SERPER_API_KEY: str | None = None  # Google Serper API for web search (fallback)
    
    # Gemini API Keys (round-robin with 4 keys - keys 4 & 6 removed due to suspended access)
    GEMINI_API_KEY1: str  # Required for round-robin agent
    GEMINI_API_KEY2: str  # Required for round-robin agent
    GEMINI_API_KEY3: str  # Required for round-robin agent
    GEMINI_API_KEY5: str  # Required for round-robin agent
    
    # Database Configuration
    POSTGRES_URL: str | None = None  # Legacy Supabase Postgres
    SUPABASE_POSTGRES_URI: str | None = None  # Supabase connection string (for checkpointer)
    
    # Vector Database (Qdrant)
    QDRANT_URL: str
    QDRANT_API_KEY: str
    
    # RAG Configuration
    RAG_CHUNK_SIZE: int = 512
    RAG_EMBED_MODEL: str = "BAAI/bge-m3"  # HuggingFace model for embeddings
    RAG_RETRIEVAL_TOP_K: int = 5
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Webhooks
    WHATSAPP_WEBHOOK_SECRET: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
