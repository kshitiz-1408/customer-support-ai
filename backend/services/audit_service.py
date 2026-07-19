import logging
from datetime import datetime, timezone
from typing import Optional, Any
from bson import ObjectId
from database.database import get_audit_logs_collection
from utils.exceptions import DatabaseFailureException

logger = logging.getLogger("customer_support_backend")

class AuditService:
    @classmethod
    def log_action(
        cls,
        admin_id: Optional[str],
        target_user_id: Optional[str],
        action: str,
        previous_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        resource_type: str = "user",
        resource_id: Optional[str] = None,
        status: str = "success",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        additional_metadata: Optional[dict] = None
    ) -> dict:
        """Records a security-sensitive event to the audit logs collection."""
        try:
            coll = get_audit_logs_collection()
            now = datetime.now(timezone.utc)
            doc_id = str(ObjectId())

            # 1. Resolve actor parameters
            actor_email = None
            actor_role = None
            if admin_id:
                from database.database import get_users_collection
                actor = get_users_collection().find_one({"_id": admin_id})
                if actor:
                    actor_email = actor.get("email")
                    actor_role = actor.get("role")
                    if hasattr(actor_role, "value"):
                        actor_role = actor_role.value
            
            if not actor_role:
                actor_role = "anonymous" if not admin_id else "user"

            # 2. Resolve target parameters
            target_email = None
            if target_user_id:
                from database.database import get_users_collection
                target = get_users_collection().find_one({"_id": target_user_id})
                if target:
                    target_email = target.get("email")

            # 3. Resolve resource_id fallback
            res_id = resource_id or target_user_id or doc_id

            log_doc = {
                "_id": doc_id,
                "audit_id": doc_id,
                "timestamp": now,
                
                # Actor specifications
                "actor_user_id": admin_id,
                "actor_email": actor_email,
                "actor_role": actor_role,
                
                # Operation details
                "action": action,
                "resource_type": resource_type,
                "resource_id": res_id,
                
                # Target user details
                "target_user_id": target_user_id,
                "target_email": target_email,
                
                # Outcomes & client headers
                "status": status,
                "ip_address": ip_address,
                "user_agent": user_agent,
                
                # Differencing parameters
                "previous_value": previous_value,
                "new_value": new_value,
                "additional_metadata": additional_metadata or {},
                
                # Backward compatibility
                "admin_id": admin_id or ""
            }
            coll.insert_one(log_doc)
            logger.info(f"Audit log recorded: Actor {admin_id or 'anonymous'} performed {action} on {resource_type} {res_id}.")
            return log_doc
        except Exception as e:
            logger.error(f"Failed to record audit log: {str(e)}", exc_info=True)
            raise DatabaseFailureException(f"Error persisting audit log: {str(e)}")

    @classmethod
    def get_audit_logs_by_target(cls, target_user_id: str) -> list:
        """Retrieves all audit logs related to a specific target user."""
        try:
            coll = get_audit_logs_collection()
            if hasattr(coll, "find"):
                cursor = coll.find({"target_user_id": target_user_id})
                docs = list(cursor)
            else:
                docs = list(coll.find({"target_user_id": target_user_id}))
            
            # Sort first so it's consistent
            # Handle datetime vs ISO string comparison safely
            def get_time(x):
                t = x.get("timestamp")
                if isinstance(t, datetime):
                    return t
                if isinstance(t, str):
                    try:
                        return datetime.fromisoformat(t.replace("Z", "+00:00"))
                    except ValueError:
                        pass
                return datetime.min.replace(tzinfo=timezone.utc)

            docs.sort(key=get_time, reverse=True)
            
            # Convert timestamp to string if it is datetime for serialization
            for doc in docs:
                if isinstance(doc.get("timestamp"), datetime):
                    doc["timestamp"] = doc["timestamp"].isoformat()
            
            return docs
        except Exception as e:
            logger.error(f"Failed to read audit logs: {str(e)}")
            raise DatabaseFailureException(f"Error reading audit logs: {str(e)}")
