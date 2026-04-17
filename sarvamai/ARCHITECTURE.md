# Sahayak AI — System Architecture

## Overview

**Phase 3: Agentic AI with LangGraph**

Sahayak AI is a WhatsApp-first, multilingual **agentic assistant** that helps Indian citizens understand 
and apply for government welfare schemes. Users send text or voice messages in any Indian language. 
The system transcribes voice, translates to English, then **routes the query through a LangGraph agent**
that can dynamically choose from 4 tools (search knowledge base, search web, check eligibility, fetch user profile).
The agent reasons through multi-step queries, generates grounded answers with Gemini, translates back,
and replies — all inside a single asynchronous background task triggered by one incoming webhook POST.

---

## Architecture Diagram (Phase 3: LangGraph Agent)

```
WhatsApp User (text or voice note)
        |
        | WhatsApp message
        v
  Twilio Gateway  ──────────────────────────────────────────────────────┐
  (WhatsApp API)                                                         |
        |                                                                |
        | POST /api/v1/webhooks/langgraph/twilio/webhook                |
        | (HTTP to public URL → Cloudflare Tunnel → localhost:8000)     |
        v                                                                |
  FastAPI Server (uvicorn, port 8000)                                   |
        |                                                                |
        | 1. Returns 200 OK immediately (Twilio requires fast ACK)      |
        | 2. Spawns BackgroundTask                                       |
        v                                                                |
  ┌──────────────────────────────────────────────────────────────────┐   |
  │  Background Processing Pipeline                                  │   |
  │                                                                  │   |
  │  [Voice note?] ────────────────────────────────────────────────  │   |
  │       |                                                          │   |
  │       | Download audio from Twilio media URL                    │   |
  │       v                                                          │   |
  │  Sarvam STT (Saaras v3)                                          │   |
  │       | → transcript text + detected language code               │   |
  │       v                                                          │   |
  │  [Text message or transcript]                                    │   |
  │       |                                                          │   |
  │       | Sarvam Translate (Mayura)                                │   |
  │       | → English query + source language                        │   |
  │       v                                                          │   |
  │  ┌─────────────────────────────────────────────────────────┐     │   |
  │  │  LangGraph Agent (StateGraph)                           │     │   |
  │  │                                                          │     │   |
  │  │  Agent Node (reasoning loop):                           │     │   |
  │  │  - Analyzes user query                                  │     │   |
  │  │  - Decides which tools to call (or none)                │     │   |
  │  │  - Available Tools:                                      │     │   |
  │  │    * search_schemes → Qdrant KB (top-K chunks)          │     │   |
  │  │    * web_search → Serper API (current info)             │     │   |
  │  │    * check_eligibility → Income rules (PMAY-U, etc)    │     │   |
  │  │    * fetch_user_profile → Session history              │     │   |
  │  │                                                          │     │   |
  │  │  Tool Node (execution):                                  │     │   |
  │  │  - Calls selected tools sequentially                     │     │   |
  │  │  - Returns results as ToolMessages                       │     │   |
  │  │                                                          │     │   |
  │  │  Should Continue (edge decision):                        │     │   |
  │  │  - If tools were called → loop back to Agent            │     │   |
  │  │  - If no more tools needed → move to response           │     │   |
  │  │                                                          │     │   |
  │  │  Output: Structured answer with tool context            │     │   |
  │  └─────────────────────────────────────────────────────────┘     │   |
  │       |                                                          │   |
  │       | Agent output (with search results + eligibility)        │   |
  │       v                                                          │   |
  │  Google Gemini 2.5 Flash (with context)                         │   |
  │  (round-robin across 6 API keys)                                │   |
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

## Phase 3 Agent Architecture (Detailed)

### LangGraph StateGraph Flow

```
START
  |
  v
agent_node()
  - Current state: messages[], intent, user_context
  - LLM (Gemini 2.5 Flash, next key from round-robin)
  - Binds 4 tools: [search_schemes, web_search, check_eligibility, fetch_user_profile]
  - LLM decides if tools needed or responds directly
  |
  v
should_continue() conditional
  - Did the LLM emit tool calls?
  - YES → tools_node()
  - NO → END
  |
  v
tools_node()  (if tools called)
  - Executes each tool sequentially
  - Collects results as ToolMessages
  - Adds messages to state
  |
  v
agent_node() [LOOP]
  - LLM sees tool results
  - Decides: call more tools OR respond to user
  |
  v
(on final response)
  |
  v
END
  - Final message returned to webhook handler
  - Sent to user via Twilio WhatsApp
```

### The 4 Agent Tools

| Tool | Purpose | Data Source | When Used |
|------|---------|-------------|-----------|
| **search_schemes** | Find scheme details, eligibility rules, application process | Qdrant vector DB (hybrid search: semantic + BM25) | User asks about specific scheme (e.g., "What is PMAY-U?") |
| **web_search** | Search Google for current/real-time info (updated policies, recent news, deadline changes) | Google Serper API (top 5 results) | KB doesn't have current answer (e.g., "What changed in PM-JAY 2024?") |
| **check_eligibility** | Verify income-based eligibility for schemes (hardcoded rules: PMAY-U EWS/LIG/MIG, PM-JAY, PMJDY) | Local eligibility rules in function | User asks "Am I eligible for X?" with income info |
| **fetch_user_profile** | Retrieve user's prior context (name, state, income, language) from session history | Supabase Postgres or in-memory cache | Personalized follow-ups (e.g., "What schemes fit YOUR state?") |

### Session Management

User sessions are stored in two layers:
1. **In-Memory Cache** (fast lookup, development-friendly)
2. **Supabase Postgres** (persistent, for analytics and multi-device continuity)

When `fetch_user_profile` is called:
- Check memory cache first (if found, return)
- Query Supabase `user_sessions` table
- Cache result in memory for subsequent calls
- Return user profile dict with: `{name, state, income, ...}`

### Round-Robin Gemini API Key Rotation

Because rate limits can block a single key, we rotate across 6 keys using `itertools.cycle()`:

```python
API_KEYS = [
  settings.GEMINI_API_KEY1,
  settings.GEMINI_API_KEY2,
  settings.GEMINI_API_KEY3,
  settings.GEMINI_API_KEY4,
  settings.GEMINI_API_KEY5,
  settings.GEMINI_API_KEY6,
]

gemini_key_cycle = itertools.cycle(API_KEYS)

def get_next_gemini_llm():
    next_key = next(gemini_key_cycle)  # KEY1 → KEY2 → ... → KEY6 → KEY1
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=next_key,
        temperature=0.7,
        max_tokens=500,
    )
```

Every time the agent calls `get_next_gemini_llm()`, it rotates to the next key, automatically balancing
load and providing fallback if one key hits quota.
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
