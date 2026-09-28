"""Base repository class providing shared access to Supabase client and DEMO_MODE checks."""

from typing import Optional
from config.settings import Settings, get_settings
from services.supabase_service import SupabaseService, supabase_service
from repositories.mock_store import mock_store, MockDataStore


class BaseRepository:
    """Base repository handling Supabase connection states and mock store routing."""

    def __init__(
        self,
        supabase_svc: Optional[SupabaseService] = None,
        settings: Optional[Settings] = None,
        store: Optional[MockDataStore] = None,
    ):
        self.settings = settings or get_settings()
        self.supabase_svc = supabase_svc or supabase_service
        self.mock_store = store or mock_store

    @property
    def is_demo_mode(self) -> bool:
        """Return True if running in DEMO_MODE or without valid Supabase credentials."""
        return self.settings.demo_mode or not self.supabase_svc.is_configured
