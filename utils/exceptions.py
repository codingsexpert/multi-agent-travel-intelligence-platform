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
