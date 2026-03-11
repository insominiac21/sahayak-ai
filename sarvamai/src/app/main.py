# Sarvam AI main entrypoint
from fastapi import FastAPI
from app.api.v1.endpoints.webhooks_twilio import router as whatsapp_router

app = FastAPI(title="Sarvam AI", version="1.0.0")
app.include_router(whatsapp_router, prefix="/api/v1/webhooks/twilio", tags=["whatsapp"])
