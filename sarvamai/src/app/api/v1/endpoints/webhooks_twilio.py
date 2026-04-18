# WhatsApp webhook endpoint

import logging
import json
from urllib.parse import parse_qs
from fastapi import APIRouter, BackgroundTasks, Request
from starlette.responses import JSONResponse
from app.services.audio.stt_sarvam import transcribe_audio
from app.services.agent.langgraph_agent import run_agent
from app.repositories.message_log import write_message_log
from app.services.channels.twilio_whatsapp import (
    SUPPORTED_AUDIO_CONTENT_TYPES,
    parse_twilio_request,
    send_whatsapp_reply,
)

router = APIRouter()
logger = logging.getLogger(__name__)

HELP_MENU = (
    "*Sahayak AI* — Government Scheme Assistant\n\n"
    "*What can I help with?*\n"
    "Ask me about 8 Indian government schemes in any language (text or voice)\n\n"
    "*Available Schemes:*\n"
    "1. PMAY-U 2.0 — Housing for poor families\n"
    "2. PMJDY — Free zero-balance bank accounts\n"
    "3. PMUY (Ujjwala) — Free LPG for women\n"
    "4. Ayushman Bharat — Health insurance (₹5 lakh/year)\n"
    "5. NSAP — Pensions for elderly/widow/disabled\n"
    "6. Sukanya Samriddhi — Girl child education savings\n"
    "7. APY — Guaranteed pension scheme\n"
    "8. Stand-Up India — Loans for SC/ST/women\n\n"
    "*Example questions:*\n"
    "- What are the requirements for PMAY-U 2.0?\n"
    "- Tell me about Ayushman Bharat eligibility\n"
    "- How to get free LPG?" 
    "- मुझे कौन सी पेंशन मिल सकती है?\n"
    "- Or send a voice note asking your question\n\n"
    "Just type or send your question to get started!"
)


def _wants_help_menu(text: str) -> bool:
    # Ensure text is a string (Twilio payload might return list)
    if isinstance(text, list):
        text = text[0] if text else ""
    elif not isinstance(text, str):
        text = str(text)
    
    normalized = (text or "").strip().lower()
    return normalized in {"", "help", "menu", "start", "hi", "hello", "1", "2"}

@router.post("/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    # Twilio typically sends application/x-www-form-urlencoded.
    # Parse raw body first so fallback paths are not affected by form-parser errors.
    content_type = (request.headers.get("content-type") or "").lower()
    raw_body = (await request.body()).decode("utf-8", errors="ignore")

    if "application/x-www-form-urlencoded" in content_type:
        parsed = parse_qs(raw_body)
        payload = {k: (v[0] if isinstance(v, list) and v else v) for k, v in parsed.items()}
    elif "application/json" in content_type:
        payload = json.loads(raw_body) if raw_body else {}
    else:
        # Keep form parser for multipart edge cases and local tooling.
        try:
            form_data = await request.form()
            payload = dict(form_data)
        except Exception:
            parsed = parse_qs(raw_body)
            payload = {k: (v[0] if isinstance(v, list) and v else v) for k, v in parsed.items()} if parsed else {}

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
    
    # Ensure text is a string (not list or bytes)
    if isinstance(text, list):
        text = text[0] if text else ""
    elif isinstance(text, bytes):
        text = text.decode("utf-8", errors="ignore")
    elif not isinstance(text, str):
        text = str(text) if text else ""
    
    inbound_text = text
    transcript = ""
    answer = ""
    media_types = ", ".join(media_content_types) if media_content_types else ""

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
                write_message_log(
                    user_number=user_number,
                    inbound_text=inbound_text,
                    query_text=text,
                    transcript=transcript,
                    answer_text=None,
                    media_count=len(media_urls),
                    media_types=media_types,
                    status="unsupported_media",
                    raw_payload=str(payload),
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
                write_message_log(
                    user_number=user_number,
                    inbound_text=inbound_text,
                    query_text=text,
                    transcript=transcript,
                    answer_text=None,
                    media_count=len(media_urls),
                    media_types=media_types,
                    status="stt_empty",
                    raw_payload=str(payload),
                )
                return

        if _wants_help_menu(text):
            if user_number:
                logger.info("Sending help menu to %s", user_number)
                send_whatsapp_reply(to=user_number, message=HELP_MENU)
            write_message_log(
                user_number=user_number,
                inbound_text=inbound_text,
                query_text=text,
                transcript=transcript,
                answer_text=HELP_MENU,
                media_count=len(media_urls),
                media_types=media_types,
                status="help_menu",
                raw_payload=str(payload),
            )
            return

        # LangGraph Agent handles: detect intent → choose tools → retrieve → generate → respond
        logger.info("Running LangGraph agent for %s", user_number)
        answer = run_agent(
            user_message=text,
            thread_id=user_number,
            user_context={"phone": user_number, "transcript": transcript if transcript else None}
        )
        
        # Send successful response
        if user_number:
            send_whatsapp_reply(to=user_number, message=answer)
        
        write_message_log(
            user_number=user_number,
            inbound_text=inbound_text,
            query_text=text,
            transcript=transcript,
            answer_text=answer,
            media_count=len(media_urls),
            media_types=media_types,
            status="success",
            raw_payload=str(payload),
        )
    
    except Exception as exc:
        logger.exception("Failed to process incoming WhatsApp message: %s", exc)
        write_message_log(
            user_number=user_number,
            inbound_text=inbound_text,
            query_text=text,
            transcript=transcript,
            answer_text=None,
            media_count=len(media_urls),
            media_types=media_types,
            status="failed",
            error_message=str(exc),
            raw_payload=str(payload),
        )
        if user_number:
            try:
                send_whatsapp_reply(
                    to=user_number,
                    message="Something went wrong while processing your request. Please try again.",
                )
            except Exception:
                logger.exception("Failed to send fallback WhatsApp reply")
