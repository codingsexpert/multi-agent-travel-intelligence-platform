"""Repository for conversational sessions management."""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid
from repositories.base import BaseRepository
from utils.logger import logger
from utils.exceptions import ServiceError


class ConversationRepository(BaseRepository):
    """Repository handling CRUD operations for conversation threads."""

    def create_conversation(
        self,
        user_id: str,
        trip_id: Optional[str] = None,
        title: str = "Trip Planning Conversation",
    ) -> Dict[str, Any]:
        """Create a new conversation thread."""
        now = datetime.now(timezone.utc).isoformat()
        conv_id = str(uuid.uuid4())

        if self.is_demo_mode:
            logger.info(f"[DEMO_MODE] Creating conversation {conv_id} for user {user_id}")
            record = {
                "id": conv_id,
                "user_id": user_id,
                "trip_id": trip_id,
                "title": title,
                "created_at": now,
                "updated_at": now,
                "is_demo": True,
            }
            self.mock_store.conversations[conv_id] = record
            return record

        client = self.supabase_svc.get_client()
        if not client:
            raise ServiceError("ConversationRepository", "Supabase client unavailable.")

        try:
            payload = {
                "id": conv_id,
                "user_id": user_id,
                "trip_id": trip_id,
                "title": title,
            }
            res = client.table("conversations").insert(payload).execute()
            if not res.data:
                raise ServiceError("ConversationRepository", "Failed to insert conversation.")
            record = res.data[0]
            record["is_demo"] = False
            return record
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            raise ServiceError("ConversationRepository", f"Database error creating conversation: {str(e)}") from e

    def get_conversation(self, conversation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve conversation by ID enforcing user isolation."""
        if self.is_demo_mode:
            conv = self.mock_store.conversations.get(conversation_id)
            if conv and conv.get("user_id") == user_id:
                return dict(conv)
            return None

        client = self.supabase_svc.get_client()
        if not client:
            raise ServiceError("ConversationRepository", "Supabase client unavailable.")

        try:
            res = client.table("conversations").select("*").eq("id", conversation_id).eq("user_id", user_id).execute()
            if res.data:
                record = res.data[0]
                record["is_demo"] = False
                return record
            return None
        except Exception as e:
            logger.error(f"Error retrieving conversation {conversation_id}: {str(e)}")
            raise ServiceError("ConversationRepository", f"Database error retrieving conversation: {str(e)}") from e

    def list_conversations_for_user(
        self,
        user_id: str,
        trip_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all conversations owned by a user, optionally filtered by trip."""
        if self.is_demo_mode:
            convs = [
                dict(c) for c in self.mock_store.conversations.values()
                if c.get("user_id") == user_id and (trip_id is None or c.get("trip_id") == trip_id)
            ]
            convs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return convs

        client = self.supabase_svc.get_client()
        if not client:
            raise ServiceError("ConversationRepository", "Supabase client unavailable.")

        try:
            query = client.table("conversations").select("*").eq("user_id", user_id)
            if trip_id:
                query = query.eq("trip_id", trip_id)
            res = query.order("created_at", desc=True).execute()
            items = res.data or []
            for item in items:
                item["is_demo"] = False
            return items
        except Exception as e:
            logger.error(f"Error listing conversations for user {user_id}: {str(e)}")
            raise ServiceError("ConversationRepository", f"Database error listing conversations: {str(e)}") from e


# Global singleton instance
conversation_repository = ConversationRepository()
