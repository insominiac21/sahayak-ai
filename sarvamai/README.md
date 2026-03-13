# Sahayak AI

A WhatsApp-first, multilingual assistant that helps Indian citizens understand and apply
for government welfare schemes. Users send text or voice messages in any Indian language;
the system replies with accurate, scheme-grounded answers in the same language.

---

## What it does

- Accepts WhatsApp messages (text or voice note) via Twilio
- Transcribes voice notes using Sarvam AI (Saaras v3 STT)
- Detects and translates the query to English (Sarvam Mayura)
- Retrieves relevant scheme excerpts from a Qdrant vector database
- Generates a grounded answer with Google Gemini 2.5 Flash
- Translates the answer back to the user's language and replies via WhatsApp

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Channel | Twilio WhatsApp | WhatsApp API requires a business partnership; Twilio provides sandbox access with no approval needed for development |
| Web framework | FastAPI + uvicorn | Async request handling; `BackgroundTasks` lets the webhook ACK immediately while the heavy pipeline (STT + LLM) runs asynchronously |
| STT | Sarvam Saaras v3 | Purpose-built for Indian languages and accents; outperforms Whisper on code-mixed Hindi/English voice notes |
| Translation | Sarvam Mayura | Auto-detects source language; covers 10+ scheduled Indian languages in one API call |
| Vector DB | Qdrant Cloud | Dedicated vector store with ANN indexing; supports 3072-dim Gemini embeddings; generous free tier |
| LLM | Gemini 2.5 Flash | 1M token context window; same vendor as embeddings (consistent embedding space); round-robin across 6 keys avoids rate limits |
| Embeddings | gemini-embedding-001 | 3072-dim; used identically at ingest time and query time |
| Tunnel (dev) | Cloudflare Tunnel | Exposes localhost:8000 to the internet via a free HTTPS URL; no port-forwarding or VPS required |

---

## Repository File Index

Below is the practical file map (excluding local runtime artifacts like `__pycache__`).

```
sarvamai/
├── .env.example
├── .env
├── README.md
├── ARCHITECTURE.md
├── BUILD_CHECKLIST.md
├── scripts/
│   ├── ingest.py
│   ├── eval.py
│   ├── ping_test.py
│   ├── send_twilio_test_message.py
│   ├── test_sarvam.py
│   ├── test_audio_input.py
│   ├── test_audio_to_answer.py
│   ├── test_e2e_pipeline.py
│   ├── test_multilang.py
│   ├── test_retrieval.py
│   ├── test_retrieval_quality.py
│   ├── results/
│   │   ├── audio_to_answer.json
│   │   ├── e2e_pipeline.json
│   │   ├── multilang_retrieval.json
│   │   ├── retrieval_basic.json
│   │   └── sarvam_translation.json
│   └── test_data/
│       └── audio/
│           ├── WhatsApp Ptt 2026-03-13 at 9.26.26 PM.ogg
│           ├── WhatsApp Ptt 2026-03-13 at 9.30.20 PM.ogg
│           ├── WhatsApp Ptt 2026-03-13 at 9.34.36 PM.ogg
│           ├── WhatsApp Ptt 2026-03-13 at 9.50.48 PM.ogg
│           ├── WhatsApp Ptt 2026-03-13 at 9.51.28 PM.ogg
│           └── WhatsApp Ptt 2026-03-13 at 9.51.52 PM.ogg
└── src/
        ├── __init__.py
        └── app/
                ├── __init__.py
                ├── main.py
                ├── api/
                │   └── v1/
                │       ├── router.py
                │       └── endpoints/
                │           └── webhooks_twilio.py
                ├── core/
                │   └── config.py
                ├── db/
                │   ├── base.py
                │   └── session.py
                ├── models/
                │   ├── user.py
                │   └── message_log.py
                ├── repositories/
                │   ├── user.py
                │   └── message_log.py
                ├── schemas/
                │   └── user.py
                ├── services/
                │   ├── __init__.py
                │   ├── agent/
                │   │   ├── checklist_tool.py
                │   │   ├── eligibility_tool.py
                │   │   └── orchestrator.py
                │   ├── audio/
                │   │   ├── stt_sarvam.py
                │   │   └── translate_sarvam.py
                │   ├── channels/
                │   │   └── twilio_whatsapp.py
                │   ├── llm/
                │   │   ├── __init__.py
                │   │   └── gemini_client.py
                │   └── rag/
                │       ├── __init__.py
                │       ├── embeddings.py
                │       ├── ingest.py
                │       ├── qdrant_client.py
                │       └── retrieve.py
                ├── tests/
                │   └── test_webhook.py
                └── utils/
                        └── logging.py
```

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
