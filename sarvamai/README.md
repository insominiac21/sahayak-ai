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

## Project Structure

```
sarvamai/
├── src/
│   └── app/
│       ├── main.py                          # FastAPI app, router registration
│       ├── core/
│       │   └── config.py                    # Pydantic Settings, loads .env
│       ├── api/v1/endpoints/
│       │   └── webhooks_twilio.py           # Webhook handler, help menu, background pipeline
│       └── services/
│           ├── channels/
│           │   └── twilio_whatsapp.py       # Parse Twilio payload, send reply
│           ├── audio/
│           │   ├── stt_sarvam.py            # Download audio, Sarvam STT
│           │   └── translate_sarvam.py      # Sarvam language detect + translate
│           ├── rag/
│           │   └── retrieve.py              # Embed query, search Qdrant
│           ├── agent/
│           │   └── orchestrator.py          # Build prompt, call Gemini, translate answer
│           └── llm/
│               └── gemini_client.py         # Round-robin Gemini client with key failover
├── scripts/
│   ├── ingest.py                            # One-time: chunk docs, embed, upload to Qdrant
│   ├── send_twilio_test_message.py          # Send a live WhatsApp message from the CLI
│   └── ping_test.py                         # Health-check all API keys
├── tests/
├── .env.example                             # Required environment variables
├── README.md                                # This file
└── ARCHITECTURE.md                          # Detailed system design and component docs
```

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
pip install -e ".[dev]"
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
