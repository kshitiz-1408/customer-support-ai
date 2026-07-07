import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional
from database.database import get_conversations_collection, get_messages_collection

logger = logging.getLogger("customer_support_backend")


class ConversationMemory:
    @classmethod
    def create_conversation(cls, session_id: Optional[str] = None, user_id: Optional[str] = None, title: Optional[str] = None) -> dict:
        """Create a new conversation thread document in MongoDB."""
        conv_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        doc = {
            "conversation_id": conv_id,
            "user_id": user_id,
            "session_id": session_id,
            "title": title,
            "created_at": now,
            "updated_at": now
        }
        try:
            get_conversations_collection().insert_one(doc)
        except Exception as e:
            logger.error(f"MongoDB create_conversation failed: {str(e)}", exc_info=True)
        return doc

    @classmethod
    def get_conversation(cls, conversation_id: str) -> Optional[dict]:
        """Fetch a single conversation by its ID."""
        try:
            return get_conversations_collection().find_one({"conversation_id": conversation_id}, {"_id": 0})
        except Exception as e:
            logger.error(f"MongoDB get_conversation failed: {str(e)}", exc_info=True)
            return None

    @classmethod
    def get_or_create_conversation(cls, conversation_id: Optional[str] = None, session_id: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """Resolve an existing conversation thread or create a new one."""
        if conversation_id:
            conv = cls.get_conversation(conversation_id)
            if conv:
                return conversation_id
                
        # If no conversation_id but session_id is provided, find the latest conversation for that session
        if session_id and session_id.strip():
            try:
                latest = get_conversations_collection().find_one(
                    {"session_id": session_id},
                    sort=[("updated_at", -1)]
                )
                if latest:
                    return latest["conversation_id"]
            except Exception as e:
                logger.error(f"MongoDB get_or_create_conversation search failed: {str(e)}", exc_info=True)
                
        # Fallback to creating a new conversation thread
        new_conv = cls.create_conversation(session_id=session_id, user_id=user_id)
        return new_conv["conversation_id"]

    @classmethod
    def list_conversations(cls, user_id: Optional[str] = None, session_id: Optional[str] = None) -> List[dict]:
        """List conversation threads filtered by user_id or session_id."""
        query = {}
        if user_id:
            query["user_id"] = user_id
        if session_id:
            query["session_id"] = session_id
        try:
            return list(get_conversations_collection().find(query, {"_id": 0}).sort("updated_at", -1))
        except Exception as e:
            logger.error(f"MongoDB list_conversations failed: {str(e)}", exc_info=True)
            return []

    @classmethod
    def get_conversation_history(cls, conversation_id: str, limit: int = 20) -> List[dict]:
        """
        Retrieve messages for a specific conversation thread.
        Returns messages in chronological order.
        """
        if not conversation_id:
            return []
        try:
            docs = list(get_messages_collection().find({"conversation_id": conversation_id}, {"_id": 0}).sort("created_at", -1).limit(limit))
            docs.reverse()
            return docs
        except Exception as e:
            logger.error(f"MongoDB get_conversation_history failed: {str(e)}", exc_info=True)
            return []

    @classmethod
    def get_history(cls, session_id: str, limit: int = 10) -> List[dict]:
        """
        Legacy/compatibility helper to fetch memory context logs structured as:
        [{"role": "user"|"assistant", "content": "..."}]
        """
        if not session_id or not session_id.strip():
            return []
        try:
            latest = get_conversations_collection().find_one(
                {"session_id": session_id},
                sort=[("updated_at", -1)]
            )
            if not latest:
                return []
            history_msgs = cls.get_conversation_history(latest["conversation_id"], limit=limit)
            return [{"role": m["role"], "content": m["content"]} for m in history_msgs]
        except Exception as e:
            logger.error(f"MongoDB get_history failed: {str(e)}", exc_info=True)
            return []

    @classmethod
    def add_message(cls, conversation_id: str, role: str, content: str, intent: Optional[str] = None, agent: Optional[str] = None, sources: Optional[List[dict]] = None) -> dict:
        """Persist a message and update the parent conversation's timestamp."""
        msg_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        
        # Clean sources: remove raw text chunk bodies, only store metadata (source, page, type)
        cleaned_sources = []
        if sources:
            for s in sources:
                cleaned_sources.append({
                    "source": s.get("source", "unknown"),
                    "page": s.get("page", 1),
                    "type": s.get("type", "unknown")
                })
                
        doc = {
            "message_id": msg_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "intent": intent,
            "agent": agent,
            "sources": cleaned_sources if cleaned_sources else None,
            "created_at": now
        }
        
        try:
            # Insert message
            get_messages_collection().insert_one(doc)
            
            # Update parent conversation's updated_at timestamp & add title if missing
            conv_coll = get_conversations_collection()
            conv = conv_coll.find_one({"conversation_id": conversation_id})
            update_fields = {"updated_at": now}
            if conv and not conv.get("title") and role == "user":
                update_fields["title"] = content[:50] + "..." if len(content) > 50 else content
                
            conv_coll.update_one(
                {"conversation_id": conversation_id},
                {"$set": update_fields}
            )
        except Exception as e:
            logger.error(f"MongoDB add_message failed: {str(e)}", exc_info=True)
        return doc
