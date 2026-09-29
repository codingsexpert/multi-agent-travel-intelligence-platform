"""Startup and runtime environment configuration validation layer.

Ensures that production credentials, security thresholds, and external
endpoints are correctly structured before servicing requests, without
ever logging or leaking secret values.
"""

from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from config.settings import Settings, get_settings
from utils.logger import logger


class ConfigValidationResult(BaseModel):
    """Structured report returned from environment validation."""

    is_valid: bool = Field(description="True if system satisfies all readiness criteria")
    environment: str = Field(description="Configured runtime environment (DEMO, DEVELOPMENT, PRODUCTION)")
    demo_mode: bool = Field(description="Whether DEMO_MODE is active")
    errors: List[str] = Field(default_factory=list, description="Critical configuration errors preventing startup")
    warnings: List[str] = Field(default_factory=list, description="Non-blocking advisories or optional provider gaps")
    provider_status: Dict[str, str] = Field(default_factory=dict, description="Redacted readiness summary for providers")


def validate_environment(settings: Optional[Settings] = None) -> ConfigValidationResult:
    """Validate current runtime configuration against environment requirements.

    Args:
        settings: Optional Settings instance; uses cached get_settings() if omitted.

    Returns:
        ConfigValidationResult with validation status, errors, and warnings.
    """
    cfg = settings or get_settings()
    errors: List[str] = []
    warnings: List[str] = []
    provider_status: Dict[str, str] = {}

    env_label = "DEMO" if cfg.demo_mode else cfg.app_env.upper()

    # 1. Guardrail limits validation (both Demo and Production)
    if cfg.max_agent_steps <= 0:
        errors.append("MAX_AGENT_STEPS must be a positive integer.")
    if cfg.max_tool_calls <= 0:
        errors.append("MAX_TOOL_CALLS must be a positive integer.")
    if cfg.max_workflow_cost <= 0.0:
        errors.append("MAX_WORKFLOW_COST must be a positive floating-point ceiling.")
    if cfg.max_total_tokens <= 0:
        errors.append("MAX_TOTAL_TOKENS must be a positive integer.")
    if cfg.workflow_timeout_seconds <= 0:
        errors.append("WORKFLOW_TIMEOUT_SECONDS must be a positive number.")
    if cfg.rate_limit_requests <= 0 or cfg.rate_limit_window_seconds <= 0:
        errors.append("Rate limit requests and window duration must be positive integers.")

    # 2. DEMO_MODE vs PRODUCTION Validation
    if cfg.demo_mode:
        warnings.append("DEMO_MODE is active. External API calls will use sandboxed deterministic mocks.")
        provider_status["runtime_mode"] = "SANDBOXED_MOCK"
        provider_status["llm_tier"] = "Mock & Rule Fallback Available"
        provider_status["database"] = "In-Memory Store Active"
    else:
        # Production / Live Mode Validation
        provider_status["runtime_mode"] = "LIVE_PRODUCTION"

        # Check Supabase Database & Auth URL
        if not cfg.supabase_url:
            errors.append("Missing required production variable: SUPABASE_URL")
            provider_status["database"] = "MISSING_URL"
        else:
            parsed = urlparse(cfg.supabase_url)
            if not parsed.scheme or not parsed.netloc or parsed.scheme not in ("http", "https"):
                errors.append("SUPABASE_URL is malformed. Must be a valid HTTP or HTTPS endpoint.")
                provider_status["database"] = "INVALID_URL"
            else:
                provider_status["database"] = "CONFIGURED"

        # Check Supabase Anon Key
        if not cfg.supabase_key or not cfg.supabase_key.get_secret_value():
            errors.append("Missing required production variable: SUPABASE_KEY (Supabase Anonymous/Public Key)")
            provider_status["auth"] = "MISSING_KEY"
        else:
            provider_status["auth"] = "CONFIGURED"

        # Check Primary LLM
        if not cfg.has_llm_config:
            errors.append("Missing primary LLM credentials: OPENAI_API_KEY is required for live reasoning.")
            provider_status["llm"] = "MISSING_API_KEY"
        else:
            provider_status["llm"] = f"CONFIGURED ({cfg.primary_llm_model})"

        # Optional External Providers in Production (warnings, not fatal errors)
        if cfg.has_amadeus_config:
            provider_status["flights_hotels"] = "AMADEUS_LIVE"
        else:
            warnings.append("Amadeus credentials not configured; flight/hotel searches will use mock fallback.")
            provider_status["flights_hotels"] = "MOCK_FALLBACK"

        if cfg.has_tavily_config or cfg.has_brave_search_config:
            provider_status["web_search"] = "LIVE_SEARCH"
        else:
            warnings.append("Live search API key not provided; research agent will rely on curated RAG and open sources.")
            provider_status["web_search"] = "RAG_FALLBACK"

        if cfg.has_langsmith_config:
            provider_status["observability"] = f"LANGSMITH_ACTIVE ({cfg.langsmith_project})"
        else:
            warnings.append("LangSmith tracing is disabled or unconfigured.")
            provider_status["observability"] = "DISABLED"

    is_valid = len(errors) == 0

    if not is_valid:
        logger.error(f"[CONFIG_VALIDATION] Failed with {len(errors)} critical configuration errors.")
    else:
        logger.info(f"[CONFIG_VALIDATION] Configuration verified successfully ({env_label}).")

    return ConfigValidationResult(
        is_valid=is_valid,
        environment=env_label,
        demo_mode=cfg.demo_mode,
        errors=errors,
        warnings=warnings,
        provider_status=provider_status,
    )


def ensure_startup_configuration(raise_on_error: bool = False) -> ConfigValidationResult:
    """Convenience bootstrap function to check configuration at app or test startup."""
    result = validate_environment()
    if not result.is_valid and raise_on_error:
        from utils.exceptions import ConfigurationError
        error_msg = "; ".join(result.errors)
        raise ConfigurationError("StartupConfigValidator", f"Production environment validation failed: {error_msg}")
    return result
