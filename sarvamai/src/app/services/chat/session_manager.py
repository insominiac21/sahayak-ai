"""
Session Manager for Multi-Turn Conversations

Handles:
- User session creation (per WhatsApp phone number)
- Conversation history tracking via Supabase
- Context injection for follow-ups
- Session state management (previous scheme, intent, etc.)

Database Schema (Supabase Postgres):

1. user_sessions table
   - session_id (UUID primary key)
   - user_phone_number (VARCHAR, unique, indexed)
   - session_state (VARCHAR) - "main_menu", "qna_active", "closed"
   - conversation_context (JSONB) - stores metadata
   - created_at (TIMESTAMP)
   - last_message_at (TIMESTAMP)
   - expires_at (TIMESTAMP)

2. conversation_history table
   - history_id (UUID primary key)
   - session_id (FK to user_sessions)
   - turn_number (INT) - Sequence in conversation
   - user_query (TEXT)
   - user_query_reformulated (TEXT)
   - intent_detected (VARCHAR)
   - retrieved_scheme_names (JSONB array)
   - bot_answer (TEXT)
   - timestamp (TIMESTAMP)
"""

from typing import List, Dict, Optional
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """Single turn in a conversation."""
    history_id: str
    session_id: str
    turn_number: int
    user_query: str
    user_query_reformulated: Optional[str]
    intent_detected: Optional[str]
    retrieved_scheme_names: List[str]
    bot_answer: str
    timestamp: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database storage."""
        return asdict(self)


@dataclass
class UserSession:
    """User session for multi-turn conversation tracking."""
    session_id: str
    user_phone_number: str
    session_state: str  # "main_menu", "qna_active", "closed"
    conversation_context: Dict
    created_at: str
    last_message_at: str
    expires_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database storage."""
        return asdict(self)


class SessionManager:
    """
    Manages multi-turn conversation sessions with Supabase persistence.
    
    Responsibilities:
    - Create/retrieve user sessions (per phone number)
    - Track conversation history in Supabase
    - Maintain context for follow-ups
    - Manage session state (main_menu, qna_active, closed)
    """
    
    def __init__(self, supabase_client=None):
        """
        Initialize session manager.
        
        Args:
            supabase_client: Supabase client instance (optional)
        """
        self.db = supabase_client
        self.sessions = {}  # In-memory cache for current session
        self._init_db()
    
    def _init_db(self):
        """Initialize Supabase client if not provided."""
        if self.db is None:
            try:
                from app.core.supabase_client import supabase_manager
                self.db = supabase_manager.get_client()
                if self.db is None:
                    logger.warning("Supabase not configured, using in-memory storage only")
            except Exception as e:
                logger.warning(f"Could not initialize Supabase: {e}")
    
    def get_or_create_session(
        self,
        phone_number: str,
        language: str = "en",
    ) -> UserSession:
        """
        Get existing session or create new one.
        
        Args:
            phone_number: WhatsApp phone number (normalized, e.g., "+919876543210")
            language: User language (en, hi, ta, te)
            
        Returns:
            UserSession object
        """
        # Check in-memory cache first
        if phone_number in self.sessions:
            return self.sessions[phone_number]
        
        now = datetime.utcnow().isoformat()
        
        # Try to load from Supabase
        if self.db:
            try:
                response = self.db.table("user_sessions").select("*").eq(
                    "user_phone_number", phone_number
                ).execute()
                
                if response.data and len(response.data) > 0:
                    session_data = response.data[0]
                    session = UserSession(
                        session_id=session_data["session_id"],
                        user_phone_number=session_data["user_phone_number"],
                        session_state=session_data.get("session_state", "qna_active"),
                        conversation_context=session_data.get("conversation_context", {}),
                        created_at=session_data["created_at"],
                        last_message_at=session_data["last_message_at"],
                        expires_at=session_data.get("expires_at"),
                    )
                    self.sessions[phone_number] = session
                    return session
            except Exception as e:
                logger.warning(f"Error retrieving session from DB: {e}")
        
        # Create new session
        session = UserSession(
            session_id=str(uuid.uuid4()),
            user_phone_number=phone_number,
            session_state="qna_active",
            conversation_context={
                "language": language,
                "first_message_timestamp": now,
            },
            created_at=now,
            last_message_at=now,
        )
        
        # Save to Supabase
        if self.db:
            try:
                self.db.table("user_sessions").insert(session.to_dict()).execute()
                logger.info(f"Created new session in DB for {phone_number}")
            except Exception as e:
                logger.warning(f"Error saving session to DB: {e}")
        
        # Cache locally
        self.sessions[phone_number] = session
        return session
    
    def add_turn(
        self,
        session_id: str,
        user_message: str,
        bot_response: str,
        user_message_reformulated: Optional[str] = None,
        intent_detected: Optional[str] = None,
        retrieved_scheme_names: Optional[List[str]] = None,
    ) -> ConversationTurn:
        """
        Add a conversation turn to history.
        
        Args:
            session_id: Current session ID
            user_message: What user said
            bot_response: How bot responded
            user_message_reformulated: Reformulated query after context injection
            intent_detected: Intent classification
            retrieved_scheme_names: Schemes retrieved in this turn
            
        Returns:
            ConversationTurn object
        """
        # Find session to get turn number
        session = None
        for s in self.sessions.values():
            if s.session_id == session_id:
                session = s
                break
        
        if not session:
            logger.warning(f"Session {session_id} not found, creating new turn anyway")
            turn_number = 1
        else:
            turn_number = len(self._get_local_history(session_id)) + 1
        
        timestamp = datetime.utcnow().isoformat()
        
        turn = ConversationTurn(
            history_id=str(uuid.uuid4()),
            session_id=session_id,
            turn_number=turn_number,
            user_query=user_message,
            user_query_reformulated=user_message_reformulated,
            intent_detected=intent_detected,
            retrieved_scheme_names=retrieved_scheme_names or [],
            bot_answer=bot_response,
            timestamp=timestamp,
        )
        
        # Save to Supabase
        if self.db:
            try:
                self.db.table("conversation_history").insert(turn.to_dict()).execute()
                logger.info(f"Saved turn {turn_number} to DB for session {session_id}")
            except Exception as e:
                logger.warning(f"Error saving turn to DB: {e}")
        
        # Update session last_message_at
        if session:
            session.last_message_at = timestamp
            if intent_detected:
                session.conversation_context["last_intent"] = intent_detected
            if retrieved_scheme_names:
                session.conversation_context["last_scheme"] = retrieved_scheme_names[0]
            
            # Update in DB
            if self.db:
                try:
                    self.db.table("user_sessions").update({
                        "last_message_at": timestamp,
                        "conversation_context": session.conversation_context,
                    }).eq("session_id", session_id).execute()
                except Exception as e:
                    logger.warning(f"Error updating session in DB: {e}")
        
        return turn
    
    def _get_local_history(self, session_id: str) -> List[ConversationTurn]:
        """Get history stored locally (for testing)."""
        # This will be replaced by actual DB queries in production
        return []
    
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
        if not self.db:
            return []
        
        try:
            response = self.db.table("conversation_history").select("*").eq(
                "session_id", session_id
            ).order("turn_number", desc=True).limit(limit).execute()
            
            turns = []
            for row in response.data:
                turn = ConversationTurn(
                    history_id=row["history_id"],
                    session_id=row["session_id"],
                    turn_number=row["turn_number"],
                    user_query=row["user_query"],
                    user_query_reformulated=row.get("user_query_reformulated"),
                    intent_detected=row.get("intent_detected"),
                    retrieved_scheme_names=row.get("retrieved_scheme_names", []),
                    bot_answer=row["bot_answer"],
                    timestamp=row["timestamp"],
                )
                turns.append(turn)
            
            return turns
        except Exception as e:
            logger.warning(f"Error retrieving history from DB: {e}")
            return []
    
    def get_context_for_follow_up(self, session_id: str) -> Dict:
        """
        Get context for answering a follow-up question.
        
        Returns:
            Dict with:
            - last_scheme: Last scheme discussed
            - last_intent: Last detected intent
            - conversation_history: Last 3-5 turns
            - language: User language
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
            "last_scheme": session.conversation_context.get("last_scheme"),
            "last_intent": session.conversation_context.get("last_intent"),
            "conversation_history": [t.to_dict() for t in reversed(history)],  # oldest first
            "language": session.conversation_context.get("language", "en"),
            "session_turn_count": len(history),
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
