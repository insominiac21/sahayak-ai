def route_tools(query, chunks, user_profile):
    """
    Answer user query using retrieved scheme chunks + Gemini.
    Uses Sarvam translation for input/output.
    """
    from app.services.audio.translate_sarvam import detect_and_translate, SARVAM_LANG_CODES
    from app.services.llm.gemini_client import generate_with_fallback

    # Step 1: Translate input to English (if needed)
    detected = detect_and_translate(query, target_lang="en-IN")
    english_query = detected["translated_text"]
    user_lang = detected["source_language_code"]

    # Step 2: Build prompt with retrieved context chunks
    context_text = "\n\n---\n\n".join(
        c.get("text", "") if isinstance(c, dict) else str(c)
        for c in (chunks or [])
    )
    prompt = (
        "You are Sahayak AI, an assistant that helps Indian citizens understand "
        "government welfare schemes. Answer the user's question using ONLY the "
        "scheme information provided below. Be concise, helpful, and accurate. "
        "If the answer is not in the context, say so clearly.\n\n"
        f"=== Scheme Information ===\n{context_text}\n\n"
        f"=== User Question ===\n{english_query}"
    )

    # Step 3: Call Gemini with round-robin fallback
    response = generate_with_fallback(contents=prompt)
    answer = response.text

    # Step 4: Translate answer back to user's language
    if user_lang != "en-IN" and user_lang in SARVAM_LANG_CODES:
        translated = detect_and_translate(answer, target_lang=user_lang)
        final_answer = translated["translated_text"]
    else:
        final_answer = answer

    return {
        "answer": final_answer,
        "answer_en": answer,
        "user_lang": user_lang,
    }
