def route_tools(query, chunks, user_profile):
    """
    Route to eligibility or checklist tool using Gemini function calling (official template).
    Uses Sarvam translation for input/output.
    """
    from google import genai
    from google.genai import types
    from app.services.agent.eligibility_tool import check_eligibility
    from app.services.agent.checklist_tool import generate_checklist
    from app.services.audio.translate_sarvam import detect_and_translate
    from app.services.llm.gemini_client import generate_with_fallback

    # Step 1: Translate input to English (if needed)
    detected = detect_and_translate(query, target_lang="en-IN")
    english_query = detected["translated_text"]
    user_lang = detected["source_language_code"]

    # Step 2: Configure Gemini tools
    config = types.GenerateContentConfig(
        tools=[check_eligibility, generate_checklist],
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="AUTO")
        )
    )

    # Step 3: Call Gemini with round-robin fallback
    response = generate_with_fallback(
        contents=english_query,
        config=config,
    )
    answer = response.text
    # Step 4: Translate answer back to user's language
    from app.services.audio.translate_sarvam import SARVAM_LANG_CODES
    if user_lang != "en-IN" and user_lang in SARVAM_LANG_CODES:
        translated = detect_and_translate(answer, target_lang=user_lang)
        final_answer = translated["translated_text"]
    else:
        final_answer = answer

    return {
        "answer": final_answer,
        "answer_en": answer,
        "citations": getattr(response, "citations", None),
        "user_lang": user_lang
    }
