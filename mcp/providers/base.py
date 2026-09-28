"""Base provider abstractions, HTTP resiliency client, error classification, and attribution."""

import time
import httpx
import contextvars
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Type, Callable
from pydantic import BaseModel, Field

from config.settings import settings
from utils.exceptions import AppError
from utils.logger import logger
from mcp.providers.cache import ProviderCache

# Context variable propagating demo vs live mode down from MCPClient into provider adapters
_execution_mode_ctx: contextvars.ContextVar[Optional[bool]] = contextvars.ContextVar(
    "execution_mode_ctx", default=None
)


def set_execution_mode(is_demo: bool):
    """Set the execution mode context for the current execution thread or async context."""
    return _execution_mode_ctx.set(is_demo)


def reset_execution_mode(token) -> None:
    """Reset the execution mode context."""
    _execution_mode_ctx.reset(token)


def get_effective_demo_mode(override: Optional[bool] = None) -> bool:
    """Determine whether execution should operate in DEMO mode based on override, context, or config."""
    if override is not None:
        return override
    ctx_val = _execution_mode_ctx.get()
    if ctx_val is not None:
        return ctx_val
    return settings.demo_mode


# ==============================================================================
# Provider Exception Hierarchy
# ==============================================================================

class ProviderError(AppError):
    """Base exception for all external provider integration errors."""

    def __init__(self, message: str, provider: str, retryable: bool = False, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"[{provider}] {message}",
            user_message=f"Provider {provider} encountered an issue: {message}",
            details=details or {},
            code=f"PROVIDER_{provider.upper()}_ERROR",
        )
        self.provider = provider
        self.retryable = retryable


class ProviderConfigurationError(ProviderError):
    """Raised when required API credentials, secrets, or endpoints are missing or invalid."""

    def __init__(self, message: str, provider: str):
        super().__init__(message=message, provider=provider, retryable=False)


class ProviderAuthenticationError(ProviderError):
    """Raised when API returns HTTP 401 or 403 unauthorized."""

    def __init__(self, message: str, provider: str):
        super().__init__(message=message, provider=provider, retryable=False)


class ProviderRateLimitError(ProviderError):
    """Raised when API returns HTTP 429 Too Many Requests."""

    def __init__(self, message: str, provider: str, retry_after: Optional[float] = None):
        super().__init__(message=message, provider=provider, retryable=True, details={"retry_after": retry_after})
        self.retry_after = retry_after


class ProviderTimeoutError(ProviderError):
    """Raised when HTTP request exceeds timeout limit."""

    def __init__(self, message: str, provider: str):
        super().__init__(message=message, provider=provider, retryable=True)


class ProviderNetworkError(ProviderError):
    """Raised when transport connection fails, DNS fails, or HTTP 5xx is encountered."""

    def __init__(self, message: str, provider: str, status_code: Optional[int] = None):
        super().__init__(message=message, provider=provider, retryable=True, details={"status_code": status_code})
        self.status_code = status_code


class ProviderResponseValidationError(ProviderError):
    """Raised when external API payload does not conform to expected schema."""

    def __init__(self, message: str, provider: str):
        super().__init__(message=message, provider=provider, retryable=False)


# ==============================================================================
# Source Attribution & Telemetry Models
# ==============================================================================

class SourceAttribution(BaseModel):
    """Metadata tracking external provenance, source URL, timestamp, and mode."""

    provider: str
    source_url: str
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data_mode: str = Field(default="LIVE", description="'LIVE' or 'DEMO'")


# ==============================================================================
# Base Provider Class with Resilient Request Execution
# ==============================================================================

class BaseProvider:
    """Base class for all external service adapters providing retry policies, timeouts, and logging."""

    DEFAULT_TIMEOUT_SECONDS: float = 8.0
    DEFAULT_MAX_RETRIES: int = 2

    def __init__(self, provider_name: str, base_url: str = ""):
        self.provider_name = provider_name
        self.base_url = base_url

    def _sanitize_headers(self, headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Scrub secret headers before logging."""
        if not headers:
            return {}
        sanitized = {}
        for k, v in headers.items():
            if any(s in k.lower() for s in ("auth", "key", "token", "secret", "bearer", "cookie")):
                sanitized[k] = "[REDACTED_SECRET]"
            else:
                sanitized[k] = v
        return sanitized

    def execute_http_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> httpx.Response:
        """Execute HTTP request with exponential backoff, rate limit handling, and error mapping."""
        req_timeout = timeout or self.DEFAULT_TIMEOUT_SECONDS
        retries_limit = max_retries if max_retries is not None else self.DEFAULT_MAX_RETRIES

        merged_headers = {
            "User-Agent": "TravelIntelligencePlatform/1.0 (Travel Intelligence Platform; contact@example.com)",
            "Accept": "application/json, text/html, */*",
        }
        if headers:
            merged_headers.update(headers)

        attempt = 0
        while True:
            attempt += 1
            start_time = time.time()
            try:
                with httpx.Client(timeout=req_timeout) as client:
                    resp = client.request(
                        method=method,
                        url=url,
                        params=params,
                        headers=merged_headers,
                        json=json_data,
                    )

                latency_ms = round((time.time() - start_time) * 1000, 2)

                # 1. Handle HTTP 429 Rate Limiting
                if resp.status_code == 429:
                    retry_after_hdr = resp.headers.get("Retry-After")
                    retry_after = float(retry_after_hdr) if retry_after_hdr and retry_after_hdr.isdigit() else 1.0
                    logger.warning(
                        f"[{self.provider_name}] Rate limited (429). Attempt {attempt}/{retries_limit + 1}. "
                        f"Retry-After: {retry_after}s"
                    )
                    if attempt <= retries_limit:
                        time.sleep(min(retry_after, 3.0))
                        continue
                    raise ProviderRateLimitError(
                        f"Rate limit exceeded (429). Provider requests throttled.",
                        provider=self.provider_name,
                        retry_after=retry_after,
                    )

                # 2. Handle HTTP 401 / 403 Authentication Failures
                if resp.status_code in (401, 403):
                    logger.error(f"[{self.provider_name}] Authentication failure ({resp.status_code})")
                    raise ProviderAuthenticationError(
                        f"Authentication failed with status {resp.status_code}. Verify API keys.",
                        provider=self.provider_name,
                    )

                # 3. Handle 5xx Server Errors (Retryable)
                if 500 <= resp.status_code < 600:
                    logger.warning(
                        f"[{self.provider_name}] Server error ({resp.status_code}). Attempt {attempt}/{retries_limit + 1}"
                    )
                    if attempt <= retries_limit:
                        time.sleep(0.3 * (2 ** (attempt - 1)))
                        continue
                    raise ProviderNetworkError(
                        f"Remote server error: HTTP {resp.status_code}",
                        provider=self.provider_name,
                        status_code=resp.status_code,
                    )

                # 4. Handle other 4xx Client Errors (Non-Retryable)
                if 400 <= resp.status_code < 500:
                    raise ProviderError(
                        f"Client request error: HTTP {resp.status_code} - {resp.text[:200]}",
                        provider=self.provider_name,
                        retryable=False,
                    )

                return resp

            except (httpx.TimeoutException, TimeoutError) as te:
                logger.warning(f"[{self.provider_name}] Request timeout on attempt {attempt}/{retries_limit + 1}")
                if attempt <= retries_limit:
                    time.sleep(0.3 * (2 ** (attempt - 1)))
                    continue
                raise ProviderTimeoutError(
                    f"Request timed out after {req_timeout}s: {str(te)}",
                    provider=self.provider_name,
                )

            except (httpx.ConnectError, httpx.NetworkError) as ne:
                logger.warning(f"[{self.provider_name}] Network connectivity issue: {str(ne)}")
                if attempt <= retries_limit:
                    time.sleep(0.3 * (2 ** (attempt - 1)))
                    continue
                raise ProviderNetworkError(
                    f"Network transport error: {str(ne)}",
                    provider=self.provider_name,
                )
