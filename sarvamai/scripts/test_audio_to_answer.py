"""Batch test: audio file -> STT -> translate -> retrieve -> Gemini answer -> back-translate.

Run:
  python scripts/test_audio_to_answer.py
  python scripts/test_audio_to_answer.py --input-dir scripts/test_data/audio --top-k 5

Saves results to: scripts/results/audio_to_answer.json
"""
import argparse
import asyncio
import glob
import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from google.genai import types

from app.services.audio.stt_sarvam import transcribe_audio
from app.services.audio.translate_sarvam import detect_and_translate, SARVAM_LANG_CODES
from app.services.llm.gemini_client import generate_with_fallback
from app.services.rag.retrieve import retrieve_chunks


SYSTEM_PROMPT = (
    "You are Sahayak AI, a helpful Indian government schemes assistant. "
    "Answer the user's question using ONLY the provided context chunks. "
    "Be specific: mention scheme names, eligibility criteria, amounts, and required documents. "
    "If the context doesn't have enough info, say so honestly. "
    "Keep the answer concise but complete (3-5 sentences). "
    "Always cite which scheme you're referring to."
)


def build_rag_prompt(query: str, chunks: list[dict]) -> str:
    context = "\n\n".join(f"[Source: {c['source']}]\n{c['text']}" for c in chunks)
    return (
        f"CONTEXT:\n{context}\n\n"
        f"USER QUESTION:\n{query}\n\n"
        "Answer using only the context above. Mention scheme names, eligibility, amounts, and documents needed."
    )


async def process_one(audio_path: str, top_k: int) -> dict:
    media_url = f"file://{os.path.abspath(audio_path)}"

    stt = await transcribe_audio(media_url)
    transcript = (stt.get("transcript") or "").strip()
    stt_lang = stt.get("language_code") or ""

    if not transcript:
        return {
            "file": os.path.basename(audio_path),
            "ok": False,
            "error": "Empty transcript from STT",
            "stt_language_code": stt_lang,
            "transcript": "",
        }

    detected = detect_and_translate(transcript, target_lang="en-IN")
    user_lang = detected["source_language_code"]
    english_query = detected["translated_text"]

    chunks = retrieve_chunks(english_query, top_k=top_k)
    sources = list(dict.fromkeys(c["source"] for c in chunks))
    top_score = chunks[0]["score"] if chunks else 0.0

    rag_prompt = build_rag_prompt(english_query, chunks)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.3,
        max_output_tokens=1024,
    )
    gemini_response = generate_with_fallback(contents=rag_prompt, config=config)
    answer_en = (gemini_response.text or "").strip()

    if user_lang != "en-IN" and user_lang in SARVAM_LANG_CODES:
        answer_local = detect_and_translate(answer_en, target_lang=user_lang)["translated_text"]
    else:
        answer_local = answer_en

    return {
        "file": os.path.basename(audio_path),
        "ok": True,
        "stt_language_code": stt_lang,
        "detected_language_code": user_lang,
        "transcript": transcript,
        "english_query": english_query,
        "sources_matched": sources,
        "top_score": round(float(top_score), 4),
        "answer_en": answer_en,
        "answer_local": answer_local,
    }


async def main(input_dir: str, top_k: int):
    files = sorted(glob.glob(os.path.join(input_dir, "*")))
    if not files:
        print(f"No audio files found in: {input_dir}")
        return

    print("=" * 90)
    print(f"Audio -> Answer Test | files={len(files)} | top_k={top_k}")
    print("=" * 90)

    results = []
    for path in files:
        name = os.path.basename(path)
        print(f"\n--- {name} ---")
        try:
            result = await process_one(path, top_k=top_k)
            results.append(result)
            if not result["ok"]:
                print(f"STT LANG: {result.get('stt_language_code', '')}")
                print(f"ERROR: {result.get('error', 'Unknown error')}")
                continue

            print(f"STT LANG: {result['stt_language_code']} | DETECTED: {result['detected_language_code']}")
            print(f"TRANSCRIPT: {result['transcript'][:220]}{'...' if len(result['transcript']) > 220 else ''}")
            print(f"SOURCES: {', '.join(result['sources_matched'])} (top score={result['top_score']:.4f})")
            print(f"ANSWER: {result['answer_local'][:320]}{'...' if len(result['answer_local']) > 320 else ''}")
        except Exception as exc:
            err = {"file": name, "ok": False, "error": str(exc)}
            results.append(err)
            print(f"ERROR: {str(exc)[:300]}")

    passed = sum(1 for r in results if r.get("ok"))
    failed = len(results) - passed

    os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
    out_path = os.path.join(os.path.dirname(__file__), "results", "audio_to_answer.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "test": "audio_to_answer",
                "timestamp": datetime.now().isoformat(),
                "input_dir": input_dir,
                "total_files": len(results),
                "passed": passed,
                "failed": failed,
                "results": results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("\n" + "=" * 90)
    print(f"Done | passed={passed} failed={failed}")
    print(f"Saved: {out_path}")
    print("=" * 90)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="scripts/test_data/audio", help="Directory containing audio files")
    parser.add_argument("--top-k", type=int, default=5, help="Number of retrieved chunks")
    args = parser.parse_args()
    asyncio.run(main(args.input_dir, args.top_k))
