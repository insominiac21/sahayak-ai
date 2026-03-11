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

### Why Both Sarvam AI and Gemini?

Sarvam AI and Gemini serve **completely different roles** — they are complementary, not redundant:

| Task | Service | Why This One? |
|------|---------|---------------|
| Voice → text (STT) | **Sarvam AI** (Saaras v3) | Purpose-built for Indian languages — best ASR accuracy for Hindi, Tamil, Telugu, etc. |
| Language detection + translation | **Sarvam AI** (Mayura) | Native support for 10+ Indian languages with auto-detection |
| Understanding queries, reasoning, tool-calling, answer generation | **Gemini 2.5 Flash** | General-purpose LLM with function calling — Sarvam does not offer a reasoning LLM |

**Sarvam AI** handles the **multilingual I/O layer** (speech and translation), while **Gemini** handles the **intelligence layer** (reading retrieved chunks, deciding which tool to call, generating cited answers). Sarvam doesn't have a general-purpose LLM that can do RAG-based Q&A or tool orchestration — that's exactly what Gemini provides.

---

## Sample Retrieval Outputs (Multi-Language)

Tested with queries in 8 Indian languages against the 68 ingested scheme vectors:

```
[English] "pension for elderly women"
  → score=0.8574 | scheme_4.md | ₹5 lakh family floater cover, cashless hospitalization...
  → score=0.8171 | scheme_2.md | PMJDY (Pradhan Mantri Jan-Dhan Yojana)...
  → score=0.8156 | scheme_5.md | NSAP official portal (Eligibility + assistance)...

[Hindi] "बुज़ुर्गों के लिए पेंशन योजना"
  → score=0.8549 | scheme_1.md | All participating States/UTs...
  → score=0.8216 | scheme_6.md | Early closure allowed only in specific conditions...
  → score=0.8133 | scheme_6.md | Deposit rules, minimum yearly deposit requirement...

[Tamil] "முதியோருக்கான ஓய்வூதியம்"
  → score=0.9022 | scheme_8.md | at least 51% shareholding and control...
  → score=0.8897 | scheme_7.md | PFRDA FAQ — Atal Pension Yojana...
  → score=0.8478 | scheme_7.md | Checklist (Exact KYC may vary by bank)...

[Telugu] "రైతులకు ఆర్థిక సహాయం"
  → score=0.8708 | scheme_4.md | SECC 2011-based entitled families...
  → score=0.8588 | scheme_6.md | Early closure allowed only in specific conditions...

[Bengali] "গরীব পরিবারের জন্য সরকারি যোজনা"
  → score=0.8575 | scheme_6.md | Early closure allowed only in specific conditions...
  → score=0.8532 | scheme_2.md | Pan-India (available through participating banks)...

[Marathi] "शेतकऱ्यांसाठी आर्थिक मदत"
  → score=0.8264 | scheme_8.md | Stand-Up India scheme to facilitate bank loans...
  → score=0.8182 | scheme_6.md | Deposit rules, minimum yearly deposit requirement...

[Kannada] "ಬಡವರ ಕುಟುಂಬಗಳಿಗೆ ಆರೋಗ್ಯ ವಿಮೆ"
  → score=0.8982 | scheme_2.md | PMJDY (Pradhan Mantri Jan-Dhan Yojana)...
  → score=0.8820 | scheme_5.md | NSAP local verification details...

[Malayalam] "ദരിദ്രരായ കുടുംബങ്ങള്‍ക്ക് സഹായം"
  → score=0.8836 | scheme_6.md | One account per girl child, maximum two per family...
  → score=0.8444 | scheme_2.md | DBT linkage / JAM pipeline...
```

> **Note:** Current v1 uses deterministic SHA-256 dummy embeddings (384-dim). Scores reflect cosine similarity between hash-based vectors — semantic accuracy will improve significantly once Sarvam embedding API is integrated in v2.

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

| # | Scheme | What It Does |
|---|--------|-------------|
| 1 | **PMAY-U 2.0** (Pradhan Mantri Awas Yojana – Urban) | Affordable housing assistance for urban EWS/LIG/MIG families |
| 2 | **PMJDY** (Pradhan Mantri Jan-Dhan Yojana) | Zero-balance bank accounts + financial inclusion |
| 3 | **PMUY** (Pradhan Mantri Ujjwala Yojana) | Free LPG connections for BPL households |
| 4 | **Ayushman Bharat PM-JAY** | ₹5 lakh health insurance for eligible families |
| 5 | **NSAP** (National Social Assistance Programme) | Pensions for elderly, widows, disabled |
| 6 | **Sukanya Samriddhi Yojana (SSY)** | Savings scheme for girl child education/marriage |
| 7 | **APY** (Atal Pension Yojana) | Guaranteed pension for unorganized sector workers |
| 8 | **Stand-Up India** | ₹10L–₹1Cr bank loans for SC/ST/women entrepreneurs |

### How Were the Data Cards Created?

Each Markdown file in `data/seed_docs/` was **manually curated** by scraping official government portals and PDFs:

| Source Portal | Schemes Covered |
|---------------|----------------|
| `pmay-urban.gov.in`, `pmaymis.gov.in` | PMAY-U 2.0 |
| `pmjdy.gov.in` | PMJDY |
| `pmuy.gov.in` | PMUY / Ujjwala 2.0 |
| `nha.gov.in/PM-JAY`, `mohfw.gov.in` | Ayushman Bharat PM-JAY |
| `nsap.gov.in`, `nsap.dord.gov.in` | NSAP |
| `dea.gov.in`, `pib.gov.in` | Sukanya Samriddhi Yojana |
| `pfrda.org.in`, `jansuraksha.gov.in` | Atal Pension Yojana |
| `standupmitra.in`, `ncgtc.in` | Stand-Up India |

Every card follows a **uniform structure** — `Overview → Eligibility → Official Sources → Checklist → Sections` — so the RAG chunker can split them consistently. The eligibility section is structured with State/Age/Income/Category fields to power the eligibility-check tool.

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
