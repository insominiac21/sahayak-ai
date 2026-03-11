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
    TWILIO_AUTH_TOKEN: str
    TWILIO_ACCOUNT_SID: str
    TWILIO_WHATSAPP_NUMBER: str
    SARVAM_API_KEY: str
    POSTGRES_URL: str  # Supabase Postgres
    QDRANT_URL: str
    QDRANT_API_KEY: str
    GEMINI_API_KEY1: str = None
    GEMINI_API_KEY2: str = None
    GEMINI_API_KEY3: str = None
    GEMINI_API_KEY4: str = None
    GEMINI_API_KEY5: str = None
    GEMINI_API_KEY6: str = None
    RAG_CHUNK_SIZE: int = 512
    RAG_EMBED_MODEL: str = "sarvam-embed-v1"
    RAG_RETRIEVAL_TOP_K: int = 5
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
