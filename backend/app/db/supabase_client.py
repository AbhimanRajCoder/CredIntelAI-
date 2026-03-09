"""
Intelli-Credit: Supabase Client Module.
Provides a reusable singleton Supabase client loaded from environment variables.
"""

import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

_supabase_client = None


def get_supabase_client():
    """
    Get or create the Supabase client singleton.

    Returns None if SUPABASE_URL or SUPABASE_KEY are not configured,
    allowing the application to fall back to in-memory operation.
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    settings = get_settings()

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.warning(
            "Supabase credentials not configured (SUPABASE_URL / SUPABASE_KEY). "
            "Database features will be disabled — falling back to in-memory storage."
        )
        return None

    try:
        from supabase import create_client, Client

        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY,
        )
        logger.info(f"Supabase client initialized (URL: {settings.SUPABASE_URL[:30]}...)")
        return _supabase_client

    except ImportError:
        logger.error(
            "supabase package not installed. Run: pip install supabase"
        )
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None


def is_supabase_configured() -> bool:
    """Check if Supabase is properly configured and available."""
    return get_supabase_client() is not None
