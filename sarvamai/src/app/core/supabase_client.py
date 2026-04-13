"""Supabase client configuration and connection management"""

import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
except ImportError:
    Client = None
    logger.warning("Supabase client library not installed. Install with: pip install supabase")

class SupabaseManager:
    """Singleton manager for Supabase connections"""
    
    _instance: Optional['SupabaseManager'] = None
    _client: Optional[Client] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize Supabase client with credentials from environment"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            logger.error("SUPABASE_URL and SUPABASE_ANON_KEY environment variables not set")
            self._client = None
            return
        
        if Client is None:
            logger.error("Supabase client library not available")
            self._client = None
            return
        
        try:
            self._client = create_client(supabase_url, supabase_key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self._client = None
    
    def get_client(self) -> Optional[Client]:
        """Get the Supabase client instance"""
        return self._client
    
    def is_connected(self) -> bool:
        """Check if Supabase is connected"""
        return self._client is not None


# Export singleton manager
supabase_manager = SupabaseManager()
