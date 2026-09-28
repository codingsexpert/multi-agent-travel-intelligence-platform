"""Unit tests for custom exception hierarchy and logger secret scrubbing."""

import logging
from utils.exceptions import (
    AppError,
    ConfigurationError,
    ValidationError,
    ServiceError,
    GuardrailViolationError,
)
from utils.logger import setup_logger, SecretScrubbingFilter


def test_custom_exceptions():
    """Verify custom exception serialization and safe user messages."""
    err = AppError("Internal DB connection timeout", user_message="Service unavailable", code="TIMEOUT")
    data = err.to_dict()
    assert data["code"] == "TIMEOUT"
    assert data["message"] == "Internal DB connection timeout"
    assert data["user_message"] == "Service unavailable"

    config_err = ConfigurationError("Missing key", details={"key": "SUPABASE_URL"})
    assert config_err.code == "CONFIG_ERROR"
    assert config_err.details["key"] == "SUPABASE_URL"

    val_err = ValidationError("Negative budget")
    assert val_err.code == "VALIDATION_ERROR"

    svc_err = ServiceError("Amadeus", "Rate limit exceeded")
    assert svc_err.code == "SERVICE_ERROR"
    assert svc_err.details["service"] == "Amadeus"

    gr_err = GuardrailViolationError("PROMPT_INJECTION", "Detected system prompt leak attempt")
    assert gr_err.code == "GUARDRAIL_VIOLATION"


def test_logger_secret_scrubbing():
    """Verify that sensitive keys, tokens, and passwords are masked by the logging filter."""
    scrubber = SecretScrubbingFilter()
    sample_log = "Error connecting with api_key=sk-1234567890abcdef1234567890 and token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc"
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg=sample_log,
        args=(),
        exc_info=None,
    )
    scrubber.filter(record)
    assert "sk-1234567890abcdef1234567890" not in record.msg
    assert "[REDACTED" in record.msg
