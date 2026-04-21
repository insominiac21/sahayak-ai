#!/usr/bin/env python
"""Quick quota check - minimal logging"""
import os, sys, logging
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, str(Path(__file__).parent / "sarvamai" / "src"))

load_dotenv(Path(__file__).parent / "sarvamai" / ".env")

from langchain_google_genai import ChatGoogleGenerativeAI

key1 = os.getenv("GEMINI_API_KEY1")
if key1:
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=key1, max_retries=0)
        llm.invoke("ok")
        print("✅ Key 1: HAS QUOTA")
    except Exception as e:
        if "429" in str(e):
            print("❌ Key 1: QUOTA_EXHAUSTED")
        else:
            print(f"⚠️ Key 1: {type(e).__name__}")
else:
    print("❌ Key 1: MISSING")
