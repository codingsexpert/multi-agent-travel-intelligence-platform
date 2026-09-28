"""Health and system status check abstraction."""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from config.settings import Settings, get_settings


class SystemComponentStatus(BaseModel):
    """Status representation for a single subsystem."""

    name: str
    status: str  # "OK", "CONFIGURED", "NOT_CONFIGURED", "WARNING"
    details: Optional[str] = None


class SystemHealthReport(BaseModel):
    """Aggregate health and readiness report for the platform."""

    overall_status: str = Field(description="Overall platform status: HEALTHY, DEGRADED, or UNHEALTHY")
    environment: str = Field(description="Runtime environment: DEMO, DEVELOPMENT, or PRODUCTION")
    demo_mode: bool = Field(description="Whether DEMO_MODE is active")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    configuration_status: str
    supabase_status: str
    llm_status: str
    langsmith_status: str

    components: Dict[str, SystemComponentStatus] = Field(default_factory=dict)


def get_health_status(settings: Optional[Settings] = None) -> SystemHealthReport:
    """Evaluate system status based strictly on configuration state without making outbound network calls."""
    cfg = settings or get_settings()

    # Determine environment label
    if cfg.demo_mode:
        env_label = "DEMO"
    else:
        env_label = cfg.app_env.upper()

    supabase_status = "Connected" if cfg.has_supabase_config else "Not Configured"
    llm_status = "Configured" if cfg.has_llm_config else "Not Configured"
    langsmith_status = "Configured" if cfg.has_langsmith_config else "Not Configured"

    # Configuration status
    config_status = "OK"

    # Determine overall status
    if cfg.demo_mode:
        overall_status = "HEALTHY"
    elif cfg.is_production:
        if cfg.has_supabase_config and cfg.has_llm_config:
            overall_status = "HEALTHY"
        else:
            overall_status = "UNHEALTHY"
            config_status = "INCOMPLETE"
    else:
        # Development non-demo
        overall_status = "HEALTHY" if (cfg.has_supabase_config or cfg.has_llm_config) else "DEGRADED"

    components = {
        "configuration": SystemComponentStatus(
            name="Configuration",
            status=config_status,
            details=f"Environment: {cfg.app_env}, Log Level: {cfg.log_level}",
        ),
        "supabase": SystemComponentStatus(
            name="Supabase Database & Auth",
            status=supabase_status,
            details=f"URL: {cfg.supabase_url or 'None (Offline Mock Mode)'}",
        ),
        "llm": SystemComponentStatus(
            name="LLM Provider",
            status=llm_status,
            details=f"Primary Model: {cfg.primary_llm_model}, Fast Model: {cfg.fast_llm_model}",
        ),
        "langsmith": SystemComponentStatus(
            name="LangSmith Observability",
            status=langsmith_status,
            details=f"Tracing: {cfg.langsmith_tracing}, Project: {cfg.langsmith_project}",
        ),
    }

    return SystemHealthReport(
        overall_status=overall_status,
        environment=env_label,
        demo_mode=cfg.demo_mode,
        configuration_status=config_status,
        supabase_status=supabase_status,
        llm_status=llm_status,
        langsmith_status=langsmith_status,
        components=components,
    )
