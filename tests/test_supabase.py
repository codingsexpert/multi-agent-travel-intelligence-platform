"""Unit tests for Supabase service abstraction and DEMO_MODE fallback."""

import pytest
from config.settings import Settings
from services.supabase_service import SupabaseService
from utils.exceptions import ConfigurationError


def test_supabase_service_missing_credentials_in_demo_mode():
    """Verify that in DEMO_MODE missing Supabase credentials returns None without raising an error."""
    settings = Settings(
        _env_file=None,
        app_env="development",
        demo_mode=True,
        supabase_url=None,
        supabase_key=None,
    )
    service = SupabaseService(settings=settings)

    assert service.is_configured is False
    assert service.is_demo_mode is True

    # Calling get_client should safely return None without crashing
    client = service.get_client()
    assert client is None

    # Status check
    status = service.get_status()
    assert status["configured"] is False
    assert status["status"] == "Not Configured"
    assert status["demo_mode"] is True


def test_supabase_service_missing_credentials_in_live_mode():
    """Verify that in live mode (demo_mode=False) missing credentials raises ConfigurationError."""
    settings = Settings(
        _env_file=None,
        app_env="production",
        demo_mode=False,
        supabase_url=None,
        supabase_key=None,
    )
    service = SupabaseService(settings=settings)

    assert service.is_configured is False
    assert service.is_demo_mode is False

    with pytest.raises(ConfigurationError) as exc_info:
        service.get_client()

    assert "Missing SUPABASE_URL or SUPABASE_KEY" in str(exc_info.value)
    assert exc_info.value.code == "CONFIG_ERROR"
