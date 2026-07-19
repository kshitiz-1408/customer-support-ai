import uuid
import logging
import time
from datetime import datetime, timezone
from typing import List, Optional
from database.database import get_conversations_collection, get_messages_collection
from utils.tracing import pipeline_tracker_var
from utils.resilience import retry_mongodb_read

logger = logging.getLogger("customer_support_backend")


class ConversationMemory:
    @classmethod
    def create_conversation(cls, session_id: Optional[str] = None, user_id: Optional[str] = None, title: Optional[str] = None) -> dict:
        """Create a new conversation thread document in MongoDB."""
        start_time = time.perf_counter()
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
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            
            tracker = pipeline_tracker_var.get()
            if tracker:
                tracker.db_conversation_creation_ms = duration_ms
                
            logger.info({
                "event": "conversation_created",
                "conversation_id": conv_id,
                "duration_ms": int(duration_ms)
            })
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error({
                "event": "persistence_failed",
                "operation": "create_conversation",
                "exception_type": type(e).__name__,
                "error_detail": str(e),
                "duration_ms": int(duration_ms)
            })
        return doc

    @classmethod
    def get_conversation(cls, conversation_id: str) -> Optional[dict]:
        """Fetch a single conversation by its ID."""
        start_time = time.perf_counter()
        try:
            res = retry_mongodb_read(
                get_conversations_collection().find_one,
                {"conversation_id": conversation_id},
                {"_id": 0}
            )
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            
            tracker = pipeline_tracker_var.get()
            if tracker:
                tracker.db_conversation_lookup_ms = duration_ms
                
            logger.debug({
                "event": "conversation_loaded",
                "conversation_id": conversation_id,
                "duration_ms": int(duration_ms)
            })
            return res
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error({
                "event": "persistence_failed",
                "operation": "get_conversation",
                "conversation_id": conversation_id,
                "exception_type": type(e).__name__,
                "error_detail": str(e),
                "duration_ms": int(duration_ms)
            })
            return None

    @classmethod
    def get_or_create_conversation(cls, conversation_id: Optional[str] = None, session_id: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """Resolve an existing conversation thread or create a new one."""
        if conversation_id:
            conv = cls.get_conversation(conversation_id)
            if conv:
                return conversation_id
                
        if session_id and session_id.strip():
            start_time = time.perf_counter()
            try:
                query_filter = {"session_id": session_id}
                if user_id:
                    query_filter["user_id"] = user_id
                latest = retry_mongodb_read(
                    get_conversations_collection().find_one,
                    query_filter,
                    sort=[("updated_at", -1)]
                )
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                
                tracker = pipeline_tracker_var.get()
                if tracker:
                    tracker.db_conversation_lookup_ms = duration_ms
                    
                logger.debug({
                    "event": "conversation_session_lookup",
                    "session_id": session_id,
                    "user_id": user_id,
                    "found": latest is not None,
                    "duration_ms": int(duration_ms)
                })
                if latest:
                    return latest["conversation_id"]
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                logger.error({
                    "event": "persistence_failed",
                    "operation": "get_or_create_conversation_lookup",
                    "session_id": session_id,
                    "exception_type": type(e).__name__,
                    "error_detail": str(e),
                    "duration_ms": int(duration_ms)
                })
                
        new_conv = cls.create_conversation(session_id=session_id, user_id=user_id)
        return new_conv["conversation_id"]

    @classmethod
    def list_conversations(cls, user_id: Optional[str] = None, session_id: Optional[str] = None) -> List[dict]:
        """List conversation threads filtered by user_id or session_id."""
        start_time = time.perf_counter()
        query = {}
        if user_id:
            query["user_id"] = user_id
        if session_id:
            query["session_id"] = session_id
        try:
            def run_query():
                return list(get_conversations_collection().find(query, {"_id": 0}).sort("updated_at", -1))
                
            res = retry_mongodb_read(run_query)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.info({
                "event": "conversations_listed",
                "query_keys": list(query.keys()),
                "result_count": len(res),
                "duration_ms": int(duration_ms)
            })
            return res
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error({
                "event": "persistence_failed",
                "operation": "list_conversations",
                "exception_type": type(e).__name__,
                "error_detail": str(e),
                "duration_ms": int(duration_ms)
            })
            return []

    @classmethod
    def get_conversation_history(cls, conversation_id: str, limit: int = 20) -> List[dict]:
        """
        Retrieve messages for a specific conversation thread.
        Returns messages in chronological order.
        """
        if not conversation_id:
            return []
        start_time = time.perf_counter()
        try:
            def run_history_query():
                return list(get_messages_collection().find({"conversation_id": conversation_id}, {"_id": 0}).sort("created_at", -1).limit(limit))
                
            docs = retry_mongodb_read(run_history_query)
            docs.reverse()
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            
            tracker = pipeline_tracker_var.get()
            if tracker:
                tracker.db_history_query_ms = duration_ms
                
            logger.info({
                "event": "history_loaded",
                "conversation_id": conversation_id,
                "message_count": len(docs),
                "duration_ms": int(duration_ms)
            })
            return docs
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error({
                "event": "persistence_failed",
                "operation": "get_conversation_history",
                "conversation_id": conversation_id,
                "exception_type": type(e).__name__,
                "error_detail": str(e),
                "duration_ms": int(duration_ms)
            })
            return []

    @classmethod
    def get_history(cls, session_id: str, limit: int = 10, user_id: Optional[str] = None) -> List[dict]:
        """
        Legacy/compatibility helper to fetch memory context logs structured as:
        [{"role": "user"|"assistant", "content": "..."}]
        """
        if not session_id or not session_id.strip():
            return []
        start_time = time.perf_counter()
        try:
            query_filter = {"session_id": session_id}
            if user_id:
                query_filter["user_id"] = user_id
            latest = retry_mongodb_read(
                get_conversations_collection().find_one,
                query_filter,
                sort=[("updated_at", -1)]
            )
            if not latest:
                return []
            history_msgs = cls.get_conversation_history(latest["conversation_id"], limit=limit)
            return [{"role": m["role"], "content": m["content"]} for m in history_msgs]
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error({
                "event": "persistence_failed",
                "operation": "get_history",
                "session_id": session_id,
                "exception_type": type(e).__name__,
                "error_detail": str(e),
                "duration_ms": int(duration_ms)
            })
            return []

    @classmethod
    def add_message(cls, conversation_id: str, role: str, content: str, intent: Optional[str] = None, agent: Optional[str] = None, sources: Optional[List[dict]] = None, user_id: Optional[str] = None, confidence_score: Optional[float] = None) -> dict:
        """Persist a message and update the parent conversation's timestamp."""
        start_time = time.perf_counter()
        msg_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        
        # Fallback to retrieve user_id from parent conversation thread if not explicitly passed
        if not user_id:
            conv = cls.get_conversation(conversation_id)
            if conv:
                user_id = conv.get("user_id")
        
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
            "user_id": user_id,
            "role": role,
            "content": content,
            "intent": intent,
            "agent": agent,
            "sources": cleaned_sources if cleaned_sources else None,
            "confidence_score": confidence_score,
            "created_at": now
        }
        
        try:
            # Insert message (Write: Do NOT retry writes)
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
            
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            
            tracker = pipeline_tracker_var.get()
            if tracker:
                if role == "user":
                    tracker.db_user_message_insert_ms = duration_ms
                else:
                    tracker.db_assistant_message_insert_ms = duration_ms
                    
            logger.info({
                "event": "message_persisted",
                "conversation_id": conversation_id,
                "role": role,
                "intent": intent,
                "agent": agent,
                "duration_ms": int(duration_ms)
            })
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error({
                "event": "persistence_failed",
                "operation": "add_message",
                "conversation_id": conversation_id,
                "role": role,
                "exception_type": type(e).__name__,
                "error_detail": str(e),
                "duration_ms": int(duration_ms)
            })
        return doc
