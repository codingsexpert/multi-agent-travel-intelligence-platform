"""Unit tests for configuration loading and environment validation."""

import pytest
from pydantic import SecretStr
from config.settings import Settings


def test_default_settings():
    """Verify default settings configuration."""
    settings = Settings(
        _env_file=None,  # Do not load any local .env
    )
    assert settings.app_env == "development"
    assert settings.demo_mode is True
    assert settings.log_level == "INFO"
    assert settings.primary_llm_model == "gpt-4o"
    assert settings.fast_llm_model == "gpt-4o-mini"
    assert settings.has_supabase_config is False
    assert settings.has_llm_config is False
    assert settings.has_langsmith_config is False
    assert settings.is_production is False


def test_demo_mode_setting():
    """Verify explicit toggling of DEMO_MODE."""
    settings_demo = Settings(_env_file=None, demo_mode=True)
    assert settings_demo.demo_mode is True

    settings_live = Settings(_env_file=None, demo_mode=False)
    assert settings_live.demo_mode is False


def test_credential_detection():
    """Verify detection of configured credentials without leaking secrets."""
    settings = Settings(
        _env_file=None,
        supabase_url="https://example.supabase.co",
        supabase_key=SecretStr("mock_secret_key_12345"),
        openai_api_key=SecretStr("sk-mock-key-1234567890"),
        langsmith_api_key=SecretStr("mock_ls_key_12345"),
        langsmith_tracing=True,
    )
    assert settings.has_supabase_config is True
    assert settings.has_llm_config is True
    assert settings.has_langsmith_config is True
    assert "mock_secret_key" not in repr(settings.supabase_key)
