from sarvamai import SarvamAI
from app.core.config import settings

client = SarvamAI(api_subscription_key=settings.SARVAM_API_KEY)

SARVAM_LANG_CODES = {
    "bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN", "ml-IN", "mr-IN",
    "od-IN", "pa-IN", "ta-IN", "te-IN",
}
# Note: Sarvam API accepts 22 codes in validation (as-IN, brx-IN, doi-IN,
# kok-IN, ks-IN, mai-IN, mni-IN, ne-IN, sa-IN, sat-IN, sd-IN, ur-IN)
# but returns 400 for translation on those — only the 11 above actually work.

def detect_and_translate(text: str, target_lang: str, speaker_gender: str = "Male", mode: str = "formal") -> dict:
    """
    Detect language and translate text to target_lang using Sarvam AI.
    target_lang must use Sarvam format: 'hi-IN', 'en-IN', 'ta-IN', etc.
    Returns dict with translated_text and detected source_language_code.
    """
    if target_lang not in SARVAM_LANG_CODES:
        raise ValueError(f"Invalid target_lang '{target_lang}'. Must be one of: {sorted(SARVAM_LANG_CODES)}")
    response = client.text.translate(
        input=text,
        source_language_code="auto",
        target_language_code=target_lang,
        speaker_gender=speaker_gender,
        mode=mode
    )
    return {
        "translated_text": response.translated_text,
        "source_language_code": response.source_language_code
    }
