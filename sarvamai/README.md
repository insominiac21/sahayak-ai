# Sahayak AI — Agentic AI Assistant for Government Schemes

**Sahayak AI** is a **production-grade agentic AI system** that helps Indian citizens understand and apply for 
government welfare schemes via WhatsApp — in **22 Indian languages**, with **voice support**.

Users send text or voice messages in any language. Sahayak AI transcribes, translates, **reasons through a 
4-tool agent** to search knowledge bases and the web, and replies with accurate, personalized answers — 
all in the user's original language.

### **Why Agentic, Not Just RAG?**

Unlike simple retrieval systems, Sahayak AI **thinks and decides**:
- **Analyzes** each query to determine intent (scheme search? eligibility check? something else?)
- **Dynamically chooses** which tools to use (search knowledge base? search web? check eligibility rules?)
- **Reasons** through multi-step problems (if KB doesn't have answer → fallback to web search)
- **Remembers** entire conversation history (no amnesia between turns)
- **Never gives up** — proactively uses tools instead of saying "I don't know"

---

## Core Features

### **🌍 22 Indian Languages + English** (Auto-Detect)
Hindi, Tamil, Telugu, Kannada, Malayalam, Marathi, Gujarati, Bengali, Urdu, Punjabi, Assamese, Oriya,
Manipuri, Maithili, Konkani, Bodo, Santali, Kashmiri, Sindhi, and more.
- **No language selection** — system auto-detects from voice or text
- **Voice → Text → Process → Text → Voice** — fully spoken conversation support

### **🎤 Voice & Text Messages** (WhatsApp Native)
- Accept voice notes, transcribe with **Sarvam Saaras v3** (built for Indian accents)
- Accept typed messages in any language
- Reply with text (sent to WhatsApp) and optional text-to-speech

### **🤖 Agentic Reasoning** (LangGraph StateGraph)
The agent decides which of 4 tools to call:
1. **search_schemes** — Query knowledge base for scheme details (40+ document chunks)
2. **web_search** — Search Google for current info (PM NITI AYOG, scheme updates, new programs)
3. **check_eligibility** — Calculate income/age/criteria (covers all 8 supported schemes)
4. **fetch_user_profile** — Get user's saved context (state, income, language, age)

**Example Flow**:
```
User: "Tell me about PM NITI AYOG" (in Tamil)
1. Transcribe & translate to English
2. Agent analyzes: "This is a scheme question"
3. Agent calls search_schemes("PM NITI AYOG")
4. KB returns no results → Agent auto-triggers web_search
5. web_search returns top 5 results with details
6. Agent synthesizes answer with context
7. Translate back to Tamil → Send via WhatsApp
```

### **💡 Conversation Memory** (No Amnesia)
- Entire chat history stored per user (thread ID = WhatsApp number)
- Agent loads all previous messages before each turn
- Example:
  - **Turn 1**: "Tell me about SSY" → Agent: "Sukanya Samriddhi is for girl children..."
  - **Turn 2**: "Talk about eligibility" → Agent remembers SSY, calls `check_eligibility("SSY")`
  - **Result**: Perfect follow-up answer (not "I don't know")

### **🚫 Never Gives Up**
Agent has explicit instructions to **always find answers**:
- Doesn't say "not in knowledge base" — uses tools to search
- For unknown schemes → automatically calls web_search
- For eligibility → always calls check_eligibility tool
- Philosophy: "Users come hoping to improve lives — don't crush that hope"

---

## What It Solves

| Problem | Solution |
|---------|----------|
| **Language barrier** | 22 Indian languages, auto-detect, voice support |
| **Information gap** | Access to 8 major government schemes + web search for others |
| **Not knowing eligibility** | Agent intelligently checks income/age/criteria rules |
| **No conversation context** | Full history per user, multi-turn reasoning |
| **Defensive chatbots** | Agentic AI that proactively finds answers using tools |
| **Scheme updates** | Web search fallback for current policies and deadlines |
| **Tech illiteracy** | Simple WhatsApp interface, no app download, voice support |

---

## Tech Stack — Production-Ready

| Layer | Tech | Why |
|-------|------|-----|
| **Channel** | Twilio WhatsApp | WhatsApp's official sandbox; supports 15M+ messages/month |
| **Web Framework** | FastAPI + uvicorn | Async I/O; WebSocket-ready; 3ms response time |
| **Agent Brain** | LangGraph 1.1.8 | StateGraph for multi-step reasoning; tool binding; memory |
| **LLM** | Gemini 2.5 Flash | 1M token context; round-robin across 6 keys (load distribution) |
| **STT** | Sarvam Saaras v3 | 22 Indian languages; >95% accuracy on code-mixed audio |
| **Translation** | Sarvam Mayura | Auto-detect + translate in one API call; 22+ languages |
| **Vector DB** | Qdrant Cloud | ANN indexing; 1024-dim vectors; <50ms search |
| **Embeddings** | BAAI/bge-m3 | 1024-dim; HuggingFace Inference API with retry logic |
| **Web Search** | Google Serper | Real-time results; covers trending schemes and updates |
| **Session Store** | Supabase / Memory | User profiles with fallback to in-memory cache |
| **Deployment** | Render | Auto-scale, GitHub CI/CD, uptime SLA |

---

## Supported Schemes (8 Major Programs)

The agent covers these with hardcoded eligibility rules:

1. **PMAY-U 2.0** — Urban housing (EWS/LIG/MIG brackets)
2. **PM-JAY** — Health insurance (₹5L coverage, SECC 2011)
3. **PMJDY** — Jan Dhan banking (universal banking)
4. **SSY** — Sukanya Samriddhi (girl child savings, <10 years)
5. **APY** — Atal Pension (guaranteed pension, 18-40 entry)
6. **PMUY** — Ujjwala (free LPG for BPL)
7. **NSAP** — National social assistance (pensions)
8. **Stand-Up India** — Entrepreneur loans (SC/ST/Women)

For schemes not in KB → agent uses **web_search** to find current info.

---

## How the Agent Decides (Architecture Overview)

```
User Message (WhatsApp)
    |
    v
[STT] Transcribe voice if needed
    |
    v
[Translation] Auto-detect language & translate to English
    |
    v
┌──────────────────────────────────────────┐
│  LangGraph StateGraph (Agent)             │
│                                          │
│  Agent Node (Reasoning):                 │
│  - Analyzes query for intent             │
│  - Detects: scheme question?             │
│  - Detects: eligibility question?        │
│  - Detects: unknown program?             │
│                                          │
│  Tool Selection:                         │
│  - Scheme Q? → search_schemes            │
│  - Eligibility Q? → check_eligibility    │
│  - KB empty? → web_search (fallback)     │
│  - Want context? → fetch_user_profile    │
│                                          │
│  Loop:                                   │
│  - Call selected tools                   │
│  - LLM sees results                      │
│  - Reason again: need more tools?        │
│  - If yes → call more tools              │
│  - If no → generate final answer         │
│                                          │
│  Memory:                                 │
│  - Load all previous messages (thread)   │
│  - Agent sees full conversation          │
│  - No multi-turn amnesia                 │
└──────────────────────────────────────────┘
    |
    v
[LLM] Google Gemini 2.5 Flash synthesizes answer
    | (with round-robin key rotation)
    v
[Translation] Translate answer back to user's language
    |
    v
[Twilio] Send reply via WhatsApp
```

---

## Key Differentiators

🎯 **Agentic** — Reasons about which tools to use (not just templates)
🌍 **Polyglot** — 22 Indian languages, auto-detect, voice-native
🚀 **Proactive** — Never says "I don't know"; uses fallback tools
💾 **Stateful** — Remembers entire conversation per user
🔗 **Multi-Step** — Can chain tools (search → reason → search again)
⚡ **Fast** — <2s response (including STT + LLM + translation)
📱 **WhatsApp-Native** — No app, no downloads, in-chat experience

---

## Repository File Index — What Goes Where

```
sarvamai/  (Main project directory)
├── .env                          # ⚠️ Secrets (DO NOT COMMIT)
├── .env-example                  # ✅ Safe template for all 41 env vars
├── README.md                      # This file
├── ARCHITECTURE.md                # Detailed agent flow + tool descriptions
│
├── src/app/
│   ├── main.py                   # FastAPI entry point (Twilio webhook)
│   │
│   ├── api/v1/endpoints/
│   │   └── webhooks_langgraph.py  # ✨ AGENT WEBHOOK: Receives WhatsApp → triggers run_agent()
│   │
│   ├── services/
│   │   ├── agent/
│   │   │   └── langgraph_agent.py  # ✨ AGENT BRAIN: StateGraph, 4 tools, round-robin Gemini
│   │   │
│   │   ├── audio/
│   │   │   ├── stt_sarvam.py       # Speech-to-text (22 Indian languages)
│   │   │   └── translate_sarvam.py # Translation (auto-detect + translate)
│   │   │
│   │   └── rag/
│   │       ├── retrieve.py         # Qdrant hybrid search (semantic + BM25)
│   │       └── embeddings_bge.py   # HuggingFace embeddings with retry logic
│   │
│   ├── db/
│   │   └── session_manager.py     # User profile storage (memory + Supabase)
│   │
│   └── core/
│       └── config.py              # 41 environment variables (Pydantic Settings)
│
└── scripts/
    └── ingest.py                  # One-time: Ingest scheme docs → Qdrant
```

**Key Files by Purpose**:

| Purpose | File |
|---------|------|
| **Agent Logic** | `services/agent/langgraph_agent.py` |
| **Webhook Handler** | `api/v1/endpoints/webhooks_langgraph.py` |
| **Voice Processing** | `services/audio/{stt_sarvam, translate_sarvam}.py` |
| **Knowledge Search** | `services/rag/retrieve.py` |
| **Config & Secrets** | `core/config.py` |
| **User Memory** | `db/session_manager.py` |
| **Setup** | `.env-example` (copy to `.env`) |

---

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
- ✅ **Serper API key (Web Search Fallback)** — [serper.dev](https://serper.dev) (free tier: 100/month)
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

# Serper API (Google Search - Fallback for Unknown Schemes)
SERPER_API_KEY=...

# Optional: Supabase message logging
POSTGRES_URL=postgresql://user:password@host:5432/database
```

#### 2.5 **Configure Serper API (Web Search Fallback)**

**Why Serper**?
- ✅ Real-time Google search results for unknown/new schemes
- ✅ Fallback when KB doesn't have answer (e.g., "Tell me about PM NITI AYOG")
- ✅ Free tier: 100 searches/month (then $0.005/query)
- ✅ Fast: <500ms response time

**Setup**:
1. Go to [serper.dev](https://serper.dev)
2. Sign up (free account, no credit card needed)
3. Copy your API key from dashboard
4. Add to `.env`:
   ```
   SERPER_API_KEY=your_key_here
   ```

**Test Serper Connection**:
```powershell
cd sarvamai
python scripts/test_serper.py
```

Output should show:
```
✅ SERPER_API_KEY is configured
✅ Successfully connected to Serper API
✅ Got 3 results
Success Rate: 4/4
✅ SERPER API TEST COMPLETE
```

**How It Works**:
- User: "Tell me about PMAY 3.0" 
- Agent: Calls `search_schemes()` → KB returns no results (only PMAY 2.0)
- Agent: Sees "Not in KB" message → triggers `web_search()`
- Serper: Returns latest Google results about PMAY 3.0
- Agent: Synthesizes answer from search results
- User: Gets current information with links ✅

**If Serper is Not Configured**:
- Agent still works (falls back to hardcoded eligibility rules)
- But won't have access to latest scheme updates
- Message: "Web search temporarily unavailable (API key not configured)"

---

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
| **`test_serper.py`** | **Test Serper API (web search)** | **`python scripts/test_serper.py`** |
| `send_twilio_test_message.py` | Send message directly from CLI | `python scripts/send_twilio_test_message.py --to whatsapp:+91XXXXXXXXXX --message "hello"` |
| `test_retrieval.py` | Test vector search | `python scripts/test_retrieval.py` |
| `test_audio_input.py` | Test STT on sample audio | `python scripts/test_audio_input.py` |
| `test_audio_to_answer.py` | Test full audio pipeline | `python scripts/test_audio_to_answer.py` |
| `test_e2e_pipeline.py` | End-to-end with real queries | `python scripts/test_e2e_pipeline.py` |

---

## Troubleshooting

### **Serper API (Web Search) Not Working**

**Symptom**: Agent responds with "Web search temporarily unavailable" when asking about unknown schemes.

**Root Cause**: `SERPER_API_KEY` is not configured.

**Diagnosis**:
```powershell
# Test Serper connectivity
python scripts/test_serper.py
```

**Expected Output**:
```
✅ SERPER_API_KEY is configured
✅ Successfully connected to Serper API
✅ Got 3 results
Success Rate: 4/4
✅ SERPER API TEST COMPLETE
```

**If Test Fails**:

| Error | Reason | Fix |
|-------|--------|-----|
| `SERPER_API_KEY is NOT configured` | Key not in `.env` or environment | Add `SERPER_API_KEY=` to `.env` file (get free key from [serper.dev](https://serper.dev)) |
| `Status 401 (Unauthorized)` | Invalid API key | Go to [serper.dev](https://serper.dev) → copy correct key from dashboard |
| `Status 403 (Forbidden)` | Quota exceeded or key disabled | Check [serper.dev](https://serper.dev) quota (100 free/month, then $0.005/query) |
| `Status 429 (Rate Limited)` | Too many requests too fast | Wait before retrying (10s backoff) or upgrade plan |
| `Connection Error` | Network issue or Serper down | Check internet connection or [serper.dev status page](https://status.serper.dev) |
| `Timeout` | Serper taking >10s to respond | Retry (usually works on second attempt) |

**How Agentic AI Uses Serper**:

```
User Query (e.g., "Tell me about PM NITI AYOG")
    ↓
Agent Analyzes: "This is a scheme question"
    ↓
Agent Calls: search_schemes() → Search local Qdrant KB
    ↓
KB Returns: ❌ No results (scheme not in knowledge base)
    ↓
search_schemes Tool Response: 
"Scheme not found in knowledge base. 
 Please call web_search('PM NITI AYOG') to find current information."
    ↓
Agent SEES this message and DECIDES:
"KB is empty → trigger fallback"
    ↓
Agent Calls: web_search("PM NITI AYOG 2024")
    ↓
Serper API Returns: Top 5 Google results + snippets
    ↓
Agent Synthesizes answer from Google results
    ↓
User Gets: Current info about PM NITI AYOG with links ✅
```

**Why This Is Agentic**:
- ✅ Agent **decides** when to use web_search (only if KB empty)
- ✅ Agent **chains** tools (search_schemes → sees empty → web_search)
- ✅ Agent **adapts** based on results (doesn't give up)
- ✅ Agent **never says** "I don't know" (uses fallback)

**If Serper is Disabled** (no API key):
- ✅ Agent still works (uses hardcoded eligibility rules + KB search)
- ⚠️ Can't access latest scheme updates or unknown schemes
- Falls back to: "Web search temporarily unavailable (API key not configured)"

---

### **Agent Not Using Web Search**

**Symptom**: Agent doesn't search web even for unknown schemes.

**Debug**:
1. Check logs for: `web_search` tool calls
2. Run: `python scripts/test_serper.py` (verify API key works)
3. Check agent system prompt (should have "call web_search" instructions)

**If Agent Bypasses Web Search**:
- May not have detected it as a "scheme question"
- Add scheme keywords to user query: "Tell me about [SCHEME NAME]", "What is [SCHEME]?"
- Or phrase as eligibility question: "Am I eligible for [SCHEME]?"

---

### **Internet Search Found Relevant Info**

If you ran an internet search and found information about Serper or the agent's web search capability:

**To Test It Yourself**:
```powershell
cd sarvamai
python scripts/test_serper.py
```

This script:
- ✅ Verifies API key is configured
- ✅ Tests connectivity to Serper API
- ✅ Runs 4 sample scheme queries
- ✅ Validates response structure
- ✅ Shows actual search results

**What You'll See**:
```
Test 1: Basic Connectivity
✅ Successfully connected to Serper API
✅ Got 3 results

Test 2: Multiple Scheme Queries
✅ 'PM-JAY Ayushman Bharat eligibility': 3 results
✅ 'PMJDY Jan Dhan eligibility': 3 results
✅ 'SSY Sukanya Samriddhi': 3 results
✅ 'latest government schemes 2024': 3 results

Success Rate: 4/4
```

**Real Example** (What Happens When User Asks Unknown Scheme):

```
User: "What about PM NITI AYOG?"
├─ Agent: "This is scheme question → use search_schemes"
├─ search_schemes(): Qdrant search for "NITI AYOG" → ❌ Not found
├─ Agent: "KB is empty → must call web_search"
├─ web_search("PM NITI AYOG"): Serper API returns →
│   1. NITI Aayog official website
│   2. Article: "NITI Aayog 2024 Initiatives"
│   3. "Government Think Tank Programs"
├─ Agent synthesizes: "NITI Aayog is Government's think tank for..."
└─ User: Gets current info about NITI Aayog ✅
```

---

### **Verifying All Tools Work**

Run comprehensive test:
```powershell
python scripts/ping_test.py          # All API keys
python scripts/test_serper.py        # Web search
python scripts/test_retrieval.py     # Vector DB search
python scripts/test_audio_input.py   # Voice transcription
```

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed component design, technology rationale,
request flow, and development decisions.
