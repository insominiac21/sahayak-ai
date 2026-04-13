"""
Session Manager for Multi-Turn Conversations

Handles:
- User session creation (per WhatsApp phone number)
- Conversation history tracking
- Context injection for follow-ups
- Session state management (previous scheme, intent, etc.)

Database Schema (Supabase Postgres):

1. user_sessions table
   - session_id (UUID primary key)
   - phone_number (VARCHAR, unique, indexed)
   - first_message_at (TIMESTAMP)
   - last_message_at (TIMESTAMP)
   - conversation_count (INT)
   - current_intent (VARCHAR) - "scheme_inquiry", "eligibility_check", etc.
   - current_scheme (VARCHAR) - Last scheme discussed
   - user_language (VARCHAR) - Detected language (hindi, tamil, english, etc.)

2. conversation_history table
   - message_id (UUID primary key)
   - session_id (FK to user_sessions)
   - message_number (INT) - Sequence in conversation
   - user_message (TEXT)
   - bot_response (TEXT)
   - scheme_mentioned (VARCHAR)
   - intent_detected (VARCHAR)
   - chunks_used (JSONB array of chunk_ids)
   - created_at (TIMESTAMP)
"""

from typing import List, Dict, Optional
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class ConversationTurn:
    """Single turn in a conversation."""
    message_id: str
    session_id: str
    message_number: int
    user_message: str
    bot_response: str
    scheme_mentioned: Optional[str] = None
    intent_detected: Optional[str] = None
    chunks_used: Optional[List[str]] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database storage."""
        return asdict(self)


@dataclass
class UserSession:
    """User session for multi-turn conversation tracking."""
    session_id: str
    phone_number: str
    first_message_at: str
    last_message_at: str
    conversation_count: int
    current_intent: Optional[str] = None
    current_scheme: Optional[str] = None
    user_language: str = "english"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database storage."""
        return asdict(self)


class SessionManager:
    """
    Manages multi-turn conversation sessions.
    
    Responsibilities:
    - Create/retrieve user sessions (per phone number)
    - Track conversation history
    - Maintain context for follow-ups
    - Detect intent and scheme mentions
    """
    
    def __init__(self, supabase_client=None):
        """
        Initialize session manager.
        
        Args:
            supabase_client: Supabase client instance (optional for testing)
        """
        self.db = supabase_client
        self.sessions = {}  # In-memory cache during development
    
    def get_or_create_session(
        self,
        phone_number: str,
        language: str = "en",
    ) -> UserSession:
        """
        Get existing session or create new one.
        
        Args:
            phone_number: WhatsApp phone number (normalized)
            language: User language (en, hi, ta, te)
            
        Returns:
            UserSession object
        """
        # Check in-memory cache
        if phone_number in self.sessions:
            return self.sessions[phone_number]
        
        # In production: query Supabase
        # For now: create new session
        now = datetime.utcnow().isoformat()
        
        # Map language codes
        lang_map = {
            "en": "english",
            "hi": "hindi",
            "ta": "tamil",
            "te": "telugu",
        }
        
        session = UserSession(
            session_id=str(uuid.uuid4()),
            phone_number=phone_number,
            first_message_at=now,
            last_message_at=now,
            conversation_count=0,
            user_language=lang_map.get(language, "english"),
        )
        
        self.sessions[phone_number] = session
        return session
    
    def add_turn(
        self,
        session_id: str,
        user_message: str,
        bot_response: str,
        scheme_mentioned: Optional[str] = None,
        intent_detected: Optional[str] = None,
        chunks_used: Optional[List[str]] = None,
    ) -> ConversationTurn:
        """
        Add a conversation turn to history.
        
        Args:
            session_id: Current session ID
            user_message: What user said
            bot_response: How bot responded
            scheme_mentioned: Scheme name if detected
            intent_detected: Intent classification
            chunks_used: Which retrieval chunks were used
            
        Returns:
            ConversationTurn object
        """
        # Get session to increment counter
        session = None
        for s in self.sessions.values():
            if s.session_id == session_id:
                session = s
                break
        
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        message_number = session.conversation_count + 1
        
        turn = ConversationTurn(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            message_number=message_number,
            user_message=user_message,
            bot_response=bot_response,
            scheme_mentioned=scheme_mentioned,
            intent_detected=intent_detected,
            chunks_used=chunks_used or [],
            created_at=datetime.utcnow().isoformat(),
        )
        
        # Update session
        session.conversation_count = message_number
        session.last_message_at = turn.created_at
        if intent_detected:
            session.current_intent = intent_detected
        if scheme_mentioned:
            session.current_scheme = scheme_mentioned
        
        # In production: save to Supabase
        return turn
    
    def get_conversation_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[ConversationTurn]:
        """
        Get recent conversation history for context.
        
        Args:
            session_id: Session ID
            limit: Max number of turns to retrieve
            
        Returns:
            List of ConversationTurn objects (most recent first)
        """
        # In production: query Supabase
        # For now: return empty (will be populated from DB)
        return []
    
    def get_context_for_follow_up(self, session_id: str) -> Dict:
        """
        Get context for answering a follow-up question.
        
        Returns:
            Dict with:
            - previous_scheme: Last scheme discussed
            - previous_intent: Last detected intent
            - conversation_history: Last 3-5 turns
            - user_language: Detected language
        """
        # Get session
        session = None
        for s in self.sessions.values():
            if s.session_id == session_id:
                session = s
                break
        
        if not session:
            return {}
        
        # Get context
        history = self.get_conversation_history(session_id, limit=5)
        
        return {
            "previous_scheme": session.current_scheme,
            "previous_intent": session.current_intent,
            "conversation_history": [t.to_dict() for t in history],
            "user_language": session.user_language,
            "session_turn_count": session.conversation_count,
        }


# Global instance
_session_manager = None

def get_session_manager(supabase_client=None) -> SessionManager:
    """
    Get or create global session manager.
    
    Args:
        supabase_client: Supabase client (optional, for initialization)
        
    Returns:
        SessionManager singleton
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(supabase_client=supabase_client)
    return _session_manager
