"""Production health check and readiness probe service.

Evaluates operational status across Application, Database, Auth, LLM, MCP,
Search, RAG, and LangSmith without executing transactional or mutating operations.
"""

from datetime import datetime, timezone
import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from config.settings import Settings, get_settings


class SubsystemHealth(BaseModel):
    """Health status and metadata for a specific platform component."""

    name: str
    status: str = Field(description="Subsystem status: HEALTHY, DEGRADED, UNAVAILABLE, or NOT_CONFIGURED")
    readiness: bool = Field(default=True, description="Whether this component satisfies minimum operational readiness")
    details: Optional[str] = Field(default=None, description="Safe descriptive context without secrets")


# Backward compatibility alias
SystemComponentStatus = SubsystemHealth


class SystemHealthReport(BaseModel):
    """Overall platform health report covering liveness, readiness, and subsystem status."""

    overall_status: str = Field(description="Aggregated platform status: HEALTHY, DEGRADED, or UNAVAILABLE")
    liveness: bool = Field(default=True, description="True if process is alive and responding")
    readiness: bool = Field(description="True if platform is capable of servicing planning requests")
    environment: str = Field(description="Runtime environment identifier (DEMO, DEVELOPMENT, PRODUCTION)")
    demo_mode: bool = Field(description="Whether DEMO_MODE sandbox is active")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    configuration_status: str
    supabase_status: str
    llm_status: str
    langsmith_status: str

    components: Dict[str, SubsystemHealth] = Field(default_factory=dict)


_PROCESS_START_TIME = time.time()


def get_liveness_status() -> Dict[str, Any]:
    """Basic liveness probe checking that the application process is running."""
    uptime_seconds = round(time.time() - _PROCESS_START_TIME, 1)
    return {
        "status": "HEALTHY",
        "liveness": True,
        "uptime_seconds": uptime_seconds,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_readiness_status(settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Readiness probe evaluating if mandatory planning dependencies are satisfied."""
    report = get_health_status(settings)
    return {
        "status": report.overall_status,
        "readiness": report.readiness,
        "environment": report.environment,
        "demo_mode": report.demo_mode,
        "components": {k: v.status for k, v in report.components.items()},
    }


def get_health_status(settings: Optional[Settings] = None) -> SystemHealthReport:
    """Perform a comprehensive, non-mutating operational health evaluation across all 8 subsystems."""
    cfg = settings or get_settings()

    env_label = "DEMO" if cfg.demo_mode else cfg.app_env.upper()

    components: Dict[str, SubsystemHealth] = {}

    # 1. Application Liveness Component
    components["application"] = SubsystemHealth(
        name="Application Process",
        status="HEALTHY",
        readiness=True,
        details=f"Process active. Mode: {env_label}. Max Steps: {cfg.max_agent_steps}",
    )

    # 2. Database Component
    if cfg.demo_mode:
        db_status = "HEALTHY"
        db_details = "In-memory isolated mock data store active"
        db_ready = True
    elif cfg.has_supabase_config:
        db_status = "HEALTHY"
        db_details = f"Supabase PostgreSQL configured ({cfg.supabase_url})"
        db_ready = True
    else:
        db_status = "UNAVAILABLE"
        db_details = "Supabase URL or Key missing in production"
        db_ready = False

    components["database"] = SubsystemHealth(
        name="Database (PostgreSQL)",
        status=db_status,
        readiness=db_ready,
        details=db_details,
    )

    # 3. Authentication Component
    if cfg.demo_mode:
        auth_status = "HEALTHY"
        auth_details = "Local deterministic session provider"
        auth_ready = True
    elif cfg.has_supabase_config:
        auth_status = "HEALTHY"
        auth_details = "Supabase Auth with RLS token validation"
        auth_ready = True
    else:
        auth_status = "UNAVAILABLE"
        auth_details = "Supabase Auth credentials missing"
        auth_ready = False

    components["authentication"] = SubsystemHealth(
        name="Authentication & RLS",
        status=auth_status,
        readiness=auth_ready,
        details=auth_details,
    )

    # 4. LLM Provider Component
    if cfg.demo_mode:
        llm_status = "HEALTHY"
        llm_details = f"Deterministic model router with mock fallback (Primary: {cfg.primary_llm_model})"
        llm_ready = True
    elif cfg.has_llm_config:
        llm_status = "HEALTHY"
        llm_details = f"OpenAI configured (Primary: {cfg.primary_llm_model}, Fast: {cfg.fast_llm_model})"
        llm_ready = True
    else:
        llm_status = "UNAVAILABLE"
        llm_details = "OpenAI API key missing in live mode"
        llm_ready = False

    components["llm"] = SubsystemHealth(
        name="LLM Provider & Model Router",
        status=llm_status,
        readiness=llm_ready,
        details=llm_details,
    )

    # 5. MCP Tools Component
    components["mcp"] = SubsystemHealth(
        name="Model Context Protocol (MCP)",
        status="HEALTHY",
        readiness=True,
        details="Standardized MCP tool adapters active (Flights, Hotels, Weather)",
    )

    # 6. Web Search Provider Component
    if cfg.has_tavily_config or cfg.has_brave_search_config:
        search_status = "HEALTHY"
        search_details = "Live search provider API active"
    else:
        search_status = "DEGRADED" if not cfg.demo_mode else "HEALTHY"
        search_details = "Curated RAG & Wikipedia open search fallback"

    components["search"] = SubsystemHealth(
        name="Web Search Provider",
        status=search_status,
        readiness=True,
        details=search_details,
    )

    # 7. RAG Knowledge Fabric Component
    components["rag"] = SubsystemHealth(
        name="RAG Knowledge Fabric",
        status="HEALTHY",
        readiness=True,
        details=f"Provider: {cfg.embedding_provider}, Model: {cfg.embedding_model}, Top-K: {cfg.rag_top_k}",
    )

    # 8. LangSmith Observability Component
    if cfg.has_langsmith_config:
        ls_status = "HEALTHY"
        ls_details = f"Tracing enabled (Project: {cfg.langsmith_project})"
    else:
        ls_status = "NOT_CONFIGURED" if cfg.demo_mode else "DEGRADED"
        ls_details = "Tracing inactive; local workflow telemetry active"

    components["langsmith"] = SubsystemHealth(
        name="LangSmith Observability",
        status=ls_status,
        readiness=True,
        details=ls_details,
    )

    # Legacy compatibility fields
    supabase_status = "Connected" if cfg.has_supabase_config else "Not Configured"
    llm_status = "Configured" if cfg.has_llm_config else "Not Configured"
    langsmith_status = "Configured" if cfg.has_langsmith_config else "Not Configured"

    # Backward compatibility component aliases
    components["configuration"] = SubsystemHealth(
        name="Configuration",
        status="OK" if (cfg.demo_mode or (cfg.has_supabase_config and cfg.has_llm_config)) else "INCOMPLETE",
        readiness=True,
        details=f"Environment: {cfg.app_env}, Log Level: {cfg.log_level}",
    )
    components["supabase"] = SubsystemHealth(
        name="Supabase Database & Auth",
        status=supabase_status,
        readiness=components["database"].readiness,
        details=components["database"].details,
    )

    # Determine overall status and readiness
    if cfg.demo_mode:
        overall_status = "HEALTHY"
        config_status = "OK"
    elif cfg.is_production:
        if cfg.has_supabase_config and cfg.has_llm_config:
            overall_status = "HEALTHY"
            config_status = "OK"
        else:
            overall_status = "UNHEALTHY"
            config_status = "INCOMPLETE"
    else:
        overall_status = "HEALTHY" if (cfg.has_supabase_config or cfg.has_llm_config) else "DEGRADED"
        config_status = "OK"

    readiness = overall_status in ("HEALTHY", "DEGRADED")

    return SystemHealthReport(
        overall_status=overall_status,
        liveness=True,
        readiness=readiness,
        environment=env_label,
        demo_mode=cfg.demo_mode,
        configuration_status=config_status,
        supabase_status=supabase_status,
        llm_status=llm_status,
        langsmith_status=langsmith_status,
        components=components,
    )
