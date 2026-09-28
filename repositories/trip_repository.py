"""Repository for trips and trip preferences management."""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid
from repositories.base import BaseRepository
from utils.logger import logger
from utils.exceptions import ServiceError


class TripRepository(BaseRepository):
    """Repository handling CRUD operations for trips and preferences."""

    def create_trip(
        self,
        user_id: str,
        trip_data: Dict[str, Any],
        preferences_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new trip and its associated preferences.

        Args:
            user_id: Owner user UUID.
            trip_data: Core trip fields (origin, destination, start_date, end_date, budget, etc.).
            preferences_data: Optional preferences dict (interests, travel_style, etc.).

        Returns:
            Created trip record combined with preferences and persistence metadata.
        """
        now = datetime.now(timezone.utc).isoformat()
        trip_id = trip_data.get("id") or str(uuid.uuid4())

        if self.is_demo_mode:
            logger.info(f"[DEMO_MODE] Storing trip {trip_id} in mock store for user {user_id}.")
            record = {
                "id": trip_id,
                "user_id": user_id,
                "origin": trip_data["origin"],
                "destination": trip_data["destination"],
                "start_date": str(trip_data["start_date"]),
                "end_date": str(trip_data["end_date"]),
                "travelers": int(trip_data.get("travelers", 1)),
                "budget": float(trip_data["budget"]),
                "currency": trip_data.get("currency", "USD"),
                "status": trip_data.get("status", "DRAFT"),
                "created_at": now,
                "updated_at": now,
                "is_demo": True,
            }
            self.mock_store.trips[trip_id] = record

            if preferences_data:
                pref_id = str(uuid.uuid4())
                pref_record = {
                    "id": pref_id,
                    "trip_id": trip_id,
                    "preferences": preferences_data.get("preferences", []),
                    "travel_style": preferences_data.get("travel_style", "Balanced"),
                    "accommodation_preference": preferences_data.get("accommodation_preference", "Hotel"),
                    "additional_requirements": preferences_data.get("additional_requirements", ""),
                    "created_at": now,
                    "updated_at": now,
                    "is_demo": True,
                }
                self.mock_store.trip_preferences[trip_id] = pref_record
                record["preferences"] = pref_record

            return record

        # Live Supabase execution
        client = self.supabase_svc.get_client()
        if not client:
            raise ServiceError("TripRepository", "Supabase client unavailable.")

        try:
            insert_payload = {
                "id": trip_id,
                "user_id": user_id,
                "origin": trip_data["origin"],
                "destination": trip_data["destination"],
                "start_date": str(trip_data["start_date"]),
                "end_date": str(trip_data["end_date"]),
                "travelers": int(trip_data.get("travelers", 1)),
                "budget": float(trip_data["budget"]),
                "currency": trip_data.get("currency", "USD"),
                "status": trip_data.get("status", "DRAFT"),
            }
            res = client.table("trips").insert(insert_payload).execute()
            if not res.data:
                raise ServiceError("TripRepository", "Failed to insert trip record.")

            created_trip = res.data[0]
            created_trip["is_demo"] = False

            if preferences_data:
                pref_payload = {
                    "trip_id": trip_id,
                    "preferences": preferences_data.get("preferences", []),
                    "travel_style": preferences_data.get("travel_style", "Balanced"),
                    "accommodation_preference": preferences_data.get("accommodation_preference", "Hotel"),
                    "additional_requirements": preferences_data.get("additional_requirements", ""),
                }
                pref_res = client.table("trip_preferences").insert(pref_payload).execute()
                if pref_res.data:
                    created_trip["preferences"] = pref_res.data[0]

            logger.info(f"Trip persisted successfully to Supabase: {trip_id}")
            return created_trip
        except Exception as e:
            logger.error(f"Error persisting trip to Supabase: {str(e)}")
            raise ServiceError("TripRepository", f"Database error creating trip: {str(e)}") from e

    def get_trip(self, trip_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a trip by ID ensuring user data isolation."""
        if self.is_demo_mode:
            trip = self.mock_store.trips.get(trip_id)
            if trip and trip.get("user_id") == user_id:
                trip_copy = dict(trip)
                if trip_id in self.mock_store.trip_preferences:
                    trip_copy["preferences"] = self.mock_store.trip_preferences[trip_id]
                return trip_copy
            return None

        client = self.supabase_svc.get_client()
        if not client:
            raise ServiceError("TripRepository", "Supabase client unavailable.")

        try:
            res = client.table("trips").select("*, trip_preferences(*)").eq("id", trip_id).eq("user_id", user_id).execute()
            if res.data:
                item = res.data[0]
                item["is_demo"] = False
                return item
            return None
        except Exception as e:
            logger.error(f"Error fetching trip {trip_id}: {str(e)}")
            raise ServiceError("TripRepository", f"Database error retrieving trip: {str(e)}") from e

    def list_user_trips(self, user_id: str) -> List[Dict[str, Any]]:
        """List all trips owned by the specified user."""
        if self.is_demo_mode:
            user_trips = [
                dict(t) for t in self.mock_store.trips.values()
                if t.get("user_id") == user_id
            ]
            user_trips.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            for t in user_trips:
                t_id = t["id"]
                if t_id in self.mock_store.trip_preferences:
                    t["preferences"] = self.mock_store.trip_preferences[t_id]
            return user_trips

        client = self.supabase_svc.get_client()
        if not client:
            raise ServiceError("TripRepository", "Supabase client unavailable.")

        try:
            res = client.table("trips").select("*, trip_preferences(*)").eq("user_id", user_id).order("created_at", desc=True).execute()
            items = res.data or []
            for item in items:
                item["is_demo"] = False
            return items
        except Exception as e:
            logger.error(f"Error listing trips for user {user_id}: {str(e)}")
            raise ServiceError("TripRepository", f"Database error listing trips: {str(e)}") from e

    def update_trip_status(self, trip_id: str, user_id: str, status: str) -> Optional[Dict[str, Any]]:
        """Update lifecycle status of a trip owned by user."""
        now = datetime.now(timezone.utc).isoformat()
        if self.is_demo_mode:
            trip = self.mock_store.trips.get(trip_id)
            if trip and trip.get("user_id") == user_id:
                trip["status"] = status
                trip["updated_at"] = now
                return dict(trip)
            return None

        client = self.supabase_svc.get_client()
        if not client:
            raise ServiceError("TripRepository", "Supabase client unavailable.")

        try:
            res = client.table("trips").update({"status": status, "updated_at": now}).eq("id", trip_id).eq("user_id", user_id).execute()
            if res.data:
                item = res.data[0]
                item["is_demo"] = False
                return item
            return None
        except Exception as e:
            logger.error(f"Error updating status for trip {trip_id}: {str(e)}")
            raise ServiceError("TripRepository", f"Database error updating trip: {str(e)}") from e


# Global singleton instance
trip_repository = TripRepository()
