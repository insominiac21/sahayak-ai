# Sahayak AI

A WhatsApp-first, multilingual **agentic AI assistant** that helps Indian citizens understand and apply
for government welfare schemes. Users send text or voice messages in any Indian language;
the system uses multi-step reasoning with a **LangGraph agent** to search knowledge bases and the web,
reply with accurate scheme-grounded answers in the same language.

---

## What it does

- Accepts WhatsApp messages (text or voice note) via Twilio
- Transcribes voice notes using Sarvam AI (Saaras v3 STT)
- Detects and translates the query to English (Sarvam Mayura)
- **Phase 3 Agent**: Uses 4-tool LangGraph agent for intelligent multi-step reasoning:
  - **search_schemes**: Retrieves relevant scheme excerpts from Qdrant vector DB
  - **web_search**: Searches Google (Serper API) for current/real-time info when KB doesn't have answer
  - **check_eligibility**: Calculates income-based scheme eligibility (PMAY-U, PM-JAY, PMJDY rules)
  - **fetch_user_profile**: Retrieves user context from session history (name, state, income)
- Agent decides which tools to use, what order, and when to stop
- Generates grounded answer with Google Gemini 2.5 Flash (round-robin across 6 API keys)
- Translates the answer back to the user's language and replies via WhatsApp

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Channel | Twilio WhatsApp | WhatsApp API requires a business partnership; Twilio provides sandbox access with no approval needed for development |
| Web framework | FastAPI + uvicorn | Async request handling; `BackgroundTasks` lets the webhook ACK immediately while the heavy pipeline (STT + LLM) runs asynchronously |
| Agent Framework | LangGraph 1.1.8 | StateGraph for multi-step agentic reasoning; automatic tool binding and message routing |
| STT | Sarvam Saaras v3 | Purpose-built for Indian languages and accents; outperforms Whisper on code-mixed Hindi/English voice notes |
| Translation | Sarvam Mayura | Auto-detects source language; covers 10+ scheduled Indian languages in one API call |
| Vector DB | Qdrant Cloud | Dedicated vector store with ANN indexing; supports 1024-dim HuggingFace embeddings; generous free tier |
| LLM | Gemini 2.5 Flash | 1M token context window; round-robin across 6 API keys avoids rate limits and auto-distributes load |
| Embeddings | BAAI/bge-m3 | 1024-dim; via HuggingFace Inference API with exponential backoff retry logic (503/504 handling) |
| Web Search | Google Serper | Real-time web search when knowledge base doesn't have current/time-sensitive info |
| Session Store | Supabase Postgres / Memory | User profile caching (name, state, income) for personalized follow-ups |
| Tunnel (dev) | Cloudflare Tunnel | Exposes localhost:8000 to the internet via a free HTTPS URL; no port-forwarding or VPS required |

---

## Repository File Index

Below is the practical file map for Phase 3 (excluding local runtime artifacts like `__pycache__`, `.pyc`, and test data).

```
sarvamai/
├── .env                                   # Environment variables (secrets, DO NOT COMMIT)
├── .env-example                           # Template for all env vars (safe to commit)
├── README.md                              # This file (project overview)
├── ARCHITECTURE.md                        # Phase 3 LangGraph architecture (detailed)
├── pyproject.toml                         # Python package config (at repo root)
├── requirements.txt                       # All 41 pinned dependencies (at repo root)
│
├── scripts/                               # Utility scripts (mostly deprecated, kept for reference)
│   ├── ingest.py                          # Ingest scheme docs into Qdrant (run once)
│   ├── eval.py                            # Evaluation utilities
│   ├── test_data/                         # Sample audio files
│   └── results/                           # Test output JSONs
│
└── src/
    └── app/
        ├── __init__.py
        ├── main.py                        # FastAPI app entry point; includes both Phase 2 & 3 routers
        │
        ├── api/
        │   └── v1/
        │       ├── router.py              # API router registry
        │       └── endpoints/
        │           ├── webhooks_langgraph.py    # ✨ Phase 3: LangGraph agent webhook
        │           └── webhooks_twilio.py       # Phase 2: Legacy Twilio webhook (deprecated)
        │
        ├── core/
        │   └── config.py                  # Pydantic Settings: env vars (GEMINI_KEY1-6, HF_TOKEN, SERPER_API_KEY, etc)
        │
        ├── db/
        │   ├── __init__.py
        │   ├── base.py                    # SQLAlchemy declarative base
        │   ├── session.py                 # Database session factory
        │   └── session_manager.py         # ✨ NEW: User session store (get/save/clear)
        │
        ├── models/                        # SQLAlchemy ORM models (if using Postgres)
        │   ├── __init__.py
        │   └── user.py
        │
        ├── repositories/                  # Data access layer
        │   ├── __init__.py
        │   └── user.py
        │
        ├── schemas/                       # Pydantic request/response schemas
        │   └── __init__.py
        │
        ├── services/
        │   ├── __init__.py
        │   │
        │   ├── agent/                     # ✨ Phase 3: LangGraph Agent
        │   │   ├── __init__.py
        │   │   └── langgraph_agent.py     # StateGraph with 4 tools:
        │   │                              #   - search_schemes (Qdrant KB)
        │   │                              #   - web_search (Serper API)
        │   │                              #   - check_eligibility (income rules)
        │   │                              #   - fetch_user_profile (session)
        │   │                              # Round-robin Gemini key rotation
        │   │                              # MemorySaver checkpointer
        │   │
        │   ├── audio/                     # STT & Translation
        │   │   ├── __init__.py
        │   │   ├── stt_sarvam.py          # Sarvam Saaras v3 (speech-to-text)
        │   │   └── translate_sarvam.py    # Sarvam Mayura (language translation)
        │   │
        │   ├── channels/                  # Integration adapters
        │   │   ├── __init__.py
        │   │   └── twilio_whatsapp.py     # Twilio client wrapper
        │   │
        │   ├── llm/                       # LLM clients
        │   │   ├── __init__.py
        │   │   └── gemini_client.py       # Google Gemini with 403 error handling & key rotation
        │   │
        │   ├── rag/                       # Retrieval-Augmented Generation
        │   │   ├── __init__.py
        │   │   ├── embeddings_bge.py      # HuggingFace BAAI/bge-m3 with @retry decorator
        │   │   ├── ingest.py              # Semantic chunking + vector upload
        │   │   ├── retrieve.py            # Hybrid search (semantic + BM25)
        │   │   └── qdrant_client.py       # Qdrant client singleton
        │   │
        │   └── chat/                      # Phase 2 (legacy)
        │       ├── __init__.py
        │       ├── session_manager.py     # Phase 2 session manager (for reference)
        │       └── orchestrator.py        # Phase 2 9-step orchestrator
        │
        └── utils/
            └── logging.py                 # Structured logging config
```

### Key Files by Purpose

| Purpose | Files |
|---------|-------|
| **Agent Brain** | `services/agent/langgraph_agent.py` |
| **Webhook Handler (Phase 3)** | `api/v1/endpoints/webhooks_langgraph.py` |
| **Configuration** | `core/config.py` (41 env vars) |
| **User Sessions** | `db/session_manager.py` (memory + Supabase) |
| **Vector Search** | `services/rag/retrieve.py` (hybrid BM25+semantic) |
| **Embeddings** | `services/rag/embeddings_bge.py` (HF API + retry logic) |
| **Speech-to-Text** | `services/audio/stt_sarvam.py` |
| **Translation** | `services/audio/translate_sarvam.py` |
| **Ingest Pipeline** | `scripts/ingest.py` (run once to populate Qdrant) |
| **Environment Template** | `.env-example` (copy to `.env`) |

At repository root (outside `sarvamai/`), deployment files are also used:

```
render.yaml
pyproject.toml
requirements.txt
README.md
```

---

## Audio Subsystem

Audio support is first-class in this project, not an add-on.

### Audio Input Flow

1. Twilio sends `MediaUrl0` and `MediaContentType0` in webhook payload.
2. `webhooks_twilio.py` normalizes content type (for example, `audio/ogg; codecs=opus` -> `audio/ogg`).
3. `stt_sarvam.py` downloads media with Twilio auth and follows redirect to `mms.twiliocdn.com`.
4. Audio bytes are sent to Sarvam STT using tuple format:
     `("audio.ogg", audio_bytes, "audio/ogg")`.
5. Transcript is then routed through retrieval + Gemini + translation.
6. Final answer is sent back on WhatsApp.

### Supported Audio Types

- `audio/ogg`
- `audio/opus`
- `audio/mpeg`
- `audio/mp3`
- `audio/wav`
- `audio/x-wav`
- `audio/wave`
- `audio/aac`
- `audio/mp4`
- `audio/x-m4a`
- `audio/amr`
- `application/ogg`

### Audio Tests and Artifacts

- Test scripts:
    - `scripts/test_audio_input.py`
    - `scripts/test_audio_to_answer.py`
- Sample WhatsApp voice notes:
    - `scripts/test_data/audio/*.ogg`
- Saved outputs:
    - `scripts/results/audio_to_answer.json`

---

## Setup

### Quick Prerequisites Checklist

Before starting, collect these API keys:

- ✅ **Sarvam AI API key** — [sarvam.ai](https://www.sarvam.ai)
- ✅ **Google Gemini API key (1–6 keys)** — [aistudio.google.com](https://aistudio.google.com)
- ✅ **Qdrant Cloud cluster URL + API key** — [cloud.qdrant.io](https://cloud.qdrant.io) (free tier)
- ✅ **Twilio Account SID + Auth Token** — [twilio.com](https://www.twilio.com) (includes Sandbox)
- ✅ **(Optional) Supabase Postgres URL** — for message logging to [supabase.com](https://supabase.com)

### Development Setup (Local)

#### 1. Virtual Environment & Dependencies

```powershell
# From repo root
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install from pyproject.toml (includes all dependencies)
pip install -e .
```

Or with `uv` (faster):
```powershell
uv sync
```

#### 2. Environment Configuration

```powershell
cd sarvamai
cp .env.example .env
# Edit .env with all your API keys (see .env.example for format)
```

**Required `.env` variables**:
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxx...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=+14155238886

SARVAM_API_KEY=...

GEMINI_API_KEY1=AIza...
GEMINI_API_KEY2=AIza...
# Add more GEMINI_API_KEY2–GEMINI_API_KEY6 for better rate-limit handling

QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=...

# Optional: Supabase message logging
POSTGRES_URL=postgresql://user:password@host:5432/database
```

#### 3. Ingest Scheme Documents

**Run once** to embed all scheme documents and store vectors in Qdrant:

```powershell
cd sarvamai
$env:PYTHONPATH = "$PWD\src"
python scripts/ingest.py
```

This:
- Reads 8 scheme Markdown files from `../data/seed_docs/`
- Chunks them semantically
- Embeds using Gemini `embedding-001` (3072-dim)
- Uploads ~68 vectors to Qdrant Cloud
- Prints: `Ingested [N] vectors successfully`

On full restart, this step runs again (idempotent).

#### 4. Start Local Development Server

```powershell
cd sarvamai
$env:PYTHONPATH = "$PWD\src"
python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --log-level info
```

Verify startup:
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### 5. Expose Locally to Internet (Cloudflare Tunnel)

Twilio needs a public HTTPS URL to send webhook requests. Use Cloudflare Tunnel (no charge):

```powershell
# Download from https://github.com/cloudflare/cloudflared/releases
# Or: scoop install cloudflare/cloudflare-cli/cloudflared

cloudflared tunnel --url http://localhost:8000
```

It prints:
```
Your quick tunnel has been created! Visit it at (it may take a few seconds to be reachable):

https://abc123def456.trycloudflare.com
```

**Important**: Each restart creates a **new URL**. You'll need to update Twilio's webhook URL each time (see Step 6).

#### 6. Configure Twilio Webhook

1. Go to [Twilio Console](https://console.twilio.com)
2. Navigate to: **Messaging** → **Try it out** → **Send a WhatsApp message** → **Sandbox settings**
3. In **"When a message comes in"** field, paste:
   ```
   https://abc123def456.trycloudflare.com/api/v1/webhooks/twilio/webhook
   ```
   (Replace `abc123def456` with your actual Cloudflare Tunnel URL)
4. Set Method to: **HTTP POST**
5. Click **Save**

#### 7. Test on WhatsApp

Send a message from WhatsApp to Twilio Sandbox number **+14155238886**:

**First time?** Send: `join acres-moving`  
(This activates your sandbox access; you only do this once)

Then try:
- Text: `"help"` → see the help menu
- Text: `"Am I eligible for PM-KISAN?"` → get scheme-based answer
- Voice note: record a question about pensions or housing
- Hindi: `"मुझे कौन सी पेंशन मिल सकती है?"` (What pensions am I eligible for?)
- Check your local terminal for logs: STT transcript, LLM reasoning, answer generation

#### 8. Run Test Scripts (Optional)

```powershell
cd sarvamai
$env:PYTHONPATH = "$PWD\src"

# Test individual components
python scripts/test_retrieval.py          # Vector search
python scripts/test_audio_input.py        # STT on sample audio
python scripts/test_audio_to_answer.py    # Full audio pipeline
python scripts/test_e2e_campaign.py       # End-to-end with real queries
python scripts/test_multilang.py          # Language detection + translation
```

Outputs are saved to `scripts/results/` as JSON files.

---

### Production Deployment (Always-On)

See the **root [README.md](../README.md#-production-deployment-render--uptimerobot)** for full Render + UptimeRobot setup.

For cost breakdown and service longevity details, see the **[Service Longevity](../README.md#-service-longevity-how-long-can-this-run)** section in the root README covering all components: Render, Twilio, Gemini, Sarvam AI, Qdrant, Supabase, and UptimeRobot.

---

## Supabase Status (Current)

Supabase Postgres logging is now wired for webhook processing.

Every incoming message writes one row to the `message_logs` table with:

- `user_number`
- `inbound_text`
- `query_text`
- `transcript` (for audio)
- `answer_text`
- `media_count` and `media_types`
- `status` (`answered`, `help_menu`, `stt_empty`, `unsupported_media`, `failed`)
- `error_message` (if failed)
- `raw_payload`

Table creation is automatic on first write (via SQLAlchemy `create_all`).

If rows are still missing, verify `POSTGRES_URL` is set correctly in your environment.

---

## How Cloudflare Tunnel Works (Local Webhook Forwarding)

A common question: *"My server is running locally — how does Twilio reach it?"*

```
User → WhatsApp → Twilio
                    |
                    | POST https://xyz.trycloudflare.com/...
                    |
                    v
          Cloudflare Edge (internet-facing)
                    |
                    | encrypted tunnel (persistent outbound connection
                    | from your laptop to Cloudflare)
                    |
                    v
          cloudflared process (on your laptop)
                    |
                    | HTTP forward to
                    v
          localhost:8000 (uvicorn / FastAPI)
                    |
                    | processes request, replies via Twilio REST API
                    v
          Twilio → WhatsApp reply to user
```

**The key insight**: `cloudflared` makes an **outbound** TLS connection to Cloudflare when it starts. Cloudflare holds that connection open and uses it to forward inbound requests. Your laptop never needs to accept inbound connections; your firewall and NAT are irrelevant. Each restart creates a **new random URL** — that's by design.

---

## Useful Scripts

| Script | Purpose | Command |
|--------|---------|---------|
| `ingest.py` | Ingest scheme docs into Qdrant | `python scripts/ingest.py` |
| `ping_test.py` | Verify all API keys work | `python scripts/ping_test.py` |
| `send_twilio_test_message.py` | Send message directly from CLI | `python scripts/send_twilio_test_message.py --to whatsapp:+91XXXXXXXXXX --message "hello"` |
| `test_retrieval.py` | Test vector search | `python scripts/test_retrieval.py` |
| `test_audio_input.py` | Test STT on sample audio | `python scripts/test_audio_input.py` |
| `test_audio_to_answer.py` | Test full audio pipeline | `python scripts/test_audio_to_answer.py` |
| `test_e2e_pipeline.py` | End-to-end with real queries | `python scripts/test_e2e_pipeline.py` |

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed component design, technology rationale,
request flow, and development decisions.
