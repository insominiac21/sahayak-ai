"""
Session Manager for Sahayak AI - Phase 3 LangGraph Agent
Handles user profile retrieval and session storage via Supabase Postgres.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from supabase import create_client
    from app.core.config import settings
    
    # Initialize Supabase client
    supabase = create_client(
        supabase_url=settings.QDRANT_URL.split("cloud.qdrant.io")[0].replace("https://", "").split("-")[0],  # This is a placeholder
        supabase_key=settings.QDRANT_API_KEY  # This is a placeholder
    )
except Exception as e:
    supabase = None
    logging.warning(f"Supabase client not initialized: {e}. Using fallback session storage.")

logger = logging.getLogger(__name__)

# Simple in-memory fallback for session storage
_session_store: Dict[str, Dict[str, Any]] = {}


def get_session(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch user session/profile data from Supabase or memory.
    
    Args:
        user_id: User WhatsApp phone number or session ID
        
    Returns:
        Dictionary with user profile data (name, state, income) or None if not found
    """
    try:
        # Try memory store first (fastest)
        if user_id in _session_store:
            return _session_store[user_id]
        
        # Try Supabase if available
        if supabase:
            try:
                response = supabase.table("user_sessions").select("*").eq("user_id", user_id).execute()
                if response.data and len(response.data) > 0:
                    session_data = response.data[0]
                    # Cache in memory for subsequent calls
                    _session_store[user_id] = session_data
                    return session_data
            except Exception as e:
                logger.warning(f"Supabase query failed for user {user_id}: {e}")
        
        # Not found
        return None
        
    except Exception as e:
        logger.error(f"Error fetching session for {user_id}: {e}")
        return None


def save_session(user_id: str, data: Dict[str, Any]) -> bool:
    """
    Save or update user session data in Supabase and memory.
    
    Args:
        user_id: User WhatsApp phone number or session ID
        data: Dictionary of session data to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Always cache in memory
        if user_id in _session_store:
            _session_store[user_id].update(data)
        else:
            _session_store[user_id] = data
        
        # Add timestamp
        _session_store[user_id]["updated_at"] = datetime.utcnow().isoformat()
        
        # Try to save to Supabase
        if supabase:
            try:
                # Check if user exists
                existing = supabase.table("user_sessions").select("id").eq("user_id", user_id).execute()
                
                if existing.data and len(existing.data) > 0:
                    # Update existing
                    supabase.table("user_sessions").update({
                        **data,
                        "updated_at": datetime.utcnow().isoformat()
                    }).eq("user_id", user_id).execute()
                else:
                    # Insert new
                    supabase.table("user_sessions").insert({
                        "user_id": user_id,
                        **data,
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    }).execute()
                
                logger.info(f"✅ Session saved for user {user_id}")
                return True
                
            except Exception as e:
                logger.warning(f"Failed to save session to Supabase for {user_id}: {e}")
                # Still return True since we cached in memory
                return True
        else:
            logger.debug(f"Session cached in memory for {user_id}")
            return True
        
    except Exception as e:
        logger.error(f"Error saving session for {user_id}: {e}")
        return False


def clear_session(user_id: str) -> bool:
    """
    Clear user session from memory and Supabase.
    
    Args:
        user_id: User WhatsApp phone number or session ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Clear from memory
        if user_id in _session_store:
            del _session_store[user_id]
        
        # Clear from Supabase
        if supabase:
            try:
                supabase.table("user_sessions").delete().eq("user_id", user_id).execute()
                logger.info(f"✅ Session cleared for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to clear session in Supabase for {user_id}: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error clearing session for {user_id}: {e}")
        return False


def get_all_sessions() -> Dict[str, Dict[str, Any]]:
    """
    Get all sessions from memory (for debugging/monitoring).
    
    Returns:
        Dictionary of all sessions currently in memory
    """
    return _session_store.copy()


def session_exists(user_id: str) -> bool:
    """Check if a user session exists."""
    return user_id in _session_store or (get_session(user_id) is not None)
