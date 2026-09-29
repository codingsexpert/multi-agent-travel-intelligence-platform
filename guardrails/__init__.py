"""Production guardrails and security layer (Phase 11).

Provides zero-trust protection for:
1. Input Guardrails (injection defense, normalization, PII sanitization, schema/parameter validation)
2. Tool Guardrails (least privilege allowlists, high-risk autonomous action blocking, argument validation)
3. Output Guardrails (Pydantic schema validation, value bounds, fact/source attribution safety)
4. Runtime Security (secret redaction, PII sanitization, rate limiting, circuit breaker, security auditing)
"""

from guardrails.input import GuardrailResult, InputGuardrail
from guardrails.output import OutputGuardrail, OutputGuardrailResult
from guardrails.security import (
    DataInstructionSeparator,
    PIISanitizer,
    RateLimiter,
    SecretRedactor,
    SecurityAuditor,
    WorkflowCircuitBreaker,
    rate_limiter,
)
from guardrails.tools import ToolAuthorizationResult, ToolGuardrail

__all__ = [
    "GuardrailResult",
    "InputGuardrail",
    "OutputGuardrail",
    "OutputGuardrailResult",
    "ToolGuardrail",
    "ToolAuthorizationResult",
    "SecretRedactor",
    "PIISanitizer",
    "RateLimiter",
    "WorkflowCircuitBreaker",
    "SecurityAuditor",
    "DataInstructionSeparator",
    "rate_limiter",
]
