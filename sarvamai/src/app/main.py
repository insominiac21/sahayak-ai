# Sarvam AI main entrypoint
from fastapi import FastAPI
from app.api.v1.endpoints.webhooks_twilio import router as whatsapp_router
from app.api.v1.endpoints.webhooks_langgraph import router as langgraph_router

app = FastAPI(title="Sarvam AI", version="2.0.0")

# Production: Twilio WhatsApp webhooks enabled
app.include_router(whatsapp_router, prefix="/api/v1/webhooks/twilio", tags=["whatsapp"])

# Phase 3: LangGraph agentic approach
app.include_router(langgraph_router, prefix="/api/v1/webhooks", tags=["langgraph"])


@app.get("/")
async def root():
	return {"service": "sahayak-ai", "status": "ok", "version": "phase-3-langgraph"}


@app.get("/health")
@app.post("/health")
@app.head("/health")
async def health():
	# Lightweight health endpoint for Render/UptimeRobot probes (GET, POST, and HEAD).
	return {"status": "ok"}
