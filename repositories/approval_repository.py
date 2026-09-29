"""Repository for Human-in-the-Loop action proposals, approval requests, executions, and audit records."""

import logging
from typing import Any, Dict, List, Optional
from models.approval import (
    ActionProposal,
    ApprovalRequest,
    ActionExecutionResult,
    ApprovalAuditEvent,
    ApprovalStatus,
)
from repositories.base import BaseRepository
from utils.exceptions import ServiceError

logger = logging.getLogger("travel_platform.approval_repository")


class ApprovalRepository(BaseRepository):
    """Repository handling persistence of HITL proposals, approvals, executions, and audit logs."""

    # --------------------------------------------------------------------------
    # Proposals
    # --------------------------------------------------------------------------
    def create_proposal(self, proposal: ActionProposal) -> Dict[str, Any]:
        """Save a new action proposal."""
        data = proposal.model_dump(mode="json")
        if self.is_demo_mode:
            self.mock_store.action_proposals[proposal.proposal_id] = data
            return data

        client = self.supabase_svc.get_client()
        if not client:
            self.mock_store.action_proposals[proposal.proposal_id] = data
            return data

        try:
            res = client.table("action_proposals").insert(data).execute()
            return res.data[0] if res.data else data
        except Exception as e:
            logger.error(f"[ApprovalRepository] Error inserting action proposal: {str(e)}")
            self.mock_store.action_proposals[proposal.proposal_id] = data
            return data

    def get_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve action proposal by ID."""
        if self.is_demo_mode:
            return self.mock_store.action_proposals.get(proposal_id)

        client = self.supabase_svc.get_client()
        if not client:
            return self.mock_store.action_proposals.get(proposal_id)

        try:
            res = client.table("action_proposals").select("*").eq("id", proposal_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"[ApprovalRepository] Error fetching proposal {proposal_id}: {str(e)}")
            return self.mock_store.action_proposals.get(proposal_id)

    def update_proposal(self, proposal_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an action proposal."""
        if self.is_demo_mode:
            existing = self.mock_store.action_proposals.get(proposal_id, {})
            existing.update(updates)
            self.mock_store.action_proposals[proposal_id] = existing
            return existing

        client = self.supabase_svc.get_client()
        if not client:
            existing = self.mock_store.action_proposals.get(proposal_id, {})
            existing.update(updates)
            self.mock_store.action_proposals[proposal_id] = existing
            return existing

        try:
            res = client.table("action_proposals").update(updates).eq("id", proposal_id).execute()
            if res.data:
                return res.data[0]
            existing = self.mock_store.action_proposals.get(proposal_id, {})
            existing.update(updates)
            return existing
        except Exception as e:
            logger.error(f"[ApprovalRepository] Error updating proposal {proposal_id}: {str(e)}")
            existing = self.mock_store.action_proposals.get(proposal_id, {})
            existing.update(updates)
            return existing

    def get_proposals_for_trip(self, trip_id: str) -> List[Dict[str, Any]]:
        """Retrieve all proposals for a given trip."""
        if self.is_demo_mode:
            return [
                p for p in self.mock_store.action_proposals.values()
                if p.get("trip_id") == trip_id
            ]

        client = self.supabase_svc.get_client()
        if not client:
            return [
                p for p in self.mock_store.action_proposals.values()
                if p.get("trip_id") == trip_id
            ]

        try:
            res = client.table("action_proposals").select("*").eq("trip_id", trip_id).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"[ApprovalRepository] Error fetching proposals for trip {trip_id}: {str(e)}")
            return [
                p for p in self.mock_store.action_proposals.values()
                if p.get("trip_id") == trip_id
            ]

    # --------------------------------------------------------------------------
    # Approvals
    # --------------------------------------------------------------------------
    def create_approval_request(self, request: ApprovalRequest) -> Dict[str, Any]:
        """Save a new approval request."""
        data = request.model_dump(mode="json")
        if self.is_demo_mode:
            self.mock_store.approval_requests[request.approval_id] = data
            return data

        client = self.supabase_svc.get_client()
        if not client:
            self.mock_store.approval_requests[request.approval_id] = data
            return data

        try:
            res = client.table("approval_requests").insert(data).execute()
            return res.data[0] if res.data else data
        except Exception as e:
            logger.error(f"[ApprovalRepository] Error inserting approval request: {str(e)}")
            self.mock_store.approval_requests[request.approval_id] = data
            return data

    def update_approval_request(self, approval_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update decision or status of an approval request."""
        if self.is_demo_mode:
            existing = self.mock_store.approval_requests.get(approval_id, {})
            existing.update(updates)
            self.mock_store.approval_requests[approval_id] = existing
            return existing

        client = self.supabase_svc.get_client()
        if not client:
            existing = self.mock_store.approval_requests.get(approval_id, {})
            existing.update(updates)
            self.mock_store.approval_requests[approval_id] = existing
            return existing

        try:
            res = client.table("approval_requests").update(updates).eq("id", approval_id).execute()
            if res.data:
                return res.data[0]
            existing = self.mock_store.approval_requests.get(approval_id, {})
            existing.update(updates)
            return existing
        except Exception as e:
            logger.error(f"[ApprovalRepository] Error updating approval request {approval_id}: {str(e)}")
            existing = self.mock_store.approval_requests.get(approval_id, {})
            existing.update(updates)
            return existing

    def get_approval_request(self, approval_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve approval request by ID."""
        if self.is_demo_mode:
            return self.mock_store.approval_requests.get(approval_id)

        client = self.supabase_svc.get_client()
        if not client:
            return self.mock_store.approval_requests.get(approval_id)

        try:
            res = client.table("approval_requests").select("*").eq("id", approval_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"[ApprovalRepository] Error fetching approval {approval_id}: {str(e)}")
            return self.mock_store.approval_requests.get(approval_id)

    def get_pending_approvals(
        self, trip_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve all active PENDING approval requests."""
        if self.is_demo_mode:
            items = list(self.mock_store.approval_requests.values())
            res = [a for a in items if a.get("status") == ApprovalStatus.PENDING.value]
            if trip_id:
                res = [a for a in res if a.get("trip_id") == trip_id]
            if user_id:
                res = [a for a in res if a.get("user_id") == user_id]
            return res

        client = self.supabase_svc.get_client()
        if not client:
            items = list(self.mock_store.approval_requests.values())
            res = [a for a in items if a.get("status") == ApprovalStatus.PENDING.value]
            if trip_id:
                res = [a for a in res if a.get("trip_id") == trip_id]
            if user_id:
                res = [a for a in res if a.get("user_id") == user_id]
            return res

        try:
            q = client.table("approval_requests").select("*").eq("status", ApprovalStatus.PENDING.value)
            if trip_id:
                q = q.eq("trip_id", trip_id)
            if user_id:
                q = q.eq("user_id", user_id)
            res = q.order("requested_at", desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"[ApprovalRepository] Error fetching pending approvals: {str(e)}")
            items = list(self.mock_store.approval_requests.values())
            res = [a for a in items if a.get("status") == ApprovalStatus.PENDING.value]
            if trip_id:
                res = [a for a in res if a.get("trip_id") == trip_id]
            if user_id:
                res = [a for a in res if a.get("user_id") == user_id]
            return res

    def get_approvals_for_trip(self, trip_id: str) -> List[Dict[str, Any]]:
        """Retrieve all approvals associated with a trip."""
        if self.is_demo_mode:
            return [
                a for a in self.mock_store.approval_requests.values()
                if a.get("trip_id") == trip_id
            ]

        client = self.supabase_svc.get_client()
        if not client:
            return [
                a for a in self.mock_store.approval_requests.values()
                if a.get("trip_id") == trip_id
            ]

        try:
            res = (
                client.table("approval_requests")
                .select("*")
                .eq("trip_id", trip_id)
                .order("requested_at", desc=True)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"[ApprovalRepository] Error fetching approvals for trip {trip_id}: {str(e)}")
            return [
                a for a in self.mock_store.approval_requests.values()
                if a.get("trip_id") == trip_id
            ]

    # --------------------------------------------------------------------------
    # Executions & Idempotency
    # --------------------------------------------------------------------------
    def create_execution(self, execution: ActionExecutionResult) -> Dict[str, Any]:
        """Record an action execution result."""
        data = execution.model_dump(mode="json")
        if self.is_demo_mode:
            self.mock_store.action_executions[execution.execution_id] = data
            return data

        client = self.supabase_svc.get_client()
        if not client:
            self.mock_store.action_executions[execution.execution_id] = data
            return data

        try:
            res = client.table("action_executions").insert(data).execute()
            return res.data[0] if res.data else data
        except Exception as e:
            logger.error(f"[ApprovalRepository] Error inserting execution record: {str(e)}")
            self.mock_store.action_executions[execution.execution_id] = data
            return data

    def get_execution_for_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Find an existing execution by proposal ID to guarantee idempotency."""
        for ex in self.mock_store.action_executions.values():
            if ex.get("proposal_id") == proposal_id:
                return ex

        client = self.supabase_svc.get_client()
        if not client or self.is_demo_mode:
            return None

        try:
            res = client.table("action_executions").select("*").eq("proposal_id", proposal_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"[ApprovalRepository] Error checking execution for proposal {proposal_id}: {str(e)}")
            return None

    def get_execution_by_idempotency_key(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve execution by idempotency key to prevent duplicate transactional executions."""
        for ex in self.mock_store.action_executions.values():
            if ex.get("idempotency_key") == idempotency_key:
                return ex

        client = self.supabase_svc.get_client()
        if not client or self.is_demo_mode:
            return None

        try:
            res = client.table("action_executions").select("*").eq("idempotency_key", idempotency_key).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"[ApprovalRepository] Error checking execution for key {idempotency_key}: {str(e)}")
            return None

    def update_execution(self, execution_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an execution record."""
        if self.is_demo_mode:
            existing = self.mock_store.action_executions.get(execution_id, {})
            existing.update(updates)
            self.mock_store.action_executions[execution_id] = existing
            return existing

        client = self.supabase_svc.get_client()
        if not client:
            existing = self.mock_store.action_executions.get(execution_id, {})
            existing.update(updates)
            self.mock_store.action_executions[execution_id] = existing
            return existing

        try:
            res = client.table("action_executions").update(updates).eq("id", execution_id).execute()
            if res.data:
                return res.data[0]
            existing = self.mock_store.action_executions.get(execution_id, {})
            existing.update(updates)
            return existing
        except Exception as e:
            logger.error(f"[ApprovalRepository] Error updating execution {execution_id}: {str(e)}")
            existing = self.mock_store.action_executions.get(execution_id, {})
            existing.update(updates)
            return existing

    def get_executions_for_trip(self, trip_id: str) -> List[Dict[str, Any]]:
        """Retrieve all action executions for a trip."""
        if self.is_demo_mode:
            return [
                ex for ex in self.mock_store.action_executions.values()
                if ex.get("trip_id") == trip_id
            ]

        client = self.supabase_svc.get_client()
        if not client:
            return [
                ex for ex in self.mock_store.action_executions.values()
                if ex.get("trip_id") == trip_id
            ]

        try:
            res = client.table("action_executions").select("*").eq("trip_id", trip_id).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"[ApprovalRepository] Error fetching executions for trip {trip_id}: {str(e)}")
            return [
                ex for ex in self.mock_store.action_executions.values()
                if ex.get("trip_id") == trip_id
            ]

    # --------------------------------------------------------------------------
    # Audit Trail
    # --------------------------------------------------------------------------
    def record_audit_event(self, event: ApprovalAuditEvent) -> Dict[str, Any]:
        """Record an immutable approval audit trail event."""
        data = event.model_dump(mode="json")
        if self.is_demo_mode:
            self.mock_store.approval_audit_events.append(data)
            return data

        client = self.supabase_svc.get_client()
        if not client:
            self.mock_store.approval_audit_events.append(data)
            return data

        try:
            res = client.table("approval_audit_events").insert(data).execute()
            return res.data[0] if res.data else data
        except Exception as e:
            logger.error(f"[ApprovalRepository] Error inserting audit event: {str(e)}")
            self.mock_store.approval_audit_events.append(data)
            return data

    def get_audit_events_for_trip(self, trip_id: str) -> List[Dict[str, Any]]:
        """Retrieve audit events for a trip."""
        if self.is_demo_mode:
            return [
                ev for ev in self.mock_store.approval_audit_events
                if ev.get("trip_id") == trip_id
            ]

        client = self.supabase_svc.get_client()
        if not client:
            return [
                ev for ev in self.mock_store.approval_audit_events
                if ev.get("trip_id") == trip_id
            ]

        try:
            res = (
                client.table("approval_audit_events")
                .select("*")
                .eq("trip_id", trip_id)
                .order("timestamp", desc=False)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"[ApprovalRepository] Error fetching audit events: {str(e)}")
            return [
                ev for ev in self.mock_store.approval_audit_events
                if ev.get("trip_id") == trip_id
            ]


# Singleton repository instance
approval_repository = ApprovalRepository()
