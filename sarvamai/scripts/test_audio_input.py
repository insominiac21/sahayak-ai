"""Smoke test for audio input handling (Twilio-style payload + Sarvam STT call)."""
import argparse
import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from app.services.channels.twilio_whatsapp import parse_twilio_request
from app.services.audio.stt_sarvam import transcribe_audio


def _build_media_url(source: str) -> str:
    if source.startswith("http://") or source.startswith("https://"):
        return source

    abs_path = os.path.abspath(source)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Audio file not found: {abs_path}")
    return f"file://{abs_path}"


async def main(source: str):
    media_url = _build_media_url(source)
    content_type = "audio/mpeg" if source.lower().endswith(".mp3") else "audio/ogg"
    payload = {
        "From": "whatsapp:+911234567890",
        "Body": "",
        "NumMedia": "1",
        "MediaUrl0": media_url,
        "MediaContentType0": content_type,
    }

    body, media_urls, media_types = parse_twilio_request(payload)
    print(f"Parsed body: {body!r}")
    print(f"Parsed media URLs: {media_urls}")
    print(f"Parsed media types: {media_types}")

    if media_urls:
        result = await transcribe_audio(media_urls[0])
        print("STT result:", result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        default="https://raw.githubusercontent.com/anars/blank-audio/master/1-second-of-silence.mp3",
        help="Audio source URL or local file path",
    )
    args = parser.parse_args()
    asyncio.run(main(args.source))
