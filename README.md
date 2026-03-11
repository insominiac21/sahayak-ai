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
**User Input → Language Detected → Translated to English → RAG Retrieval → Response in Same Language**

```
==========================================================================================
  End-to-End Pipeline Test — Realistic Helpline Queries
  Input → Detect Language → Translate to EN → Retrieve → Reply in Same Language
==========================================================================================

[English] — 67-year-old asking about pension eligibility
  INPUT   : My name is Ramesh, I am 67 years old and my monthly income is around
            4000 rupees. I live in Bihar and I don't have any pension right now.
            Am I eligible for any government pension scheme? What documents do I need?
  DETECTED: English (en-IN)
  ENGLISH : (same as input)
  RETRIEVED: scheme_3.md, scheme_1.md, scheme_5.md (top score=0.8603)
  RESPONSE: Based on scheme_3.md: Checklist — exact fields may vary slightly by
            distributor/State; this is the common minimum...

[Hindi] — Woman asking about housing scheme with family income
  INPUT   : मेरा नाम सुनीता है, मैं उत्तर प्रदेश में रहती हूँ। मेरे पति की सालाना आय
            लगभग 2.5 लाख रुपये है और हमारे पास अपना घर नहीं है। क्या हम प्रधानमंत्री
            आवास योजना के लिए पात्र हैं? आवेदन के लिए कौन कौन से कागज़ात चाहिए?
  DETECTED: Hindi (hi-IN)
  ENGLISH : My name is Sunita, I live in Uttar Pradesh. My husband has a salary
            of around 2.5 lakhs per annum and we do not own a house. Are we
            eligible for PMAY? What documents are needed to apply?
  RETRIEVED: scheme_2.md, scheme_6.md, scheme_4.md (top score=0.8589)
  RESPONSE: योजना_2 पर आधारित — सूची: सटीक KYC/क्षेत्र बैंक पर निर्भर करते हैं,
            सहायक के लिए इसे अपना न्यूनतम अपेक्षित...

[Tamil] — Father asking about Sukanya Samriddhi for daughter
  INPUT   : என் பெயர் முருகன், எனக்கு 5 வயது மகள் இருக்கிறாள். நான் ஒரு தனியார்
            நிறுவனத்தில் வேலை செய்கிறேன், மாத சம்பளம் 15000 ரூபாய். என் மகளுக்கு
            சுகன்யா சம்ரிதி கணக்கு திறக்க என்ன ஆவணங்கள் தேவை? குறைந்தபட்ச டெபாசிட் எவ்வளவு?
  DETECTED: Tamil (ta-IN)
  ENGLISH : My name is Murugan, I have a 5-year-old daughter. I work in a private
            company, salary Rs 15000/month. What documents are needed to open a
            Sukanya Samriddhi account? What is the minimum deposit?
  RETRIEVED: scheme_1.md, scheme_6.md, scheme_3.md (top score=0.8211)
  RESPONSE: scheme_1 அடிப்படையாகக் கொண்டது — சரிபார்ப்பு பட்டியல்:
            மாநில/ULB மற்றும் நீங்கள் எந்த செங்குத்து நிலைக்குக்...

[Telugu] — SC farmer asking about Stand-Up India loan
  INPUT   : నా పేరు వెంకటేష్, నేను ఆంధ్రప్రదేశ్‌లో చిన్న రైతుని. నా వార్షిక ఆదాయం
            1.5 లక్షలు. నేను SC కేటగిరీకి చెందినవాడిని. Stand-Up India లోన్ కోసం
            అప్లై చేయాలనుకుంటున్నాను. ఎంత లోన్ వస్తుంది? ఏ డాక్యుమెంట్స్ కావాలి?
  DETECTED: Telugu (te-IN)
  ENGLISH : My name is Venkatesh, I am a small farmer from AP. Annual income 1.5L.
            I belong to SC category. I want to apply for Stand-Up India loan.
            How much loan can I get? What documents are needed?
  RETRIEVED: scheme_1.md, scheme_2.md, scheme_7.md (top score=0.8664)
  RESPONSE: స్కీమ్_1 ఆధారంగా — అర్హత: పాల్గొనే అన్ని రాష్ట్రాలు/యూటీలు
            (అమలు రాష్ట్రాలు/యూటీలు/యుఎల్‌బిలు/పిఎల్‌ఐల ద్వారా)...

[Bengali] — Woman asking about Ayushman Bharat for mother-in-law's hospitalization
  INPUT   : আমার নাম ফাতিমা, আমি পশ্চিমবঙ্গে থাকি। আমার পরিবারে ৫ জন সদস্য আছে,
            স্বামীর বার্ষিক আয় ১.৮ লাখ টাকা। আমার শাশুড়ির হাসপাতালে ভর্তি হওয়া দরকার।
            আয়ুষ্মান ভারত কার্ড কীভাবে বানাবো? ক্যাশলেস চিকিৎসা কি পাওয়া যাবে?
  DETECTED: Bengali (bn-IN)
  ENGLISH : My name is Fatima, I live in West Bengal. 5 members in family, husband
            earns 1.8L/year. Mother-in-law needs hospitalization. How to make
            Ayushman Bharat card? Is cashless treatment available?
  RETRIEVED: scheme_1.md, scheme_8.md, scheme_3.md (top score=0.8903)
  RESPONSE: স্কিম_1-এর উপর ভিত্তি করে — কার্যকরী সংস্থা/ইউএলবি দ্বারা জিজ্ঞাসা
            করা হিসাবে যাচাইয়ের জন্য প্রয়োজনীয় মৌলিক আবেদন...

[Kannada] — Widow asking about pension eligibility
  INPUT   : ನನ್ನ ಹೆಸರು ಲಕ್ಷ್ಮಿ, ನಾನು ವಿಧವೆ, ವಯಸ್ಸು 55 ವರ್ಷ. ನನ್ನ ಮಕ್ಕಳು ಕೂಲಿ ಕೆಲಸ
            ಮಾಡುತ್ತಾರೆ. ನನಗೆ ಯಾವುದೇ ಆದಾಯ ಇಲ್ಲ. ವಿಧವಾ ಪಿಂಚಣಿ ಯೋಜನೆಗೆ ನಾನು ಅರ್ಹಳಾ?
            ಎಷ್ಟು ಹಣ ಸಿಗುತ್ತದೆ ಮತ್ತು ಎಲ್ಲಿ ಅರ್ಜಿ ಸಲ್ಲಿಸಬೇಕು?
  DETECTED: Kannada (kn-IN)
  ENGLISH : My name is Lakshmi, I am a widow, age 55. My children do coolie work.
            I don't have any income. Am I eligible for widow pension scheme?
            How much money will I get and where to apply?
  RETRIEVED: scheme_4.md, scheme_5.md, scheme_7.md (top score=0.8336)
  RESPONSE: ಸ್ಕೀಮ್_4 ಆಧಾರಿತ — ಆಯುಷ್ಮಾನ್ ಭಾರತ್ ಪಿ.ಎಂ.-ಜೆ.ಎ.ವೈ.
            (ಪ್ರಧಾನ ಮಂತ್ರಿ ಜನ ಆರೋಗ್ಯ ಯೋಜನೆ)...

[Gujarati] — BPL family asking about Ujjwala LPG scheme
  INPUT   : મારું નામ રાધાબેન છે, હું ગુજરાતના એક ગામમાં રહું છું. અમારી પાસે BPL
            કાર્ડ છે અને અમે હજી સુધી LPG કનેક્શન લીધું નથી. ઉજ્જવલા યોજનામાં ફ્રી
            ગેસ કનેક્શન મળશે? KYC માટે શું શું જોઈએ? ક્યાં અરજી કરવી?
  DETECTED: Gujarati (gu-IN)
  ENGLISH : My name is Radhaben, I live in a village in Gujarat. We have a BPL card
            and haven't taken LPG connection yet. Will we get free gas under Ujjwala?
            What KYC documents needed? Where to apply?
  RETRIEVED: scheme_5.md, scheme_4.md (top score=0.8309)
  RESPONSE: યોજના_5 પર આધારિત — NSAP (રાષ્ટ્રીય સામાજિક સહાય કાર્યક્રમ)...

[Malayalam] — Asking about Jan Dhan zero-balance account
  INPUT   : എന്റെ പേര് അനിത, ഞാൻ കേരളത്തിൽ താമസിക്കുന്നു. എനിക്ക് ബാങ്ക് അക്കൗണ്ട്
            ഇല്ല. ജൻ ധൻ യോജനയിൽ സീറോ ബാലൻസ് അക്കൗണ്ട് തുറക്കാൻ ആധാർ കാർഡ് മാത്രം
            മതിയോ? എന്തെല്ലാം ആനുകൂല്യങ്ങൾ ലഭിക്കും? ഡെബിറ്റ് കാർഡ് കിട്ടുമോ?
  DETECTED: Malayalam (ml-IN)
  ENGLISH : I am Anitha, from Kerala. I don't have a bank account. Is Aadhaar card
            enough to open a zero balance account under Jan Dhan Yojana? What
            benefits will I get? Will I get a debit card?
  RETRIEVED: scheme_8.md, scheme_3.md, scheme_5.md (top score=0.8496)
  RESPONSE: സ്കീം_8 അടിസ്ഥാനമാക്കി — സ്റ്റാൻഡ്-അപ്പ് ഇന്ത്യ: ₹10 ലക്ഷം
            മുതൽ ₹1 കോടി വരെ ബാങ്ക് വായ്പ...

[Punjabi] — Auto-rickshaw driver asking about Atal Pension
  INPUT   : ਮੇਰਾ ਨਾਮ ਗੁਰਪ੍ਰੀਤ ਹੈ, ਮੈਂ ਪੰਜਾਬ ਵਿੱਚ ਆਟੋ ਰਿਕਸ਼ਾ ਚਲਾਉਂਦਾ ਹਾਂ। ਮੇਰੀ ਉਮਰ
            30 ਸਾਲ ਹੈ ਅਤੇ ਮੇਰੇ ਕੋਲ ਕੋਈ ਪੈਨਸ਼ਨ ਨਹੀਂ ਹੈ। ਅਟਲ ਪੈਨਸ਼ਨ ਯੋਜਨਾ ਵਿੱਚ ਮਹੀਨੇ
            ਦਾ ਕਿੰਨਾ ਯੋਗਦਾਨ ਦੇਣਾ ਪਵੇਗਾ? 60 ਸਾਲ ਬਾਅਦ ਕਿੰਨੀ ਪੈਨਸ਼ਨ ਮਿਲੇਗੀ?
  DETECTED: Punjabi (pa-IN)
  ENGLISH : My name is Gurpreet, I drive an auto-rickshaw in Punjab. I am 30 years
            old and don't have a pension. How much monthly contribution for Atal
            Pension Yojana? How much pension after 60?
  RETRIEVED: scheme_3.md, scheme_4.md, scheme_7.md (top score=0.8201)
  RESPONSE: ਸਕੀਮ_3 'ਤੇ ਆਧਾਰਿਤ — ਪੀਐੱਮਯੂਵਾਈ (ਪ੍ਰਧਾਨ ਮੰਤਰੀ ਉਜਵਲਾ ਯੋਜਨਾ) /
            ਉਜਵਲਾ 2.0...

[Odia] — Son asking about disability pension for father
  INPUT   : ମୋ ନାଁ ସୁରେଶ, ମୁଁ ଓଡ଼ିଶାରେ ରହେ। ମୋ ବାପାଙ୍କ ବୟସ 72 ବର୍ଷ ଏବଂ ସେ ଶାରୀରିକ
            ଭାବେ ଅକ୍ଷମ। ସେ କୌଣସି ସରକାରୀ ପେନ୍‌ସନ ପାଉନାହାନ୍ତି। NSAP ଯୋଜନାରେ ବିକଳାଙ୍ଗ
            ପେନ୍‌ସନ ପାଇଁ କିପରି ଆବେଦନ କରିବା? କେତେ ଟଙ୍କା ମିଳିବ?
  DETECTED: Odia (od-IN)
  ENGLISH : My name is Suresh, I live in Odisha. My father is 72 years old and
            physically handicapped. He doesn't get any government pension. How to
            apply for disability pension under NSAP? How much money will he get?
  RETRIEVED: scheme_7.md, scheme_4.md (top score=0.8899)
  RESPONSE: ସ୍କିମ୍_7 ଉପରେ ଆଧାରିତ — ଯୋଗ୍ୟତା: ସମଗ୍ର ଭାରତ (ବ୍ୟାଙ୍କ ଏବଂ ଭାରତ
            ପୋଷ୍ଟ / ଡାକଘର ସଞ୍ଚୟ ଖାତା ମାଧ୍ୟମରେ)...

[Marathi] — Woman entrepreneur asking about Stand-Up India loan
  INPUT   : माझे नाव प्रिया आहे, मी पुण्यात राहते. मला एक छोटा कपड्यांचा व्यवसाय
            सुरू करायचा आहे. माझ्याकडे 3 लाख रुपये स्वतःचे आहेत. Stand-Up India
            योजनेतून बँक लोन मिळू शकते का? किती लोन मिळेल? कुठल्या बँकेत जायचे?
  DETECTED: Marathi (mr-IN)
  ENGLISH : My name is Priya, I live in Pune. I want to start a small clothing
            business. I have Rs 3 lakhs of my own. Can I get a bank loan through
            Stand-Up India? How much loan? Which bank to go to?
  RETRIEVED: scheme_4.md, scheme_8.md, scheme_2.md (top score=0.8567)
  RESPONSE: योजना_4 वर आधारित — SECC 2011 आधारित पात्र कुटुंबे
            (योजनेच्या रचनेनुसार तपशील)...

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
sahayak-ai/
├── data/seed_docs/             # 8 curated Markdown scheme documents
├── sarvamai/
│   ├── .env.example            # Environment template
│   ├── scripts/
│   │   ├── ingest.py           # Chunk + embed docs → Qdrant
│   │   ├── eval.py             # Offline evaluation harness
│   │   ├── ping_test.py        # Health-check all API keys
│   │   └── results/            # Detailed JSON test outputs
│   │       ├── e2e_pipeline.json
│   │       ├── multilang_retrieval.json
│   │       ├── retrieval_basic.json
│   │       └── sarvam_translation.json
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
│       │   │   ├── embeddings.py        # Gemini embedding-001 (3072-dim)
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
