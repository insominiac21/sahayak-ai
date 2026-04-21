# DEPLOYMENT CHECKLIST - RENDER

**Status:** ✅ Ready to Deploy  
**Version:** Phase 3 - LangGraph Agentic AI  
**Date:** April 21, 2026

---

## ✅ PRE-DEPLOYMENT VERIFICATION

- [x] **Twilio webhooks enabled** in `main.py`
- [x] **API keys updated** in `render.yaml` (KEY1,2,3,5 - removed KEY4)
- [x] **Spell-check disabled** to preserve user intent
- [x] **Retries optimized** - fail fast on quota errors
- [x] **Token limits reduced** (500 → 300 tokens)
- [x] **Text preprocessing** disabled (too aggressive)
- [x] **Health endpoint** working (`/health`)

---

## 🚀 DEPLOYMENT STEPS

### Step 1: Push to GitHub
```bash
git add -A
git commit -m "Phase 3: Optimized LangGraph agent with Twilio webhooks enabled"
git push origin main
```

### Step 2: Set Environment Variables on Render Dashboard
**Navigate:** https://dashboard.render.com → Your Service → Environment

Set these 11 variables:
```
GEMINI_API_KEY1       = (from .env)
GEMINI_API_KEY2       = (from .env)
GEMINI_API_KEY3       = (from .env)
GEMINI_API_KEY5       = (from .env)
TWILIO_ACCOUNT_SID    = (from .env)
TWILIO_AUTH_TOKEN     = (from .env)
TWILIO_WHATSAPP_NUMBER = +14155238886
SARVAM_API_KEY        = (from .env)
QDRANT_URL            = (from .env)
QDRANT_API_KEY        = (from .env)
SERPER_API_KEY        = (from .env)
HF_TOKEN              = (from .env)
```

### Step 3: Configure Twilio Webhook
**Navigate:** https://www.twilio.com/console/phone-numbers

1. Select WhatsApp Number: `+14155238886`
2. When a message comes in → Webhook URL:
   ```
   https://YOUR-RENDER-URL/api/v1/webhooks/twilio/incoming
   ```
3. Method: POST
4. Save

### Step 4: Test Webhook
Send WhatsApp message to `+14155238886`

Expected flow:
1. Message received → Twilio → Render webhook
2. Twilio returns 200 OK immediately
3. Agent processes async (STT + LangGraph + response)
4. WhatsApp reply sent back

### Step 5: Monitor Logs
```bash
# Render dashboard → Logs
# Watch for:
# - "Processing WhatsApp message"
# - "LangGraph agent" logs
# - Any errors with emoji handling
```

---

## ⚠️ KNOWN LIMITATIONS

### 1. **Daily API Quota** (20 requests/day)
- All 4 Gemini keys share free tier quota
- **Workaround:** Only use for demo/testing
- **Production:** Upgrade to paid tier or create separate GCP projects

### 2. **Context Window** (Checkpoint loading)
- Previous messages not fully preserved
- Agent starts fresh each conversation
- Workaround: Agent still understands follow-ups via system prompt

### 3. **Spell-Check Disabled**
- Heuristic corrections were breaking queries
- Qdrant fuzzy search is robust enough for typos

---

## 📊 PERFORMANCE EXPECTATIONS

| Metric | Value |
|--------|-------|
| Time to respond | 5-15 seconds |
| API calls/message | 2-4 (depending on tools) |
| Daily message capacity | ~5 (with quota limit) |
| Monthly cost (paid tier) | ~$0.50-$2 at Gemini rates |

---

## 🔍 TROUBLESHOOTING

### Issue: WhatsApp no response
**Check:**
1. Twilio console → Phone Numbers → Verify webhook URL
2. Render logs → Look for incoming webhook calls
3. Is TWILIO_AUTH_TOKEN correct?

### Issue: Agent returns error
**Check:**
1. Are all 4 API keys in Render environment?
2. Did quota reset? Check via `curl https://YOUR-URL/health`
3. Check Render logs for 429 RESOURCE_EXHAUSTED

### Issue: Text formatting wrong
**Check:**
1. Agent response has `**bold**` or `__italic__`?
2. Verify `_normalize_whatsapp_formatting()` is converting to `*bold*` and `_italic_`

---

## 📝 FILES READY FOR DEPLOYMENT

```
✅ sarvamai/src/app/main.py              (Twilio enabled)
✅ sarvamai/src/app/services/agent/langgraph_agent.py  (Optimized)
✅ sarvamai/src/app/utils/text_preprocessing.py        (Disabled)
✅ render.yaml                           (KEY5 instead of KEY4)
✅ requirements.txt                      (All dependencies)
✅ .env-example                          (Template for Render)
```

---

## ✨ DEPLOYMENT COMMAND

```bash
# After setting env vars on Render:
git push origin main

# Render auto-deploys on push
# Monitor: https://dashboard.render.com/services/sahayak-ai-phase3
```

**Estimated Deploy Time:** 3-5 minutes

---

**Next:** After deployment, test with 1 message to WhatsApp number: Ask to confirm it works ✅
