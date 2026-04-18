# Phase 2 Deployment Guide: Multi-Turn Chatbot + Supabase Integration

## ✅ What's Done

**Phase 2 Code (All Components Created & Tested):**
- ✅ Session Manager (now with Supabase persistence)
- ✅ Intent Classifier (5 intent types, multilingual)
- ✅ Query Reformulator (implicit follow-up detection)
- ✅ Context Injector (3 modes: minimal/balanced/full)
- ✅ Multi-Turn Orchestrator (9-step pipeline)
- ✅ Comprehensive test suite (all passing)

**New Files Added:**
- ✅ `supabase_client.py` - Singleton Supabase connection manager
- ✅ `migrations/001_create_sessions_tables.sql` - Database schema
- ✅ Updated `session_manager.py` - Now saves to Supabase
- ✅ Updated `webhooks_twilio.py` - Uses MultiTurnOrchestrator
- ✅ Updated `pyproject.toml` - Added supabase dependency

---

## 🚀 Deployment Steps

### Step 1: Set Up Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create a new project (or use existing one)
3. Note down:
   - **Project URL** → `SUPABASE_URL`
   - **Anon/Public Key** → `SUPABASE_ANON_KEY`

### Step 2: Create Database Tables

1. In Supabase Console, go to **SQL Editor**
2. Create a new query
3. Copy the contents of `saarnam-ai/supabase/migrations/001_create_sessions_tables.sql`
4. Paste into SQL Editor
5. Click **Run**

**Tables created:**
- `user_sessions` - Stores active/past sessions
- `conversation_history` - Stores all turns in conversation
- Auto-expiry triggers (30 min)
- RLS policies enabled

### Step 3: Update Environment Variables

Add to your `.env` file (Render):

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
```

### Step 4: Deploy Code Changes

1. Commit all Phase 2 code:
   ```bash
   git add .
   git commit -m "Phase 2F: Supabase Integration & Webhook Update"
   git push origin main
   ```

2. Render will auto-deploy from main branch
3. Wait for deployment (~3-5 min)

### Step 5: Test Multi-Turn Conversation

Send these messages to your WhatsApp bot via the live number:

```
User: "Tell me about PM Kisan"
Bot: [Explains PM Kisan scheme]

User: "How much will I get?"
Bot: [Follow-up answered, knows context is PM Kisan]

User: "What documents needed?"
Bot: [Another follow-up, still knows previous context]

User: "Tell me about APY"
Bot: [New topic, clears context]

User: "Who is eligible?"
Bot: [Follow-up for APY]
```

**Expected behavior:**
- Turn 1-2: Follow-ups reformulated with PM Kisan context ✅
- Turn 3: Context switches to APY ✅
- Turn 4: Follows APY context ✅

### Step 6: Verify Database Logs

1. Go to Supabase Console
2. Click **SQL Editor**
3. Run this query to check sessions:
   ```sql
   SELECT session_id, user_phone_number, session_state, created_at, last_message_at 
   FROM user_sessions 
   ORDER BY created_at DESC 
   LIMIT 10;
   ```

4. Check conversation history:
   ```sql
   SELECT turn_number, user_query, bot_answer, timestamp 
   FROM conversation_history 
   WHERE session_id = 'YOUR_SESSION_ID' 
   ORDER BY turn_number;
   ```

---

## 🔧 Architecture: How It Works Now

### Full Multi-Turn Message Flow:

```
1. WhatsApp Message Arrives
   ↓
2. Twilio Webhook Handler
   - Extract phone_number
   - Detect language (en, hi, ta, te)
   ↓
3. SessionManager.get_or_create_session()
   - Query Supabase for existing session
   - If not found, create new session
   - Store session_id in memory + DB
   ↓
4. IntentClassifier.classify()
   - Determine intent (scheme_inquiry, eligibility_check, etc.)
   - Extract scheme names
   - Detect if follow-up or new topic
   ↓
5. QueryReformulator.reformulate()
   - If follow-up: expand vague query
   - Example: "How much?" → "How much subsidy for PM Kisan?"
   ↓
6. ContextInjector.inject()
   - Add previous scheme name to query
   - Add conversation history if needed
   ↓
7. Two-Stage Retrieval (Phase 1)
   - Hybrid search (dense + sparse)
   - Reranking with cross-encoder
   - Return top 4 chunks
   ↓
8. LLM Generation (Gemini)
   - Include chat history in prompt
   - Generate answer using retrieved chunks
   ↓
9. SessionManager.add_turn()
   - Save user_query, bot_answer, intent, timestamp to Supabase
   - Update session last_message_at
   ↓
10. Send Response to WhatsApp
   ↓
11. Auto-Expire Sessions
   - If no message for 30 min → mark session as "closed"
   - Triggers run automatically via Supabase
```

---

## 📊 Database Schema

### `user_sessions` Table
```
session_id (UUID, PK)
user_phone_number (VARCHAR, UNIQUE)
session_state (VARCHAR) - "main_menu" | "qna_active" | "closed"
conversation_context (JSONB) - {"language": "en", "last_scheme": "pm-kisan", ...}
created_at (TIMESTAMP)
last_message_at (TIMESTAMP)
expires_at (TIMESTAMP) - Auto-set to 30 min in future
```

### `conversation_history` Table
```
history_id (UUID, PK)
session_id (UUID, FK)
turn_number (INT) - 1, 2, 3, ...
user_query (TEXT)
user_query_reformulated (TEXT, optional)
intent_detected (VARCHAR)
retrieved_scheme_names (JSONB array)
bot_answer (TEXT)
latency_ms (INT, optional)
timestamp (TIMESTAMP)
```

---

## 🧪 Testing Without Supabase (Local Development)

If Supabase is not configured:
- SessionManager falls back to in-memory storage
- All functionality works but sessions don't persist across server restarts
- Perfect for local testing!

No changes needed to code.

---

## 📈 Monitoring

### Key Metrics to Track

1. **Session Duration:** How long do users stay engaged?
2. **Follow-Up Rate:** % of messages that are follow-ups (should be high!)
3. **Intent Distribution:** Which intents are most common?
4. **Response Latency:** End-to-end, should be < 3 seconds

**Query to check latency:**
```sql
SELECT 
  turn_number,
  latency_ms,
  EXTRACT(EPOCH FROM timestamp) as unix_timestamp
FROM conversation_history 
WHERE session_id = 'YOUR_SESSION_ID'
ORDER BY turn_number;
```

---

## 🐛 Troubleshooting

### Issue: "Supabase not configured"
**Solution:** Check `.env` has `SUPABASE_URL` and `SUPABASE_ANON_KEY`

### Issue: "Session not found in DB"
**Solution:** Check RLS policies allow reads/writes (should be enabled by default)

### Issue: "Follow-ups not being reformulated"
**Solution:** Check intent_classifier is detecting follow-ups correctly
- Run: `SELECT intent_detected FROM conversation_history ORDER BY timestamp DESC LIMIT 5;`

### Issue: "Bot responses slow after turn 3"
**Solution:** Database queries might be slow
- Check conversation_history table has proper indexes (should be created by migration)

---

## 🎯 What's Next (Phase 3)

After Supabase is live and tested:

1. **Eligibility Calculator** - Auto-detect if user qualifies
2. **Multi-Scheme Comparison** - Compare schemes side-by-side
3. **Action Item Extraction** - "Here's what you need to do next"
4. **Proactive Reminders** - Follow-up messages for incomplete applications
5. **Analytics Dashboard** - Track conversation flows and success rates

---

## 📝 Quick Reference

**Environment Variables Needed:**
```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJxxx...
```

**Files Modified:**
- `webhooks_twilio.py` - Now uses MultiTurnOrchestrator
- `session_manager.py` - Now has Supabase persistence
- `supabase_client.py` - NEW: Connection manager
- `pyproject.toml` - Added supabase dependency

**New SQL Migrations:**
- `supabase/migrations/001_create_sessions_tables.sql`

**Testing:**
- All Phase 2 tests pass locally
- End-to-end multi-turn tested
- Ready for production!

---

## ✅ Deployment Checklist

- [ ] Supabase project created
- [ ] Database tables created (SQL migration run)
- [ ] Environment variables set in Render
- [ ] Code committed and pushed to main
- [ ] Render deployment complete
- [ ] Multi-turn conversation tested (5+ messages)
- [ ] Database logs verified (user_sessions table populated)
- [ ] Response latency acceptable (< 3 sec)
- [ ] Session expiry working (30 min timeout)

---

**Status:** ✅ All Phase 2 code ready for production deployment!
