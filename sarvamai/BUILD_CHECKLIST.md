# Sahayak AI Build & Deployment Checklist

## PHASE 1: PRODUCTION RAG PIPELINE ✅ COMPLETE

### 1.1 Data Setup ✅
- [x] Created `data/seed_docs/` with 8 government scheme markdown files
- [x] Implemented semantic markdown-aware chunking
- [x] Generated 40 high-quality semantic chunks (5 per scheme)
- [x] Extracted 8 metadata fields per chunk (scheme, category, benefits, eligibility, income_limit, chunk_type, source, text)

### 1.2 Embedding & Indexing ✅
- [x] Installed BAAI/BGE-M3 (1024D asymmetric embeddings)
- [x] Migrated from Gemini embeddings (3072D) to BGE-M3
- [x] Created Qdrant database schema with cosine similarity
- [x] Embedded 40 chunks → stored in Qdrant Cloud
- [x] Tested embedding quality on sample queries

### 1.3 Hybrid Search Layer ✅
- [x] Implemented BM25 sparse indexing (903-term vocabulary)
- [x] Built hybrid retriever: 60% dense (BGE-M3) + 40% sparse (BM25)
- [x] Normalized scores across dense/sparse dimensions
- [x] Tested on 8 queries; retrieved correct schemes consistently
- [x] Latency: ~400ms per hybrid search ✅

### 1.4 Cross-Encoder Reranking ✅
- [x] Loaded ms-marco-MiniLM-L-2-v2 cross-encoder (62MB, multilingual)
- [x] Implemented pairwise relevance scoring (query, document) → score
- [x] Built reranker that takes 20 candidates → 4 final chunks
- [x] Validated "Lost in the Middle" bias mitigation
- [x] Latency: ~200ms for 20→4 reranking ✅

### 1.5 Two-Stage Retrieval Pipeline ✅
- [x] Orchestrated complete pipeline: hybrid → reranking → results
- [x] Total latency: ~600ms (acceptable for WhatsApp's 5-min window)
- [x] Tested with representative queries across all 8 schemes
- [x] Verified metadata preservation through pipeline
- [x] Integrated with WhatsApp webhook handler

### 1.6 Health Checks & Validation ✅
- [x] Created `health_check.py` testing 7 critical services
- [x] Verified Qdrant connectivity (40 vectors loaded)
- [x] Verified BGE-M3 embeddings (1024D confirmed)
- [x] Verified BM25 sparse indexing (903 terms)
- [x] Verified cross-encoder loading (model weights OK)
- [x] Verified hybrid retriever (both stages operational)
- [x] Verified two-stage pipeline (full pipeline latency tested)
- [x] All services: ✅ GREEN

### 1.7 Documentation & Testing ✅
- [x] Updated README.md with Phase 1 section (600+ lines)
- [x] Documented architecture decisions (why each choice)
- [x] Created phase_1b_test.py (hybrid search benchmarks)
- [x] Created phase_1d_test.py (two-stage pipeline validation)
- [x] Added performance benchmarks (latency, quality scores)
- [x] Git commit f8338b9 pushed to main ✅

---

## PHASE 2: MULTI-TURN CONTEXT-AWARE CHATBOT 🔄 IN PROGRESS

### 2.1 Session Management ✅
- [x] Created `session_manager.py` (180+ lines)
- [x] Implemented UserSession dataclass
- [x] Implemented ConversationTurn dataclass
- [x] Built SessionManager class with:
  - [x] `get_or_create_session(phone_number, language)`
  - [x] `add_turn(session_id, user_message, bot_response, ...)`
  - [x] `get_context_for_follow_up(session_id)`
  - [x] `get_conversation_history(session_id)`
- [x] In-memory storage (Supabase schema creation pending)

### 2.2 Intent Classification ✅
- [x] Created `intent_classifier.py` (200+ lines)
- [x] Implemented 5 intent types:
  - [x] eligibility_check
  - [x] documents_needed
  - [x] how_to_apply
  - [x] benefits_details
  - [x] scheme_inquiry
- [x] Added multilingual patterns (English, Hindi, Tamil, Telugu)
- [x] Implemented `classify(query)` → (intent, confidence)
- [x] Implemented `extract_scheme(query)` → Optional[scheme_name]
- [x] Implemented `is_follow_up(query, context)` → bool

### 2.3 Query Reformulation ✅
- [x] Created `query_reformulator.py` (170+ lines)
- [x] Implemented follow-up detection heuristics
- [x] Implemented query expansion with scheme context
- [x] Created scheme fullname mapping (8 schemes)
- [x] Implemented `reformulate(query, previous_scheme)` → reformulated_query
- [x] Implemented `is_reformulation_needed(query, previous_scheme)` → bool
- [x] Tested on 3 example follow-up scenarios

### 2.4 Context Injection ✅
- [x] Created `context_injector.py` (200+ lines)
- [x] Implemented ContextWindow dataclass
- [x] Built 3 injection modes:
  - [x] Minimal (scheme only)
  - [x] Balanced (scheme + intent)
  - [x] Full (include conversation history)
- [x] Implemented `build_context_window(session_context)` → ContextWindow
- [x] Implemented `inject_into_query(query, context_window, mode)` → injected_query
- [x] Implemented `should_inject_context(query, context_window)` → bool decision logic

### 2.5 Multi-Turn Orchestrator ✅
- [x] Created `multi_turn_orchestrator.py` (300+ lines)
- [x] Implemented 9-step orchestration pipeline:
  1. [x] Session lookup
  2. [x] Intent detection
  3. [x] Scheme extraction
  4. [x] Context building
  5. [x] Query reformulation
  6. [x] Context injection
  7. [x] Two-stage retrieval
  8. [x] Response generation
  9. [x] Turn storage
- [x] Implemented MultiTurnResult dataclass
- [x] Implemented `process_message(phone_number, user_message, language)` → MultiTurnResult
- [x] Implemented `_generate_response(...)` with scheme context

### 2.6 Phase 2 Testing ✅
- [x] Created `phase_2_test.py` (400+ lines comprehensive test suite)
- [x] Test 1: Query Reformulator ✅
  - [x] Explicit query (no reform needed)
  - [x] Implicit follow-up (reform needed)
  - [x] Question-only pattern
- [x] Test 2: Context Injector ✅
  - [x] Context window building
  - [x] Minimal injection mode
  - [x] Balanced injection mode
  - [x] Full injection mode
- [x] Test 3: Intent Classification ✅
  - [x] scheme_inquiry (PM-KISAN)
  - [x] eligibility_check (PMAY-U)
  - [x] documents_needed
  - [x] how_to_apply
  - [x] Multilingual patterns (English, Hindi, Tamil, Telugu)
- [x] Test 4: Session Management ✅
  - [x] Session creation
  - [x] Turn storage
  - [x] Context retrieval
- [x] Test 5: Multi-Turn Orchestrator ✅
  - [x] 5-turn conversation simulation
  - [x] Turn 1 (PM-KISAN inquiry): 1113ms ✅
  - [x] Turn 2 (follow-up subsidy): 625ms ✅
  - [x] Turn 3 (follow-up application): 620ms ✅
  - [x] Turn 4 (scheme switch APY): 536ms ✅
  - [x] Turn 5 (follow-up on APY): 599ms ✅
  - [x] Implicit follow-ups detected ✅
  - [x] Context preserved ✅
  - [x] Scheme switching handled ✅

### 2.7 Git & Documentation ✅
- [x] Committed all Phase 2 files to git (commit bbc2db5)
- [x] Updated README.md with Phase 2 section (1200+ lines)
- [x] Documented all 5 components and their interactions
- [x] Added system architecture diagram
- [x] Added test results and performance benchmarks
- [x] Pushed to origin/main ✅

---

## PHASE 2 CONTINUATION (Pending)

### 2.8 Supabase Schema Creation ⏳
- [ ] Create `user_sessions` table
  - [ ] session_id (UUID primary key)
  - [ ] phone_number (VARCHAR, unique indexed)
  - [ ] conversation_count (INT)
  - [ ] current_scheme (VARCHAR, nullable)
  - [ ] current_intent (VARCHAR, nullable)
  - [ ] user_language (VARCHAR)
  - [ ] created_at (TIMESTAMP)
  - [ ] updated_at (TIMESTAMP)
  - [ ] expires_at (TIMESTAMP, 30-day auto-delete)

- [ ] Create `conversation_history` table
  - [ ] id (SERIAL primary key)
  - [ ] session_id (UUID, FK to user_sessions)
  - [ ] message_number (INT)
  - [ ] user_message (TEXT)
  - [ ] bot_response (TEXT)
  - [ ] intent_detected (VARCHAR)
  - [ ] scheme_mentioned (VARCHAR)
  - [ ] chunks_used (JSON array)
  - [ ] created_at (TIMESTAMP)

### 2.9 Session Persistence ⏳
- [ ] Replace SessionManager in-memory dict with Supabase queries
- [ ] Implement `get_or_create_session()` → Supabase lookup/insert
- [ ] Implement `add_turn()` → Supabase insert to conversation_history
- [ ] Implement session TTL (auto-delete after 30 days)
- [ ] Test persistence across multiple service restarts

### 2.10 Webhook Integration ⏳
- [ ] Update WhatsApp webhook handler in `webhooks_twilio.py`
- [ ] Extract phone_number from Twilio message
- [ ] Pass to `orchestrator.process_message(phone_number, text, language)`
- [ ] Store response back to Supabase message_logs
- [ ] Test with live WhatsApp sandbox messages

### 2.11 Production Testing ⏳
- [ ] Deploy Phase 2 to Render
- [ ] Run 100-message multi-turn simulation
- [ ] Monitor latency, accuracy, error rates
- [ ] Test across all 8 schemes
- [ ] Test multilingual follow-ups (Hindi, Tamil)
- [ ] Load test (5+ concurrent conversations)

### 2.12 Analytics Dashboard ⏳
- [ ] Create Supabase dashboard queries for:
  - [ ] Most common intents across all users
  - [ ] Scheme popularity (which schemes asked about most)
  - [ ] Multi-turn flow analysis (how many turns before resolution)
  - [ ] Reformulation accuracy (did reformulation help?)
  - [ ] Intent classification accuracy (cross-validation)

---

## PHASE 3: ADVANCED CONTEXT (Future)

### Features
- [ ] Multi-scheme comparisons ("Compare PMAY-U vs Sukanya")
- [ ] Eligibility auto-calculator (determine if user qualifies)
- [ ] Action item extraction (summarize what user needs to do)
- [ ] Proactive assistance ("You mentioned housing; want to know about loans?")
- [ ] Cross-conversation learning (anonymized patterns)

---

## Deployment Commands

### Local Development (Phase 1 + Phase 2 Integrated)
```bash
# Terminal 1: Start Render-like server
cd sarvamai
python -m uvicorn src.app.main:app --reload --port 8000

# Terminal 2: Test multi-turn conversation
python src/app/services/chat/phase_2_test.py

# Terminal 3: Test individual components
python src/app/services/chat/phase_2_test.py --component intent_classifier
```

### Production Deployment (Render)
```bash
# Render watches this branch; auto-deploys on git push
git add -A
git commit -m "Phase X: <description>"
git push origin main

# Check logs
https://render.com → sahayak-ai-4oqf → Logs tab
```

### Verify Health
```bash
# Local
curl http://localhost:8000/health

# Production
curl https://sahayak-ai-4oqf.onrender.com/health
```

---

**Last Updated:** April 14, 2026 | **Status:** Phase 2 In Progress (70% complete)