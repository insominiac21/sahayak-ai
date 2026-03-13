# WhatsApp webhook endpoint

import logging
from fastapi import APIRouter, BackgroundTasks, Request
from starlette.responses import JSONResponse
from app.services.audio.stt_sarvam import transcribe_audio
from app.services.rag.retrieve import retrieve_chunks
from app.services.agent.orchestrator import route_tools
from app.services.channels.twilio_whatsapp import (
    SUPPORTED_AUDIO_CONTENT_TYPES,
    parse_twilio_request,
    send_whatsapp_reply,
)

router = APIRouter()
logger = logging.getLogger(__name__)

HELP_MENU = (
    "*Sahayak AI* — Government Scheme Assistant\n\n"
    "*How to use*\n"
    "1. Type your question in any Indian language.\n"
    "2. Send a voice note — it will be transcribed automatically.\n\n"
    "*Example questions*\n"
    "- Am I eligible for PMAY housing scheme?\n"
    "- What documents are needed for PM Vishwakarma?\n"
    "- PM Kisan yojana ke liye kya chahiye?\n\n"
    "Reply with any question to get started."
)


def _wants_help_menu(text: str) -> bool:
    normalized = (text or "").strip().lower()
    return normalized in {"", "help", "menu", "start", "hi", "hello", "1", "2"}

@router.post("/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    # Twilio posts form-encoded fields; keep JSON fallback for local tests.
    try:
        form_data = await request.form()
        payload = dict(form_data)
    except Exception:
        payload = await request.json()

    logger.info(
        "Incoming Twilio webhook: from=%s body_len=%s num_media=%s",
        payload.get("From"),
        len((payload.get("Body") or "").strip()),
        payload.get("NumMedia", 0),
    )

    # Immediately return 200 OK and process async.
    background_tasks.add_task(process_message, payload)
    return JSONResponse({"status": "ack"})

async def process_message(payload: dict):
    user_number = payload.get("From")
    text, media_urls, media_content_types = parse_twilio_request(payload)

    logger.info(
        "Processing WhatsApp message: from=%s text_present=%s media_count=%s",
        user_number,
        bool(text),
        len(media_urls),
    )

    try:
        # If the user sent voice note/audio, transcribe first.
        if media_urls:
            first_media_type = media_content_types[0] if media_content_types else ""
            # Strip codec parameters e.g. "audio/ogg; codecs=opus" → "audio/ogg"
            base_media_type = first_media_type.split(";")[0].strip()
            logger.info("Detected inbound media: from=%s content_type=%s base=%s", user_number, first_media_type, base_media_type)
            if base_media_type and base_media_type not in SUPPORTED_AUDIO_CONTENT_TYPES:
                if user_number:
                    logger.info("Rejecting unsupported media type for %s: %s", user_number, base_media_type)
                    send_whatsapp_reply(
                        to=user_number,
                        message=(
                            "Unsupported audio format. Please send OGG/Opus, MP3, WAV, AAC, M4A, or AMR audio."
                        ),
                    )
                return

            stt_result = await transcribe_audio(media_urls[0])
            transcript = (stt_result.get("transcript") or "").strip()
            if transcript:
                text = transcript
                logger.info("STT transcript ready: from=%s chars=%s lang=%s", user_number, len(text), stt_result.get("language_code"))
            else:
                logger.warning("STT returned empty transcript for %s", user_number)
                if user_number:
                    send_whatsapp_reply(to=user_number, message="Sorry, I could not transcribe your voice note. Please try again or send a text message.")
                return

        if _wants_help_menu(text):
            if user_number:
                logger.info("Sending help menu to %s", user_number)
                send_whatsapp_reply(to=user_number, message=HELP_MENU)
            return

        # Orchestrator handles: detect lang → translate → retrieve → Gemini → translate back.
        logger.info("Running retrieval/orchestration for %s", user_number)
        chunks = retrieve_chunks(text)
        result = route_tools(text, chunks, user_profile={"whatsapp": user_number})
        answer = result.get("answer") if isinstance(result, dict) else str(result)

        if user_number and answer:
            logger.info("Sending generated reply to %s", user_number)
            send_whatsapp_reply(to=user_number, message=answer)
    except Exception as exc:
        logger.exception("Failed to process incoming WhatsApp message: %s", exc)
        if user_number:
            try:
                send_whatsapp_reply(
                    to=user_number,
                    message="Something went wrong while processing your request. Please try again.",
                )
            except Exception:
                logger.exception("Failed to send fallback WhatsApp reply")
