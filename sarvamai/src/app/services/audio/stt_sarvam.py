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
    if media_url.startswith("file://"):
        file_path = media_url[len("file://"):]
        with open(file_path, "rb") as f:
            audio_bytes = f.read()
    else:
        auth = None
        if "api.twilio.com" in media_url and settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        async with httpx.AsyncClient(follow_redirects=False) as http_client:
            audio_data = await http_client.get(media_url, auth=auth, timeout=60.0)

            # Twilio media URLs can return 307 redirects to mms.twiliocdn.com.
            if audio_data.status_code in {301, 302, 303, 307, 308}:
                redirect_url = audio_data.headers.get("location")
                if redirect_url:
                    audio_data = await http_client.get(redirect_url, timeout=60.0)

            audio_data.raise_for_status()
        audio_bytes = audio_data.content

    response = client.speech_to_text.transcribe(
        file=("audio.ogg", audio_bytes, "audio/ogg"),
        model="saaras:v3",
        mode=mode,
    )
    # Sarvam SDK returns a typed response object (not a dict).
    transcript = getattr(response, "transcript", None)
    language_code = getattr(response, "language_code", None)

    # Backward-compatible fallback in case of dict-like responses.
    if transcript is None and isinstance(response, dict):
        transcript = response.get("transcript", "")
    if language_code is None and isinstance(response, dict):
        language_code = response.get("language_code", "")

    return {
        "transcript": transcript or "",
        "language_code": language_code or "",
    }
