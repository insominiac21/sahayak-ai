# Sahayak AI — System Architecture

## Overview

Sahayak AI is a WhatsApp-first, multilingual RAG assistant for Indian government schemes.
Users interact via WhatsApp (text or voice) in any Indian language. The system transcribes,
translates, retrieves relevant scheme information, runs tool-based logic, and replies in
the user's language — all within a single message round-trip.

---

## Architecture Diagram

```
┌─────────────────┐
│   WhatsApp User  │
│  (Text / Voice)  │
└────────┬────────┘
         │
         v
┌─────────────────┐     ┌─────────────────┐
│  Twilio Gateway  │────►│  FastAPI Server  │
└─────────────────┘     └────────┬────────┘
                               │
              ┌────────────────┼──────────────┐
              v              v              v
     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │ Sarvam STT │  │  Sarvam     │  │  Qdrant     │
     │ (Saaras v3)│  │ Translate  │  │ Vector DB  │
     └────────────┘  └────────────┘  └────────────┘
              │              │              │
              └──────────────┼──────────────┘
                             v
                    ┌─────────────────┐
                    │ Gemini 2.5 Flash │
                    │ (Tool Calling)   │
                    └───────┬─────────┘
                       ┌────┴────┐
                       v       v
              ┌─────────┐ ┌─────────┐
              │Eligibil.│ │Checklist│
              │  Tool   │ │  Tool   │
              └─────────┘ └─────────┘
                       │       │
                       v       v
                    ┌─────────────────┐
                    │   Supabase       │
                    │   (Postgres)     │
                    └─────────────────┘
```

---

## Component Details

### 1. Channel Layer (Twilio WhatsApp)

- **Webhook endpoint**: `POST /api/v1/webhooks/twilio/webhook`
- **Immediate ACK**: Returns 200 OK instantly to Twilio, processes message in a FastAPI BackgroundTask
- **Media handling**: Downloads voice note audio from Twilio media URL for STT
- **Reply**: Sends response back via Twilio REST API (TODO: wire up in v2)

### 2. Audio Pipeline (Sarvam AI)

#### Speech-to-Text
- **Model**: Sarvam Saaras v3
- **SDK**: `sarvamai` Python package
- **Modes**: transcribe, translate, verbatim, transliterate, codemix
- **Languages**: 10+ Indian languages auto-detected
- **Flow**: Download audio bytes → `client.speech_to_text.transcribe()` → text + language_code

#### Translation
- **API**: Sarvam Text Translate (Mayura model)
- **Auto-detection**: `source_language_code="auto"` detects input language
- **Bidirectional**: User language → English (for processing) → User language (for reply)
- **Flow**: `client.text.translate(input=text, source_language_code="auto", target_language_code=target)`

### 3. RAG Pipeline

#### Offline Ingestion (`scripts/ingest.py`)
1. Read 8 curated Markdown scheme docs from `data/seed_docs/`
2. Chunk by paragraphs (max 512 chars per chunk)
3. Generate embeddings via Google `gemini-embedding-001` (3072-dim)
4. Create Qdrant collection with `VectorParams(size=3072, distance=Cosine)`
5. Upsert `PointStruct` objects with payload: `{text, source}` (source = scheme name, e.g. "PMAY-U 2.0")
6. Result: 68 vectors across 8 schemes

#### Online Retrieval
- **Method**: `qdrant_client.query_points(query=vector, limit=top_k)`
- **SDK version**: qdrant-client v1.16.2 (uses `query_points`, not deprecated `search`)
- **Embedding**: Same `gemini-embedding-001` model used at query time for consistency
- **Returns**: Scored points with text chunk + scheme name

### 4. LLM Layer (Google Gemini)

#### Round-Robin Client (`gemini_client.py`)
- Loads up to 6 API keys from `GEMINI_API_KEY1..GEMINI_API_KEY6`
- Creates a `genai.Client` per key
- Thread-safe rotation with `threading.Lock`
- **Auto-failover**: On 429 (RESOURCE_EXHAUSTED) or 400 (INVALID/EXPIRED), skips to next key
- Tries all keys before raising `RuntimeError`
- Model: `gemini-2.5-flash`

#### Tool Orchestrator (`orchestrator.py`)
- Configures Gemini function calling with two tools: `check_eligibility`, `generate_checklist`
- `ToolConfig(function_calling_config=FunctionCallingConfig(mode="AUTO"))`
- Gemini decides which tool to call based on the query
- Pipeline: translate → Gemini tool call → translate back

### 5. Tools (Deterministic)

#### Eligibility Tool
- Input: user profile (age, income, category, state, etc.)
- Output: `{eligible: bool, reasons: [], missing_fields: []}`
- Rule-based, no LLM involved in the decision

#### Checklist Tool
- Input: scheme_id + user profile
- Output: `{documents: [], steps: [], official_links: []}`
- Returns concrete document requirements and application steps

### 6. Data Stores

#### Qdrant Cloud (Vector DB)
- Cluster: GCP europe-west3
- Collection: `schemes` (3072-dim, cosine distance)
- 68 points from 8 scheme documents
- Used for semantic retrieval at query time

#### Supabase Postgres
- Users, sessions, message logs, citations, eval runs
- Connection via `POSTGRES_URL` env var
- SQLAlchemy models in `models/`, repositories in `repositories/`

---

## Request Flow (Step by Step)

```
1. User sends WhatsApp message (text or voice note)
2. Twilio forwards POST to /api/v1/webhooks/twilio/webhook
3. Webhook returns 200 OK immediately
4. BackgroundTask starts:
   a. If voice note: download audio → Sarvam STT → text
   b. Detect language + translate to English (Sarvam)
   c. Embed query → search Qdrant → get top-K chunks
   d. Pass query + chunks to Gemini Tool Orchestrator
   e. Gemini decides: call eligibility_tool or checklist_tool (or answer directly)
   f. Generate answer with citations
   g. Translate answer back to user's language (Sarvam)
   h. Send reply via Twilio WhatsApp API
5. Log interaction to Postgres
```

---

## Design Principles

| Principle | Implementation |
|-----------|---------------|
| **No OpenAI/Groq** | 100% Gemini for LLM, Sarvam for STT/translation |
| **No persistent audio** | Voice notes transcribed on-the-fly, never stored |
| **Ephemeral docs** | Scheme docs are curated Markdown, committed to repo |
| **Lean infra** | Only Postgres + Vector DB, no Redis/S3/queues |
| **Idempotent webhook** | Background processing, immediate ACK |
| **Key rotation** | Round-robin across 6 Gemini keys with auto-skip |
| **Deterministic tools** | Eligibility/checklist use rules, not LLM |

---

## File Reference

| File | Purpose |
|------|---------|
| `sarvamai/src/app/main.py` | FastAPI app entrypoint |
| `sarvamai/src/app/core/config.py` | Environment loading, Settings class |
| `sarvamai/src/app/api/v1/endpoints/webhooks_twilio.py` | WhatsApp webhook handler |
| `sarvamai/src/app/services/llm/gemini_client.py` | Round-robin Gemini client |
| `sarvamai/src/app/services/audio/stt_sarvam.py` | Sarvam speech-to-text |
| `sarvamai/src/app/services/audio/translate_sarvam.py` | Sarvam translation |
| `sarvamai/src/app/services/rag/qdrant_client.py` | Qdrant connection singleton |
| `sarvamai/src/app/services/rag/retrieve.py` | Vector retrieval |
| `sarvamai/src/app/services/agent/orchestrator.py` | Gemini tool routing |
| `sarvamai/src/app/services/agent/eligibility_tool.py` | Eligibility checker |
| `sarvamai/src/app/services/agent/checklist_tool.py` | Document checklist |
| `sarvamai/scripts/ingest.py` | Offline ingestion to Qdrant |
| `sarvamai/scripts/ping_test.py` | API key health check |
| `sarvamai/scripts/eval.py` | Offline eval harness |

---

## Future (v2)

- Wire Twilio reply (send message back)
- Add conversation memory (multi-turn)
- Hybrid search (BM25 + embeddings + reranking)
- Rate limiting and caching
- Observability (structured logs, traces)
- Deploy on Render/Railway
