"""
Supabase Client - PostgreSQL Database Connection
Phase 1: Learning platform data (courses, lessons, progress, chat history)
"""

import os
from supabase import create_client, Client
from typing import Optional

# Supabase credentials from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Global Supabase client instance
supabase: Optional[Client] = None

def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance.
    Returns singleton client for database operations.
    """
    global supabase

    if supabase is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise ValueError(
                "Missing Supabase credentials. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables."
            )

        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print(f"✅ Supabase client initialized: {SUPABASE_URL}")

    return supabase

# Initialize client on import
try:
    supabase = get_supabase_client()
except Exception as e:
    print(f"⚠️  Warning: Could not initialize Supabase client: {e}")
    supabase = None
