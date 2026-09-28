"""Security enforcement and least-privilege policies for MCP tools."""

import re
from urllib.parse import urlparse
from typing import Set, Dict, Any, Optional
from utils.logger import logger


# Explicit tool permissions per agent role (Least Privilege)
AGENT_TOOL_PERMISSIONS: Dict[str, Set[str]] = {
    "flight": {
        "search_flights",
        "compare_flights",
        "get_flight_details",
    },
    "hotel": {
        "search_hotels",
        "get_hotel_details",
    },
    "activity": {
        "search_places",
        "calculate_route",
        "estimate_travel_time",
    },
    "weather": {
        "get_current_weather",
        "get_forecast",
        "get_weather_alerts",
    },
    "research": {
        "web_search",
        "fetch_page",
        "search_news",
    },
    "budget": {
        "get_exchange_rate",
    },
    "validator": {
        "estimate_travel_time",
        "get_exchange_rate",
    },
}

# Permitted public domains for Web Search and Fetch Page
ALLOWED_SEARCH_DOMAINS: Set[str] = {
    "wikipedia.org",
    "en.wikipedia.org",
    "wikivoyage.org",
    "en.wikivoyage.org",
    "lonelyplanet.com",
    "tripadvisor.com",
    "travel.state.gov",
    "japan.travel",
    "parisjetaime.com",
    "visitlondon.com",
    "nycgo.com",
}

# Blocked SSRF and internal addresses
BLOCKED_IP_PATTERNS = [
    r"^localhost$",
    r"^127\.",
    r"^0\.0\.0\.0$",
    r"^169\.254\.",
    r"^10\.",
    r"^192\.168\.",
    r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",
    r"^metadata\.google\.internal$",
]


class MCPSecurityManager:
    """Security gateway enforcing role permissions, URL isolation, and untrusted data sanitization."""

    @classmethod
    def verify_tool_permission(cls, agent_name: str, tool_name: str) -> None:
        """Enforce least-privilege boundary.

        Raises:
            PermissionError: If agent role is not authorized to invoke the requested MCP tool.
        """
        agent_key = agent_name.lower().replace("_agent", "").strip()
        allowed_tools = AGENT_TOOL_PERMISSIONS.get(agent_key, set())

        if tool_name not in allowed_tools:
            err = (
                f"Security Permission Denied: Agent '{agent_name}' is not authorized to execute "
                f"MCP tool '{tool_name}'. Permitted tools: {sorted(list(allowed_tools))}"
            )
            logger.warning(f"[MCPSecurity] {err}")
            raise PermissionError(err)

    @classmethod
    def validate_url(cls, url: str, enforce_domain_allowlist: bool = False) -> str:
        """Validate web URL preventing SSRF, private network traversal, and protocol tampering.

        Raises:
            ValueError: If URL is malformed, uses non-HTTP protocols, or targets private IP space.
        """
        if not url:
            raise ValueError("URL cannot be empty.")

        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Prohibited protocol '{parsed.scheme}'. Only HTTP and HTTPS are permitted.")

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            raise ValueError("Invalid URL: missing host.")

        # Reject private/loopback targets
        for pattern in BLOCKED_IP_PATTERNS:
            if re.search(pattern, hostname):
                raise ValueError(f"Prohibited target '{hostname}': access to private/loopback network space is blocked.")

        if enforce_domain_allowlist:
            is_allowed = any(hostname == d or hostname.endswith(f".{d}") for d in ALLOWED_SEARCH_DOMAINS)
            if not is_allowed:
                raise ValueError(f"Domain '{hostname}' is not in the trusted search allowlist.")

        return url.strip()

    @classmethod
    def sanitize_untrusted_content(cls, raw_content: str, max_chars: int = 5000) -> str:
        """Sanitize retrieved external web text, neutralizing prompt injection attacks.

        Strips script blocks, developer command overrides, and limits length.
        """
        if not raw_content:
            return ""

        # Remove script and style tags
        sanitized = re.sub(r"<(script|style).*?>.*?</\1>", "", raw_content, flags=re.DOTALL | re.IGNORECASE)
        # Strip other HTML tags
        sanitized = re.sub(r"<[^>]+>", " ", sanitized)

        # Neutralize common prompt injection patterns
        injection_patterns = [
            r"(?i)ignore\s+(all\s+)?previous\s+instructions",
            r"(?i)system\s*prompt",
            r"(?i)you\s+are\s+now\s+in\s+developer\s+mode",
            r"(?i)override\s+security\s+rules",
        ]
        for pat in injection_patterns:
            sanitized = re.sub(pat, "[FILTERED_UNTRUSTED_INSTRUCTION]", sanitized)

        # Truncate to maximum characters
        return sanitized.strip()[:max_chars]

    @classmethod
    def sanitize_metadata(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Scrub potential secrets and tokens from telemetry payloads before logging."""
        sanitized = {}
        sensitive_keys = {"api_key", "secret", "token", "password", "authorization", "bearer", "cookie"}

        for k, v in data.items():
            if any(s in k.lower() for s in sensitive_keys):
                sanitized[k] = "[MASKED_SECRET]"
            elif isinstance(v, dict):
                sanitized[k] = cls.sanitize_metadata(v)
            else:
                sanitized[k] = v

        return sanitized
