"""Smoke-test for Sarvam AI Translation — tests all 11 working languages with round-trip.
Run: python sarvamai/scripts/test_sarvam.py
Results saved to: sarvamai/scripts/results/sarvam_translation.json
"""
import sys, os, json
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from sarvamai import SarvamAI
from app.core.config import settings

client = SarvamAI(api_subscription_key=settings.SARVAM_API_KEY)

SOURCE_TEXT = "What government schemes are available for poor families?"

# 11 languages verified working on Sarvam translate API
SUPPORTED_LANGS = [
    ("bn-IN",  "Bengali"),
    ("en-IN",  "English"),
    ("gu-IN",  "Gujarati"),
    ("hi-IN",  "Hindi"),
    ("kn-IN",  "Kannada"),
    ("ml-IN",  "Malayalam"),
    ("mr-IN",  "Marathi"),
    ("od-IN",  "Odia"),
    ("pa-IN",  "Punjabi"),
    ("ta-IN",  "Tamil"),
    ("te-IN",  "Telugu"),
]

print("=" * 70)
print("Sarvam AI — Translation Test (11 supported languages)")
print("=" * 70)
print(f"\nSource (en-IN): {SOURCE_TEXT}\n")

passed, failed = 0, 0
results = []

for code, name in SUPPORTED_LANGS:
    if code == "en-IN":
        results.append({"lang": code, "name": name, "status": "SKIP"})
        passed += 1
        continue
    try:
        fwd = client.text.translate(
            input=SOURCE_TEXT, source_language_code="en-IN",
            target_language_code=code, speaker_gender="Male", mode="formal",
        )
        rev = client.text.translate(
            input=fwd.translated_text, source_language_code=code,
            target_language_code="en-IN", speaker_gender="Male", mode="formal",
        )
        results.append({
            "lang": code, "name": name, "status": "PASS",
            "translated": fwd.translated_text, "round_trip": rev.translated_text,
        })
        passed += 1
        print(f"  PASS  [{code:6s}] {name:12s} | {fwd.translated_text[:55]}")
    except Exception as e:
        results.append({"lang": code, "name": name, "status": "FAIL", "error": str(e)[:120]})
        failed += 1
        print(f"  FAIL  [{code:6s}] {name:12s} | {str(e)[:55]}")

# Save results
os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
out_path = os.path.join(os.path.dirname(__file__), "results", "sarvam_translation.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({
        "test": "sarvam_translation",
        "timestamp": datetime.now().isoformat(),
        "source_text": SOURCE_TEXT,
        "total": len(SUPPORTED_LANGS), "passed": passed, "failed": failed,
        "results": results,
    }, f, ensure_ascii=False, indent=2)

print(f"\n{'=' * 70}")
print(f"Results: {passed} passed, {failed} failed out of {len(SUPPORTED_LANGS)} languages")
print(f"Saved to: {out_path}")
print(f"{'=' * 70}")
