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
    from app.services.rag.retrieve import retrieve_chunks
    from app.services.agent.orchestrator import route_tools
    # Parse incoming WhatsApp message
    data = asyncio.run(request.json())
    user_number = data.get("From")
    media_url = data.get("MediaUrl")
    text = data.get("Body")
    # Step 1: If media, transcribe audio
    if media_url:
        text = asyncio.run(transcribe_audio(media_url))
    # Step 2: Orchestrator handles: detect lang → translate → retrieve → Gemini → translate back
    chunks = retrieve_chunks(text)
    result = route_tools(text, chunks, user_profile={"whatsapp": user_number})
    # result["answer"] is already in the user's original language
    # Step 3: Send answer back via WhatsApp
    # TODO: Implement Twilio send message logic
    return
