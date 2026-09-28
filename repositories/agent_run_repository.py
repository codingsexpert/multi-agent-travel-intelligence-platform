"""Repository for agent execution telemetry and audit runs."""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid
from repositories.base import BaseRepository
from utils.logger import logger
from utils.exceptions import ServiceError


class AgentRunRepository(BaseRepository):
    """Repository handling logging and tracking of agent runs."""

    def create_agent_run(
        self,
        trip_id: str,
        agent_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record the start of an agent execution run."""
        now = datetime.now(timezone.utc).isoformat()
        run_id = str(uuid.uuid4())

        if self.is_demo_mode:
            logger.info(f"[DEMO_MODE] Recording agent run {run_id} for {agent_name}")
            record = {
                "id": run_id,
                "trip_id": trip_id,
                "agent_name": agent_name,
                "status": "RUNNING",
                "started_at": now,
                "completed_at": None,
                "error_message": None,
                "metadata": metadata or {},
                "created_at": now,
                "is_demo": True,
            }
            self.mock_store.agent_runs[run_id] = record
            return record

        client = self.supabase_svc.get_client()
        if not client:
            raise ServiceError("AgentRunRepository", "Supabase client unavailable.")

        try:
            payload = {
                "id": run_id,
                "trip_id": trip_id,
                "agent_name": agent_name,
                "status": "RUNNING",
                "started_at": now,
                "metadata": metadata or {},
            }
            res = client.table("agent_runs").insert(payload).execute()
            if not res.data:
                raise ServiceError("AgentRunRepository", "Failed to insert agent_run record.")
            record = res.data[0]
            record["is_demo"] = False
            return record
        except Exception as e:
            logger.error(f"Error creating agent run record: {str(e)}")
            raise ServiceError("AgentRunRepository", f"Database error creating agent run: {str(e)}") from e

    def update_agent_run(
        self,
        run_id: str,
        status: str,
        completed_at: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update status, error, and completion of an agent run."""
        now = completed_at or datetime.now(timezone.utc).isoformat()

        if self.is_demo_mode:
            run = self.mock_store.agent_runs.get(run_id)
            if run:
                run["status"] = status
                run["completed_at"] = now
                if error_message:
                    run["error_message"] = error_message
                if metadata:
                    run["metadata"].update(metadata)
                return dict(run)
            return None

        client = self.supabase_svc.get_client()
        if not client:
            raise ServiceError("AgentRunRepository", "Supabase client unavailable.")

        try:
            update_data = {
                "status": status,
                "completed_at": now,
            }
            if error_message is not None:
                update_data["error_message"] = error_message
            if metadata is not None:
                update_data["metadata"] = metadata

            res = client.table("agent_runs").update(update_data).eq("id", run_id).execute()
            if res.data:
                record = res.data[0]
                record["is_demo"] = False
                return record
            return None
        except Exception as e:
            logger.error(f"Error updating agent run {run_id}: {str(e)}")
            raise ServiceError("AgentRunRepository", f"Database error updating agent run: {str(e)}") from e

    def list_runs_for_trip(self, trip_id: str) -> List[Dict[str, Any]]:
        """List all agent runs for a specific trip ordered by started_at."""
        if self.is_demo_mode:
            runs = [
                dict(r) for r in self.mock_store.agent_runs.values()
                if r.get("trip_id") == trip_id
            ]
            runs.sort(key=lambda x: x.get("started_at", ""))
            return runs

        client = self.supabase_svc.get_client()
        if not client:
            raise ServiceError("AgentRunRepository", "Supabase client unavailable.")

        try:
            res = client.table("agent_runs").select("*").eq("trip_id", trip_id).order("started_at", desc=False).execute()
            items = res.data or []
            for item in items:
                item["is_demo"] = False
            return items
        except Exception as e:
            logger.error(f"Error listing agent runs for trip {trip_id}: {str(e)}")
            raise ServiceError("AgentRunRepository", f"Database error listing agent runs: {str(e)}") from e


# Global singleton instance
agent_run_repository = AgentRunRepository()
