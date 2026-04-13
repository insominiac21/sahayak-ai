"""
Query Reformulator for Context-Aware Follow-Ups

Examples:
User: "What documents do I need?"
Context: Was discussing PMAY-U (housing scheme)
Reformulated: "What documents do I need for PMAY-U (Pradhan Mantri Awas Yojana)?"

User: "What are the eligibility criteria?"
Context: Was discussing APY (pension scheme)
Reformulated: "What are the eligibility criteria for APY (Atal Pension Yojana)?"

This allows retrieval to better match context even when user is being implicit.
"""

from typing import Optional, Dict
from app.services.chat.intent_classifier import get_intent_classifier


class QueryReformulator:
    """
    Reformulate ambiguous follow-up queries with context.
    
    Helps retriever understand implicit references to previous schemes
    and intents, improving retrieval quality for follow-up questions.
    """
    
    # Scheme full names for context injection
    SCHEME_FULLNAMES = {
        "pm-kisan": "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
        "pmay-u": "PMAY-U (Pradhan Mantri Awas Yojana - Urban)",
        "pmuy": "PMUY (Pradhan Mantri Ujjwala Yojana)",
        "ayushman bharat": "Ayushman Bharat PM-JAY",
        "nsap": "NSAP (National Social Assistance Programme)",
        "sukanya samriddhi": "Sukanya Samriddhi Yojana (SSY)",
        "apy": "APY (Atal Pension Yojana)",
        "stand-up india": "Stand-Up India Scheme",
        "pmjdy": "PMJDY (Pradhan Mantri Jan Dhan Yojana)",
    }
    
    # Intent-based query templates
    INTENT_TEMPLATES = {
        "eligibility_check": "eligibility criteria|requirements|who is eligible",
        "documents_needed": "documents needed|documents required|what documents",
        "how_to_apply": "how to apply|application process|how do I register",
        "benefits_details": "benefits|what you get|coverage|entitlements",
    }
    
    def __init__(self):
        """Initialize reformulator."""
        self.classifier = get_intent_classifier()
    
    def reformulate(
        self,
        query: str,
        previous_scheme: Optional[str] = None,
        previous_intent: Optional[str] = None,
    ) -> str:
        """
        Reformulate query with context if needed.
        
        Args:
            query: Original user query
            previous_scheme: Scheme from previous message (if any)
            previous_intent: Intent from previous message (if any)
            
        Returns:
            Reformulated query (or original if already explicit)
        """
        # Check if query already mentions a scheme (is explicit)
        current_scheme = self.classifier.extract_scheme(query)
        
        # If query is explicit enough, return as-is
        if current_scheme or not previous_scheme:
            return query
        
        # Query is implicit follow-up referring to previous scheme
        # Reformulate to include scheme context
        
        scheme_fullname = self.SCHEME_FULLNAMES.get(
            previous_scheme,
            previous_scheme
        )
        
        # Add scheme context to query
        reformulated = f"{query} (referring to {scheme_fullname})"
        
        return reformulated
    
    def inject_context(
        self,
        query: str,
        context: Dict,
    ) -> str:
        """
        Inject conversation context into query.
        
        Handles:
        - Adding previous scheme name
        - Adding previous intent
        - Adding relevant history snippets
        
        Args:
            query: User query
            context: Dict from session_manager.get_context_for_follow_up()
                    with keys: previous_scheme, previous_intent, conversation_history, etc.
            
        Returns:
            Query with context injected
        """
        previous_scheme = context.get("previous_scheme")
        previous_intent = context.get("previous_intent")
        history = context.get("conversation_history", [])
        
        # If no context, return original
        if not previous_scheme and not history:
            return query
        
        # Check if this is a follow-up (implicit reference)
        current_scheme = self.classifier.extract_scheme(query)
        
        if not current_scheme and previous_scheme:
            # Implicit follow-up - add scheme context
            scheme_fullname = self.SCHEME_FULLNAMES.get(
                previous_scheme,
                previous_scheme
            )
            
            # Build context string
            context_parts = [f"[Previous scheme: {scheme_fullname}]"]
            
            if history:
                # Add last user question for reference
                last_turn = history[-1] if isinstance(history, list) else None
                if last_turn and isinstance(last_turn, dict):
                    last_question = last_turn.get("user_message", "")
                    if last_question:
                        context_parts.append(f"[Last question was: {last_question}]")
            
            # Combine
            context_str = " ".join(context_parts)
            reformulated = f"{context_str}\nCurrent question: {query}"
            
            return reformulated
        
        # Query is already explicit, just return it
        return query
    
    def is_reformulation_needed(
        self,
        query: str,
        previous_scheme: Optional[str] = None,
    ) -> bool:
        """
        Check if reformulation would help.
        
        Args:
            query: User query
            previous_scheme: Previous scheme discussed
            
        Returns:
            True if reformulation recommended
        """
        if not previous_scheme:
            return False
        
        # Check if query explicitly mentions a scheme
        current_scheme = self.classifier.extract_scheme(query)
        if current_scheme:
            return False
        
        # Check for follow-up indicators
        follow_up_indicators = [
            r"that|it|this|same|previous|above",
            r"अब|अगला|फिर|वही",
            r"அதை|இதை|அந்த",
        ]
        
        import re
        for indicator in follow_up_indicators:
            if re.search(indicator, query.lower()):
                return True
        
        # Check for question-only patterns (no scheme stated)
        question_only = [
            r"^(what|how|where|when|why|who|can|am|do|is)",
            r"^(क्या|कहाँ|कब|कैसे|किसे)",
            r"^(என்ன|எப்போது|எங்கே)",
        ]
        
        for pattern in question_only:
            if re.search(pattern, query.lower()):
                return True
        
        return False


def create_query_reformulator() -> QueryReformulator:
    """Factory function."""
    return QueryReformulator()


# Global instance
_reformulator = None

def get_query_reformulator() -> QueryReformulator:
    """Get or create global reformulator."""
    global _reformulator
    if _reformulator is None:
        _reformulator = QueryReformulator()
    return _reformulator
