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

### 1. Prerequisites

- Python 3.11+
- A [Twilio account](https://www.twilio.com) with WhatsApp Sandbox enabled
- A [Sarvam AI](https://www.sarvam.ai) API key
- A [Qdrant Cloud](https://cloud.qdrant.io) cluster (free tier is sufficient)
- One or more [Google AI Studio](https://aistudio.google.com) API keys (Gemini)

### 2. Install dependencies

```powershell
# from the repo root
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

### 3. Configure environment

Copy `.env.example` to `.env` and fill in all values:

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=+14155238886        # Twilio Sandbox number
SARVAM_API_KEY=your_sarvam_key
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_key
GEMINI_API_KEY1=AIza...
GEMINI_API_KEY2=AIza...   # add up to 6 keys for rate-limit headroom
```

### 4. Ingest scheme documents

Run once to embed and upload scheme docs to Qdrant:

```powershell
cd sarvamai
$env:PYTHONPATH="$PWD\src"
python scripts/ingest.py
```

### 5. Start the server

```powershell
cd sarvamai
$env:PYTHONPATH="$PWD\src"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
```

### 6. Expose localhost to the internet (Cloudflare Tunnel)

Twilio needs a public HTTPS URL to send webhook requests to. Cloudflare Tunnel creates
one without any port-forwarding or server:

```powershell
# Download cloudflared.exe from https://github.com/cloudflare/cloudflared/releases
# Then run:
cloudflared tunnel --url http://localhost:8000
```

It will print a URL like `https://xyz.trycloudflare.com`. Copy it.

**How it works:** `cloudflared` opens an outbound TLS connection to Cloudflare's edge.
Cloudflare assigns a random subdomain that routes all inbound HTTPS traffic back through
that tunnel to your local port 8000. No inbound firewall rules are needed. Each restart
generates a new URL — you must re-paste it into the Twilio console.

### 7. Configure Twilio Webhook

In the [Twilio Console](https://console.twilio.com), go to:

```
Messaging → Try it out → Send a WhatsApp message → Sandbox settings
```

Set **"When a message comes in"** to:

```
https://xyz.trycloudflare.com/api/v1/webhooks/twilio/webhook
```

Method: `HTTP POST`

### 8. Test

Send "hi" to the Twilio Sandbox number on WhatsApp. You should receive the help menu.
Send any scheme question in English or any Indian language (text or voice note).

### 9. Run test scripts (including audio)

```powershell
cd sarvamai
$env:PYTHONPATH="$PWD\src"

# audio-focused checks
python scripts/test_audio_input.py
python scripts/test_audio_to_answer.py

# retrieval/e2e checks
python scripts/test_retrieval.py
python scripts/test_retrieval_quality.py
python scripts/test_multilang.py
python scripts/test_e2e_pipeline.py
```

Test outputs are written under `scripts/results/`.

---

## Always-On Deployment (Render + UptimeRobot)

Use this when you want a stable public URL and 24x7 availability.

### Render

1. Push the latest code to GitHub.
2. In Render, create a new Web Service from your repository.
3. Use the repository-level `render.yaml` blueprint (included in this repo), or set manually:
    - Build command: `pip install -e .`
    - Start command: `uvicorn app.main:app --app-dir sarvamai/src --host 0.0.0.0 --port $PORT`
    - Health check path: `/health`
4. Add environment variables in Render dashboard:
    - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER`
    - `SARVAM_API_KEY`
    - `QDRANT_URL`, `QDRANT_API_KEY`
    - `GEMINI_API_KEY1` (and additional Gemini keys if used)
    - `POSTGRES_URL` (optional currently; see Supabase status below)
5. After deploy succeeds, copy your Render URL:
    - `https://<your-service>.onrender.com/api/v1/webhooks/twilio/webhook`
6. Paste it into Twilio Sandbox "When a message comes in" webhook URL.

### UptimeRobot

1. Create an HTTP(s) monitor.
2. Monitor URL: `https://<your-service>.onrender.com/health`
3. Interval: 5 minutes.
4. Enable alerts (email/Telegram) for downtime.

This gives you uptime alerts and helps reduce cold starts on free plans.

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

## Local Webhook — How It Actually Works

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

The key insight: `cloudflared` makes an **outbound** connection to Cloudflare when it
starts. Cloudflare holds that connection open and uses it to forward inbound requests.
Your laptop never needs to accept inbound connections; your firewall and NAT are irrelevant.

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/ingest.py` | Chunk scheme Markdown docs, embed with Gemini, upload to Qdrant |
| `scripts/ping_test.py` | Verify all API keys are valid and services are reachable |
| `scripts/send_twilio_test_message.py` | Send a WhatsApp message directly from the command line |

```powershell
# Send a test message
python scripts/send_twilio_test_message.py --to whatsapp:+91XXXXXXXXXX --message "hello"

# Send the help menu
python scripts/send_twilio_test_message.py --to whatsapp:+91XXXXXXXXXX --menu
```

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed component design, technology rationale,
request flow, and development decisions.
