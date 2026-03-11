# Sarvam AI v1 Build Checklist

## 1. Directory & Data Setup
- [ ] Create `data/seed_docs/` and add 8 Markdown files (one per scheme)
- [ ] Ensure all core directories exist: `src/app/`, `services/`, `api/`, `core/`, `db/`, `models/`, `schemas/`, `repositories/`, `middleware/`, `utils/`, `tests/`, `scripts/`, `docker/`

## 2. Environment Variables
- [ ] Add to `.env`:
    - `OPENAI_API_KEY` (or Groq)
    - `QDRANT_API_KEY` (or Upstash)
    - `POSTGRES_URL`
    - `TWILIO_ACCOUNT_SID`
    - `TWILIO_AUTH_TOKEN`
    - `SARVAM_API_KEY`
    - `WHATSAPP_WEBHOOK_SECRET`

## 3. Key Modules & Files
- [ ] WhatsApp webhook: `src/app/api/v1/endpoints/webhooks_twilio.py`
- [ ] STT (voice notes): `src/app/services/audio/stt_sarvam.py`
- [ ] RAG retrieval: `src/app/services/rag/retrieve.py`
- [ ] Tool orchestrator: `src/app/services/agent/orchestrator.py`
- [ ] Eligibility tool: `src/app/services/agent/eligibility_tool.py`
- [ ] Checklist tool: `src/app/services/agent/checklist_tool.py`
- [ ] Ingestion script: `scripts/ingest.py`
- [ ] Eval script: `scripts/eval.py`

## 4. Minimal Code Structure
- [ ] FastAPI app entrypoint: `main.py`
- [ ] Config loader: `src/app/core/config.py`
- [ ] Postgres models/schemas/repositories: `src/app/models/`, `src/app/schemas/`, `src/app/repositories/`
- [ ] Utils: `src/app/utils/`
- [ ] Tests: `src/app/tests/`

## 5. Essential Commands
- [ ] Run server: `uvicorn sarvamai.src.app.main:app --reload`
- [ ] Ingest docs: `python sarvamai/scripts/ingest.py`
- [ ] Run eval: `python sarvamai/scripts/eval.py`

---

Check off each item as you build. Request code templates for any module/file as needed.