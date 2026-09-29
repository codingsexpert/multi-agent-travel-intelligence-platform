"""Centralized application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable loading and validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core Application Settings
    app_env: str = Field(default="development", description="Runtime environment (development, staging, production)")
    demo_mode: bool = Field(default=True, description="When True, uses mock services without requiring live APIs")
    log_level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")

    # Supabase Configuration (Optional in DEMO_MODE)
    supabase_url: Optional[str] = Field(default=None, description="Supabase project URL")
    supabase_key: Optional[SecretStr] = Field(
        default=None,
        description="Supabase anonymous or public API key",
        validation_alias="supabase_key",
    )

    # LLM Provider Configuration (Optional in DEMO_MODE)
    openai_api_key: Optional[SecretStr] = Field(default=None, description="OpenAI API Key for reasoning models")
    primary_llm_model: str = Field(default="gpt-4o", description="Primary model for planning and reasoning")
    fast_llm_model: str = Field(default="gpt-4o-mini", description="Fast model for extraction and summarization")

    # LangSmith Observability Configuration (Optional)
    langsmith_api_key: Optional[SecretStr] = Field(
        default=None,
        description="LangSmith API Key",
        validation_alias="langsmith_api_key",
    )
    langsmith_tracing: bool = Field(
        default=False,
        description="Enable LangSmith distributed tracing",
        validation_alias="langsmith_tracing",
    )
    langsmith_project: str = Field(
        default="travel-intelligence-platform",
        description="LangSmith project name",
        validation_alias="langsmith_project",
    )

    # External Provider Configuration (Phase 8 - Optional when DEMO_MODE=true)
    amadeus_client_id: Optional[SecretStr] = Field(default=None, description="Amadeus API Client ID for Flights & Hotels")
    amadeus_client_secret: Optional[SecretStr] = Field(default=None, description="Amadeus API Client Secret")
    openweather_api_key: Optional[SecretStr] = Field(default=None, description="OpenWeatherMap API Key (optional; Open-Meteo is default)")
    tavily_api_key: Optional[SecretStr] = Field(default=None, description="Tavily Web Search API Key")
    brave_search_api_key: Optional[SecretStr] = Field(default=None, description="Brave Search API Key")
    google_places_api_key: Optional[SecretStr] = Field(default=None, description="Google Places API Key (optional; OSM/Photon is default)")

    # RAG & pgvector Knowledge Configuration (Phase 9)
    embedding_provider: str = Field(
        default="openai",
        description="Embedding provider (openai, mock)",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name",
    )
    embedding_dimension: int = Field(
        default=1536,
        description="Vector dimension matching model and database column",
    )
    rag_top_k: int = Field(
        default=4,
        description="Default number of relevant chunks to retrieve",
    )
    rag_chunk_size: int = Field(
        default=500,
        description="Character/token window target for document chunking",
    )
    rag_chunk_overlap: int = Field(
        default=80,
        description="Overlap between adjacent chunks in characters/tokens",
    )

    # Production Guardrails & Security Limits (Phase 11)
    max_agent_steps: int = Field(
        default=15,
        description="Maximum agent execution steps permitted in a single workflow run",
    )
    max_tool_calls: int = Field(
        default=25,
        description="Maximum external tool invocations permitted per workflow run",
    )
    max_retries: int = Field(
        default=2,
        description="Maximum retry attempts on transient network or 5xx provider failures",
    )
    max_search_calls: int = Field(
        default=5,
        description="Maximum web search or news calls permitted per workflow run",
    )
    max_rag_results: int = Field(
        default=10,
        description="Maximum curated RAG chunks retrieved per query",
    )
    max_input_chars: int = Field(
        default=2000,
        description="Hard character limit on raw user travel requests",
    )
    max_context_chars: int = Field(
        default=15000,
        description="Maximum characters for assembled context windows",
    )
    workflow_timeout_seconds: float = Field(
        default=30.0,
        description="Hard timeout ceiling for complete LangGraph workflow execution",
    )
    rate_limit_requests: int = Field(
        default=60,
        description="Maximum allowed requests per sliding time window",
    )
    rate_limit_window_seconds: int = Field(
        default=60,
        description="Sliding window duration in seconds for rate limiter",
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env.lower() == "production"

    @property
    def has_amadeus_config(self) -> bool:
        """Check if Amadeus credentials are provided."""
        return bool(
            self.amadeus_client_id
            and self.amadeus_client_id.get_secret_value()
            and self.amadeus_client_secret
            and self.amadeus_client_secret.get_secret_value()
        )

    @property
    def has_tavily_config(self) -> bool:
        """Check if Tavily search API key is provided."""
        return bool(self.tavily_api_key and self.tavily_api_key.get_secret_value())

    @property
    def has_brave_search_config(self) -> bool:
        """Check if Brave search API key is provided."""
        return bool(self.brave_search_api_key and self.brave_search_api_key.get_secret_value())

    @property
    def has_openweather_config(self) -> bool:
        """Check if OpenWeatherMap API key is provided."""
        return bool(self.openweather_api_key and self.openweather_api_key.get_secret_value())

    @property
    def has_google_places_config(self) -> bool:
        """Check if Google Places API key is provided."""
        return bool(self.google_places_api_key and self.google_places_api_key.get_secret_value())

    @property
    def has_supabase_config(self) -> bool:
        """Check if Supabase credentials are provided."""
        return bool(self.supabase_url and self.supabase_key and self.supabase_key.get_secret_value())

    @property
    def has_llm_config(self) -> bool:
        """Check if OpenAI API key is provided."""
        return bool(self.openai_api_key and self.openai_api_key.get_secret_value())

    @property
    def has_langsmith_config(self) -> bool:
        """Check if LangSmith credentials and tracing are provided."""
        return bool(
            self.langsmith_tracing
            and self.langsmith_api_key
            and self.langsmith_api_key.get_secret_value()
        )

    @property
    def has_embedding_config(self) -> bool:
        """Check if embedding credentials are validly configured."""
        if self.embedding_provider.lower() == "mock":
            return True
        return bool(self.openai_api_key and self.openai_api_key.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    return Settings()


# Singleton settings instance for convenience
settings: Settings = get_settings()
