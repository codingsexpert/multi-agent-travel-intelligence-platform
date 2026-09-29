"""In-memory datastore for repository operations in DEMO_MODE."""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import uuid


class MockDataStore:
    """Thread-safe in-memory store simulating PostgreSQL persistence during DEMO_MODE."""

    def __init__(self):
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self.trips: Dict[str, Dict[str, Any]] = {}
        self.trip_preferences: Dict[str, Dict[str, Any]] = {}
        self.conversations: Dict[str, Dict[str, Any]] = {}
        self.messages: List[Dict[str, Any]] = []
        self.agent_runs: Dict[str, Dict[str, Any]] = {}
        self.replanning_events: Dict[str, Dict[str, Any]] = {}
        self.action_proposals: Dict[str, Dict[str, Any]] = {}
        self.approval_requests: Dict[str, Dict[str, Any]] = {}
        self.action_executions: Dict[str, Dict[str, Any]] = {}
        self.approval_audit_events: List[Dict[str, Any]] = []

    def clear(self) -> None:
        """Reset all in-memory collections."""
        self.profiles.clear()
        self.trips.clear()
        self.trip_preferences.clear()
        self.conversations.clear()
        self.messages.clear()
        self.agent_runs.clear()
        self.replanning_events.clear()
        self.action_proposals.clear()
        self.approval_requests.clear()
        self.action_executions.clear()
        self.approval_audit_events.clear()


# Global singleton in-memory storage for DEMO_MODE
mock_store = MockDataStore()
