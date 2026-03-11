# API v1 router
from fastapi import APIRouter
from .endpoints import webhooks_twilio, chat, admin_ingestion, health

api_router = APIRouter()
api_router.include_router(webhooks_twilio.router, prefix="/webhooks/twilio", tags=["whatsapp"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(admin_ingestion.router, prefix="/admin/ingestion", tags=["admin"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
