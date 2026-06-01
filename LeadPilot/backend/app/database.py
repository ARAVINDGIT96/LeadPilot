from supabase import create_client, Client
from app.config import settings
from functools import lru_cache

_supabase_client = None

@lru_cache()
def get_supabase() -> Client:
    """Get or create Supabase client instance"""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.SUPABASE_URL, 
            settings.SUPABASE_KEY
        )
    return _supabase_client

# For backward compatibility
supabase = None  # Will be initialized on first use
