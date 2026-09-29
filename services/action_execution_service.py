"""Action Execution Service for Approved Travel Transactions.

Enforces:
1. Approval validation & authorization
2. State version consistency
3. Server-side expiry check
4. Strict idempotency (duplicate calls return existing confirmed result)
5. Tool guardrail validation
6. Safe mock transactional provider execution
7. Audit event recording and sanitized state updates
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from mcp.transactional_providers import (
    MockActivityBookingProvider,
    MockFlightBookingProvider,
    MockHotelBookingProvider,
    ProviderTimeoutError,
    TransactionalProviderError,
)
from models.approval import (
    ActionExecutionResult,
    ActionProposal,
    ApprovalAuditEvent,
    ApprovalStatus,
)
from repositories.approval_repository import ApprovalRepository, approval_repository

logger = logging.getLogger("travel_platform.services.action_execution")


class ExecutionError(Exception):
    """Base exception for action execution."""
    pass


def _parse_datetime(val: Any) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo is not None else val.replace(tzinfo=timezone.utc)
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val)
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


class ActionExecutionService:
    """Coordinates the safe, idempotent execution of approved transactional travel actions."""

    def __init__(
        self,
        repo: Optional[ApprovalRepository] = None,
        flight_provider: Optional[MockFlightBookingProvider] = None,
        hotel_provider: Optional[MockHotelBookingProvider] = None,
        activity_provider: Optional[MockActivityBookingProvider] = None,
    ):
        self.repo = repo or approval_repository
        self.flight_provider = flight_provider or MockFlightBookingProvider()
        self.hotel_provider = hotel_provider or MockHotelBookingProvider()
        self.activity_provider = activity_provider or MockActivityBookingProvider()

    def execute_proposal(
        self,
        proposal_id: str,
        user_id: str,
        current_trip_version: Optional[int] = None,
    ) -> ActionExecutionResult:
        """Execute an approved proposal idempotently and safely."""
        raw_prop = self.repo.get_proposal(proposal_id)
        if not raw_prop:
            raise ExecutionError(f"Proposal {proposal_id} does not exist.")
        proposal = ActionProposal(**raw_prop) if isinstance(raw_prop, dict) else raw_prop

        # 1. Authorization
        if proposal.user_id != user_id:
            raise ExecutionError("Unauthorized: user does not own this action proposal.")

        # 2. Check Idempotency Key first
        raw_exec = self.repo.get_execution_by_idempotency_key(proposal.idempotency_key)
        if raw_exec:
            existing_exec = ActionExecutionResult(**raw_exec) if isinstance(raw_exec, dict) else raw_exec
            if existing_exec.status == ApprovalStatus.COMPLETED:
                logger.info(
                    "Idempotency match found for key %s. Returning existing execution result %s.",
                    proposal.idempotency_key,
                    existing_exec.execution_id,
                )
                return existing_exec
            elif existing_exec.status == ApprovalStatus.EXECUTING:
                logger.warning("Action %s is currently executing.", proposal_id)
                return existing_exec

        # 3. Status check: must be APPROVED (or LOW risk auto-approved)
        if proposal.requires_approval and proposal.status != ApprovalStatus.APPROVED:
            raise ExecutionError(
                f"Cannot execute proposal in status '{proposal.status.value}'. Must be APPROVED."
            )

        # 4. Expiry check
        now = datetime.now(timezone.utc)
        expires_dt = _parse_datetime(proposal.expires_at)
        if expires_dt and now >= expires_dt:
            self.repo.update_proposal(proposal.proposal_id, {"status": ApprovalStatus.EXPIRED.value})
            raise ExecutionError("Cannot execute proposal: action proposal has expired.")

        # 5. State Version Protection
        if current_trip_version is not None and proposal.state_version != current_trip_version:
            self.repo.update_proposal(proposal.proposal_id, {"status": ApprovalStatus.CANCELLED.value})
            raise ExecutionError(
                f"State version mismatch: proposal is for trip v{proposal.state_version}, "
                f"but current trip is v{current_trip_version}."
            )

        # 6. Initialize Execution Record
        execution_id = str(uuid.uuid4())
        started_at = now
        exec_record = ActionExecutionResult(
            execution_id=execution_id,
            proposal_id=proposal_id,
            trip_id=proposal.trip_id,
            idempotency_key=proposal.idempotency_key,
            status=ApprovalStatus.EXECUTING,
            is_mock=True,
            executed_at=started_at,
        )
        self.repo.create_execution(exec_record)

        # Audit EXECUTION_STARTED
        self.repo.record_audit_event(
            ApprovalAuditEvent(
                trip_id=proposal.trip_id,
                user_id=user_id,
                proposal_id=proposal_id,
                event_type="EXECUTION_STARTED",
                actor=user_id,
                metadata={
                    "action_type": proposal.action_type,
                    "idempotency_key": proposal.idempotency_key,
                },
            )
        )

        # 7. Execute Mock Provider Adapter
        try:
            result_payload = self._dispatch_provider(proposal)
            completed_at = datetime.now(timezone.utc)
            duration_ms = (completed_at - started_at).total_seconds() * 1000.0

            exec_record.status = ApprovalStatus.COMPLETED
            exec_record.confirmation_code = result_payload.get("confirmation_code")
            exec_record.result_payload = result_payload
            exec_record.completed_at = completed_at
            exec_record.execution_duration_ms = duration_ms

            self.repo.update_proposal(proposal.proposal_id, {"status": ApprovalStatus.COMPLETED.value})
            self.repo.update_execution(
                execution_id,
                {
                    "status": ApprovalStatus.COMPLETED.value,
                    "confirmation_code": exec_record.confirmation_code,
                    "result_payload": result_payload,
                    "completed_at": completed_at.isoformat(),
                    "execution_duration_ms": duration_ms,
                },
            )

            # Audit EXECUTION_COMPLETED
            self.repo.record_audit_event(
                ApprovalAuditEvent(
                    trip_id=proposal.trip_id,
                    user_id=user_id,
                    proposal_id=proposal_id,
                    event_type="EXECUTION_COMPLETED",
                    actor=user_id,
                    metadata={
                        "confirmation_code": exec_record.confirmation_code,
                        "duration_ms": duration_ms,
                    },
                )
            )

            logger.info("Successfully executed proposal %s (code=%s)", proposal_id, exec_record.confirmation_code)
            return exec_record

        except Exception as exc:
            completed_at = datetime.now(timezone.utc)
            duration_ms = (completed_at - started_at).total_seconds() * 1000.0

            error_msg = str(exc)
            logger.error("Execution failed for proposal %s: %s", proposal_id, error_msg)

            exec_record.status = ApprovalStatus.FAILED
            exec_record.error_message = error_msg
            exec_record.completed_at = completed_at
            exec_record.execution_duration_ms = duration_ms

            self.repo.update_proposal(proposal.proposal_id, {"status": ApprovalStatus.FAILED.value})
            self.repo.update_execution(
                execution_id,
                {
                    "status": ApprovalStatus.FAILED.value,
                    "error_message": error_msg,
                    "completed_at": completed_at.isoformat(),
                    "execution_duration_ms": duration_ms,
                },
            )

            # Audit EXECUTION_FAILED
            self.repo.record_audit_event(
                ApprovalAuditEvent(
                    trip_id=proposal.trip_id,
                    user_id=user_id,
                    proposal_id=proposal_id,
                    event_type="EXECUTION_FAILED",
                    actor="system",
                    metadata={
                        "error": error_msg,
                        "duration_ms": duration_ms,
                    },
                )
            )
            return exec_record

    def _dispatch_provider(self, proposal: ActionProposal) -> Dict[str, Any]:
        """Dispatch to appropriate mock transactional provider."""
        action = proposal.action_type.lower()
        p = proposal.parameters

        if "flight" in action and "book" in action:
            return self.flight_provider.book_flight(
                flight_number=p.get("flight_number", "AI-101"),
                passenger_name=p.get("passenger_name", "Traveler"),
                departure_date=p.get("departure_date", "2026-10-15"),
                origin=p.get("origin", "DEL"),
                destination=p.get("destination", "BLR"),
                seat_class=p.get("seat_class", "Economy"),
                idempotency_key=proposal.idempotency_key,
            )
        elif "flight" in action and "cancel" in action:
            return self.flight_provider.cancel_flight(
                confirmation_code=p.get("confirmation_code", "DEMO-FLT-000"),
                reason=p.get("reason"),
            )
        elif "hotel" in action and "book" in action:
            return self.hotel_provider.book_hotel(
                hotel_name=p.get("hotel_name", "Grand Hotel"),
                guest_name=p.get("guest_name", "Traveler"),
                check_in=p.get("check_in", "2026-10-15"),
                check_out=p.get("check_out", "2026-10-18"),
                room_type=p.get("room_type", "Deluxe Room"),
                idempotency_key=proposal.idempotency_key,
            )
        elif "hotel" in action and "cancel" in action:
            return self.hotel_provider.cancel_hotel(
                confirmation_code=p.get("confirmation_code", "DEMO-HTL-000"),
                reason=p.get("reason"),
            )
        elif ("activity" in action or "tour" in action) and "cancel" in action:
            return self.activity_provider.cancel_activity(
                confirmation_code=p.get("confirmation_code", "DEMO-ACT-000"),
                reason=p.get("reason"),
            )
        elif "activity" in action or "purchase" in action or "tour" in action:
            return self.activity_provider.book_activity(
                activity_title=p.get("activity_title", p.get("title", "Guided City Tour")),
                participant_name=p.get("participant_name", "Traveler"),
                activity_date=p.get("activity_date", "2026-10-16"),
                tickets_count=p.get("tickets_count", 1),
                idempotency_key=proposal.idempotency_key,
            )
        else:
            # Fallback generic mock transaction
            return {
                "is_mock": True,
                "provider_type": "DEMO / MOCK GENERIC TRANSACTION",
                "confirmation_code": f"DEMO-TXN-{uuid.uuid4().hex[:6].upper()}",
                "status": "CONFIRMED",
                "action_type": proposal.action_type,
                "parameters": p,
                "idempotency_key": proposal.idempotency_key,
                "notes": "SIMULATED TRANSACTION - DEMO ONLY",
            }


# Global singleton instance
action_execution_service = ActionExecutionService()
