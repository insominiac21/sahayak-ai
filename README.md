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

## End-to-End Pipeline Output (11 Languages)

Real output from `test_e2e_pipeline.py` — realistic helpline-style queries showing the full flow:  
**User Input → Language Detected → Translated to English → RAG Retrieval → Gemini Answer → Response in Same Language**

```
==========================================================================================
  End-to-End Pipeline Test — Realistic Helpline Queries (Gemini-powered)
  Input → Detect Lang → Translate → Retrieve → Gemini Answer → Translate Back
==========================================================================================

[English] — 67-year-old asking about pension eligibility
  INPUT   : My name is Ramesh, I am 67 years old and my monthly income is around
            4000 rupees. I live in Bihar and I don't have any pension right now.
            Am I eligible for any government pension scheme? What documents do I need?
  DETECTED: English (en-IN)
  ENGLISH : (same as input)
  RETRIEVED: NSAP (National Social Assistance Programme), APY (Atal Pension Yojana)
             (top score=0.7308)
  RESPONSE: Ramesh, being 67 years old, may be eligible for the Indira Gandhi
            National Old Age Pension Scheme (IGNOAPS) under NSAP, provided he
            belongs to a BPL household. Under IGNOAPS, he could receive ₹200 as
            central assistance (for ages 60-79). He might also be eligible for
            the Annapurna scheme (10kg food grains/month).

[Hindi] — Woman asking about housing scheme with family income
  INPUT   : मेरा नाम सुनीता है, मैं उत्तर प्रदेश में रहती हूँ। मेरे पति की सालाना आय
            लगभग 2.5 लाख रुपये है और हमारे पास अपना घर नहीं है। क्या हम प्रधानमंत्री
            आवास योजना के लिए पात्र हैं? आवेदन के लिए कौन कौन से कागज़ात चाहिए?
  DETECTED: Hindi (hi-IN)
  RETRIEVED: PMAY-U 2.0 (Pradhan Mantri Awas Yojana – Urban 2.0) (top score=0.7156)
  RESPONSE: जी हाँ, PMAY-U 2.0 के संदर्भ में, आप पात्र प्रतीत होते हैं। आपका
            पारिवारिक आय ₹2.5 लाख प्रति वर्ष है, इसलिए आप आर्थिक रूप से कमजोर
            वर्ग (ईडब्ल्यूएस) श्रेणी (₹3 लाख तक) के अंतर्गत आते हैं। आवेदन हेतु
            आधार/वर्चुअल ID, घोषणा पत्र (कोई पक्का घर नहीं), और BLC हेतु भूमि
            स्वामित्व प्रमाण आवश्यक।

[Tamil] — Father asking about Sukanya Samriddhi for daughter
  INPUT   : என் பெயர் முருகன், எனக்கு 5 வயது மகள் இருக்கிறாள்...
  DETECTED: Tamil (ta-IN)
  RETRIEVED: Sukanya Samriddhi Yojana (SSY) (top score=0.7884)
  RESPONSE: சுக்கான்யா செல்வதி கணக்கு தொடங்க — பிறப்புச் சான்றிதழ், அடையாளச் சான்று,
            முகவரி சான்று, ஆதார், PAN/Form 60 தேவை. 10 வயதுக்குள் கணக்கு
            தொடங்கலாம், வருமானக் கட்டுப்பாடு இல்லை.

[Telugu] — SC farmer asking about Stand-Up India loan
  INPUT   : నా పేరు వెంకటేష్... SC కేటగిరీ... Stand-Up India లోన్...
  DETECTED: Telugu (te-IN)
  RETRIEVED: Stand-Up India Scheme (top score=0.7608)
  RESPONSE: స్టాండ్-అప్ ఇండియా పథకం క్రింద, SC వ్యాపారవేత్తగా ₹10 లక్షల నుండి
            ₹1 కోటి వరకు రుణం. KYC, SC సర్టిఫికెట్, DPR, వ్యాపార ప్రణాళిక అవసరం.

[Bengali] — Woman asking about Ayushman Bharat
  INPUT   : আমার নাম ফাতিমা... আয়ুষ্মান ভারত কার্ড কীভাবে বানাবো?
  DETECTED: Bengali (bn-IN)
  RETRIEVED: Ayushman Bharat PM-JAY (top score=0.7524)
  RESPONSE: আয়ুষ্মান ভারত পিএম-জেএওয়াই-এ ₹5 লক্ষ/পরিবার/সাল নগদহীন বীমা। SECC
            2011 ভিত্তিক পাত্রতা। তালিকাভুক্ত হাসপাতালে নগদহীন চিকিৎসা উপলব্ধ।

[Kannada] — Widow asking about pension eligibility
  INPUT   : ನನ್ನ ಹೆಸರು ಲಕ್ಷ್ಮಿ, ನಾನು ವಿಧವೆ, ವಯಸ್ಸು 55...
  DETECTED: Kannada (kn-IN)
  RETRIEVED: NSAP (National Social Assistance Programme) (top score=0.7362)
  RESPONSE: ಇಂದಿರಾ ಗಾಂಧಿ ರಾಷ್ಟ್ರೀಯ ವಿಧವಾ ಪಿಂಚಣಿ ಯೋಜನೆ (IGNWPS) ಅಡಿ ಅರ್ಹ. 40-59
            ವಯಸ್ಸಿನ BPL ವಿಧವೆಯರಿಗೆ ₹300/ತಿಂಗಳು. ಪೋರ್ಟಲ್/CSC ಮೂಲಕ ಅರ್ಜಿ.

[Gujarati] — BPL family asking about Ujjwala LPG scheme
  INPUT   : મારું નામ રાધાબેન છે... BPL કાર્ડ છે... ઉજ્જવલા યોજના...
  DETECTED: Gujarati (gu-IN)
  RETRIEVED: PMUY (Pradhan Mantri Ujjwala Yojana) / Ujjwala 2.0 (top score=0.7505)
  RESPONSE: હા, PMUY/ઉજ્જવલા 2.0 હેઠળ LPG જોડાણ માટે પાત્ર. KYC: અરજીપત્રક,
            રાશન કાર્ડ/સ્વ-ઘોષણા, આધાર, સરનામા પુરાવો. નજીકના LPG distributor
            પર અરજી.

[Malayalam] — Asking about Jan Dhan zero-balance account
  INPUT   : എന്റെ പേര് അനിത... ജൻ ധൻ യോജന... സീറോ ബാലൻസ് അക്കൗണ്ട്...
  DETECTED: Malayalam (ml-IN)
  RETRIEVED: PMJDY (Pradhan Mantri Jan-Dhan Yojana) (top score=0.7157)
  RESPONSE: PMJDY പ്രകാരം സീറോ ബാലൻസ് BSBD അക്കൗണ്ട് + RuPay ഡെബിറ്റ് കാർഡ്
            (അപകട ഇൻഷുറൻസ് ഉൾപ്പെടെ). 6 മാസത്തിന് ശേഷം ക്രെഡിറ്റ്/ഓവർഡ്രാഫ്റ്റ്
            സൗകര്യം.

[Punjabi] — Auto-rickshaw driver asking about Atal Pension
  INPUT   : ਮੇਰਾ ਨਾਮ ਗੁਰਪ੍ਰੀਤ ਹੈ... ਅਟਲ ਪੈਨਸ਼ਨ ਯੋਜਨਾ...
  DETECTED: Punjabi (pa-IN)
  RETRIEVED: APY (Atal Pension Yojana) (top score=0.8047)
  RESPONSE: APY ਅਧੀਨ 18-40 ਉਮਰ ਯੋਗ. 60 ਸਾਲ ਬਾਅਦ ₹1,000-₹5,000/ਮਹੀਨਾ ਪੈਨਸ਼ਨ.
            ਬੱਚਤ ਖਾਤਾ ਜ਼ਰੂਰੀ, 1 ਅਕਤੂਬਰ 2022 ਤੋਂ ਟੈਕਸ ਦਾਤਾ ਅਯੋਗ.

[Odia] — Son asking about disability pension for father
  INPUT   : ମୋ ନାଁ ସୁରେଶ... ବାପାଙ୍କ ବୟସ 72... NSAP ବିକଳାଙ୍ଗ ପେନ୍‌ସନ...
  DETECTED: Odia (od-IN)
  RETRIEVED: NSAP (National Social Assistance Programme) (top score=0.7401)
  RESPONSE: IGNDPS (ଇନ୍ଦିରା ଗାନ୍ଧୀ ଦିବ୍ୟାଙ୍ଗ ପେନସନ) ଅଧୀନ ଯୋଗ୍ୟ. 18-79 ବୟସ,
            80%+ ଅକ୍ଷମତା, BPL ଘର ଆବଶ୍ୟକ.

[Marathi] — Woman entrepreneur asking about Stand-Up India loan
  INPUT   : माझे नाव प्रिया आहे... कपड्यांचा व्यवसाय... Stand-Up India...
  DETECTED: Marathi (mr-IN)
  RETRIEVED: Stand-Up India Scheme (top score=0.7612)
  RESPONSE: हो प्रिया, महिला उद्योजक म्हणून ₹10 लाख ते ₹1 कोटी कर्ज उपलब्ध.
            अनुसूचित बँकेत, पोर्टलद्वारे किंवा LDM मार्फत अर्ज. KYC, व्यवसाय
            योजना/DPR, स्थान/परवाने पुरावे आवश्यक.

==========================================================================================
  All 11 queries processed successfully!
==========================================================================================
```

> Retrieval uses Google `gemini-embedding-001` (3072-dim) for both ingestion and query-time embedding, with Qdrant cosine similarity. Gemini generates a cited answer from the retrieved context before back-translation to the user's language.
>
> Full JSON outputs with scores, retrieved chunks, and raw translations are in [`sarvamai/scripts/results/`](sarvamai/scripts/results/).

---

## Project Structure

```
whatsapp-RAG/
├── .gitignore
├── .python-version
├── main.py
├── pyproject.toml
├── README.md
├── render.yaml
├── requirements.txt
├── uv.lock
├── .vscode/
│   └── settings.json
├── data/
│   └── seed_docs/
│       ├── scheme_1.md
│       ├── scheme_2.md
│       ├── scheme_3.md
│       ├── scheme_4.md
│       ├── scheme_5.md
│       ├── scheme_6.md
│       ├── scheme_7.md
│       └── scheme_8.md
└── sarvamai/
  ├── .env
  ├── .env.example
  ├── ARCHITECTURE.md
  ├── BUILD_CHECKLIST.md
  ├── README.md
  ├── scripts/
  │   ├── eval.py
  │   ├── ingest.py
  │   ├── ping_test.py
  │   ├── send_twilio_test_message.py
  │   ├── test_audio_input.py
  │   ├── test_audio_to_answer.py
  │   ├── test_e2e_pipeline.py
  │   ├── test_multilang.py
  │   ├── test_retrieval.py
  │   ├── test_retrieval_quality.py
  │   ├── test_sarvam.py
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
      │   ├── message_log.py
      │   └── user.py
      ├── repositories/
      │   ├── message_log.py
      │   └── user.py
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
- **Semantic embeddings**: Google `gemini-embedding-001` (3072-dim) for both ingestion and retrieval

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
