#!/usr/bin/env python
"""
Test script to check quota availability on each Gemini API key.
This helps identify which keys still have available requests.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add sarvamai to path
sys.path.insert(0, str(Path(__file__).parent / "sarvamai" / "src"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# Load env vars
env_file = Path(__file__).parent / "sarvamai" / ".env"
if not env_file.exists():
    env_file = Path(__file__).parent / ".env"
load_dotenv(env_file)

# Import after path setup
from langchain_google_genai import ChatGoogleGenerativeAI


def test_api_key(key_num: int, api_key: str) -> dict:
    """Test a single API key and return quota status."""
    result = {
        "key_num": key_num,
        "api_key": api_key[:20] + "..." if api_key else "MISSING",
        "status": "UNKNOWN",
        "message": "",
        "has_quota": False
    }
    
    if not api_key:
        result["status"] = "MISSING"
        result["message"] = "API key not found in .env"
        return result
    
    try:
        logger.info(f"🔑 Testing Gemini API Key {key_num}...")
        
        # Create LLM instance
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            api_key=api_key,
            max_retries=0  # Don't retry, just fail fast
        )
        
        # Minimal test call
        response = llm.invoke("say 'ok'")
        
        result["status"] = "✅ ACTIVE"
        result["message"] = "API key is working - HAS QUOTA"
        result["has_quota"] = True
        logger.info(f"✅ Key {key_num}: QUOTA AVAILABLE")
        
    except Exception as e:
        error_msg = str(e)
        
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            result["status"] = "❌ QUOTA_EXHAUSTED"
            result["message"] = "Rate limit or quota exceeded"
            result["has_quota"] = False
            logger.warning(f"❌ Key {key_num}: QUOTA EXHAUSTED (429)")
            
        elif "403" in error_msg or "PERMISSION_DENIED" in error_msg:
            result["status"] = "❌ PERMISSION_DENIED"
            result["message"] = "Invalid key or project suspended"
            result["has_quota"] = False
            logger.warning(f"❌ Key {key_num}: PERMISSION DENIED (403)")
            
        elif "401" in error_msg or "INVALID_ARGUMENT" in error_msg:
            result["status"] = "❌ INVALID_KEY"
            result["message"] = "API key is invalid or malformed"
            result["has_quota"] = False
            logger.warning(f"❌ Key {key_num}: INVALID KEY (401)")
            
        else:
            result["status"] = "⚠️ ERROR"
            result["message"] = error_msg[:100]
            result["has_quota"] = False
            logger.error(f"⚠️ Key {key_num}: Unexpected error - {error_msg[:100]}")
    
    return result


def main():
    """Test all 4 API keys."""
    logger.info("=" * 80)
    logger.info("🧪 GEMINI API KEY QUOTA TEST")
    logger.info("=" * 80)
    
    # Get API keys from env
    api_keys = {
        1: os.getenv("GEMINI_API_KEY1"),
        2: os.getenv("GEMINI_API_KEY2"),
        3: os.getenv("GEMINI_API_KEY3"),
        5: os.getenv("GEMINI_API_KEY5"),  # Note: Key 4 removed (403 error)
    }
    
    results = []
    for key_num, api_key in sorted(api_keys.items()):
        result = test_api_key(key_num, api_key)
        results.append(result)
        print()  # Newline for readability
    
    # Summary
    logger.info("=" * 80)
    logger.info("📊 QUOTA TEST SUMMARY")
    logger.info("=" * 80)
    
    available_keys = [r for r in results if r["has_quota"]]
    exhausted_keys = [r for r in results if r["status"] == "❌ QUOTA_EXHAUSTED"]
    error_keys = [r for r in results if r["status"] in ["❌ PERMISSION_DENIED", "❌ INVALID_KEY"]]
    
    logger.info(f"Total Keys Tested: {len(results)}")
    logger.info(f"✅ Keys with Quota: {len(available_keys)}")
    logger.info(f"❌ Keys Exhausted: {len(exhausted_keys)}")
    logger.info(f"⚠️ Keys with Errors: {len(error_keys)}")
    
    if available_keys:
        logger.info("\n✅ AVAILABLE KEYS:")
        for r in available_keys:
            logger.info(f"   Key {r['key_num']}: {r['status']}")
    
    if exhausted_keys:
        logger.info("\n❌ EXHAUSTED KEYS (will try again after UTC midnight):")
        for r in exhausted_keys:
            logger.info(f"   Key {r['key_num']}: {r['status']}")
    
    if error_keys:
        logger.info("\n⚠️ INVALID KEYS (fix required):")
        for r in error_keys:
            logger.info(f"   Key {r['key_num']}: {r['status']} - {r['message']}")
    
    logger.info("=" * 80)
    
    # Return exit code based on available keys
    return 0 if available_keys else 1


if __name__ == "__main__":
    sys.exit(main())
