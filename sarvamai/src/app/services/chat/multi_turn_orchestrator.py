"""
Multi-Turn Orchestrator

Orchestrates the complete Phase 2 pipeline:
1. Session management (track user across messages)
2. Intent detection (understand what user wants)
3. Query reformulation (expand implicit follow-ups)
4. Context injection (augment with conversation history)
5. Two-stage retrieval (retrieve with context)
6. Response generation (use retrieved chunks)

This module is the glue that ties all Phase 2 components together.

Usage:
    orchestrator = get_multi_turn_orchestrator()
    
    # First message from user
    result = orchestrator.process_message(
        phone_number="+919876543210",
        user_message="What is PM-KISAN?",
    )
    print(f"Response: {result.bot_response}")
    
    # Follow-up message
    result = orchestrator.process_message(
        phone_number="+919876543210",
        user_message="What documents do I need?",  # Implicit follow-up
    )
    # Orchestrator will:
    # 1. Restore session
    # 2. Detect this is "documents_needed" intent
    # 3. Reformulate to "What documents for PM-KISAN?"
    # 4. Inject previous context
    # 5. Retrieve with context
    # 6. Generate response based on chunks
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

from app.services.chat.session_manager import get_session_manager
from app.services.chat.intent_classifier import get_intent_classifier
from app.services.chat.query_reformulator import get_query_reformulator
from app.services.chat.context_injector import get_context_injector
from app.services.rag.two_stage_retriever import get_two_stage_retriever

logger = logging.getLogger(__name__)


@dataclass
class MultiTurnResult:
    """Result of processing a multi-turn message."""
    
    session_id: str
    message_id: str
    user_message: str
    bot_response: str
    
    # Pipeline intermediate states
    intent_detected: Optional[str] = None
    scheme_extracted: Optional[str] = None
    reformulated_query: Optional[str] = None
    retrieved_chunks: List[Dict] = field(default_factory=list)
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    latency_ms: float = 0.0
    
    # Debug info
    pipeline_steps: List[str] = field(default_factory=list)


class MultiTurnOrchestrator:
    """
    Orchestrates multi-turn conversation pipeline.
    
    Responsible for:
    - Session lifecycle management
    - Intent classification
    - Query reformulation for follow-ups
    - Context injection for awareness
    - Retrieval orchestration
    - Response generation
    """
    
    def __init__(self):
        """Initialize orchestrator with all components."""
        self.session_manager = get_session_manager()
        self.intent_classifier = get_intent_classifier()
        self.query_reformulator = get_query_reformulator()
        self.context_injector = get_context_injector()
        self.retriever = get_two_stage_retriever()
    
    def process_message(
        self,
        phone_number: str,
        user_message: str,
        language: str = "en",
    ) -> MultiTurnResult:
        """
        Process a user message through the complete multi-turn pipeline.
        
        Pipeline:
        1. Get or create session
        2. Classify intent
        3. Extract scheme mention
        4. Reformulate query if needed
        5. Build context window
        6. Inject context into query
        7. Retrieve with context
        8. Store turn in session
        
        Args:
            phone_number: User's phone number (session identifier)
            user_message: Raw user input
            language: Language of user message (en, hi, ta, te)
            
        Returns:
            MultiTurnResult with bot response and metadata
        """
        import time
        start_time = time.time()
        
        result = MultiTurnResult(
            session_id="",
            message_id="",
            user_message=user_message,
            bot_response="",
        )
        
        try:
            # Step 1: Session management
            result.pipeline_steps.append("session_lookup")
            session = self.session_manager.get_or_create_session(
                phone_number=phone_number,
                language=language,
            )
            result.session_id = session.session_id
            logger.info(f"Session: {session.session_id} ({session.conversation_count} turns)")
            
            # Step 2: Intent classification
            result.pipeline_steps.append("intent_classification")
            intent_result = self.intent_classifier.classify(user_message)
            intent_name = intent_result[0] if intent_result else None
            result.intent_detected = intent_name
            logger.info(f"Intent: {intent_name}")
            
            # Step 3: Extract scheme
            result.pipeline_steps.append("scheme_extraction")
            scheme = self.intent_classifier.extract_scheme(user_message)
            result.scheme_extracted = scheme
            if scheme:
                logger.info(f"Scheme: {scheme}")
            
            # Step 4: Get session context
            result.pipeline_steps.append("context_building")
            session_context = self.session_manager.get_context_for_follow_up(
                session.session_id
            )
            
            # Step 5: Query reformulation
            result.pipeline_steps.append("query_reformulation")
            previous_scheme = session_context.get("previous_scheme")
            
            if self.query_reformulator.is_reformulation_needed(
                user_message,
                previous_scheme
            ):
                reformulated = self.query_reformulator.reformulate(
                    user_message,
                    previous_scheme=previous_scheme,
                )
                result.reformulated_query = reformulated
                retrieval_query = reformulated
                logger.info(f"Reformulated: {reformulated}")
            else:
                retrieval_query = user_message
            
            # Step 6: Context injection
            result.pipeline_steps.append("context_injection")
            context_window = self.context_injector.build_context_window(
                session_context
            )
            
            # Determine if injection would help
            if self.context_injector.should_inject_context(
                retrieval_query,
                context_window
            ):
                injected_query = self.context_injector.inject_into_query(
                    retrieval_query,
                    context_window,
                    mode="balanced",  # Safe default: scheme + intent
                )
                logger.info(f"Context injected: {injected_query}")
            else:
                injected_query = retrieval_query
            
            # Step 7: Retrieval
            result.pipeline_steps.append("two_stage_retrieval")
            retrieval_result = self.retriever.retrieve(
                injected_query,
                return_full_pipeline=True,
            )
            
            # Handle both list and dict return types
            if isinstance(retrieval_result, list):
                retrieved_chunks = retrieval_result
            else:
                retrieved_chunks = retrieval_result.get(
                    "final_results", 
                    retrieval_result.get("results", [])
                )
            result.retrieved_chunks = retrieved_chunks
            logger.info(f"Retrieved: {len(retrieved_chunks)} chunks")
            
            # Step 8: Response generation (placeholder - uses chunks)
            result.pipeline_steps.append("response_generation")
            bot_response = self._generate_response(
                user_message,
                intent_name,
                scheme,
                retrieved_chunks,
            )
            result.bot_response = bot_response
            
            # Step 9: Store turn in session
            result.pipeline_steps.append("session_store")
            turn = self.session_manager.add_turn(
                session_id=session.session_id,
                user_message=user_message,
                bot_response=bot_response,
                intent_detected=intent_name,
                scheme_mentioned=scheme or previous_scheme,
                chunks_used=[c.get("chunk_id") for c in retrieved_chunks],
            )
            result.message_id = turn.message_id
            
            # Update session scheme and intent
            if scheme:
                session.current_scheme = scheme
            if intent_name:
                session.current_intent = intent_name
            
            result.latency_ms = (time.time() - start_time) * 1000
            logger.info(f"Total latency: {result.latency_ms:.1f}ms")
            
        except Exception as e:
            logger.error(f"Error in orchestrator: {e}", exc_info=True)
            result.bot_response = f"Sorry, I encountered an error: {str(e)}"
            raise
        
        return result
    
    def _generate_response(
        self,
        user_message: str,
        intent: Optional[str],
        scheme: Optional[str],
        chunks: List[Dict],
    ) -> str:
        """
        Generate bot response from retrieved chunks.
        
        Simple version: Extract first chunk + add context.
        
        Args:
            user_message: Original user query
            intent: Detected intent
            scheme: Detected or previous scheme
            chunks: Retrieved answer chunks
            
        Returns:
            Bot response text
        """
        if not chunks:
            # No relevant information found
            return (
                f"I couldn't find specific information about that. "
                f"Could you rephrase your question or mention which scheme you're asking about?"
            )
        
        # Use first chunk as primary answer
        primary_chunk = chunks[0]
        chunk_text = primary_chunk.get("text", "")
        
        if not chunk_text:
            return "I found relevant information but couldn't extract the text."
        
        # Build response
        response_parts = []
        
        # Add scheme context if available
        if scheme:
            response_parts.append(f"[Regarding {scheme}]\n")
        
        # Add chunk content
        response_parts.append(chunk_text)
        
        # Add pointer to additional info
        if len(chunks) > 1:
            response_parts.append(f"\n\n(I have {len(chunks)-1} more relevant pieces of information available.)")
        
        return "".join(response_parts)
    
    def get_session_status(self, session_id: str) -> Dict:
        """
        Get current status of a session.
        
        Args:
            session_id: Session ID to check
            
        Returns:
            Dict with session info
        """
        # This would need session lookup - placeholder
        return {
            "session_id": session_id,
            "status": "active",
        }


def create_multi_turn_orchestrator() -> MultiTurnOrchestrator:
    """Factory function."""
    return MultiTurnOrchestrator()


# Global instance
_orchestrator = None

def get_multi_turn_orchestrator() -> MultiTurnOrchestrator:
    """Get or create global orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiTurnOrchestrator()
    return _orchestrator
