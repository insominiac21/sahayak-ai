# WhatsApp webhook endpoint

from fastapi import APIRouter, BackgroundTasks, Request
from starlette.responses import JSONResponse
from app.services.audio.stt_sarvam import transcribe_audio
from app.services.rag.retrieve import retrieve_chunks
from app.services.agent.orchestrator import route_tools

router = APIRouter()

@router.post("/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    # Immediately return 200 OK
    background_tasks.add_task(process_message, request)
    return JSONResponse({"status": "ack"})

def process_message(request: Request):
    import asyncio
    from app.services.audio.stt_sarvam import transcribe_audio
    from app.services.audio.translate_sarvam import detect_and_translate
    from app.services.rag.retrieve import retrieve_chunks
    from app.services.agent.orchestrator import route_tools
    from app.core.config import settings
    # Parse incoming WhatsApp message
    data = asyncio.run(request.json())
    user_number = data.get("From")
    media_url = data.get("MediaUrl")
    text = data.get("Body")
    # Step 1: If media, transcribe audio
    if media_url:
        text = asyncio.run(transcribe_audio(media_url))
    # Step 2: Detect language and translate to English
    detected = detect_and_translate(text, target_lang="en-IN")
    english_query = detected["translated_text"]
    user_lang = detected["source_language_code"]
    # Step 3: Retrieve chunks for RAG
    chunks = retrieve_chunks(english_query, language="en-IN")
    # Step 4: Route to tools (Gemini function calling)
    result = route_tools(english_query, chunks, user_profile={"whatsapp": user_number})
    # Step 5: Send answer back via WhatsApp (implementation omitted)
    # answer = result["answer"]
    # citations = result["citations"]
    # user_lang = result["user_lang"]
    # TODO: Implement Twilio send message logic
    return
