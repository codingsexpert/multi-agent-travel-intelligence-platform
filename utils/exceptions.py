"""Application exception hierarchy for safe and structured error handling."""

from typing import Optional, Dict, Any


class AppError(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        code: str = "INTERNAL_ERROR",
    ):
        super().__init__(message)
        self.message = message
        self.user_message = user_message or "An unexpected error occurred. Please try again later."
        self.details = details or {}
        self.code = code

    def to_dict(self) -> Dict[str, Any]:
        """Serialize error for logging or structured inspection."""
        return {
            "code": self.code,
            "message": self.message,
            "user_message": self.user_message,
            "details": self.details,
        }


class ConfigurationError(AppError):
    """Raised when application configuration is invalid or missing required values."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            user_message="System configuration issue detected. Please contact the administrator.",
            details=details,
            code="CONFIG_ERROR",
        )


class ValidationError(AppError):
    """Raised when data validation fails against business rules."""

    def __init__(self, message: str, user_message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            user_message=user_message or "Invalid travel request parameters provided.",
            details=details,
            code="VALIDATION_ERROR",
        )


class ServiceError(AppError):
    """Raised when an external service or internal subsystem fails."""

    def __init__(
        self,
        service_name: str,
        message: str,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        full_details = {"service": service_name, **(details or {})}
        super().__init__(
            message=f"[{service_name}] {message}",
            user_message=user_message or f"Service '{service_name}' is temporarily unavailable.",
            details=full_details,
            code="SERVICE_ERROR",
        )


class GuardrailViolationError(AppError):
    """Raised when an input or output violates security or safety guardrails."""

    def __init__(self, violation_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        full_details = {"violation_type": violation_type, **(details or {})}
        super().__init__(
            message=f"Guardrail violation ({violation_type}): {message}",
            user_message="Your request could not be processed due to safety constraints.",
            details=full_details,
            code="GUARDRAIL_VIOLATION",
        )


class EmbeddingConfigurationError(ConfigurationError):
    """Raised when embedding provider credentials or configurations are missing."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details=details)
        self.code = "EMBEDDING_CONFIG_ERROR"
        self.user_message = "Vector embedding service is not configured. Please supply API credentials or enable DEMO_MODE."


class RAGRetrievalError(ServiceError):
    """Raised when knowledge ingestion or vector similarity retrieval fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(service_name="RAGKnowledgeRetriever", message=message, details=details)
        self.code = "RAG_RETRIEVAL_ERROR"


class InputValidationError(GuardrailViolationError):
    """Raised when user input violates input formatting or sanity guardrails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(violation_type="INPUT_VALIDATION_ERROR", message=message, details=details)
        self.code = "INPUT_VALIDATION_ERROR"
        self.user_message = "Travel request parameters are invalid or malformed."


class PromptInjectionError(GuardrailViolationError):
    """Raised when malicious instructions or prompt injection attempts are detected."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(violation_type="PROMPT_INJECTION_DETECTED", message=message, details=details)
        self.code = "PROMPT_INJECTION_DETECTED"
        self.user_message = "Your request was rejected due to suspicious or unauthorized instruction patterns."


class ToolPermissionDeniedError(GuardrailViolationError):
    """Raised when an agent attempts to invoke an unauthorized tool or high-risk action."""

    def __init__(self, tool_name: str, agent_role: str, details: Optional[Dict[str, Any]] = None):
        full_details = {"tool_name": tool_name, "agent_role": agent_role, **(details or {})}
        super().__init__(
            violation_type="TOOL_PERMISSION_DENIED",
            message=f"Agent '{agent_role}' is not authorized to execute tool '{tool_name}'.",
            details=full_details,
        )
        self.code = "TOOL_PERMISSION_DENIED"
        self.user_message = "The requested tool action is not permitted."


class ToolArgumentInvalidError(GuardrailViolationError):
    """Raised when arguments passed to a tool fail schema or safety bounds."""

    def __init__(self, tool_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        full_details = {"tool_name": tool_name, **(details or {})}
        super().__init__(
            violation_type="TOOL_ARGUMENT_INVALID",
            message=f"Invalid arguments for tool '{tool_name}': {message}",
            details=full_details,
        )
        self.code = "TOOL_ARGUMENT_INVALID"
        self.user_message = "Tool execution failed due to invalid arguments."


class RateLimitExceededError(GuardrailViolationError):
    """Raised when rate limit bounds are exceeded for requests or tools."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(violation_type="RATE_LIMIT_EXCEEDED", message=message, details=details)
        self.code = "RATE_LIMIT_EXCEEDED"
        self.user_message = "Rate limit exceeded. Please wait a moment before trying again."


class WorkflowLimitExceededError(GuardrailViolationError):
    """Raised when workflow circuit breakers (steps, tool calls, retries, timeout) trip."""

    def __init__(self, limit_name: str, current_value: Any, max_value: Any, details: Optional[Dict[str, Any]] = None):
        full_details = {"limit_name": limit_name, "current_value": current_value, "max_value": max_value, **(details or {})}
        super().__init__(
            violation_type="WORKFLOW_LIMIT_EXCEEDED",
            message=f"Workflow execution limit reached for '{limit_name}' ({current_value} >= {max_value}).",
            details=full_details,
        )
        self.code = "WORKFLOW_LIMIT_EXCEEDED"
        self.user_message = "Workflow halted safely because maximum execution budget was reached."


class OutputValidationError(GuardrailViolationError):
    """Raised when agent or tool outputs fail schema, bounds, or source verification."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(violation_type="OUTPUT_VALIDATION_ERROR", message=message, details=details)
        self.code = "OUTPUT_VALIDATION_ERROR"
        self.user_message = "Generated itinerary output did not pass data validation."


class SecurityViolationError(GuardrailViolationError):
    """Raised for runtime security violations like SSRF, unauthorized data access, etc."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(violation_type="SECURITY_VIOLATION", message=message, details=details)
        self.code = "SECURITY_VIOLATION"
        self.user_message = "Security policy violation detected."

