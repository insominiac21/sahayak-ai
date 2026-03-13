# Sahayak AI — System Architecture

## Overview

Sahayak AI is a WhatsApp-first, multilingual RAG (Retrieval-Augmented Generation) assistant
that helps Indian citizens understand and apply for government welfare schemes. Users send
text or voice messages in any Indian language over WhatsApp. The system transcribes voice,
translates to English, retrieves relevant scheme excerpts from a vector database, generates
a grounded answer with Gemini, translates back to the user's language, and replies — all
inside a single asynchronous background task triggered by one incoming webhook POST.

---

## Architecture Diagram

```
WhatsApp User (text or voice note)
        |
        | WhatsApp message
        v
  Twilio Gateway  ──────────────────────────────────────────────────────┐
  (WhatsApp API)                                                         |
        |                                                                |
        | POST /api/v1/webhooks/twilio/webhook                          |
        | (HTTP to public URL → Cloudflare Tunnel → localhost:8000)     |
        v                                                                |
  FastAPI Server (uvicorn, port 8000)                                   |
        |                                                                |
        | 1. Returns 200 OK immediately (Twilio requires fast ACK)      |
        | 2. Spawns BackgroundTask                                       |
        v                                                                |
  ┌─────────────────────────────────────────────────────────────────┐   |
  │  Background Processing Pipeline                                  │   |
  │                                                                  │   |
  │  [Voice note?] ──────────────────────────────────────────────   │   |
  │       |                                                          │   |
  │       | Download audio from Twilio media URL (follows 307)      │   |
  │       v                                                          │   |
  │  Sarvam STT (Saaras v3)                                          │   |
  │       | → transcript text + detected language code               │   |
  │       v                                                          │   |
  │  [Text message or transcript]                                    │   |
  │       |                                                          │   |
  │       | Sarvam Translate (Mayura)                                │   |
  │       | → English query + source language                        │   |
  │       v                                                          │   |
  │  Qdrant Vector DB (Cloud, Cosine, 3072-dim)                      │   |
  │       | → top-K scheme text chunks                               │   |
  │       v                                                          │   |
  │  Google Gemini 2.5 Flash                                         │   |
  │  (prompted with chunks + query)                                  │   |
  │       | → English answer                                         │   |
  │       v                                                          │   |
  │  Sarvam Translate                                                │   |
  │       | → answer in user's language                              │   |
  └───────────────────────────────|─────────────────────────────────┘   |
                                  |                                      |
                                  | Twilio Messages REST API             |
                                  └──────────────────────────────────────┘
                                    WhatsApp reply delivered to user
```

---

## How Local Development Works with Cloudflare Tunnel

Twilio requires a **publicly reachable HTTPS URL** to send webhook POST requests to. When
running locally, your server is only accessible at `localhost:8000` — invisible to the
internet. Cloudflare Tunnel (`cloudflared`) solves this without port-forwarding or a VPS.

```
WhatsApp User
     |
     | sends message
     v
Twilio  ──► POST https://xyz.trycloudflare.com/api/v1/webhooks/twilio/webhook
                          |
                          | Cloudflare edge (internet-facing)
                          | ↓  encrypted tunnel (persistent outbound connection)
                          | Cloudflared process running on your laptop
                          | ↓  forwards to
                          localhost:8000  (uvicorn / FastAPI)
                                |
                                | processes, replies via Twilio REST API
                                v
                          Twilio → WhatsApp reply to user
```

**Why this works:**

1. `cloudflared tunnel --url http://localhost:8000` starts a process on your machine that
   opens an **outbound** TLS connection to a Cloudflare edge server. No inbound firewall
   rules needed — outbound connections are almost never blocked.

2. Cloudflare assigns a random subdomain (`xyz.trycloudflare.com`) that routes all traffic
   to your local process through that persistent tunnel.

3. You paste that URL into the Twilio Sandbox webhook field. Twilio now sends all incoming
   WhatsApp messages to Cloudflare, which forwards them through the tunnel to your laptop.

4. Every time you restart `cloudflared`, you get a **new random URL**. You must re-paste
   it into the Twilio console. For a stable URL, use a named Cloudflare tunnel with a
   custom domain (requires a Cloudflare account and registered domain).

**Critical detail:** The tunnel URL must point to the exact port where uvicorn is listening.
If the app is on `:8000` and the tunnel points to `:8001`, all Twilio webhooks silently
fail with a connection refused error on your end — Twilio keeps retrying but gets no reply.

---

## Technology Choices — Why Each Was Selected

### WhatsApp via Twilio
WhatsApp does not provide direct API access to developers without an approved Business API
account. Twilio acts as an intermediary: it has a WhatsApp partnership and exposes a clean
REST API and webhook model. The Twilio Sandbox requires no formal approval for development,
making it the fastest path to a working WhatsApp integration.

### FastAPI + uvicorn
FastAPI gives async request handling and `BackgroundTasks` built-in. The webhook handler
must return a `200 OK` within a few seconds or Twilio marks the delivery as failed and
retries. FastAPI's `BackgroundTasks` lets us ACK immediately and do the heavy processing
(STT, retrieval, LLM call) asynchronously without needing a separate task queue like
Celery or Redis.

### Sarvam AI (STT + Translation)
Sarvam is purpose-built for Indian languages. Its Saaras v3 STT model handles the
code-mixed, accented speech patterns common in Indian WhatsApp voice notes far better
than general-purpose models (Whisper, Google Speech-to-Text). Its Mayura translation
model covers 10+ scheduled Indian languages with auto-detection — no separate
language-detection step needed. Using one vendor for both STT and translation reduces
latency and API surface.

### Qdrant (Vector Database)
Qdrant is a dedicated vector database with a generous free cloud tier. It supports cosine
similarity search over high-dimensional embeddings (3072-dim from Gemini's
`gemini-embedding-001`) with fast approximate nearest-neighbour (ANN) indexing. Compared
to storing embeddings in Postgres (pgvector), Qdrant gives better query performance at
scale and a simpler SDK. The scheme corpus (68 vectors) fits entirely in the free tier.

### Google Gemini 2.5 Flash
Gemini 2.5 Flash has a large context window (1M tokens), making it suitable for RAG
prompts that include multiple retrieved text chunks. Using the same Google API for both
embeddings (`gemini-embedding-001`) and generation (Gemini Flash) keeps the vendor count
low and ensures embedding-space consistency. The round-robin across 6 API keys prevents
rate-limit errors during bursty usage.

### RAG (Retrieval-Augmented Generation)
Scheme eligibility rules change frequently. Fine-tuning an LLM on scheme data would
require retraining whenever rules change. RAG instead keeps scheme knowledge in a
searchable document store that can be updated by re-running `scripts/ingest.py`. The LLM
only needs to synthesise a readable answer from retrieved excerpts — it does not need to
memorise scheme rules. This keeps answers grounded and reduces hallucination.

---

## Component Details

### 1. Channel Layer — `twilio_whatsapp.py`

- **Webhook**: `POST /api/v1/webhooks/twilio/webhook`
- Twilio sends form-encoded fields: `From`, `Body`, `NumMedia`, `MediaUrl0`,
  `MediaContentType0`, etc.
- Returns `{"status": "ack"}` with HTTP 200 immediately; all processing is async.
- `send_whatsapp_reply()` calls the Twilio Messages REST API to deliver the response.
  Both `From` and `To` are auto-prefixed with `whatsapp:` if not already present.

### 2. Audio Pipeline — `stt_sarvam.py`

- **Model**: Sarvam Saaras v3 (`saaras:v3`)
- **Download**: Uses `httpx` with manual 307/308 redirect handling. Twilio media URLs
  redirect to `mms.twiliocdn.com`; the redirect is followed explicitly (not via
  `follow_redirects=True`) to correctly attach Twilio Basic Auth only to the first hop.
- **SDK call**: `client.speech_to_text.transcribe(file=("audio.ogg", bytes, "audio/ogg"),
  model="saaras:v3", mode="transcribe")`
  The `file` parameter must be a `(filename, bytes, mime_type)` tuple — raw bytes are
  rejected by the SDK.
- **Content-type handling**: Twilio sends `audio/ogg; codecs=opus`. The codec suffix is
  stripped with `.split(";")[0].strip()` before checking against the supported set.

### 3. Translation — `translate_sarvam.py`

- **Model**: Sarvam Mayura
- `detect_and_translate(text, target_lang)` auto-detects the source language and
  translates. Returns `{translated_text, source_language_code}`.
- Used twice per request: query → English before retrieval, answer → user's language
  before reply.

### 4. RAG Pipeline

#### Offline Ingestion — `scripts/ingest.py`
1. Reads curated Markdown scheme docs from `data/seed_docs/`
2. Chunks by paragraphs (max 512 chars per chunk)
3. Embeds each chunk with `gemini-embedding-001` (3072-dim vectors)
4. Creates Qdrant collection `schemes` with cosine distance
5. Upserts `PointStruct` objects, payload: `{text, source}` where source is the scheme name
6. Result: 68 vectors across 8 scheme documents

#### Online Retrieval — `retrieve.py`
- Embeds the English query with `gemini-embedding-001`
- Calls `qdrant_client.query_points(collection_name="schemes", query=vector, limit=top_k)`
- Returns scored text chunks with scheme names as citations

### 5. LLM Layer — `gemini_client.py` + `orchestrator.py`

#### Round-Robin Gemini Client
- Loads up to 6 API keys from env vars `GEMINI_API_KEY1` … `GEMINI_API_KEY6`
- Creates a `genai.Client` per key; rotates with `threading.Lock`
- On `429 RESOURCE_EXHAUSTED` or `400 INVALID_ARGUMENT`, skips to next key
- Raises `RuntimeError` only after all keys are exhausted

#### Orchestrator — `orchestrator.py`
Builds a structured prompt containing:
1. A system instruction (role, answer rules, formatting rules — no emojis, plain lists)
2. The retrieved scheme chunks as labelled context
3. The user's English question

Sends the prompt to Gemini Flash via `generate_with_fallback()`. Translates the answer
back to the user's language with Sarvam before returning.

### 6. Data Stores

#### Qdrant Cloud
- GCP europe-west3 cluster (free tier)
- Collection: `schemes`, 3072-dim, cosine distance
- 68 vectors from 8 scheme documents
- Queried at runtime for every user message

#### Supabase Postgres (planned)
- Intended for users, sessions, message logs, citations, eval runs
- Connection via `POSTGRES_URL` env var
- SQLAlchemy models in `src/app/models/`, repositories in `src/app/repositories/`

---

## Request Flow (Step by Step)

```
1.  User sends WhatsApp message (text or voice note)
2.  Twilio POSTs form data to https://<tunnel>/api/v1/webhooks/twilio/webhook
3.  Cloudflare Tunnel forwards the request to localhost:8000
4.  FastAPI webhook handler:
      a. Parses form fields (From, Body, NumMedia, MediaUrl0, MediaContentType0)
      b. Returns HTTP 200 {"status": "ack"} immediately
      c. Spawns BackgroundTask(process_message, payload)
5.  process_message() runs asynchronously:
      a. [Voice note] Strip codec suffix from content-type
                      Download audio bytes from Twilio media URL (follow 307 redirect)
                      POST to Sarvam STT → transcript + detected language code
      b. [Help trigger] If message is empty/hi/help/start → send help menu and return
      c. Sarvam translate query → English
      d. Embed English query → query Qdrant → top-K scheme chunks
      e. Build prompt (system rules + chunks + question) → Gemini 2.5 Flash → answer
      f. Sarvam translate answer → user's language
      g. Twilio Messages REST API → reply delivered to user's WhatsApp
```

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Immediate 200 ACK + BackgroundTask | Twilio retries if no response within ~15 s; heavy pipeline (STT + LLM) takes longer |
| Sarvam for STT and translation | Best-in-class for Indian languages; single vendor for both tasks |
| RAG over fine-tuning | Scheme rules change; updating a vector store is trivial vs. retraining |
| Gemini for embeddings and generation | Same embedding space used offline (ingest) and online (query); keeps results consistent |
| Round-robin Gemini keys | Free-tier rate limits (RPM); distributing load across 6 keys avoids 429 errors |
| `httpx` manual redirect for Twilio audio | Twilio returns 307 to `mms.twiliocdn.com`; auth headers must only accompany the first hop |
| Cloudflare Tunnel for local dev | No port-forwarding, no VPS, no ngrok account needed; free and zero-config |
| No Redis / no Celery | `BackgroundTasks` is sufficient for single-message async; queue infra adds operational cost |

---

## File Reference

| File | Purpose |
|------|---------|
| `src/app/main.py` | FastAPI app entrypoint, router registration |
| `src/app/core/config.py` | Pydantic Settings, loads `.env` |
| `src/app/api/v1/endpoints/webhooks_twilio.py` | Webhook handler, help menu, background pipeline |
| `src/app/services/channels/twilio_whatsapp.py` | Parse Twilio form data, send reply via REST |
| `src/app/services/audio/stt_sarvam.py` | Download audio, call Sarvam STT, return transcript |
| `src/app/services/audio/translate_sarvam.py` | Detect language, translate with Sarvam Mayura |
| `src/app/services/rag/retrieve.py` | Embed query, search Qdrant, return chunks |
| `src/app/services/agent/orchestrator.py` | Build prompt, call Gemini, translate answer back |
| `src/app/services/llm/gemini_client.py` | Round-robin Gemini client with key failover |
| `scripts/ingest.py` | One-time offline ingestion of scheme docs to Qdrant |
| `scripts/send_twilio_test_message.py` | CLI to send a live WhatsApp message via Twilio |
| `scripts/ping_test.py` | Health-check all API keys (Gemini, Sarvam, Qdrant, Twilio) |

---

## Roadmap

- Add conversation memory (multi-turn context per user)
- Hybrid retrieval: BM25 keyword search + dense embeddings + cross-encoder reranking
- Rate limiting per user (prevent abuse)
- Structured logging and tracing (OpenTelemetry)
- Deploy on Render or Railway with a permanent domain (no more tunnel URL changes)
- Supabase Postgres integration for message history and eval tracking
