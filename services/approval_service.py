"""Approval Service for Human-in-the-Loop Travel Actions.

Enforces deterministic action-risk classification, human ownership validation,
server-side expiry, audit logging, and trip state version matching.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from models.approval import (
    ActionProposal,
    ActionRiskLevel,
    ApprovalAuditEvent,
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
    classify_action_risk,
)
from repositories.approval_repository import ApprovalRepository, approval_repository

logger = logging.getLogger("travel_platform.services.approval")


class ApprovalError(Exception):
    """Base exception for approval workflows."""
    pass


class UnauthorizedApprovalError(ApprovalError):
    """Raised when an unauthorized user attempts to inspect or decide an approval."""
    pass


class InvalidApprovalStateError(ApprovalError):
    """Raised when deciding on an already decided, expired, or cancelled approval."""
    pass


class StaleProposalError(ApprovalError):
    """Raised when proposal state version doesn't match current trip itinerary version."""
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


class ApprovalService:
    """Manages the lifecycle of action proposals, approvals, and audit trails."""

    def __init__(self, repo: Optional[ApprovalRepository] = None):
        self.repo = repo or approval_repository

    def create_proposal(
        self,
        trip_id: str,
        user_id: str,
        action_type: str,
        description: str,
        parameters: Dict[str, Any],
        state_version: int,
        estimated_cost: float = 0.0,
        currency: str = "USD",
        proposed_by: str = "agent",
        target_resource: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        expires_in_minutes: int = 1440,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ActionProposal:
        """Create a new action proposal with deterministic risk classification."""
        risk_level = classify_action_risk(action_type)
        requires_approval = (risk_level != ActionRiskLevel.LOW)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=expires_in_minutes)

        proposal_id = str(uuid.uuid4())
        key = idempotency_key or f"prop-{proposal_id[:8]}"

        proposal = ActionProposal(
            proposal_id=proposal_id,
            trip_id=trip_id,
            user_id=user_id,
            action_type=action_type,
            description=description,
            risk_level=risk_level,
            proposed_by=proposed_by,
            target_resource=target_resource,
            parameters=parameters,
            estimated_cost=estimated_cost,
            currency=currency,
            created_at=now,
            expires_at=expires_at,
            state_version=state_version,
            idempotency_key=key,
            requires_approval=requires_approval,
            status=ApprovalStatus.PENDING if requires_approval else ApprovalStatus.APPROVED,
            metadata=metadata or {},
        )

        self.repo.create_proposal(proposal)

        # Audit proposal creation
        self.repo.record_audit_event(
            ApprovalAuditEvent(
                trip_id=trip_id,
                user_id=user_id,
                proposal_id=proposal_id,
                event_type="PROPOSAL_CREATED",
                actor=proposed_by,
                metadata={
                    "action_type": action_type,
                    "risk_level": risk_level.value,
                    "requires_approval": requires_approval,
                    "estimated_cost": estimated_cost,
                    "currency": currency,
                    "state_version": state_version,
                },
            )
        )

        # If approval is required, create an ApprovalRequest
        if requires_approval:
            approval_id = str(uuid.uuid4())
            approval_req = ApprovalRequest(
                approval_id=approval_id,
                proposal_id=proposal_id,
                trip_id=trip_id,
                user_id=user_id,
                status=ApprovalStatus.PENDING,
                requested_at=now,
                expires_at=expires_at,
                metadata=metadata or {},
            )
            self.repo.create_approval_request(approval_req)

            self.repo.record_audit_event(
                ApprovalAuditEvent(
                    trip_id=trip_id,
                    user_id=user_id,
                    proposal_id=proposal_id,
                    approval_id=approval_id,
                    event_type="APPROVAL_REQUESTED",
                    actor="system",
                    metadata={
                        "risk_level": risk_level.value,
                        "expires_at": expires_at.isoformat(),
                    },
                )
            )

        logger.info(
            "Created proposal %s for action %s (risk=%s, requires_approval=%s)",
            proposal_id,
            action_type,
            risk_level.value,
            requires_approval,
        )
        return proposal

    def get_pending_approvals(
        self,
        user_id: str,
        trip_id: Optional[str] = None,
    ) -> List[ApprovalRequest]:
        """Retrieve active pending approvals for a user, automatically checking server-side expiry."""
        raw_requests = self.repo.get_pending_approvals(user_id=user_id, trip_id=trip_id)
        now = datetime.now(timezone.utc)
        active_requests: List[ApprovalRequest] = []

        for item in raw_requests:
            req = ApprovalRequest(**item) if isinstance(item, dict) else item

            # Enforce server-side expiry
            expires_dt = _parse_datetime(req.expires_at)
            if expires_dt and now >= expires_dt:
                req.status = ApprovalStatus.EXPIRED
                self.repo.update_approval_request(req.approval_id, {"status": ApprovalStatus.EXPIRED.value})

                # Invalidate associated proposal
                raw_prop = self.repo.get_proposal(req.proposal_id)
                if raw_prop:
                    prop = ActionProposal(**raw_prop) if isinstance(raw_prop, dict) else raw_prop
                    if prop.status == ApprovalStatus.PENDING:
                        self.repo.update_proposal(prop.proposal_id, {"status": ApprovalStatus.EXPIRED.value})

                self.repo.record_audit_event(
                    ApprovalAuditEvent(
                        trip_id=req.trip_id,
                        user_id=req.user_id,
                        proposal_id=req.proposal_id,
                        approval_id=req.approval_id,
                        event_type="EXPIRED",
                        actor="system",
                        metadata={"expired_at": now.isoformat()},
                    )
                )
                continue

            active_requests.append(req)

        return active_requests

    def get_proposal(self, proposal_id: str, user_id: Optional[str] = None) -> ActionProposal:
        """Fetch proposal ensuring ownership if user_id is provided."""
        raw_prop = self.repo.get_proposal(proposal_id)
        if not raw_prop:
            raise ApprovalError(f"Proposal {proposal_id} not found.")
        prop = ActionProposal(**raw_prop) if isinstance(raw_prop, dict) else raw_prop
        if user_id and prop.user_id != user_id:
            raise UnauthorizedApprovalError("User does not have access to this proposal.")
        return prop

    def get_approval_request(self, approval_id: str, user_id: Optional[str] = None) -> ApprovalRequest:
        """Fetch approval request ensuring ownership if user_id is provided."""
        raw_req = self.repo.get_approval_request(approval_id)
        if not raw_req:
            raise ApprovalError(f"Approval request {approval_id} not found.")
        req = ApprovalRequest(**raw_req) if isinstance(raw_req, dict) else raw_req
        if user_id and req.user_id != user_id:
            raise UnauthorizedApprovalError("User does not have access to this approval request.")
        return req

    def decide_approval(
        self,
        approval_id: str,
        user_id: str,
        decision: ApprovalDecision,
        rejection_reason: Optional[str] = None,
        current_trip_version: Optional[int] = None,
    ) -> ApprovalRequest:
        """Process a human approval decision (APPROVE or REJECT)."""
        req = self.get_approval_request(approval_id, user_id)

        if req.status != ApprovalStatus.PENDING:
            raise InvalidApprovalStateError(
                f"Cannot decide on approval in status '{req.status.value}'. Must be PENDING."
            )

        now = datetime.now(timezone.utc)
        expires_dt = _parse_datetime(req.expires_at)
        if expires_dt and now >= expires_dt:
            req.status = ApprovalStatus.EXPIRED
            self.repo.update_approval_request(req.approval_id, {"status": ApprovalStatus.EXPIRED.value})
            raise InvalidApprovalStateError("Approval request has expired.")

        proposal = self.get_proposal(req.proposal_id, user_id)

        # Version check if trip state version is provided
        if current_trip_version is not None and proposal.state_version != current_trip_version:
            req.status = ApprovalStatus.CANCELLED
            self.repo.update_approval_request(req.approval_id, {"status": ApprovalStatus.CANCELLED.value})
            self.repo.update_proposal(proposal.proposal_id, {"status": ApprovalStatus.CANCELLED.value})
            raise StaleProposalError(
                f"Proposal version {proposal.state_version} does not match current trip version {current_trip_version}."
            )

        req.decided_at = now
        req.decided_by = user_id
        req.decision = decision

        if decision == ApprovalDecision.APPROVED:
            req.status = ApprovalStatus.APPROVED
            prop_status = ApprovalStatus.APPROVED
            event_type = "APPROVED"
        elif decision == ApprovalDecision.REJECTED:
            req.status = ApprovalStatus.REJECTED
            prop_status = ApprovalStatus.REJECTED
            req.rejection_reason = rejection_reason or "User rejected action proposal."
            event_type = "REJECTED"
        else:
            raise InvalidApprovalStateError(f"Unsupported decision: {decision}")

        self.repo.update_approval_request(
            req.approval_id,
            {
                "status": req.status.value,
                "decided_at": now.isoformat(),
                "decided_by": user_id,
                "decision": decision.value,
                "rejection_reason": req.rejection_reason,
            },
        )
        self.repo.update_proposal(proposal.proposal_id, {"status": prop_status.value})

        # Audit decision
        self.repo.record_audit_event(
            ApprovalAuditEvent(
                trip_id=req.trip_id,
                user_id=user_id,
                proposal_id=req.proposal_id,
                approval_id=req.approval_id,
                event_type=event_type,
                actor=user_id,
                metadata={
                    "decision": decision.value,
                    "rejection_reason": req.rejection_reason,
                    "decided_at": now.isoformat(),
                },
            )
        )

        logger.info(
            "User %s %s approval %s for proposal %s",
            user_id,
            decision.value,
            approval_id,
            req.proposal_id,
        )
        return req

    def invalidate_proposals_for_trip(
        self,
        trip_id: str,
        new_state_version: int,
        reason: str = "Dynamic replanning updated itinerary version",
    ) -> int:
        """Invalidate pending proposals whose state_version is older than the new trip version."""
        raw_proposals = self.repo.get_proposals_for_trip(trip_id)
        invalidated_count = 0

        for raw_prop in raw_proposals:
            prop = ActionProposal(**raw_prop) if isinstance(raw_prop, dict) else raw_prop
            if prop.status == ApprovalStatus.PENDING and prop.state_version < new_state_version:
                self.repo.update_proposal(prop.proposal_id, {"status": ApprovalStatus.CANCELLED.value})
                invalidated_count += 1

                # If there's an associated pending approval request, cancel it too
                raw_reqs = self.repo.get_pending_approvals(trip_id=trip_id)
                for raw_req in raw_reqs:
                    req = ApprovalRequest(**raw_req) if isinstance(raw_req, dict) else raw_req
                    if req.proposal_id == prop.proposal_id and req.status == ApprovalStatus.PENDING:
                        meta = req.metadata or {}
                        meta["cancellation_reason"] = reason
                        self.repo.update_approval_request(
                            req.approval_id,
                            {
                                "status": ApprovalStatus.CANCELLED.value,
                                "metadata": meta,
                            },
                        )

                self.repo.record_audit_event(
                    ApprovalAuditEvent(
                        trip_id=trip_id,
                        user_id=prop.user_id,
                        proposal_id=prop.proposal_id,
                        event_type="EXECUTION_CANCELLED",
                        actor="system",
                        metadata={
                            "reason": reason,
                            "old_version": prop.state_version,
                            "new_version": new_state_version,
                        },
                    )
                )

        logger.info(
            f"Invalidated {invalidated_count} stale proposals for trip {trip_id} following update to version {new_state_version}"
        )
        return invalidated_count


# Global singleton instance
approval_service = ApprovalService()
