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
        "You are Sahayak AI, a professional assistant that helps Indian citizens "
        "understand government welfare schemes. Your replies are delivered over WhatsApp.\n\n"
        "Formatting rules (WhatsApp markdown only):\n"
        "- Use *bold* (single asterisks) for section headings and scheme names. "
        "Do NOT use # or ## markdown headers.\n"
        "- Use numbered lists (1. 2. 3.) for steps, documents, or eligibility criteria.\n"
        "- Put each numbered item on a new line (never in the same sentence).\n"
        "- Use a dash (-) for single-level bullet points when order does not matter.\n"
        "- Separate sections with a blank line.\n"
        "- Do NOT use emojis, horizontal rules, or any other formatting.\n"
        "- Keep replies concise. Lead with a one-sentence direct answer, "
        "then provide the list or detail.\n\n"
        "Content rules:\n"
        "- Answer using ONLY the scheme information provided below.\n"
        "- If the answer is not in the context, reply with exactly: "
        "'This information is not available in my current knowledge base.'\n\n"
        f"=== Scheme Information ===\n{context_text}\n\n"
        f"=== User Question ===\n{english_query}"
    )

    # Step 3: Call Gemini with round-robin fallback
    response = generate_with_fallback(contents=prompt)
    answer = response.text

    # Step 4: Translate answer back to user's language.
    # Translate line-by-line to preserve WhatsApp list formatting.
    if user_lang != "en-IN" and user_lang in SARVAM_LANG_CODES:
        translated_lines = []
        for line in answer.split("\n"):
            if not line.strip():
                translated_lines.append("")
                continue
            translated = detect_and_translate(line, target_lang=user_lang)
            translated_lines.append(translated["translated_text"].strip())
        final_answer = "\n".join(translated_lines)
    else:
        final_answer = answer

    return {
        "answer": final_answer,
        "answer_en": answer,
        "user_lang": user_lang,
    }
