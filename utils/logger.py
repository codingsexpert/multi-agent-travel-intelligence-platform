"""Application logging utility with structured formatting and secret scrubbing."""

import logging
import re
import sys
from typing import Optional

# Regex pattern to match potential secrets, tokens, and keys in log messages
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|bearer|service_role)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"gh[op]_[a-zA-Z0-9]{20,}"),
    re.compile(r"eyJ[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]{20,}"),  # JWTs
]


class SecretScrubbingFilter(logging.Filter):
    """Logging filter to mask sensitive values like API keys, tokens, and passwords."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._scrub(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._scrub(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._scrub(str(arg)) for arg in record.args)
        return True

    @staticmethod
    def _scrub(text: str) -> str:
        for pattern in SECRET_PATTERNS:
            text = pattern.sub(r"\1: [REDACTED]", text) if "api" in pattern.pattern else pattern.sub("[REDACTED_SECRET]", text)
        return text


def setup_logger(
    name: str = "travel_platform",
    log_level: Optional[str] = None,
) -> logging.Logger:
    """Configure and return a structured logger with secret scrubbing.

    Args:
        name: Logger name (usually module name).
        log_level: Optional log level override (e.g. INFO, DEBUG, WARNING, ERROR).

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    effective_level = (log_level or "INFO").upper()
    logger.setLevel(getattr(logging, effective_level, logging.INFO))

    # Standard structured format: timestamp | level | module | message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SecretScrubbingFilter())

    logger.addHandler(console_handler)
    logger.propagate = False

    return logger


# Default application-wide logger
logger = setup_logger("travel_platform")
