"""Supabase client abstraction supporting DEMO_MODE and safe fallback."""

from typing import Optional, Any, Dict
from config.settings import Settings, get_settings
from utils.logger import logger
from utils.exceptions import ConfigurationError


class SupabaseService:
    """Wrapper around Supabase client managing connection lifecycle and DEMO_MODE fallback."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._client: Optional[Any] = None
        self._initialized: bool = False

    @property
    def is_configured(self) -> bool:
        """Check whether valid Supabase credentials are configured."""
        return self.settings.has_supabase_config

    @property
    def is_demo_mode(self) -> bool:
        """Check whether running in DEMO_MODE."""
        return self.settings.demo_mode

    def get_client(self) -> Optional[Any]:
        """Retrieve the active Supabase client.

        Returns:
            supabase.Client instance if configured, or None in DEMO_MODE.

        Raises:
            ConfigurationError: If credentials are missing in non-DEMO mode.
        """
        if self._initialized:
            return self._client

        if not self.is_configured:
            if self.is_demo_mode:
                logger.info("Supabase credentials not configured; running in DEMO_MODE without database persistence.")
                self._client = None
                self._initialized = True
                return None
            else:
                logger.error("Supabase URL and API Key are required in production/live mode.")
                raise ConfigurationError(
                    message="Missing SUPABASE_URL or SUPABASE_KEY in non-demo environment.",
                    details={"app_env": self.settings.app_env, "demo_mode": self.settings.demo_mode},
                )

        try:
            from supabase import create_client, ClientOptions

            api_key = self.settings.supabase_key.get_secret_value() if self.settings.supabase_key else ""
            self._client = create_client(
                supabase_url=self.settings.supabase_url or "",
                supabase_key=api_key,
                options=ClientOptions(postgrest_client_timeout=10),
            )
            self._initialized = True
            logger.info("Supabase client initialized successfully.")
            return self._client
        except Exception as e:
            logger.warning(f"Failed to initialize live Supabase client: {e}")
            if self.is_demo_mode:
                logger.info("Falling back to DEMO_MODE without active Supabase client.")
                self._client = None
                self._initialized = True
                return None
            raise ConfigurationError(
                message=f"Could not connect to Supabase: {str(e)}",
                details={"supabase_url": self.settings.supabase_url},
            ) from e

    def get_status(self) -> Dict[str, Any]:
        """Return connectivity status without performing expensive queries."""
        if self.is_configured:
            return {
                "configured": True,
                "status": "Configured",
                "demo_mode": self.is_demo_mode,
                "url": self.settings.supabase_url,
            }
        return {
            "configured": False,
            "status": "Not Configured",
            "demo_mode": self.is_demo_mode,
            "url": None,
        }


# Global singleton instance
supabase_service = SupabaseService()
