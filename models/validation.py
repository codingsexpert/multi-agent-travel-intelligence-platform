"""Pydantic v2 models for deterministic travel itinerary and constraint validation."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    """Severity classification for validation issues."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ValidationIssue(BaseModel):
    """Specific inconsistency, temporal conflict, or constraint violation."""

    severity: ValidationSeverity
    code: str = Field(description="Unique machine-readable issue identifier (e.g., TIME_CONFLICT).")
    message: str = Field(description="Human-readable explanation of the validation issue.")
    component: str = Field(description="Subsystem or entity evaluated (e.g., budget, flights, dates).")
    field: Optional[str] = Field(default=None, description="Optional target field associated with the issue.")


class ValidationResult(BaseModel):
    """Structured aggregate outcome of deterministic itinerary validation."""

    valid: bool = Field(description="True if no critical ERROR-level issues were detected.")
    issues: List[ValidationIssue] = Field(default_factory=list, description="All validation issues across severities.")
    warnings: List[ValidationIssue] = Field(default_factory=list, description="Recoverable WARNING-level issues.")
    errors: List[ValidationIssue] = Field(default_factory=list, description="Critical blocking ERROR-level issues.")
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = Field(description="Resulting workflow status (READY_FOR_ITINERARY, READY_WITH_WARNINGS, or VALIDATION_FAILED).")

    @classmethod
    def from_issues(cls, issues: List[ValidationIssue]) -> "ValidationResult":
        """Factory method to partition issues by severity and derive aggregate validity and status."""
        errors = [issue for issue in issues if issue.severity == ValidationSeverity.ERROR]
        warnings = [issue for issue in issues if issue.severity == ValidationSeverity.WARNING]
        is_valid = len(errors) == 0

        if not is_valid:
            status = "VALIDATION_FAILED"
        elif len(warnings) > 0:
            status = "READY_WITH_WARNINGS"
        else:
            status = "READY_FOR_ITINERARY"

        return cls(
            valid=is_valid,
            issues=issues,
            warnings=warnings,
            errors=errors,
            checked_at=datetime.now(timezone.utc).isoformat(),
            status=status,
        )
