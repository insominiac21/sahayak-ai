"""
Context Injector for Multi-Turn Conversation Awareness

Augments retrieval queries with conversation context from previous turns.

Example Flow:
1. User asks: "What documents do I need for PMAY-U?"
   → Retrieve and answer: [List of documents]
   
2. User follows up: "Can I submit Aadhaar instead?"
   → Injected context: "We have discussed PMAY-U and talked about documents. 
     The user asked about alternative documents"
   → Retrieve with this context
   → Better results because retriever knows we're still talking about PMAY-U documents

This module builds context vectors for more natural conversation flow.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass


@dataclass
class ContextWindow:
    """Context window for retrieval augmentation."""
    
    scheme_name: Optional[str] = None
    current_intent: Optional[str] = None
    last_3_questions: List[str] = None
    last_3_responses: List[str] = None
    conversation_summary: Optional[str] = None
    user_mention_history: Dict[str, int] = None
    
    def __post_init__(self):
        """Initialize defaults."""
        if self.last_3_questions is None:
            self.last_3_questions = []
        if self.last_3_responses is None:
            self.last_3_responses = []
        if self.user_mention_history is None:
            self.user_mention_history = {}


class ContextInjector:
    """
    Inject conversation context into retrieval queries.
    
    Balances:
    - Including enough context for semantic understanding
    - Avoiding "context pollution" that hurts relevance
    - Managing token budgets for embedding models
    """
    
    # Context injection templates
    CONTEXT_TEMPLATES = {
        "scheme_focus": "Conversation context: User is asking about {scheme}.",
        "multi_scheme": "User has asked about multiple schemes: {schemes}. Current focus: {scheme}.",
        "follow_up": "This is a follow-up question. Previous: {prev_q}. Now asking: {curr_q}",
        "intent_continuation": "User wants to know about {intent} for {scheme}.",
        "clarification": "User is asking for clarification on previous information about {scheme}.",
    }
    
    # Context truncation settings
    MAX_CONTEXT_TOKENS = 100  # ~200 chars for BM25, rest for embedding
    MAX_HISTORY_TURNS = 3  # Keep last 3 turns
    
    def __init__(self):
        """Initialize injector."""
        pass
    
    def build_context_window(
        self,
        session_context: Dict[str, Any],
    ) -> ContextWindow:
        """
        Build context window from session data.
        
        Args:
            session_context: Dict from SessionManager.get_context_for_follow_up()
            
        Returns:
            ContextWindow with conversation state
        """
        scheme = session_context.get("previous_scheme")
        intent = session_context.get("previous_intent")
        history = session_context.get("conversation_history", [])
        
        # Extract last N turns
        last_questions = []
        last_responses = []
        
        for turn in history[-self.MAX_HISTORY_TURNS:]:
            if isinstance(turn, dict):
                if "user_message" in turn:
                    last_questions.append(turn["user_message"][:100])
                if "bot_response" in turn:
                    # Extract first 50 chars of response
                    response = turn["bot_response"]
                    if isinstance(response, str):
                        last_responses.append(response[:50])
        
        # Build summary
        summary = self._build_summary(scheme, intent, history)
        
        return ContextWindow(
            scheme_name=scheme,
            current_intent=intent,
            last_3_questions=last_questions,
            last_3_responses=last_responses,
            conversation_summary=summary,
        )
    
    def _build_summary(
        self,
        scheme: Optional[str],
        intent: Optional[str],
        history: List,
    ) -> Optional[str]:
        """Build one-line conversation summary."""
        if not scheme and not intent and not history:
            return None
        
        parts = []
        
        if scheme:
            parts.append(f"discussing {scheme}")
        
        if intent and scheme:
            parts.append(f"asking about {intent}")
        
        if len(history) >= 2:
            parts.append(f"({len(history)} previous turns)")
        
        if parts:
            return "User is " + " and ".join(parts) + "."
        
        return None
    
    def inject_into_query(
        self,
        query: str,
        context_window: ContextWindow,
        mode: str = "minimal",
    ) -> str:
        """
        Inject context into query string.
        
        Args:
            query: Original query
            context_window: ContextWindow with conversation state
            mode: "minimal" (scheme only), "balanced" (scheme + intent), 
                  "full" (include history)
            
        Returns:
            Query with context injected
        """
        if mode == "minimal":
            return self._inject_minimal(query, context_window)
        elif mode == "balanced":
            return self._inject_balanced(query, context_window)
        elif mode == "full":
            return self._inject_full(query, context_window)
        else:
            return query
    
    def _inject_minimal(self, query: str, context_window: ContextWindow) -> str:
        """Inject only scheme context (safest)."""
        if not context_window.scheme_name:
            return query
        
        # Just add scheme name at end
        return f"{query} (about {context_window.scheme_name})"
    
    def _inject_balanced(self, query: str, context_window: ContextWindow) -> str:
        """Inject scheme + intent context."""
        parts = [query]
        
        if context_window.scheme_name:
            parts.append(f"[Scheme: {context_window.scheme_name}]")
        
        if context_window.current_intent:
            parts.append(f"[Intent: {context_window.current_intent}]")
        
        return " ".join(parts)
    
    def _inject_full(self, query: str, context_window: ContextWindow) -> str:
        """Inject full context including history (use cautiously)."""
        parts = [query]
        
        if context_window.conversation_summary:
            parts.insert(0, context_window.conversation_summary)
        
        if context_window.last_3_questions:
            # Add last question for reference
            parts.append(f"[Previous: {context_window.last_3_questions[-1]}]")
        
        return " ".join(parts)
    
    def should_inject_context(
        self,
        query: str,
        context_window: ContextWindow,
    ) -> bool:
        """
        Determine if context injection would help.
        
        Heuristics:
        - If user mentions a scheme explicitly: No (already in query)
        - If context_window is empty: No (nothing to inject)
        - If query is very specific: Maybe (might hurt relevance)
        - If query is vague: Yes (context helps)
        
        Args:
            query: User query
            context_window: Available context
            
        Returns:
            True if injection recommended
        """
        # Check if context is even available
        if not context_window.scheme_name:
            return False
        
        # Check if query is already explicit (mentions scheme/numbers/keywords)
        from app.services.chat.intent_classifier import get_intent_classifier
        
        classifier = get_intent_classifier()
        mentioned_scheme = classifier.extract_scheme(query)
        
        if mentioned_scheme:
            # Query already explicit
            return False
        
        # Check if query is vague (short, generic)
        if len(query.split()) <= 3:
            # Short questions like "What documents?" → Yes, inject
            return True
        
        # Longer queries often self-contained → Check density
        keywords = [word for word in query.split() if len(word) > 3]
        if len(keywords) < 3:
            # Few meaningful words → Yes, inject
            return True
        
        return True  # Default: inject (helps in most cases)
    
    def get_injection_report(
        self,
        original_query: str,
        injected_query: str,
        context_window: ContextWindow,
    ) -> str:
        """
        Generate report of what was injected (for debugging).
        
        Args:
            original_query: Before injection
            injected_query: After injection
            context_window: What was used
            
        Returns:
            Human-readable report
        """
        report = []
        report.append(f"Original: {original_query}")
        report.append(f"Injected: {injected_query}")
        
        if context_window.scheme_name:
            report.append(f"  + Scheme: {context_window.scheme_name}")
        
        if context_window.current_intent:
            report.append(f"  + Intent: {context_window.current_intent}")
        
        if context_window.conversation_summary:
            report.append(f"  + Summary: {context_window.conversation_summary}")
        
        return "\n".join(report)


def create_context_injector() -> ContextInjector:
    """Factory function."""
    return ContextInjector()


# Global instance
_injector = None

def get_context_injector() -> ContextInjector:
    """Get or create global injector."""
    global _injector
    if _injector is None:
        _injector = ContextInjector()
    return _injector
