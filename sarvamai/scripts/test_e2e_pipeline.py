"""End-to-end pipeline test: realistic helpline-style queries across 11 Indian languages.
Simulates what a real user would ask a government helpline or officer.
Run: python sarvamai/scripts/test_e2e_pipeline.py
Results saved to: sarvamai/scripts/results/e2e_pipeline.json
"""
import sys, os, json
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app.services.audio.translate_sarvam import detect_and_translate, SARVAM_LANG_CODES
from app.services.rag.retrieve import retrieve_chunks

# Realistic helpline-style queries — the kind of questions people actually ask
QUERIES = [
    # English — eligibility check with personal details
    (
        "My name is Ramesh, I am 67 years old and my monthly income is around 4000 rupees. "
        "I live in Bihar and I don't have any pension right now. Am I eligible for any "
        "government pension scheme? What documents do I need to apply?",
    ),
    # Hindi — a woman asking about housing scheme with family income details
    (
        "मेरा नाम सुनीता है, मैं उत्तर प्रदेश में रहती हूँ। मेरे पति की सालाना आय लगभग "
        "2.5 लाख रुपये है और हमारे पास अपना घर नहीं है। क्या हम प्रधानमंत्री आवास योजना के "
        "लिए पात्र हैं? आवेदन के लिए कौन कौन से कागज़ात चाहिए?",
    ),
    # Tamil — father asking about daughter's savings scheme
    (
        "என் பெயர் முருகன், எனக்கு 5 வயது மகள் இருக்கிறாள். நான் ஒரு தனியார் "
        "நிறுவனத்தில் வேலை செய்கிறேன், மாத சம்பளம் 15000 ரூபாய். என் மகளுக்கு "
        "சுகன்யா சம்ரிதி கணக்கு திறக்க என்ன ஆவணங்கள் தேவை? குறைந்தபட்ச டெபாசிட் எவ்வளவு?",
    ),
    # Telugu — farmer asking about financial assistance
    (
        "నా పేరు వెంకటేష్, నేను ఆంధ్రప్రదేశ్‌లో చిన్న రైతుని. నా వార్షిక ఆదాయం "
        "1.5 లక్షలు. నేను SC కేటగిరీకి చెందినవాడిని. Stand-Up India లోన్ కోసం అప్లై "
        "చేయాలనుకుంటున్నాను. ఎంత లోన్ వస్తుంది? ఏ డాక్యుమెంట్స్ కావాలి?",
    ),
    # Bengali — asking about health insurance for family
    (
        "আমার নাম ফাতিমা, আমি পশ্চিমবঙ্গে থাকি। আমার পরিবারে ৫ জন সদস্য আছে, "
        "স্বামীর বার্ষিক আয় ১.৮ লাখ টাকা। আমার শাশুড়ির হাসপাতালে ভর্তি হওয়া দরকার। "
        "আয়ুষ্মান ভারত কার্ড কীভাবে বানাবো? ক্যাশলেস চিকিৎসা কি পাওয়া যাবে?",
    ),
    # Kannada — widow asking about pension
    (
        "ನನ್ನ ಹೆಸರು ಲಕ್ಷ್ಮಿ, ನಾನು ವಿಧವೆ, ವಯಸ್ಸು 55 ವರ್ಷ. ನನ್ನ ಮಕ್ಕಳು ಕೂಲಿ "
        "ಕೆಲಸ ಮಾಡುತ್ತಾರೆ. ನನಗೆ ಯಾವುದೇ ಆದಾಯ ಇಲ್ಲ. ವಿಧವಾ ಪಿಂಚಣಿ ಯೋಜನೆಗೆ "
        "ನಾನು ಅರ್ಹಳಾ? ಎಷ್ಟು ಹಣ ಸಿಗುತ್ತದೆ ಮತ್ತು ಎಲ್ಲಿ ಅರ್ಜಿ ಸಲ್ಲಿಸಬೇಕು?",
    ),
    # Gujarati — asking about LPG scheme
    (
        "મારું નામ રાધાબેન છે, હું ગુજરાતના એક ગામમાં રહું છું. અમારી પાસે BPL કાર્ડ છે "
        "અને અમે હજી સુધી LPG કનેક્શન લીધું નથી. ઉજ્જવલા યોજનામાં ફ્રી ગેસ કનેક્શન "
        "મળશે? KYC માટે શું શું જોઈએ? ક્યાં અરજી કરવી?",
    ),
    # Malayalam — asking about Jan Dhan bank account
    (
        "എന്റെ പേര് അനിത, ഞാൻ കേരളത്തിൽ താമസിക്കുന്നു. എനിക്ക് ബാങ്ക് അക്കൗണ്ട് ഇല്ല. "
        "ജൻ ധൻ യോജനയിൽ സീറോ ബാലൻസ് അക്കൗണ്ട് തുറക്കാൻ ആധാർ കാർഡ് മാത്രം മതിയോ? "
        "എന്തെല്ലാം ആനുകൂല്യങ്ങൾ ലഭിക്കും? ഡെബിറ്റ് കാർഡ് കിട്ടുമോ?",
    ),
    # Punjabi — asking about Atal Pension for unorganized worker
    (
        "ਮੇਰਾ ਨਾਮ ਗੁਰਪ੍ਰੀਤ ਹੈ, ਮੈਂ ਪੰਜਾਬ ਵਿੱਚ ਆਟੋ ਰਿਕਸ਼ਾ ਚਲਾਉਂਦਾ ਹਾਂ। ਮੇਰੀ ਉਮਰ 30 ਸਾਲ ਹੈ "
        "ਅਤੇ ਮੇਰੇ ਕੋਲ ਕੋਈ ਪੈਨਸ਼ਨ ਨਹੀਂ ਹੈ। ਅਟਲ ਪੈਨਸ਼ਨ ਯੋਜਨਾ ਵਿੱਚ ਮਹੀਨੇ ਦਾ ਕਿੰਨਾ "
        "ਯੋਗਦਾਨ ਦੇਣਾ ਪਵੇਗਾ? 60 ਸਾਲ ਬਾਅਦ ਕਿੰਨੀ ਪੈਨਸ਼ਨ ਮਿਲੇਗੀ?",
    ),
    # Odia — asking about scheme for disabled person
    (
        "ମୋ ନାଁ ସୁରେଶ, ମୁଁ ଓଡ଼ିଶାରେ ରହେ। ମୋ ବାପାଙ୍କ ବୟସ 72 ବର୍ଷ ଏବଂ ସେ ଶାରୀରିକ "
        "ଭାବେ ଅକ୍ଷମ। ସେ କୌଣସି ସରକାରୀ ପେନ୍‌ସନ ପାଉନାହାନ୍ତି। NSAP ଯୋଜନାରେ ବିକଳାଙ୍ଗ "
        "ପେନ୍‌ସନ ପାଇଁ କିପରି ଆବେଦନ କରିବା? କେତେ ଟଙ୍କା ମିଳିବ?",
    ),
    # Marathi — woman entrepreneur asking about Stand-Up India loan
    (
        "माझे नाव प्रिया आहे, मी पुण्यात राहते. मला एक छोटा कपड्यांचा व्यवसाय सुरू "
        "करायचा आहे. माझ्याकडे 3 लाख रुपये स्वतःचे आहेत. Stand-Up India योजनेतून "
        "बँक लोन मिळू शकते का? किती लोन मिळेल? कुठल्या बँकेत जायचे?",
    ),
]

LANG_NAMES = {
    "en-IN": "English", "hi-IN": "Hindi", "ta-IN": "Tamil", "te-IN": "Telugu",
    "bn-IN": "Bengali", "kn-IN": "Kannada", "gu-IN": "Gujarati", "ml-IN": "Malayalam",
    "pa-IN": "Punjabi", "od-IN": "Odia", "mr-IN": "Marathi",
}

print("=" * 90)
print("  End-to-End Pipeline Test — Realistic Helpline Queries")
print("  Input → Detect Language → Translate to EN → Retrieve → Reply in Same Language")
print("=" * 90)

results = []

for (query,) in QUERIES:
    print(f"\n{'─' * 90}")
    print(f"  INPUT: {query[:120]}{'...' if len(query) > 120 else ''}")

    # Step 1: Detect language & translate to English
    detected = detect_and_translate(query, target_lang="en-IN")
    user_lang = detected["source_language_code"]
    english_query = detected["translated_text"]
    lang_name = LANG_NAMES.get(user_lang, user_lang)

    print(f"  DETECTED: {lang_name} ({user_lang})")
    print(f"  ENGLISH: {english_query[:120]}{'...' if len(english_query) > 120 else ''}")

    # Step 2: Retrieve from Qdrant using English query
    chunks = retrieve_chunks(english_query, top_k=3)
    top_source = chunks[0]["source"] if chunks else "N/A"
    top_snippet = chunks[0]["text"][:150].replace("\n", " ") if chunks else "N/A"
    top_score = chunks[0]["score"] if chunks else 0

    sources = [c["source"] for c in chunks[:3]]
    print(f"  RETRIEVED: {', '.join(sources)} (top score={top_score:.4f})")

    # Step 3: Build answer from top chunks (simulating Gemini output)
    answer_en = f"Based on {top_source}: {top_snippet}"

    # Step 4: Translate answer back to user's language
    if user_lang != "en-IN" and user_lang in SARVAM_LANG_CODES:
        back = detect_and_translate(answer_en, target_lang=user_lang)
        answer_local = back["translated_text"]
    else:
        answer_local = answer_en

    print(f"  RESPONSE ({lang_name}): {answer_local[:120]}{'...' if len(answer_local) > 120 else ''}")

    results.append({
        "input": query,
        "detected_lang": user_lang,
        "lang_name": lang_name,
        "english_query": english_query,
        "sources_matched": sources,
        "top_score": round(top_score, 4),
        "answer_en": answer_en[:200],
        "answer_local": answer_local[:200],
    })

print(f"\n{'=' * 90}")
print(f"  All {len(QUERIES)} queries processed successfully!")
print(f"  Languages tested: {', '.join(r['lang_name'] for r in results)}")
print(f"{'=' * 90}")

# Save results
os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
out_path = os.path.join(os.path.dirname(__file__), "results", "e2e_pipeline.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({
        "test": "e2e_pipeline_realistic",
        "timestamp": datetime.now().isoformat(),
        "total_queries": len(QUERIES),
        "results": results,
    }, f, ensure_ascii=False, indent=2)
print(f"Saved to: {out_path}")
