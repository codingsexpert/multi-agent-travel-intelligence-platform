"""Input guardrails: prompt injection detection, input normalization, parameter validation, and PII masking."""

import logging
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from config.settings import get_settings
from guardrails.security import PIISanitizer, SecretRedactor, SecurityAuditor
from utils.exceptions import InputValidationError, PromptInjectionError

logger = logging.getLogger("travel_platform.guardrails.input")


class GuardrailResult(BaseModel):
    """Structured result returned by input and workflow guardrails."""

    allowed: bool = Field(..., description="Whether the input passed all safety and validity checks")
    reason: Optional[str] = Field(default=None, description="Human-readable explanation if rejected or warned")
    category: str = Field(default="PASSED", description="Category of check (PASSED, PROMPT_INJECTION, MALFORMED_INPUT, OVERSIZED_INPUT, SUSPICIOUS_INSTRUCTION)")
    severity: str = Field(default="NONE", description="Severity level: NONE, LOW, MEDIUM, HIGH, CRITICAL")
    sanitized_input: str = Field(default="", description="Sanitized/redacted copy of user input")
    validation_errors: List[str] = Field(default_factory=list, description="Specific parameter validation errors")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata regarding validation decisions")


class InputGuardrail:
    """Centralized input validation and prompt injection defense service."""

    # Explicit prompt injection patterns
    INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions", re.IGNORECASE),
        re.compile(r"reveal\s+(?:the\s+)?(?:system\s+prompt|developer\s+prompt|instructions)", re.IGNORECASE),
        re.compile(r"(?:show|print|leak|display|dump|expose)\s+(?:me\s+)?(?:all\s+)?(?:api[\s_-]?keys?|secrets?|tokens?|credentials?)", re.IGNORECASE),
        re.compile(r"bypass\s+(?:all\s+)?(?:security|guardrails|safety|restrictions|policies)", re.IGNORECASE),

        re.compile(r"execute\s+(?:this\s+)?(?:bash|shell|command|code|script|sql)", re.IGNORECASE),
        re.compile(r"change\s+(?:your\s+)?tool\s+permissions", re.IGNORECASE),
        re.compile(r"pretend\s+you\s+are\s+(?:the\s+)?(?:system|admin|root|superuser|developer)", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+(?:in\s+)?(?:developer|god|dan|jailbreak)\s+mode", re.IGNORECASE),
        re.compile(r"(?:disregard|override|forget)\s+(?:all\s+)?(?:rules|constraints|instructions)", re.IGNORECASE),
        re.compile(r"system\s*:\s*role\s*=\s*['\"]?system['\"]?", re.IGNORECASE),
        re.compile(r"<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\]", re.IGNORECASE),
    ]

    # Suspicious tool/code execution syntax
    TOOL_CODE_PATTERNS = [
        re.compile(r"__import__\s*\(", re.IGNORECASE),
        re.compile(r"(?:eval|exec)\s*\(", re.IGNORECASE),
        re.compile(r"os\.(?:system|popen|spawn)", re.IGNORECASE),
        re.compile(r"subprocess\.(?:run|call|Popen)", re.IGNORECASE),
        re.compile(r"<script[\s>]", re.IGNORECASE),
        re.compile(r"(?:javascript|data):", re.IGNORECASE),
    ]

    VALID_CURRENCIES = {
        "USD", "EUR", "GBP", "JPY", "INR", "CAD", "AUD", "CHF", "CNY", "SGD", "AED", "NZD", "MXN", "SEK", "NOK"
    }

    @classmethod
    def validate_text(cls, text: Optional[str], execution_id: Optional[str] = None) -> GuardrailResult:
        """
        Validate raw string user input against length limits, prompt injection,
        suspicious code/tool injection, and PII.
        """
        settings = get_settings()
        raw_text = text or ""

        # 1. Check input length
        max_chars = settings.max_input_chars
        if len(raw_text) > max_chars:
            reason = f"Input exceeds maximum allowed length ({len(raw_text)} > {max_chars} characters)."
            SecurityAuditor.record_event(
                event_type="OVERSIZED_INPUT_BLOCKED",
                severity="MEDIUM",
                message=reason,
                execution_id=execution_id,
                details={"input_length": len(raw_text), "max_chars": max_chars},
            )
            return GuardrailResult(
                allowed=False,
                reason=reason,
                category="OVERSIZED_INPUT",
                severity="MEDIUM",
                sanitized_input=raw_text[:200] + "... [TRUNCATED]",
                validation_errors=[reason],
            )

        # 2. Check Prompt Injection
        for pattern in cls.INJECTION_PATTERNS:
            match = pattern.search(raw_text)
            if match:
                matched_phrase = match.group(0)
                reason = "Suspicious instruction or prompt injection attempt detected."
                SecurityAuditor.record_event(
                    event_type="PROMPT_INJECTION_DETECTED",
                    severity="HIGH",
                    message=f"Prompt injection matched: '{matched_phrase}'",
                    execution_id=execution_id,
                    details={"matched_pattern": pattern.pattern},
                )
                return GuardrailResult(
                    allowed=False,
                    reason=reason,
                    category="PROMPT_INJECTION",
                    severity="HIGH",
                    sanitized_input="[SUSPICIOUS_CONTENT_BLOCKED]",
                    validation_errors=[reason],
                    metadata={"matched_pattern": pattern.pattern},
                )

        # 3. Check Suspicious Code/Tool Injection
        for pattern in cls.TOOL_CODE_PATTERNS:
            if pattern.search(raw_text):
                reason = "Suspicious code execution or command injection syntax detected."
                SecurityAuditor.record_event(
                    event_type="SUSPICIOUS_INSTRUCTION_BLOCKED",
                    severity="HIGH",
                    message=reason,
                    execution_id=execution_id,
                    details={"matched_pattern": pattern.pattern},
                )
                return GuardrailResult(
                    allowed=False,
                    reason=reason,
                    category="SUSPICIOUS_INSTRUCTION",
                    severity="HIGH",
                    sanitized_input="[CODE_EXECUTION_BLOCKED]",
                    validation_errors=[reason],
                )

        # 4. PII Sanitization
        sanitized, pii_detected = PIISanitizer.sanitize(raw_text)
        # 5. Secret Redaction
        sanitized = SecretRedactor.redact_text(sanitized)

        if pii_detected:
            SecurityAuditor.record_event(
                event_type="PII_DETECTED_AND_SANITIZED",
                severity="LOW",
                message="Personal Identifiable Information detected in user input and sanitized.",
                execution_id=execution_id,
            )

        return GuardrailResult(
            allowed=True,
            reason=None,
            category="PASSED",
            severity="NONE",
            sanitized_input=sanitized,
            metadata={"pii_sanitized": pii_detected},
        )

    @classmethod
    def validate_travel_request(
        cls,
        data: Dict[str, Any],
        execution_id: Optional[str] = None,
    ) -> GuardrailResult:
        """
        Validate structured travel parameters:
        - destination & origin
        - dates & duration
        - travellers
        - budget & currency
        - cabin class & preferences
        """
        errors: List[str] = []

        # 1. Text validations across string fields
        text_fields = ["query", "destination", "origin", "preferences"]
        for field in text_fields:
            val = data.get(field)
            if isinstance(val, str) and val.strip():
                text_result = cls.validate_text(val, execution_id=execution_id)
                if not text_result.allowed:
                    return text_result
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, str):
                        text_result = cls.validate_text(item, execution_id=execution_id)
                        if not text_result.allowed:
                            return text_result

        # 2. Destination validation
        dest = data.get("destination")
        if dest is not None:
            if not isinstance(dest, str) or not dest.strip():
                errors.append("Destination cannot be empty.")
            elif len(dest.strip()) < 2:
                errors.append(f"Destination '{dest}' is too short.")
            elif re.search(r"[<>{}\[\]|\\]", dest):
                errors.append(f"Destination '{dest}' contains invalid special characters.")

        # 3. Origin validation
        origin = data.get("origin")
        if origin is not None and isinstance(origin, str) and origin.strip():
            if re.search(r"[<>{}\[\]|\\]", origin):
                errors.append(f"Origin '{origin}' contains invalid special characters.")

        # 4. Travellers count
        travellers = data.get("travellers")
        if travellers is not None:
            try:
                trav_int = int(travellers)
                if trav_int <= 0:
                    errors.append(f"Traveller count must be greater than 0 (got {trav_int}).")
                elif trav_int > 50:
                    errors.append(f"Unrealistic traveller count: {trav_int}. Maximum allowed is 50.")
            except (ValueError, TypeError):
                errors.append(f"Invalid traveller count format: '{travellers}'.")

        # 5. Budget and Currency
        budget = data.get("budget")
        if budget is not None:
            try:
                budget_float = float(budget)
                if budget_float < 0:
                    errors.append(f"Budget cannot be negative (got {budget_float}).")
            except (ValueError, TypeError):
                errors.append(f"Invalid budget value: '{budget}'.")

        currency = data.get("currency")
        if currency is not None:
            curr_str = str(currency).strip().upper()
            if len(curr_str) != 3 or curr_str not in cls.VALID_CURRENCIES:
                errors.append(f"Invalid currency '{currency}'. Expected standard 3-letter currency code (e.g., USD, EUR, GBP).")

        # 6. Date validation & Impossible ranges
        dep_date = data.get("departure_date") or data.get("start_date")
        ret_date = data.get("return_date") or data.get("end_date")

        parsed_dep: Optional[date] = None
        parsed_ret: Optional[date] = None

        if dep_date:
            parsed_dep = cls._parse_date(dep_date)
            if not parsed_dep:
                errors.append(f"Malformed departure date: '{dep_date}'. Expected ISO format (YYYY-MM-DD).")

        if ret_date:
            parsed_ret = cls._parse_date(ret_date)
            if not parsed_ret:
                errors.append(f"Malformed return date: '{ret_date}'. Expected ISO format (YYYY-MM-DD).")

        if parsed_dep and parsed_ret:
            if parsed_ret < parsed_dep:
                errors.append(f"Impossible date range: return date ({parsed_ret}) is before departure date ({parsed_dep}).")

        # 7. Contradictory duration
        duration = data.get("duration_days") or data.get("duration")
        if duration is not None:
            try:
                dur_int = int(duration)
                if dur_int <= 0:
                    errors.append(f"Trip duration must be at least 1 day (got {dur_int}).")
                elif parsed_dep and parsed_ret:
                    calc_days = (parsed_ret - parsed_dep).days + 1
                    if abs(dur_int - calc_days) > 1:
                        errors.append(f"Contradictory duration: specified {dur_int} days but date range spans {calc_days} days.")
            except (ValueError, TypeError):
                errors.append(f"Invalid duration format: '{duration}'.")

        # If errors were found, return structured GuardrailResult
        if errors:
            reason = "; ".join(errors)
            SecurityAuditor.record_event(
                event_type="INPUT_VALIDATION_ERROR",
                severity="MEDIUM",
                message=reason,
                execution_id=execution_id,
                details={"errors": errors},
            )
            return GuardrailResult(
                allowed=False,
                reason=reason,
                category="MALFORMED_INPUT",
                severity="MEDIUM",
                sanitized_input="",
                validation_errors=errors,
            )

        return GuardrailResult(
            allowed=True,
            reason=None,
            category="PASSED",
            severity="NONE",
            sanitized_input="",
            validation_errors=[],
        )

    @staticmethod
    def _parse_date(val: Any) -> Optional[date]:
        """Safely parse date objects or ISO strings."""
        if isinstance(val, date):
            return val
        if isinstance(val, str):
            try:
                return datetime.strptime(val.strip(), "%Y-%m-%d").date()
            except ValueError:
                return None
        return None
