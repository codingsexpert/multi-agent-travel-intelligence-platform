"""Pydantic schemas and enums for Phase 13: Human-in-the-Loop Approval Workflow."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator


class ActionRiskLevel(str, Enum):
    """Categorical classification of action operational risk."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ApprovalStatus(str, Enum):
    """Status lifecycle of an approval request."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ApprovalDecision(str, Enum):
    """Decision outcomes for an approval request."""

    APPROVE = "APPROVE"
    REJECT = "REJECT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# Deterministic classification: Read-only vs. High-Impact Transactional Actions
READ_ONLY_ACTIONS = {
    "search_flights",
    "compare_flights",
    "get_flight_details",
    "search_hotels",
    "compare_hotels",
    "get_hotel_details",
    "search_places",
    "search_activities",
    "calculate_route",
    "estimate_travel_time",
    "get_current_weather",
    "lookup_weather",
    "get_forecast",
    "get_weather_alerts",
    "web_search",
    "fetch_page",
    "search_news",
    "research",
    "get_exchange_rate",
    "generate_itinerary",
    "validate_plan",
    "calculate_budget",
}

HIGH_IMPACT_ACTIONS: Dict[str, ActionRiskLevel] = {
    "book_flight": ActionRiskLevel.HIGH,
    "book_hotel": ActionRiskLevel.HIGH,
    "purchase_activity": ActionRiskLevel.HIGH,
    "book_activity": ActionRiskLevel.HIGH,
    "reserve_car": ActionRiskLevel.MEDIUM,
    "cancel_booking": ActionRiskLevel.CRITICAL,
    "cancel_flight": ActionRiskLevel.CRITICAL,
    "cancel_hotel": ActionRiskLevel.CRITICAL,
    "cancel_activity": ActionRiskLevel.HIGH,
    "modify_booking": ActionRiskLevel.HIGH,
    "change_booking": ActionRiskLevel.HIGH,
    "process_payment": ActionRiskLevel.CRITICAL,
    "payment": ActionRiskLevel.CRITICAL,
    "charge_card": ActionRiskLevel.CRITICAL,
    "refund_request": ActionRiskLevel.HIGH,
    "request_refund": ActionRiskLevel.HIGH,
}


def classify_action_risk(action_type: str) -> ActionRiskLevel:
    """
    Deterministically classify an action's risk level.
    Approval is required for any risk level other than LOW.
    """
    normalized = action_type.lower().strip()
    if normalized in HIGH_IMPACT_ACTIONS:
        return HIGH_IMPACT_ACTIONS[normalized]

    # Check substring matches for booking / payment / cancellation actions
    for hi_action, risk in HIGH_IMPACT_ACTIONS.items():
        if hi_action in normalized or normalized in hi_action:
            return risk

    if normalized in READ_ONLY_ACTIONS:
        return ActionRiskLevel.LOW

    # Default fallback for unspecified actions: requires approval if it looks modifying/financial
    if any(k in normalized for k in ("book", "pay", "charge", "purchase", "cancel", "refund", "modify", "reserve")):
        return ActionRiskLevel.HIGH

    return ActionRiskLevel.LOW


class ActionProposal(BaseModel):
    """Structured proposal representing an intended action before approval or execution."""

    proposal_id: str = Field(
        default_factory=lambda: f"prop-{uuid.uuid4().hex[:8]}",
        description="Unique proposal identifier",
    )
    trip_id: str = Field(..., description="ID of the trip associated with the proposal")
    user_id: str = Field(..., description="ID of the trip owner")
    action_type: str = Field(..., description="Action classification (e.g. book_flight, book_hotel)")
    description: str = Field(..., description="Human-readable description of proposed action")
    risk_level: ActionRiskLevel = Field(default=ActionRiskLevel.HIGH, description="Risk level")
    proposed_by: str = Field(default="system", description="Agent or component proposing the action")
    target_resource: Optional[str] = Field(default=None, description="Identifier or name of target resource")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action arguments and details")
    estimated_cost: float = Field(default=0.0, ge=0.0, description="Estimated financial commitment")
    currency: str = Field(default="USD", description="Currency ISO code")
    created_at: Any = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )
    expires_at: Optional[Any] = Field(default=None, description="Timestamp after which proposal expires")
    state_version: int = Field(default=1, description="Itinerary/state version upon proposal generation")
    idempotency_key: str = Field(
        default_factory=lambda: f"idemp-{uuid.uuid4().hex[:12]}",
        description="Unique idempotency key to prevent double execution",
    )
    requires_approval: bool = Field(default=True, description="Whether explicit approval is mandatory")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING, description="Current proposal status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context or references")


class ApprovalRequest(BaseModel):
    """Entity representing an active or resolved human approval request."""

    approval_id: str = Field(
        default_factory=lambda: f"appr-{uuid.uuid4().hex[:8]}",
        description="Unique approval request identifier",
    )
    proposal_id: str = Field(..., description="ID of associated ActionProposal")
    trip_id: str = Field(..., description="ID of associated trip")
    user_id: str = Field(..., description="Owner user ID")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING, description="Current status")
    requested_at: Any = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of request creation",
    )
    expires_at: Optional[Any] = Field(default=None, description="Timestamp of expiry")
    decided_at: Optional[Any] = Field(default=None, description="Timestamp of user decision")
    decision: Optional[Union[ApprovalDecision, str]] = Field(default=None, description="Decision outcome")
    rejection_reason: Optional[str] = Field(default=None, description="Structured reason if rejected")
    decided_by: Optional[str] = Field(default=None, description="User ID who executed the decision")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Safe decision metadata")


class ApprovalDecisionPayload(BaseModel):
    """Payload submitted by user when approving or rejecting an action."""

    approval_id: str = Field(..., description="Target approval identifier")
    decision: ApprovalDecision = Field(..., description="Decision choice")
    decided_by: str = Field(..., description="Authenticated user ID")
    decided_at: Any = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of decision",
    )
    rejection_reason: Optional[str] = Field(default=None, description="Optional explanation for rejection")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


class ActionExecutionResult(BaseModel):
    """Deliverable returned after executing an approved transactional action."""

    execution_id: str = Field(
        default_factory=lambda: f"exec-{uuid.uuid4().hex[:8]}",
        description="Unique execution identifier",
    )
    proposal_id: str = Field(..., description="Associated proposal ID")
    approval_id: Optional[str] = Field(default=None, description="Associated approval ID")
    trip_id: str = Field(..., description="Trip ID")
    user_id: Optional[str] = Field(default=None, description="User ID")
    action_type: Optional[str] = Field(default=None, description="Action executed")
    idempotency_key: Optional[str] = Field(default=None, description="Idempotency key")
    status: ApprovalStatus = Field(default=ApprovalStatus.EXECUTING, description="Outcome status")
    provider: str = Field(default="MockProvider", description="Underlying provider or adapter")
    confirmation_code: Optional[str] = Field(default=None, description="Confirmation or PNR code")
    result_payload: Dict[str, Any] = Field(default_factory=dict, description="Provider response payload")
    error_message: Optional[str] = Field(default=None, description="Error details if execution failed")
    executed_at: Any = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Execution timestamp",
    )
    completed_at: Optional[Any] = Field(default=None, description="Completion timestamp")
    execution_duration_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
    is_mock: bool = Field(default=True, description="Always True for mock/demo transactions")


class ApprovalAuditEvent(BaseModel):
    """Immutable audit record logging an approval lifecycle event."""

    event_id: str = Field(
        default_factory=lambda: f"aud-{uuid.uuid4().hex[:8]}",
        description="Unique audit record identifier",
    )
    trip_id: str = Field(..., description="Trip identifier")
    user_id: str = Field(..., description="User identifier")
    proposal_id: Optional[str] = Field(default=None, description="Proposal ID if applicable")
    approval_id: Optional[str] = Field(default=None, description="Approval ID if applicable")
    event_type: str = Field(..., description="Classification: PROPOSAL_CREATED, APPROVAL_REQUESTED, APPROVED, REJECTED, EXPIRED, EXECUTION_STARTED, EXECUTION_COMPLETED, EXECUTION_FAILED, EXECUTION_CANCELLED")
    timestamp: Any = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of event",
    )
    actor: str = Field(default="USER", description="Actor who initiated: USER, SYSTEM, TIMEOUT, ENGINE")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Sanitized event metadata (no secrets)")
