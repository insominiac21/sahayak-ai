# Sarvam STT integration for voice notes (official SDK template)
import httpx
from sarvamai import SarvamAI
from app.core.config import settings

client = SarvamAI(api_subscription_key=settings.SARVAM_API_KEY)

async def transcribe_audio(media_url: str, mode: str = "transcribe") -> dict:
    """
    Download audio from media_url and transcribe using Sarvam Saaras v3.
    mode: 'transcribe' | 'translate' | 'verbatim' | 'translit' | 'codemix'
    Returns dict with transcript and detected language.
    """
    async with httpx.AsyncClient() as http_client:
        audio_data = await http_client.get(media_url)
    response = client.speech_to_text.transcribe(
        file=audio_data.content,
        model="saaras:v3",
        mode=mode,
    )
    return {
        "transcript": response.get("transcript", ""),
        "language_code": response.get("language_code", ""),
    }
