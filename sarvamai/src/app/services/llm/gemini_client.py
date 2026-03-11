"""
Round-robin Gemini client with auto-skip on exhaustion/failure.
Uses official google-genai SDK. Reads GEMINI_API_KEY1..GEMINI_API_KEY7 from env.
"""
import os
import threading
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_current_index = 0


def _load_keys() -> list[str]:
    """Load all GEMINI_API_KEYn from environment, filter empty."""
    keys = []
    for i in range(1, 7):
        key = os.getenv(f"GEMINI_API_KEY{i}", "").strip().strip('"')
        if key:
            keys.append(key)
    return keys


_keys = _load_keys()
_clients = [genai.Client(api_key=k) for k in _keys]


def get_gemini_client() -> genai.Client:
    """Return the next available Gemini client (round-robin)."""
    global _current_index
    with _lock:
        idx = _current_index % len(_clients)
        _current_index += 1
    return _clients[idx]


def generate_with_fallback(
    contents,
    config: types.GenerateContentConfig | None = None,
    model: str = "gemini-2.5-flash",
) -> object:
    """
    Call Gemini generate_content with round-robin key rotation.
    On 429 (RESOURCE_EXHAUSTED) or 400 (INVALID/EXPIRED), skip to next key.
    Tries all keys before raising.
    """
    global _current_index
    tried = 0
    last_error = None

    while tried < len(_clients):
        with _lock:
            idx = _current_index % len(_clients)
            _current_index += 1

        client = _clients[idx]
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            return response
        except Exception as e:
            last_error = e
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                logger.warning(f"Key {idx+1} exhausted, rotating...")
            elif "400" in error_str or "INVALID" in error_str or "expired" in error_str:
                logger.warning(f"Key {idx+1} invalid/expired, skipping...")
            else:
                logger.error(f"Key {idx+1} unexpected error: {error_str[:100]}")
                raise
            tried += 1

    raise RuntimeError(f"All {len(_clients)} Gemini keys exhausted. Last error: {last_error}")
