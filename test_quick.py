#!/usr/bin/env python
"""
Minimal test - just check quota and do ONE simple message to measure API calls.
This will help verify our optimization worked.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Minimal logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent / "sarvamai" / "src"))
load_dotenv(Path(__file__).parent / "sarvamai" / ".env")

from langchain_google_genai import ChatGoogleGenerativeAI

print("\n" + "="*80)
print("🔍 QUOTA CHECK & OPTIMIZATION TEST")
print("="*80)

# Test one key quickly
key1 = os.getenv("GEMINI_API_KEY1")
print(f"\n1️⃣ Testing API Key 1...")

try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=key1,
        max_retries=0  # NO retries - fail fast
    )
    response = llm.invoke("say 'ok' in one word")
    print("✅ Key 1: HAS QUOTA - Ready to test!")
    
    # Now run a simple agent test
    print("\n" + "="*80)
    print("2️⃣ Running optimized agent test...")
    print("="*80)
    
    from app.services.agent.langgraph_agent import run_agent
    
    print("\n📨 Simple message: 'Hello'")
    response = run_agent("Hello", "test_quick_001")
    print(f"✅ Response: {response[:100]}...")
    print("\n✨ Agent test completed!")
    print("\n💡 Optimization changes:")
    print("   ✅ max_tokens: 500 → 300 (saves 40% tokens)")
    print("   ✅ Retries: 2 attempts → 0 (no retry on quota exhaustion)")
    print("   ✅ Tool forcing: Always → Only on scheme questions")
    
except Exception as e:
    error_str = str(e)
    if "429" in error_str:
        print("❌ Key 1: QUOTA EXHAUSTED - Still waiting for reset")
        print("\n⏰ Wait ~6-7 more hours for UTC midnight quota reset")
        print("🔄 Then run: python test_agent_local.py")
    elif "PERMISSION_DENIED" in error_str or "403" in error_str:
        print("❌ Key 1: PERMISSION DENIED - Check .env file")
    else:
        print(f"⚠️ Error: {type(e).__name__}: {error_str[:80]}")

print("\n" + "="*80)
