"""Repository for individual conversation messages."""

from datetime import datetime, timezone
from typing import Dict, Any, List
import uuid
from repositories.base import BaseRepository
from utils.logger import logger
from utils.exceptions import ServiceError, ValidationError


class MessageRepository(BaseRepository):
    """Repository handling persistence and retrieval of chat messages."""

    def create_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> Dict[str, Any]:
        """Save a new message associated with a conversation."""
        valid_roles = {"user", "assistant", "system"}
        if role not in valid_roles:
            raise ValidationError(f"Invalid message role '{role}'. Must be one of: {valid_roles}")

        now = datetime.now(timezone.utc).isoformat()
        msg_id = str(uuid.uuid4())

        if self.is_demo_mode:
            logger.info(f"[DEMO_MODE] Appending message {msg_id} to conversation {conversation_id}")
            record = {
                "id": msg_id,
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "created_at": now,
                "is_demo": True,
            }
            self.mock_store.messages.append(record)
            return record

        client = self.supabase_svc.get_client()
        if not client:
            raise ServiceError("MessageRepository", "Supabase client unavailable.")

        try:
            payload = {
                "id": msg_id,
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
            }
            res = client.table("messages").insert(payload).execute()
            if not res.data:
                raise ServiceError("MessageRepository", "Failed to insert message record.")
            record = res.data[0]
            record["is_demo"] = False
            return record
        except Exception as e:
            logger.error(f"Error saving message to Supabase: {str(e)}")
            raise ServiceError("MessageRepository", f"Database error creating message: {str(e)}") from e

    def list_messages_for_conversation(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Retrieve all messages for a given conversation ordered chronologically."""
        if self.is_demo_mode:
            msgs = [
                dict(m) for m in self.mock_store.messages
                if m.get("conversation_id") == conversation_id
            ]
            msgs.sort(key=lambda x: x.get("created_at", ""))
            return msgs

        client = self.supabase_svc.get_client()
        if not client:
            raise ServiceError("MessageRepository", "Supabase client unavailable.")

        try:
            res = client.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at", desc=False).execute()
            items = res.data or []
            for item in items:
                item["is_demo"] = False
            return items
        except Exception as e:
            logger.error(f"Error listing messages for conversation {conversation_id}: {str(e)}")
            raise ServiceError("MessageRepository", f"Database error listing messages: {str(e)}") from e


# Global singleton instance
message_repository = MessageRepository()
