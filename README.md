# Sahayak AI

> **WhatsApp-first, multilingual assistant for Indian government schemes.**
> Voice + text support in 10+ Indian languages. Built with Sarvam AI, Gemini, Qdrant, and Twilio.

---

## What It Does

Indian citizens can message a WhatsApp number (text or voice note) in any Indian language and get:

- **Scheme information** with source citations
- **Eligibility checks** based on their profile
- **Document checklists** with step-by-step application guidance
- **Automatic translation** — ask in Hindi, get answers in Hindi

Currently covers **8 government schemes** including PM-KISAN, PMJDY, PM-SVANidhi, Ayushman Bharat, NSAP pensions, MGNREGA, PM Ujjwala, and Atal Pension Yojana.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **LLM** | Google Gemini 2.5 Flash | Tool-calling, answer generation |
| **STT** | Sarvam AI (Saaras v3) | Voice note transcription (10+ Indian languages) |
| **Translation** | Sarvam AI (Mayura) | Auto language detection + translation |
| **Vector DB** | Qdrant Cloud | Semantic search over scheme documents |
| **Database** | Supabase (Postgres) | Users, sessions, message logs |
| **Channel** | Twilio WhatsApp API | Message receive/send |
| **Framework** | FastAPI + uvicorn | Async webhook server |
| **Package Manager** | uv | Fast Python dependency management |

---

## Project Structure

```
sahayak-ai/
├── data/seed_docs/             # 8 curated Markdown scheme documents
├── sarvamai/
│   ├── .env.example            # Environment template
│   ├── scripts/
│   │   ├── ingest.py           # Chunk + embed docs → Qdrant
│   │   ├── eval.py             # Offline evaluation harness
│   │   └── ping_test.py        # Health-check all API keys
│   └── src/app/
│       ├── main.py             # FastAPI entrypoint
│       ├── api/v1/endpoints/
│       │   └── webhooks_twilio.py  # WhatsApp webhook handler
│       ├── core/
│       │   └── config.py       # Env loading + Settings class
│       ├── services/
│       │   ├── llm/
│       │   │   └── gemini_client.py    # Round-robin Gemini with auto-failover
│       │   ├── audio/
│       │   │   ├── stt_sarvam.py       # Speech-to-text (Sarvam Saaras v3)
│       │   │   └── translate_sarvam.py # Translation (Sarvam Mayura)
│       │   ├── rag/
│       │   │   ├── qdrant_client.py    # Qdrant connection singleton
│       │   │   ├── ingest.py           # RAG ingestion pipeline class
│       │   │   └── retrieve.py         # Semantic retrieval
│       │   └── agent/
│       │       ├── orchestrator.py     # Tool routing via Gemini function calling
│       │       ├── eligibility_tool.py # Eligibility checker
│       │       └── checklist_tool.py   # Document checklist generator
│       ├── models/                     # SQLAlchemy models
│       ├── schemas/                    # Pydantic schemas
│       ├── repositories/              # DB access layer
│       └── utils/
│           └── logging.py
├── pyproject.toml
├── requirements.txt
└── .gitignore
```

---

## Quickstart

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- API keys for: Gemini, Sarvam AI, Qdrant Cloud, Supabase, Twilio

### 1. Clone and Install

```bash
git clone https://github.com/insominiac21/sahayak-ai.git
cd sahayak-ai
uv sync
```

### 2. Configure Environment

```bash
cp sarvamai/.env.example sarvamai/.env
# Edit sarvamai/.env with your actual API keys
```

### 3. Ingest Scheme Documents

```bash
python sarvamai/scripts/ingest.py
```

This chunks all 8 scheme Markdown files and upserts 68 vectors into Qdrant Cloud.

### 4. Start the Server

```bash
uv run uvicorn sarvamai.src.app.main:app --reload
```

The API runs at http://localhost:8000. Twilio webhook: POST /api/v1/webhooks/twilio/webhook

---

## How It Works

```
User (WhatsApp) ──► Twilio Webhook ──► FastAPI
                                         |
                    +--------------------+
                    v                    v
              Voice Note?            Text Message
                    |                    |
                    v                    |
          Sarvam STT (Saaras v3)        |
                    |                    |
                    +--------+-----------+
                             v
                   Sarvam Translation
                   (auto-detect → English)
                             |
                             v
                    Qdrant Vector Search
                    (top-K scheme chunks)
                             |
                             v
                   Gemini Tool Orchestrator
                   +---------+---------+
                   v                   v
            Eligibility Tool    Checklist Tool
                   +---------+---------+
                             v
                   Gemini Answer + Citations
                             |
                             v
                   Sarvam Translation
                   (English → user language)
                             |
                             v
                   Twilio Send Reply
```

### Key Design Decisions

- **Round-robin Gemini keys**: Up to 6 API keys with automatic rotation on 429/quota exhaustion
- **No OpenAI/Groq dependency**: Entire LLM layer runs on Gemini; STT/translation on Sarvam AI
- **Deterministic tools**: Eligibility and checklist use rule-based logic, not LLM hallucination
- **Immediate webhook ACK**: Returns 200 OK instantly, processes in background task
- **Dummy embeddings (v1)**: SHA-256 hash → 384-dim vectors (to be replaced with Sarvam embeddings)

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/webhooks/twilio/webhook | Twilio WhatsApp incoming message webhook |

---

## Scripts

| Script | Command | Description |
|--------|---------|-------------|
| Ingest | python sarvamai/scripts/ingest.py | Chunk scheme docs → embed → upsert to Qdrant |
| Ping | python sarvamai/scripts/ping_test.py | Verify all Gemini keys + Qdrant are alive |
| Eval | python sarvamai/scripts/eval.py | Offline evaluation harness |
| Retrieval | python sarvamai/scripts/test_retrieval.py | Test vector search against Qdrant |

---

## Covered Schemes

1. **PM-KISAN** — Direct income support for farmers
2. **PMJDY** — Financial inclusion (bank accounts)
3. **PM-SVANidhi** — Micro-loans for street vendors
4. **Ayushman Bharat (PMJAY)** — Health insurance (₹5L cover)
5. **NSAP** — Pensions for elderly, widows, disabled
6. **MGNREGA** — Rural employment guarantee
7. **PM Ujjwala Yojana** — Free LPG connections for BPL families
8. **Atal Pension Yojana** — Pension for unorganized sector workers

---

## Environment Variables

See sarvamai/.env.example for the full template.

| Variable | Service | Required |
|----------|---------|----------|
| GEMINI_API_KEY1..6 | Google Gemini | At least 1 |
| SARVAM_API_KEY | Sarvam AI (STT + Translation) | Yes |
| QDRANT_URL | Qdrant Cloud | Yes |
| QDRANT_API_KEY | Qdrant Cloud | Yes |
| TWILIO_ACCOUNT_SID | Twilio | Yes |
| TWILIO_AUTH_TOKEN | Twilio | Yes |
| TWILIO_WHATSAPP_NUMBER | Twilio | Yes |
| POSTGRES_URL | Supabase | Yes |

---

## License

MIT
