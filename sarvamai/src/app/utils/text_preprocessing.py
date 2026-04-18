"""
Text preprocessing utilities for handling user input errors.
Handles spelling mistakes and grammatical corrections with language detection.
"""

import logging
from typing import Tuple
import re

logger = logging.getLogger(__name__)

try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False
    logger.warning("textblob not installed. Spell-check will be skipped.")

try:
    from spellchecker import SpellChecker
    HAS_SPELLCHECKER = True
except ImportError:
    HAS_SPELLCHECKER = False

try:
    from langdetect import detect, detect_langs
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False
    logger.warning("langdetect not installed. Language detection will use fallback method.")


def correct_spelling(text: str) -> str:
    """
    Correct spelling mistakes in text using TextBlob or spellchecker.
    ONLY applies to English or code-mixed text. Preserves non-English text.
    
    Args:
        text: Input text with potential spelling mistakes
        
    Returns:
        Text with spelling corrections applied (if English/code-mixed)
    """
    if not text or len(text) < 2:
        return text
    
    # Detect language first
    detected_lang = detect_language(text)
    
    # Only correct spelling if English or code-mixed (likely has English component)
    if detected_lang not in ['en', 'code-mixed']:
        logger.debug(f"Skipping spell-check for {detected_lang} text: '{text}'")
        return text
    
    # Try TextBlob first (better for context-aware corrections)
    if HAS_TEXTBLOB:
        try:
            corrected = str(TextBlob(text).correct())
            if corrected != text:
                logger.debug(f"TextBlob spell correction: '{text}' → '{corrected}'")
            return corrected
        except Exception as e:
            logger.debug(f"TextBlob spell-check error: {e}")
    
    # Fallback to spellchecker if TextBlob not available
    if HAS_SPELLCHECKER:
        try:
            spell = SpellChecker()
            words = text.split()
            corrected_words = []
            
            for word in words:
                # Check if word is misspelled (but preserve common Indian terms)
                if word.lower() not in spell and not _is_indian_term(word) and not _is_hindi_word(word):
                    correction = spell.correction(word)
                    if correction:
                        corrected_words.append(correction)
                        logger.debug(f"Spell correction: '{word}' → '{correction}'")
                    else:
                        corrected_words.append(word)
                else:
                    corrected_words.append(word)
            
            return " ".join(corrected_words)
        except Exception as e:
            logger.debug(f"SpellChecker error: {e}")
    
    # If no spell-checker available, return original text
    return text


def correct_grammar(text: str) -> str:
    """
    Correct basic grammatical errors in text.
    ONLY applies to English or code-mixed text. Preserves non-English text.
    
    Args:
        text: Input text with potential grammar issues
        
    Returns:
        Text with grammar corrections applied (if English/code-mixed)
    """
    if not text or len(text) < 2:
        return text
    
    # Detect language first
    detected_lang = detect_language(text)
    
    # Only correct grammar if English or code-mixed
    if detected_lang not in ['en', 'code-mixed']:
        logger.debug(f"Skipping grammar check for {detected_lang} text: '{text}'")
        return text
    
    if HAS_TEXTBLOB:
        try:
            # TextBlob provides grammar checking via parse and lemmatization
            blob = TextBlob(text)
            corrected = str(blob.correct())
            
            # Additional grammar fixes
            corrected = _fix_common_grammar(corrected)
            
            if corrected != text:
                logger.debug(f"Grammar correction: '{text}' → '{corrected}'")
            return corrected
        except Exception as e:
            logger.debug(f"Grammar correction error: {e}")
    
    # Apply basic grammar rules even without TextBlob
    return _fix_common_grammar(text)


def _fix_common_grammar(text: str) -> str:
    """
    Apply regex-based fixes for common grammatical patterns.
    
    Args:
        text: Input text
        
    Returns:
        Text with basic grammar fixes
    """
    # Fix spacing around punctuation
    text = re.sub(r'\s+([?.!,;:])', r'\1', text)
    
    # Fix double spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Capitalize first letter of sentence
    text = re.sub(r'(?:^|(?<=\.\s))([a-z])', lambda m: m.group(1).upper(), text)
    
    # Remove trailing spaces
    text = text.strip()
    
    return text


def _is_hindi_word(word: str) -> bool:
    """
    Check if word contains Devanagari script (Hindi).
    
    Args:
        word: Word to check
        
    Returns:
        True if word contains Devanagari characters
    """
    # Unicode range for Devanagari script
    for char in word:
        if '\u0900' <= char <= '\u097F':
            return True
    return False


def detect_language(text: str) -> str:
    """
    Detect language of the text with robust fallback.
    Returns: 'en', 'hi', 'code-mixed', or other ISO 639-1 code.
    
    Args:
        text: Text to detect language for
        
    Returns:
        Language code: 'en' (English), 'hi' (Hindi), 'code-mixed', or other ISO code
    """
    if not text or len(text) < 2:
        return 'en'  # Default to English
    
    # Method 1: langdetect (most reliable)
    if HAS_LANGDETECT:
        try:
            # Check for code-mixing (both English and non-English scripts)
            has_latin = bool(re.search(r'[a-zA-Z]', text))
            has_devanagari = bool(re.search(r'[\u0900-\u097F]', text))
            has_tamil = bool(re.search(r'[\u0B80-\u0BFF]', text))
            has_telugu = bool(re.search(r'[\u0C60-\u0C7F]', text))
            has_kannada = bool(re.search(r'[\u0C80-\u0CFF]', text))
            has_malayalam = bool(re.search(r'[\u0D00-\u0D7F]', text))
            
            # If both Latin and Indian scripts present, it's code-mixed
            if has_latin and (has_devanagari or has_tamil or has_telugu or has_kannada or has_malayalam):
                logger.debug(f"Detected code-mixed text: '{text[:50]}...'")
                return 'code-mixed'
            
            # If only Indian scripts
            if has_devanagari and not has_latin:
                return 'hi'  # Devanagari is primarily Hindi
            if has_tamil and not has_latin:
                return 'ta'
            if has_telugu and not has_latin:
                return 'te'
            if has_kannada and not has_latin:
                return 'kn'
            if has_malayalam and not has_latin:
                return 'ml'
            
            # Use langdetect for remaining cases
            detected = detect(text)
            logger.debug(f"langdetect detected: {detected}")
            return detected
        except Exception as e:
            logger.debug(f"langdetect error: {e}. Falling back to script detection.")
    
    # Method 2: Script-based detection (fallback)
    has_latin = bool(re.search(r'[a-zA-Z]', text))
    has_devanagari = bool(re.search(r'[\u0900-\u097F]', text))
    has_tamil = bool(re.search(r'[\u0B80-\u0BFF]', text))
    has_telugu = bool(re.search(r'[\u0C60-\u0C7F]', text))
    has_kannada = bool(re.search(r'[\u0C80-\u0CFF]', text))
    has_malayalam = bool(re.search(r'[\u0D00-\u0D7F]', text))
    has_gujarati = bool(re.search(r'[\u0A80-\u0AFF]', text))
    has_punjabi = bool(re.search(r'[\u0A00-\u0A7F]', text))
    
    # Code-mixed detection
    if has_latin and (has_devanagari or has_tamil or has_telugu or has_kannada or has_malayalam):
        return 'code-mixed'
    
    # Pure language detection
    if has_devanagari:
        return 'hi'
    if has_tamil:
        return 'ta'
    if has_telugu:
        return 'te'
    if has_kannada:
        return 'kn'
    if has_malayalam:
        return 'ml'
    if has_gujarati:
        return 'gu'
    if has_punjabi:
        return 'pa'
    
    # Default to English if only Latin script
    return 'en'


def _is_indian_term(word: str) -> bool:
    """
    Check if word is a common Indian term (to avoid correcting valid scheme names).
    
    Args:
        word: Word to check
        
    Returns:
        True if word is likely an Indian term
    """
    indian_terms = {
        'yojana', 'pradhan', 'mantri', 'jan', 'dhan', 'atal', 'ayushman', 'bharat',
        'pm', 'pmay', 'pmjdy', 'ssy', 'apy', 'pmuy', 'pm-jay', 'pm-kisan', 'nrega',
        'scheme', 'schemes', 'eligibility', 'income', 'benefits', 'rupees', 'lakh', 'cr',
        'secc', 'bpl', 'apl', 'ews', 'lig', 'mig', 'calamity', 'welfare', 'pension',
        'subsidy', 'loan', 'insurance', 'health', 'housing', 'agriculture', 'rural',
        'urban', 'mgnrega', 'pradhanmantri', 'sarvam', 'sahayak'
    }
    
    return word.lower() in indian_terms


def preprocess_user_input(text: str) -> Tuple[str, str]:
    """
    Complete preprocessing pipeline: language detection → spelling + grammar correction.
    
    Args:
        text: Raw user input
        
    Returns:
        Tuple of (corrected_text, original_text)
    """
    if not text:
        return text, text
    
    original = text
    
    # Detect language first (log for transparency)
    detected_lang = detect_language(text)
    logger.info(f"🌐 Detected language: {detected_lang} | Input: '{original[:60]}...'")
    
    # Step 1: Correct spelling (only for English/code-mixed)
    corrected = correct_spelling(text)
    
    # Step 2: Correct grammar (only for English/code-mixed)
    corrected = correct_grammar(corrected)
    
    # Log if corrections were made
    if corrected != original:
        logger.info(f"✏️ Auto-corrected ({detected_lang}): '{original}' → '{corrected}'")
    
    return corrected, original
