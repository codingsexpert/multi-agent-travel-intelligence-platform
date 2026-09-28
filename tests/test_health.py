"""Unit tests for health check service and environment status evaluation."""

from pydantic import SecretStr
from config.settings import Settings
from services.health_service import get_health_status


def test_health_status_in_demo_mode():
    """Verify health status reports HEALTHY in DEMO_MODE even when credentials are not configured."""
    settings = Settings(
        _env_file=None,
        app_env="development",
        demo_mode=True,
        supabase_url=None,
        supabase_key=None,
        openai_api_key=None,
    )
    report = get_health_status(settings)

    assert report.overall_status == "HEALTHY"
    assert report.environment == "DEMO"
    assert report.demo_mode is True
    assert report.configuration_status == "OK"
    assert report.supabase_status == "Not Configured"
    assert report.llm_status == "Not Configured"
    assert report.langsmith_status == "Not Configured"
    assert "configuration" in report.components
    assert "supabase" in report.components


def test_health_status_in_production_unhealthy():
    """Verify health status reports UNHEALTHY in production if required credentials are missing."""
    settings = Settings(
        _env_file=None,
        app_env="production",
        demo_mode=False,
        supabase_url=None,
        supabase_key=None,
        openai_api_key=None,
    )
    report = get_health_status(settings)

    assert report.overall_status == "UNHEALTHY"
    assert report.environment == "PRODUCTION"
    assert report.demo_mode is False
    assert report.configuration_status == "INCOMPLETE"


def test_health_status_in_production_healthy():
    """Verify health status reports HEALTHY in production when required credentials are provided."""
    settings = Settings(
        _env_file=None,
        app_env="production",
        demo_mode=False,
        supabase_url="https://prod.supabase.co",
        supabase_key=SecretStr("prod-secret-key"),
        openai_api_key=SecretStr("sk-prod-openai-key"),
    )
    report = get_health_status(settings)

    assert report.overall_status == "HEALTHY"
    assert report.environment == "PRODUCTION"
    assert report.supabase_status == "Connected"
    assert report.llm_status == "Configured"
