"""Tool guardrails: tool authorization, high-risk action blocking, argument validation, and rate limits."""

import logging
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse
from pydantic import BaseModel, Field

from guardrails.security import SecurityAuditor, rate_limiter
from utils.exceptions import ToolArgumentInvalidError, ToolPermissionDeniedError

logger = logging.getLogger("travel_platform.guardrails.tools")

BLOCKED_IP_PATTERNS = [
    r"^localhost$",
    r"^127\.",
    r"^0\.0\.0\.0$",
    r"^169\.254\.",
    r"^10\.",
    r"^192\.168\.",
    r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",
    r"^metadata\.google\.internal$",
    r"^::1$",
    r"^\[::1\]$",
    r"^fe80:",
    r"^\[fe80:",
    r"^fc00:",
    r"^\[fc00:",
    r"^fd",
    r"^\[fd",
]



class ToolAuthorizationResult(BaseModel):
    """Structured result returned by tool authorization and argument validation."""

    authorized: bool = Field(..., description="Whether tool execution is permitted")
    reason: Optional[str] = Field(default=None, description="Explanation if authorization or validation failed")
    tool_name: str = Field(..., description="Name of the MCP tool requested")
    agent_role: str = Field(..., description="Agent role attempting execution")
    category: str = Field(default="AUTHORIZED", description="Category: AUTHORIZED, PERMISSION_DENIED, HIGH_RISK_BLOCKED, ARGUMENT_INVALID, RATE_LIMITED")
    sanitized_arguments: Dict[str, Any] = Field(default_factory=dict, description="Validated and sanitized tool arguments")


class ToolGuardrail:
    """Centralized authorization gateway for all agent-to-tool invocations."""

    # High-risk autonomous actions strictly blocked in this phase
    HIGH_RISK_ACTIONS: Set[str] = {
        "booking",
        "book_flight",
        "book_hotel",
        "payment",
        "process_payment",
        "purchasing",
        "cancellation",
        "cancel_booking",
        "financial_transaction",
        "charge_card",
        "refund",
    }

    # Strict tool allowlist per agent role
    AGENT_ALLOWLIST: Dict[str, Set[str]] = {
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
            "current_weather",
            "forecast",
            "alerts",
        },
        "research": {
            "web_search",
            "fetch_page",
            "safe_fetch_page",
            "search_news",
        },
        "budget": {
            "get_exchange_rate",
        },
        "validator": {
            "estimate_travel_time",
            "get_exchange_rate",
        },
        "planner": {
            "web_search",
            "get_exchange_rate",
        },
    }

    VALID_CABIN_CLASSES = {"economy", "premium_economy", "business", "first"}
    VALID_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "INR", "CAD", "AUD", "CHF", "CNY", "SGD", "AED", "NZD", "MXN"}

    @classmethod
    def authorize(
        cls,
        agent_role: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None,
    ) -> ToolAuthorizationResult:
        """
        Full authorization pipeline:
        1. Check High-Risk Action Blockers
        2. Check Role-based Tool Allowlist
        3. Validate and Sanitize Tool Arguments
        4. Check Rate Limits
        """
        role_key = (agent_role or "").lower().replace("_agent", "").strip()
        tool_clean = (tool_name or "").strip()
        args = arguments or {}

        # 1. High-Risk Action Blocker
        if tool_clean.lower() in cls.HIGH_RISK_ACTIONS or any(hr in tool_clean.lower() for hr in ["book", "pay", "cancel", "charge"]):
            reason = f"High-risk action '{tool_clean}' cannot be executed autonomously. Requires human approval."
            SecurityAuditor.record_event(
                event_type="HIGH_RISK_ACTION_BLOCKED",
                severity="CRITICAL",
                message=reason,
                agent_role=agent_role,
                tool_name=tool_name,
                execution_id=execution_id,
            )
            return ToolAuthorizationResult(
                authorized=False,
                reason=reason,
                tool_name=tool_clean,
                agent_role=agent_role,
                category="HIGH_RISK_BLOCKED",
            )

        # 2. Role-based Tool Allowlist
        allowed_tools = cls.AGENT_ALLOWLIST.get(role_key, set())
        if tool_clean not in allowed_tools:
            reason = f"Agent '{agent_role}' is not authorized to call tool '{tool_clean}'. Permitted tools: {sorted(list(allowed_tools))}"
            SecurityAuditor.record_event(
                event_type="UNAUTHORIZED_TOOL_REQUEST",
                severity="HIGH",
                message=reason,
                agent_role=agent_role,
                tool_name=tool_name,
                execution_id=execution_id,
                details={"allowed_tools": list(allowed_tools)},
            )
            return ToolAuthorizationResult(
                authorized=False,
                reason=reason,
                tool_name=tool_clean,
                agent_role=agent_role,
                category="PERMISSION_DENIED",
            )

        # 3. Tool Argument Validation
        arg_errors = cls.validate_arguments(tool_clean, args)
        if arg_errors:
            reason = f"Invalid tool arguments for '{tool_clean}': " + "; ".join(arg_errors)
            SecurityAuditor.record_event(
                event_type="TOOL_ARGUMENT_INVALID",
                severity="MEDIUM",
                message=reason,
                agent_role=agent_role,
                tool_name=tool_name,
                execution_id=execution_id,
                details={"errors": arg_errors},
            )
            return ToolAuthorizationResult(
                authorized=False,
                reason=reason,
                tool_name=tool_clean,
                agent_role=agent_role,
                category="ARGUMENT_INVALID",
                sanitized_arguments=args,
            )

        # 4. Rate Limiting Check
        rate_key = f"tool:{role_key}:{tool_clean}"
        try:
            rate_limiter.check_and_record(rate_key)
        except Exception as e:
            reason = str(e)
            SecurityAuditor.record_event(
                event_type="TOOL_RATE_LIMIT_EXCEEDED",
                severity="MEDIUM",
                message=reason,
                agent_role=agent_role,
                tool_name=tool_name,
                execution_id=execution_id,
            )
            return ToolAuthorizationResult(
                authorized=False,
                reason=reason,
                tool_name=tool_clean,
                agent_role=agent_role,
                category="RATE_LIMITED",
            )

        return ToolAuthorizationResult(
            authorized=True,
            reason=None,
            tool_name=tool_clean,
            agent_role=agent_role,
            category="AUTHORIZED",
            sanitized_arguments=args,
        )

    @classmethod
    def validate_arguments(cls, tool_name: str, args: Dict[str, Any]) -> List[str]:
        """Validate tool-specific argument schemas and bounds."""
        errors: List[str] = []

        # Flight tools
        if "flight" in tool_name:
            origin = args.get("origin")
            dest = args.get("destination")
            if origin is not None:
                if not isinstance(origin, str) or len(origin.strip()) < 2:
                    errors.append(f"Origin '{origin}' is invalid; must be at least 2 characters.")
                elif re.search(r"[<>{}\[\];`$]", origin):
                    errors.append("Origin contains prohibited shell or script characters.")
            if dest is not None:
                if not isinstance(dest, str) or len(dest.strip()) < 2:
                    errors.append(f"Destination '{dest}' is invalid; must be at least 2 characters.")
                elif re.search(r"[<>{}\[\];`$]", dest):
                    errors.append("Destination contains prohibited shell or script characters.")

            # Dates
            dep = args.get("departure_date") or args.get("date")
            ret = args.get("return_date")
            parsed_dep = cls._parse_iso_date(dep)
            parsed_ret = cls._parse_iso_date(ret)

            if dep and not parsed_dep:
                errors.append(f"Invalid departure_date format: '{dep}'. Expected YYYY-MM-DD.")
            if ret and not parsed_ret:
                errors.append(f"Invalid return_date format: '{ret}'. Expected YYYY-MM-DD.")
            if parsed_dep and parsed_ret and parsed_ret < parsed_dep:
                errors.append("return_date cannot precede departure_date.")

            # Travellers
            if "travellers" in args:
                try:
                    trav = int(args["travellers"])
                    if trav <= 0 or trav > 50:
                        errors.append(f"Traveller count must be between 1 and 50 (got {trav}).")
                except (ValueError, TypeError):
                    errors.append(f"Invalid travellers format: '{args['travellers']}'.")

            # Cabin class
            cabin = args.get("cabin_class")
            if cabin is not None and str(cabin).lower() not in cls.VALID_CABIN_CLASSES:
                errors.append(f"Invalid cabin_class '{cabin}'. Allowed: {sorted(list(cls.VALID_CABIN_CLASSES))}.")

            # Budget
            if "budget" in args and args["budget"] is not None:
                try:
                    b_val = float(args["budget"])
                    if b_val < 0:
                        errors.append(f"Budget cannot be negative (got {b_val}).")
                except (ValueError, TypeError):
                    errors.append(f"Invalid budget: '{args['budget']}'.")

        # Hotel tools
        elif "hotel" in tool_name:
            dest = args.get("destination") or args.get("location")
            if dest is not None and (not isinstance(dest, str) or len(dest.strip()) < 2):
                errors.append(f"Destination/Location '{dest}' is too short.")

            check_in = cls._parse_iso_date(args.get("check_in_date") or args.get("check_in"))
            check_out = cls._parse_iso_date(args.get("check_out_date") or args.get("check_out"))
            if check_in and check_out and check_out < check_in:
                errors.append("check_out date cannot precede check_in date.")

            if "budget_per_night" in args and args["budget_per_night"] is not None:
                try:
                    bpn = float(args["budget_per_night"])
                    if bpn < 0:
                        errors.append("budget_per_night cannot be negative.")
                except (ValueError, TypeError):
                    errors.append("Invalid budget_per_night format.")

        # Weather tools
        elif "weather" in tool_name or tool_name in ("current_weather", "forecast", "alerts"):
            loc = args.get("location") or args.get("city")
            lat = args.get("latitude") or args.get("lat")
            lon = args.get("longitude") or args.get("lon")

            if loc is not None:
                if not isinstance(loc, str) or len(loc.strip()) < 2:
                    errors.append(f"Weather location '{loc}' is invalid.")
            elif lat is not None or lon is not None:
                try:
                    if lat is not None:
                        lat_val = float(lat)
                        if not (-90.0 <= lat_val <= 90.0):
                            errors.append(f"Latitude must be between -90 and 90 (got {lat_val}).")
                    if lon is not None:
                        lon_val = float(lon)
                        if not (-180.0 <= lon_val <= 180.0):
                            errors.append(f"Longitude must be between -180 and 180 (got {lon_val}).")
                except (ValueError, TypeError):
                    errors.append("Invalid latitude/longitude format.")

        # Search & Fetch tools
        elif tool_name in ("web_search", "search_news"):
            q = args.get("query")
            if not q or not isinstance(q, str) or not q.strip():
                errors.append("Search query cannot be empty.")
            elif len(q.strip()) > 300:
                errors.append(f"Search query too long ({len(q.strip())} > 300 characters).")

        elif tool_name in ("fetch_page", "safe_fetch_page"):
            url = args.get("url")
            if not url or not isinstance(url, str):
                errors.append("URL must be a non-empty string.")
            else:
                url_clean = url.strip()
                parsed = urlparse(url_clean)
                if parsed.scheme not in ("http", "https"):
                    errors.append(f"Unsupported protocol '{parsed.scheme}'. Only HTTP and HTTPS are permitted.")
                hostname = (parsed.hostname or "").lower()
                if not hostname:
                    errors.append("Missing host in URL.")
                else:
                    for pattern in BLOCKED_IP_PATTERNS:
                        if re.search(pattern, hostname):
                            errors.append(f"Target '{hostname}' is a prohibited loopback/private network address.")
                            break

        # Currency tool
        elif "exchange_rate" in tool_name or "currency" in tool_name:
            base = args.get("base_currency") or args.get("from_currency")
            target = args.get("target_currency") or args.get("to_currency")
            if base and (len(str(base).strip()) != 3 or str(base).strip().upper() not in cls.VALID_CURRENCIES):
                errors.append(f"Invalid base currency '{base}'.")
            if target and (len(str(target).strip()) != 3 or str(target).strip().upper() not in cls.VALID_CURRENCIES):
                errors.append(f"Invalid target currency '{target}'.")

        return errors

    @staticmethod
    def _parse_iso_date(val: Any) -> Optional[date]:
        """Parse ISO date."""
        if not val:
            return None
        if isinstance(val, date):
            return val
        if isinstance(val, str):
            try:
                return datetime.strptime(val.strip(), "%Y-%m-%d").date()
            except ValueError:
                return None
        return None
