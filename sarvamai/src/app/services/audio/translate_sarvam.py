from sarvamai import SarvamAI
from app.core.config import settings

client = SarvamAI(api_subscription_key=settings.SARVAM_API_KEY)

def detect_and_translate(text: str, target_lang: str, speaker_gender: str = "Male", mode: str = "formal") -> dict:
    """
    Detect language and translate text to target_lang using Sarvam AI official template.
    Returns dict with translated_text and detected source_language_code.
    """
    response = client.text.translate(
        input=text,
        source_language_code="auto",
        target_language_code=target_lang,
        speaker_gender=speaker_gender,
        mode=mode
    )
    return {
        "translated_text": response["translated_text"],
        "source_language_code": response["source_language_code"]
    }
