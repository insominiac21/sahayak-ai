# Phase 3: LangGraph Agentic AI Implementation Guide

## 🎯 Overview

**Phase 3** transforms Sahayak AI from a linear RAG pipeline into a **stateful, multi-agent system** using LangGraph.

### What Changed?

| Phase | Architecture | Capability | Memory |
|-------|--------------|-----------|--------|
| **Phase 1** | RAG (static retrieval) | Single-turn Q&A | None |
| **Phase 2** | RAG + Multi-turn context | Follow-ups, context injection | Session ephemeral |
| **Phase 3** | ✨ LangGraph agent + tools | Multi-step reasoning, tool use | Persistent (Postgres) |

---

## 🏗️ Architecture

### System Diagram

```
User WhatsApp Message
        ↓
[FastAPI Webhook - /api/v1/webhooks/twilio/webhook]
        ↓
Return 200 OK immediately (avoid 15s timeout)
        ↓
Background Task: process_and_send_response()
        ↓
[LangGraph Agent - langgraph_agent.py]
  ├─ Agent Node: LLM with tool bindings
  ├─ Tools Node: Execute search_schemes, check_eligibility, fetch_user_profile
  ├─ State: messages[], intent, user_context
  └─ Memory: PostgreSQL checkpointer (Supabase)
        ↓
[Tool Layer]
  ├─ search_schemes() → Qdrant + HF embeddings
  ├─ check_eligibility() → Income/age rules
  └─ fetch_user_profile() → Supabase session
        ↓
Send response via Twilio API
        ↓
✅ User receives answer
```

---

## 📂 Files

### New Files Created

1. **`langgraph_agent.py`** (Main agent brain)
   - State definition (AgentState)
   - Tool definitions (search_schemes, check_eligibility, fetch_user_profile)
   - Workflow graph (agent → tools → agent → end)
   - Postgres checkpointer setup
   - `run_agent()` helper function

2. **`webhooks_langgraph.py`** (FastAPI integration)
   - `/api/v1/webhooks/twilio/webhook` POST endpoint
   - Background task handling for 15s timeout avoidance
   - Twilio message sending
   - `/api/v1/webhooks/health` health check
   - `/api/v1/webhooks/test-agent` debug endpoint

### Updated Files

1. **`main.py`**
   - Added LangGraph router
   - Both Phase 2 and Phase 3 endpoints available simultaneously

2. **`pyproject.toml`**
   - Added: `langgraph`, `langchain`, `langchain-core`, `langchain-google-genai`, `psycopg-pool`

---

## 🔧 How It Works

### 1. Request Flow

```python
# User sends: "What is PMAY-U eligibility?"

# Step 1: Webhook receives message
POST /api/v1/webhooks/twilio/webhook
  Body: "What is PMAY-U eligibility?"
  From: +91XXXXXXXXXX

# Step 2: Send status & return 200 OK
send_twilio_reply("🕐 Processing...")
return 200 OK

# Step 3: Background task runs
background_tasks.add_task(
    _process_and_send_response,
    "What is PMAY-U eligibility?",
    "+91XXXXXXXXXX",
    {"state": "...", "income": "..."}
)

# Step 4: LangGraph agent processes
agent_response = run_agent(
    user_message="What is PMAY-U eligibility?",
    thread_id="+91XXXXXXXXXX",  # Each user gets persistent memory!
    user_context={...}
)

# Step 5: Agent reasoning
Agent Node:
  - LLM thinks: "User is asking about PMAY-U eligibility"
  - Calls: search_schemes("PMAY-U eligibility")
  
Tools Node:
  - search_schemes() queries Qdrant
  - Returns scheme details
  
Agent Node (again):
  - LLM synthesizes answer
  - Returns final response

# Step 6: Send via Twilio
send_twilio_reply(agent_response, user_phone)
```

### 2. Memory & Persistence

Each user has a **thread_id** = their WhatsApp phone number.

```python
config = {"configurable": {"thread_id": "+91XXXXXXXXXX"}}
final_state = agent_app.invoke(initial_state, config=config)
```

The **PostgreSQL checkpointer** (via Supabase) saves:
- Conversation history
- State at each step
- Tool call results
- Timestamps

Next time the user messages, the agent **recalls previous context**.

---

## 🛠️ Tools Available

### 1. `search_schemes(query: str) → str`

Searches Qdrant vector database for scheme information.

**Example:**
```python
search_schemes("PMAY-U eligibility requirements")
# Returns:
# [Scheme: PMAY-U]
# PMAY-U 2.0 provides housing assistance...EWS: up to ₹3L/year...
```

**Behind the scenes:**
- Uses HF Inference API to embed query (BGE-M3, 1024D)
- Queries Qdrant for top-4 chunks
- Formats results with scheme name + relevance score

### 2. `check_eligibility(scheme, income, age=None, state=None) → str`

Calculates eligibility based on income & demographics.

**Example:**
```python
check_eligibility("PMAY-U", income=250000)
# Returns:
# ✅ ELIGIBLE for PMAY-U: EWS (Economically Weaker Section) Category (₹0-₹3L)
```

**Supported schemes:**
- PMAY-U (income-based: EWS, LIG, MIG)
- PM-JAY (SECC 2011-based, not income)
- PMJDY (no income limit)
- Others with graceful fallback

### 3. `fetch_user_profile(user_id: str) → str`

Retrieves user's saved context from Supabase.

**Example:**
```python
fetch_user_profile("+91XXXXXXXXXX")
# Returns:
# User: Rajesh Kumar, State: Maharashtra, Income: ₹250000
```

---

## 🚀 Deployment on Render

### Environment Variables Required

Add to Render dashboard under **Environment**:

```
# Existing (from Phase 2)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=whatsapp:+14155552671
QDRANT_URL=https://...
QDRANT_API_KEY=...
HF_TOKEN=...
GOOGLE_API_KEY=...
SARVAM_API_KEY=...

# NEW (Phase 3)
SUPABASE_POSTGRES_URI=postgresql://user:password@host:5432/dbname
OPENAI_API_KEY=sk-...  (optional, fallback LLM)
```

### Postgres Connection Pool

The `PostgresSaver` uses a connection pool with max_size=10. For Render:

```
SUPABASE_POSTGRES_URI=postgresql://postgres:PASSWORD@db.REFERENCE.supabase.co:5432/postgres
```

**Connection limits:**
- Render free tier: usually allows 3-10 concurrent connections
- Our pool: max_size=10 is fine for modest traffic
- If hitting limits, reduce to max_size=5

### Deployment Steps

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run ingest to populate Qdrant (if needed)
python scripts/ingest.py

# 3. Deploy to Render
git push origin main  # Auto-deploys if connected to Render

# 4. Test health
curl https://your-app.onrender.com/health
# {"status": "ok"}

# 5. Test agent endpoint
curl -X POST "https://your-app.onrender.com/api/v1/webhooks/test-agent?message=What%20is%20PM-JAY"
```

---

## 🧪 Testing

### Local Testing

```python
from app.services.agent.langgraph_agent import run_agent

# Single turn
response = run_agent(
    "What is PMAY-U?",
    thread_id="test_user_123",
    user_context={"state": "Maharashtra"}
)
print(response)

# Multi-turn (bot remembers context)
response2 = run_agent(
    "Am I eligible with ₹250000 income?",
    thread_id="test_user_123",  # Same thread!
    user_context={"state": "Maharashtra", "income": 250000}
)
print(response2)
```

### Debug Endpoint

```bash
curl -X POST \
  "http://localhost:8000/api/v1/webhooks/test-agent?message=What%20is%20PM-JAY&user_id=test123"

# Response:
# {
#   "message": "What is PM-JAY",
#   "response": "PM-JAY is Ayushman Bharat..."
# }
```

### Webhook Testing (with Twilio emulator)

```bash
# Install ngrok
ngrok http 8000

# Point Twilio to: https://your-ngrok-url.ngrok.io/api/v1/webhooks/twilio/webhook

# Send test message via Twilio CLI or WhatsApp
```

---

## 🎯 Example Conversations

### Scenario 1: Scheme Search Only

```
User: "What is PMAY-U?"
├─ Agent routes to: search_schemes("PMAY-U")
├─ Returns: Housing scheme details...
└─ Response: "PMAY-U is a housing program..."
```

### Scenario 2: Eligibility Check

```
User: "I earn ₹250000/year. Can I get PMAY-U?"
├─ Agent routes to: check_eligibility("PMAY-U", 250000)
├─ Returns: "✅ ELIGIBLE for EWS"
└─ Response: "Yes! Your income qualifies for EWS category..."
```

### Scenario 3: Multi-Step (Synthesis)

```
User: "What's the best scheme for housing if I earn ₹2.5L?"
├─ Agent calls:
│  ├─ search_schemes("housing schemes income ₹2.5 lakh")
│  └─ check_eligibility("PMAY-U", 250000)
├─ Agent synthesizes both results
└─ Response: "PMAY-U is ideal for you (EWS). Covers up to ₹2.67L..."
```

### Scenario 4: Context Persistence

```
[Earlier in conversation]
User: "I'm from Maharashtra, income is ₹3L"
Agent: saves to thread memory

[Later]
User: "What schemes am I eligible for?"
Agent: recalls "I know this person is from Maharashtra, ₹3L income"
Agent: provides state-specific scheme recommendations
```

---

## ⚠️ Edge Cases & Error Handling

### Case 1: Tool Fails (Qdrant Down)

```python
try:
    search_results = qdrant.search(...)
except Exception as e:
    return "Error accessing scheme database: {str(e)}"
    # Agent receives error, synthesizes graceful response
```

### Case 2: Background Task Timeout

```python
# If background task takes >30 seconds:
# ✅ User gets status message immediately
# ✅ If processing completes, gets real answer
# ❌ If timeout, user gets error message
```

### Case 3: Supabase Connection Fails

```python
# Checkpointer initialization fails
# ✅ Agent still works (stateless fallback)
# ❌ Memory not persistent (new thread = no context)
```

**To prevent:** Add connection pooling monitoring, fallback to in-memory checkpointer.

---

## 🔍 Monitoring & Logs

### Log Statements to Watch

```
✅ ✅ LangGraph agent compiled successfully
✅ Supabase checkpointer initialized
🕐 Processing message from +91XXXXXXXXXX: "What is PMAY-U"?
🔧 search_schemes() called with query="PMAY-U eligibility"
✅ Generated response for +91XXXXXXXXXX: "PMAY-U is..."
✅ Sent reply to +91XXXXXXXXXX
```

### Error Logs

```
❌ Failed to setup checkpointer: Connection refused
❌ Error in agent_node: Missing 'content' in message
❌ Tool error search_schemes: Qdrant returned empty
```

---

## 🚪 Fallback Strategy (If Phase 3 breaks)

Both Phase 2 and Phase 3 run simultaneously:

```python
# Phase 2 endpoint (original)
POST /api/v1/webhooks/twilio/webhook

# Phase 3 endpoint (new)
POST /api/v1/webhooks/twilio/webhook  (same path!)
```

You can **switch back** by pointing Twilio to the original endpoint in `webhooks_twilio.py`.

---

## 🎓 Interview Talking Points

1. **"Multi-agent reasoning"** - Agent decides which tools to use and in what order
2. **"Persistent memory"** - Postgres checkpointer maintains conversation across sessions
3. **"Graceful degradation"** - If Qdrant fails, agent explains limitations and saves time
4. **"15-second timeout solved"** - Immediate acknowledgement + async background processing
5. **"Tool orchestration"** - Unified interface for search, calculate, fetch operations

---

## 📦 Dependency Overview

| Package | Purpose | Added in Phase 3 |
|---------|---------|-----------------|
| `langgraph` | Agent workflow engine | ✅ |
| `langchain-core` | Message types, tools API | ✅ |
| `langchain-google-genai` | Gemini LLM integration | ✅ |
| `langchain-openai` | OpenAI fallback LLM | ✅ |
| `psycopg-pool` | PostgreSQL connection pool | ✅ |
| `qdrant-client` | Vector search | Phase 1 |
| `google-genai` | Gemini LLM (direct API) | Phase 2 |
| `huggingface-hub` | HF Inference for embeddings | Phase 2 |

---

## 🔮 Future Enhancements

1. **Web Search Tool** - Add Serper/Tavily for real-time info
2. **Multi-language Support** - Auto-translate user queries
3. **Streaming Responses** - Real-time agent thoughts to user
4. **Tool Categorization** - Route to specialized sub-graphs
5. **Cost Tracking** - Monitor LLM tokens, tool usage per user

---

## 📞 Support

For issues:
1. Check logs: `SUPABASE_POSTGRES_URI` connectivity
2. Test endpoint: `/api/v1/webhooks/test-agent`
3. Verify Qdrant connection: `qdrant_client.collection_exists("schemes")`
4. Check Gemini API key: `google.generativeai.configure(api_key=...)`

---

**Phase 3 - LangGraph Implementation Complete!** 🚀
