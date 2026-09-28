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


@lru_cache
def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    return Settings()


# Singleton settings instance for convenience
settings: Settings = get_settings()
