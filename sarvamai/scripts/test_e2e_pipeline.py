"""End-to-end pipeline test: Input (any language) → Detect → Translate to EN → Retrieve → Translate response back.
Run: python sarvamai/scripts/test_e2e_pipeline.py
Results saved to: sarvamai/scripts/results/e2e_pipeline.json
"""
import sys, os, json
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app.services.audio.translate_sarvam import detect_and_translate, SARVAM_LANG_CODES
from app.services.rag.retrieve import retrieve_chunks

# Queries in different Indian languages (user would type/speak these)
QUERIES = [
    ("What pension schemes are available for elderly people?",),       # English
    ("गरीब परिवारों के लिए कौन सी सरकारी योजनाएँ हैं?",),            # Hindi
    ("ஏழை குடும்பங்களுக்கு என்ன அரசுத் திட்டங்கள் உள்ளன?",),         # Tamil
    ("పేద కుటుంబాలకు ఏ ప్రభుత్వ పథకాలు అందుబాటులో ఉన్నాయి?",),     # Telugu
    ("দরিদ্র পরিবারের জন্য কোন সরকারি প্রকল্প আছে?",),              # Bengali
    ("ಬಡ ಕುಟುಂಬಗಳಿಗೆ ಯಾವ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು ಲಭ್ಯವಿವೆ?",),            # Kannada
    ("ગરીબ પરિવારો માટે કઈ સરકારી યોજનાઓ ઉપલબ્ધ છે?",),            # Gujarati
    ("പാവപ്പെട്ട കുടുംബങ്ങൾക്ക് എന്ത് സർക്കാർ പദ്ധതികൾ ലഭ്യമാണ്?",), # Malayalam
    ("ਗ਼ਰੀਬ ਪਰਿਵਾਰਾਂ ਲਈ ਕਿਹੜੀਆਂ ਸਰਕਾਰੀ ਸਕੀਮਾਂ ਉਪਲਬਧ ਹਨ?",),       # Punjabi
    ("ଗରିବ ପରିବାରମାନଙ୍କ ପାଇଁ କେଉଁ ସରକାରୀ ଯୋଜନା ଉପଲବ୍ଧ?",),       # Odia
    ("गरीब कुटुंबांसाठी कोणत्या सरकारी योजना उपलब्ध आहेत?",),        # Marathi
]

LANG_NAMES = {
    "en-IN": "English", "hi-IN": "Hindi", "ta-IN": "Tamil", "te-IN": "Telugu",
    "bn-IN": "Bengali", "kn-IN": "Kannada", "gu-IN": "Gujarati", "ml-IN": "Malayalam",
    "pa-IN": "Punjabi", "od-IN": "Odia", "mr-IN": "Marathi",
}

print("=" * 75)
print("  End-to-End Pipeline Test")
print("  Input → Detect Language → Translate to EN → Retrieve → Reply in Same Language")
print("=" * 75)

results = []

for (query,) in QUERIES:
    print(f"\n{'─' * 75}")
    print(f"  INPUT: {query}")

    # Step 1: Detect language & translate to English
    detected = detect_and_translate(query, target_lang="en-IN")
    user_lang = detected["source_language_code"]
    english_query = detected["translated_text"]
    lang_name = LANG_NAMES.get(user_lang, user_lang)

    print(f"  DETECTED: {lang_name} ({user_lang})")
    print(f"  ENGLISH: {english_query}")

    # Step 2: Retrieve from Qdrant using English query
    chunks = retrieve_chunks(english_query, top_k=2)
    top_source = chunks[0]["source"] if chunks else "N/A"
    top_snippet = chunks[0]["text"][:100].replace("\n", " ") if chunks else "N/A"
    top_score = chunks[0]["score"] if chunks else 0

    print(f"  RETRIEVED: {top_source} (score={top_score:.4f})")

    # Step 3: Build a simple answer from top chunk (simulating Gemini output)
    answer_en = f"Based on {top_source}: {top_snippet}"

    # Step 4: Translate answer back to user's language
    if user_lang != "en-IN" and user_lang in SARVAM_LANG_CODES:
        back = detect_and_translate(answer_en, target_lang=user_lang)
        answer_local = back["translated_text"]
    else:
        answer_local = answer_en

    print(f"  RESPONSE ({lang_name}): {answer_local[:100]}...")

    results.append({
        "input": query,
        "detected_lang": user_lang,
        "lang_name": lang_name,
        "english_query": english_query,
        "top_source": top_source,
        "top_score": round(top_score, 4),
        "answer_en": answer_en[:150],
        "answer_local": answer_local[:150],
    })

print(f"\n{'=' * 75}")
print(f"  All {len(QUERIES)} queries processed successfully!")
print(f"  Languages tested: {', '.join(r['lang_name'] for r in results)}")
print(f"{'=' * 75}")

# Save results
os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
out_path = os.path.join(os.path.dirname(__file__), "results", "e2e_pipeline.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({
        "test": "e2e_pipeline",
        "timestamp": datetime.now().isoformat(),
        "total_queries": len(QUERIES),
        "results": results,
    }, f, ensure_ascii=False, indent=2)
print(f"Saved to: {out_path}")
