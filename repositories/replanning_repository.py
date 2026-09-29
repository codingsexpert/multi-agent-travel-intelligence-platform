"""Repository for dynamic replanning event telemetry, audit trails, and version tracking."""

import logging
from typing import Any, Dict, List, Optional
from models.replanning import ReplanningAuditRecord
from repositories.base import BaseRepository
from utils.exceptions import ServiceError

logger = logging.getLogger("travel_platform.replanning_repository")


class ReplanningRepository(BaseRepository):
    """Repository handling persistence of replanning audit records in PostgreSQL or in-memory mock store."""

    def record_replanning_event(self, record: ReplanningAuditRecord) -> Dict[str, Any]:
        """Persist a replanning transaction audit record."""
        data = record.model_dump()

        if self.is_demo_mode:
            logger.info(f"[DEMO_MODE] Recording replanning event {record.id} for trip {record.trip_id}")
            self.mock_store.replanning_events[record.id] = data
            return data

        client = self.supabase_svc.get_client()
        if not client:
            logger.warning("[ReplanningRepository] Supabase client unavailable, falling back to mock store.")
            self.mock_store.replanning_events[record.id] = data
            return data

        try:
            res = client.table("replanning_events").insert(data).execute()
            if res.data:
                return res.data[0]
            return data
        except Exception as e:
            logger.error(f"[ReplanningRepository] Failed to insert replanning event: {str(e)}")
            # Fallback to mock store to prevent breaking the flow
            self.mock_store.replanning_events[record.id] = data
            return data

    def get_events_for_trip(self, trip_id: str) -> List[Dict[str, Any]]:
        """Retrieve all replanning audit events associated with a trip, sorted chronologically."""
        if self.is_demo_mode:
            events = [
                ev for ev in self.mock_store.replanning_events.values()
                if ev.get("trip_id") == trip_id
            ]
            return sorted(events, key=lambda x: x.get("created_at", ""))

        client = self.supabase_svc.get_client()
        if not client:
            events = [
                ev for ev in self.mock_store.replanning_events.values()
                if ev.get("trip_id") == trip_id
            ]
            return sorted(events, key=lambda x: x.get("created_at", ""))

        try:
            res = (
                client.table("replanning_events")
                .select("*")
                .eq("trip_id", trip_id)
                .order("created_at", desc=False)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"[ReplanningRepository] Failed to fetch replanning events for trip {trip_id}: {str(e)}")
            return [
                ev for ev in self.mock_store.replanning_events.values()
                if ev.get("trip_id") == trip_id
            ]

    def get_latest_event_for_trip(self, trip_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the most recent replanning event for a trip."""
        events = self.get_events_for_trip(trip_id)
        return events[-1] if events else None


# Default singleton instance
replanning_repository = ReplanningRepository()
