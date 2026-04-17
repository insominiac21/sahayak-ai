"""
Phase 3: FastAPI Webhook Integration with LangGraph Agent
Handles Twilio WhatsApp messages with background task execution.
Uses asyncio for non-blocking 15-second timeout avoidance.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

from fastapi import APIRouter, Request, BackgroundTasks
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

# LangGraph agent
from app.services.agent.langgraph_agent import run_agent

# Existing session manager
from app.db.session_manager import get_session, save_session

load_dotenv()
logger = logging.getLogger(__name__)

# ============================================================================
# TWILIO CLIENT
# ============================================================================

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER")

if not all([TWILIO_SID, TWILIO_AUTH, TWILIO_PHONE]):
    logger.warning("⚠️ Twilio configuration incomplete. WhatsApp webhook will return 200 OK but won't send replies.")
    logger.warning("   For Render deployment: add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER to environment.")
    twilio_client = None
else:
    twilio_client = Client(TWILIO_SID, TWILIO_AUTH)
    logger.info("✅ Twilio client initialized")

# ============================================================================
# WEBHOOK HANDLER
# ============================================================================

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


def process_message_with_langgraph(
    user_message: str,
    user_phone: str,
    user_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Process message through LangGraph agent.
    This runs in a background task to avoid 15-second timeout.
    
    Args:
        user_message: WhatsApp message body
        user_phone: User's WhatsApp number
        user_context: Optional user data (income, age, state)
    
    Returns:
        Bot response text
    """
    try:
        logger.info(f"Processing message from {user_phone}: {user_message[:50]}...")
        
        # Run LangGraph agent with user's session as thread_id
        bot_response = run_agent(
            user_message=user_message,
            thread_id=user_phone,  # Each user gets their own conversation history
            user_context=user_context or {}
        )
        
        # Ensure response isn't too long for WhatsApp
        if len(bot_response) > 1024:
            bot_response = bot_response[:1021] + "..."
        
        logger.info(f"Generated response for {user_phone}: {bot_response[:50]}...")
        return bot_response
    
    except Exception as e:
        logger.error(f"Error in LangGraph processing for {user_phone}: {e}", exc_info=True)
        return "I'm sorry, I encountered an error while accessing the scheme databases. Please try again."


def send_twilio_reply(
    bot_response: str,
    user_phone: str,
    include_status: bool = False
) -> None:
    """
    Send response back to user via Twilio WhatsApp.
    
    Args:
        bot_response: Message to send
        user_phone: User's WhatsApp number
        include_status: Whether to include processing status
    """
    if not twilio_client:
        logger.error("Twilio client not initialized")
        return
    
    try:
        twilio_client.messages.create(
            body=bot_response,
            from_=TWILIO_PHONE,
            to=user_phone
        )
        logger.info(f"✅ Sent reply to {user_phone}")
    except Exception as e:
        logger.error(f"Failed to send Twilio message to {user_phone}: {e}")


@router.post("/twilio/webhook")
async def twilio_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Twilio hits this endpoint when user sends WhatsApp message.
    Returns immediately with 200 OK, processes async in background.
    
    This avoids Twilio's 15-second timeout by:
    1. Returning 200 OK immediately
    2. Running LangGraph agent in background task
    3. Sending response via separate Twilio API call
    """
    try:
        # Parse Twilio form data
        form_data = await request.form()
        user_message = form_data.get("Body", "").strip()
        user_phone = form_data.get("From", "").strip()
        
        logger.info(f"Received message from {user_phone}: {user_message[:50]}...")
        
        if not user_message or not user_phone:
            logger.warning(f"Missing Body or From in Twilio request")
            resp = MessagingResponse()
            return str(resp)
        
        # 1. IMMEDIATE ACKNOWLEDGEMENT to user (shows we got it)
        try:
            send_twilio_reply(
                "🕐 *Processing your request...*\nI'm checking the scheme databases.",
                user_phone
            )
        except Exception as e:
            logger.warning(f"Failed to send status message: {e}")
        
        # 2. FETCH USER CONTEXT from Supabase session
        try:
            user_session = get_session(user_phone)
            user_context = {
                "state": user_session.get("state"),
                "income": user_session.get("income"),
                "age": user_session.get("age"),
                "name": user_session.get("name"),
            }
        except Exception as e:
            logger.warning(f"Could not fetch user context: {e}")
            user_context = {}
        
        # 3. ADD HEAVY LIFTING TO BACKGROUND TASK
        # This allows us to return 200 OK immediately
        background_tasks.add_task(
            _process_and_send_response,
            user_message,
            user_phone,
            user_context
        )
        
        # 4. RETURN 200 OK IMMEDIATELY
        # Twilio just needs to know we received it
        resp = MessagingResponse()
        return str(resp)
    
    except Exception as e:
        logger.error(f"Error in webhook handler: {e}", exc_info=True)
        resp = MessagingResponse()
        resp.message("Sorry, I encountered an error. Please try again.")
        return str(resp)


async def _process_and_send_response(
    user_message: str,
    user_phone: str,
    user_context: Dict[str, Any]
) -> None:
    """
    Background task: Process message and send response.
    
    Args:
        user_message: WhatsApp message
        user_phone: User's WhatsApp number
        user_context: User's session data
    """
    try:
        # Run LangGraph agent
        bot_response = process_message_with_langgraph(
            user_message,
            user_phone,
            user_context
        )
        
        # Send response back via Twilio
        send_twilio_reply(bot_response, user_phone)
        
        # Optionally: Save interaction to Supabase for analytics
        try:
            save_session(user_phone, {
                "last_message": user_message[:100],
                "last_response": bot_response[:100],
                "last_updated": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.warning(f"Failed to save session: {e}")
    
    except Exception as e:
        logger.error(f"Error in background task for {user_phone}: {e}", exc_info=True)
        # Send error message to user
        try:
            send_twilio_reply(
                "❌ I encountered a critical error processing your request. Please try again.",
                user_phone
            )
        except:
            pass


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint for Render/monitoring.
    Returns 200 OK if service is running.
    """
    return {
        "status": "ok",
        "service": "sahayak-ai-phase3",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# DEBUG ENDPOINT (remove in production)
# ============================================================================

@router.post("/test-agent")
async def test_agent(
    message: str = "What is PMAY-U eligibility?",
    user_id: str = "test_user_123"
) -> Dict[str, str]:
    """
    Test endpoint to debug agent without Twilio.
    
    Example:
        POST /api/v1/webhooks/test-agent?message=What%20is%20PM-JAY&user_id=test123
    """
    try:
        response = process_message_with_langgraph(message, user_id)
        return {"message": message, "response": response}
    except Exception as e:
        return {"error": str(e)}
