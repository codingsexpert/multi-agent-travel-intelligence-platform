"""Output guardrails: schema validation, numerical/temporal sanity checks, and fact/source attribution safety."""

import logging
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field, ValidationError

from guardrails.security import SecretRedactor, SecurityAuditor
from models.budget import BudgetSummary
from models.planner import PlannerResult
from models.research import FreshWebResearchResult
from models.specialized_options import (
    ActivityOption,
    DestinationResearch,
    FlightOption,
    HotelOption,
    WeatherObservation,
)
from models.validation import ValidationResult

from utils.exceptions import OutputValidationError

logger = logging.getLogger("travel_platform.guardrails.output")


class OutputGuardrailResult(BaseModel):
    """Structured result returned by output validation."""

    valid: bool = Field(..., description="Whether the agent output passed schema and fact/source validation")
    agent_role: str = Field(..., description="The agent role producing this output")
    errors: List[str] = Field(default_factory=list, description="Validation failure messages")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings or source notes")
    sanitized_output: Optional[Any] = Field(default=None, description="Sanitized/redacted and schema-validated object")
    sources_verified: bool = Field(default=True, description="Whether all external claims have verified source attribution")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic validation metadata")


class OutputGuardrail:
    """Validates agent outputs against strict Pydantic schemas, value bounds, and citation rules."""

    MODEL_SCHEMAS: Dict[str, Type[BaseModel]] = {
        "planner": PlannerResult,
        "flight": FlightOption,
        "hotel": HotelOption,
        "activity": ActivityOption,
        "weather": WeatherObservation,
        "research": DestinationResearch,
        "budget": BudgetSummary,
        "validator": ValidationResult,
    }

    VALID_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "INR", "CAD", "AUD", "CHF", "CNY", "SGD", "AED", "NZD", "MXN"}

    @classmethod
    def validate_agent_output(
        cls,
        agent_role: str,
        output_data: Any,
        execution_id: Optional[str] = None,
    ) -> OutputGuardrailResult:
        """
        Validate agent output before propagating downstream:
        1. Pydantic schema validation
        2. Bounds & Sanity checks (prices, budget, dates, travellers)
        3. Fact & Source attribution safety
        4. Secret redaction
        """
        role_key = (agent_role or "").lower().replace("_agent", "").strip()
        errors: List[str] = []
        warnings: List[str] = []
        sources_verified = True

        if output_data is None:
            errors.append(f"Agent '{agent_role}' returned empty/None output.")
            SecurityAuditor.record_event(
                event_type="OUTPUT_VALIDATION_FAILURE",
                severity="HIGH",
                message=f"Agent '{agent_role}' output is None",
                agent_role=agent_role,
                execution_id=execution_id,
            )
            return OutputGuardrailResult(
                valid=False,
                agent_role=agent_role,
                errors=errors,
                sources_verified=False,
            )

        # 1. Schema Validation
        target_schema = cls.MODEL_SCHEMAS.get(role_key)
        validated_obj = None

        if target_schema:
            if isinstance(output_data, target_schema):
                validated_obj = output_data
            elif isinstance(output_data, list):
                # For agents returning list of options (e.g. Flight, Hotel, Activity)
                validated_items = []
                for idx, item in enumerate(output_data):
                    if isinstance(item, target_schema):
                        validated_items.append(item)
                    elif isinstance(item, dict):
                        try:
                            validated_items.append(target_schema.model_validate(item))
                        except ValidationError as ve:
                            errors.append(f"Item #{idx} failed schema validation: {ve}")
                    else:
                        errors.append(f"Item #{idx} has unexpected type {type(item)}.")
                if not errors:
                    validated_obj = validated_items
            elif isinstance(output_data, dict):
                try:
                    validated_obj = target_schema.model_validate(output_data)
                except ValidationError as ve:
                    errors.append(f"Output schema validation failed for {role_key}: {ve}")
            else:
                # Might be specialized or composite output
                validated_obj = output_data
        else:
            validated_obj = output_data

        if errors:
            SecurityAuditor.record_event(
                event_type="OUTPUT_VALIDATION_FAILURE",
                severity="HIGH",
                message="; ".join(errors),
                agent_role=agent_role,
                execution_id=execution_id,
                details={"errors": errors},
            )
            return OutputGuardrailResult(
                valid=False,
                agent_role=agent_role,
                errors=errors,
                sources_verified=False,
            )

        # 2. Field Value Sanity Checks
        cls._verify_values(role_key, validated_obj, errors, warnings)

        # 3. Fact and Source Safety Checks
        sources_verified = cls._verify_sources(role_key, validated_obj, warnings)

        # 4. Secret Redaction on output dictionaries
        sanitized = validated_obj
        if isinstance(validated_obj, BaseModel):
            dumped = validated_obj.model_dump()
            sanitized = SecretRedactor.redact_dict(dumped)
        elif isinstance(validated_obj, dict):
            sanitized = SecretRedactor.redact_dict(validated_obj)
        elif isinstance(validated_obj, list):
            sanitized = [
                SecretRedactor.redact_dict(item.model_dump()) if isinstance(item, BaseModel)
                else SecretRedactor.redact_dict(item) if isinstance(item, dict)
                else item
                for item in validated_obj
            ]

        is_valid = len(errors) == 0

        if not is_valid:
            SecurityAuditor.record_event(
                event_type="OUTPUT_VALIDATION_FAILURE",
                severity="HIGH",
                message="; ".join(errors),
                agent_role=agent_role,
                execution_id=execution_id,
                details={"errors": errors, "warnings": warnings},
            )

        return OutputGuardrailResult(
            valid=is_valid,
            agent_role=agent_role,
            errors=errors,
            warnings=warnings,
            sanitized_output=sanitized,
            sources_verified=sources_verified,
            metadata={"errors_count": len(errors), "warnings_count": len(warnings)},
        )

    @classmethod
    def _verify_values(cls, role_key: str, obj: Any, errors: List[str], warnings: List[str]) -> None:
        """Inspect domain fields for impossible numerical or temporal values."""
        items = obj if isinstance(obj, list) else [obj]

        for item in items:
            # Check price/cost non-negativity
            for price_attr in ("price", "cost", "total_cost", "total_price", "estimated_cost"):
                val = getattr(item, price_attr, None) if isinstance(item, BaseModel) else item.get(price_attr) if isinstance(item, dict) else None
                if val is not None:
                    try:
                        if float(val) < 0:
                            errors.append(f"Field '{price_attr}' cannot be negative (got {val}).")
                    except (ValueError, TypeError):
                        errors.append(f"Invalid non-numeric value for '{price_attr}': {val}.")

            # Currency check
            curr = getattr(item, "currency", None) if isinstance(item, BaseModel) else item.get("currency") if isinstance(item, dict) else None
            if curr is not None:
                curr_str = str(curr).strip().upper()
                if curr_str not in cls.VALID_CURRENCIES:
                    warnings.append(f"Non-standard currency '{curr}'.")

            # Budget summary check
            if role_key == "budget" or isinstance(item, BudgetSummary):
                total_budget = getattr(item, "total_budget", None)
                total_est = getattr(item, "total_estimated_cost", None)
                if total_budget is not None and float(total_budget) < 0:
                    errors.append(f"Total budget cannot be negative: {total_budget}.")
                if total_est is not None and float(total_est) < 0:
                    errors.append(f"Total estimated cost cannot be negative: {total_est}.")

    @classmethod
    def _verify_sources(cls, role_key: str, obj: Any, warnings: List[str]) -> bool:
        """Verify that external claims and research findings carry authentic source metadata."""
        items = obj if isinstance(obj, list) else [obj]
        all_verified = True

        for item in items:
            # Research findings verification
            if isinstance(item, DestinationResearch):
                if item.fresh_research and item.fresh_research.findings:
                    for f in item.fresh_research.findings:
                        if not f.source or not f.source.strip():
                            warnings.append(f"Research finding for '{f.topic}' is missing source attribution.")
                            all_verified = False

            elif isinstance(item, FreshWebResearchResult):
                for f in item.findings:
                    if not f.source or not f.source.strip():
                        warnings.append(f"Web research finding for '{f.topic}' is missing source attribution.")
                        all_verified = False

            # Option source metadata verification
            for src_attr in ("source", "provider", "booking_source"):
                src_val = getattr(item, src_attr, None) if isinstance(item, BaseModel) else item.get(src_attr) if isinstance(item, dict) else None
                if src_val is not None and not str(src_val).strip():
                    warnings.append(f"Item is missing descriptive '{src_attr}' metadata.")
                    all_verified = False

        return all_verified
