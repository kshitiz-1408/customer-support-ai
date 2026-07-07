from datetime import datetime, timezone
from typing import List, Optional
from models.ticket import Ticket, TicketCreate, TicketStatus, TicketUpdate
from database.database import get_tickets_collection, get_counters_collection


class TicketService:
    @classmethod
    def _ensure_prepopulated(cls):
        """Ensure initial seed tickets exist in MongoDB if the collection is empty."""
        try:
            coll = get_tickets_collection()
            if coll.count_documents({}) == 0:
                counters = get_counters_collection()
                # Initialize sequence at 3 to support the 3 default seed tickets
                counters.update_one({"_id": "ticket_id"}, {"$set": {"seq": 3}}, upsert=True)
                
                now = datetime.now(timezone.utc)
                tickets = [
                    {
                        "id": 1,
                        "ticket_id": "TKT-0001",
                        "customer_name": "Alice Johnson",
                        "customer_email": "alice@example.com",
                        "subject": "Unable to access billing history",
                        "description": "Every time I click on 'Billing History', the app crashes with a 500 error page. Please help.",
                        "priority": "high",
                        "category": "billing",
                        "status": "open",
                        "created_at": now,
                        "updated_at": now,
                        "assigned_agent": None,
                        "resolution_notes": None,
                        "conversation_id": None,
                        "user_id": None
                    },
                    {
                        "id": 2,
                        "ticket_id": "TKT-0002",
                        "customer_name": "Bob Smith",
                        "customer_email": "bob@example.com",
                        "subject": "Request for custom API integration documentation",
                        "description": "We are looking to integrate the customer-support dashboard with our internal logging system. Is there a webhooks specification available?",
                        "priority": "medium",
                        "category": "technical",
                        "status": "open",
                        "created_at": now,
                        "updated_at": now,
                        "assigned_agent": None,
                        "resolution_notes": None,
                        "conversation_id": None,
                        "user_id": None
                    },
                    {
                        "id": 3,
                        "ticket_id": "TKT-0003",
                        "customer_name": "Charlie Brown",
                        "customer_email": "charlie@example.com",
                        "subject": "Password reset link not arriving",
                        "description": "I have requested a password reset link three times but it has not arrived in my inbox or spam folder.",
                        "priority": "urgent",
                        "category": "account",
                        "status": "open",
                        "created_at": now,
                        "updated_at": now,
                        "assigned_agent": None,
                        "resolution_notes": None,
                        "conversation_id": None,
                        "user_id": None
                    }
                ]
                coll.insert_many(tickets)
            else:
                # Migrate any legacy tickets missing ticket_id
                for doc in list(coll.find({"ticket_id": {"$exists": False}})):
                    tid = doc.get("id", 1)
                    coll.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {
                            "ticket_id": f"TKT-{tid:04d}",
                            "conversation_id": doc.get("conversation_id"),
                            "user_id": doc.get("user_id")
                        }}
                    )
        except Exception:
            # Gracefully ignore errors to avoid blocking backend start if DB connection is lazy
            pass

    @classmethod
    def create(cls, ticket_in: TicketCreate) -> Ticket:
        """Create a new ticket and persist it to MongoDB with an auto-incrementing ID."""
        cls._ensure_prepopulated()
        
        # Atomically increment ticket sequence
        res = get_counters_collection().find_one_and_update(
            {"_id": "ticket_id"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True
        )
        new_id = res["seq"]
        stable_ticket_id = f"TKT-{new_id:04d}"
        now = datetime.now(timezone.utc)
        
        ticket_doc = {
            "id": new_id,
            "ticket_id": stable_ticket_id,
            "customer_name": ticket_in.customer_name,
            "customer_email": ticket_in.customer_email,
            "subject": ticket_in.subject,
            "description": ticket_in.description,
            "priority": ticket_in.priority.value if hasattr(ticket_in.priority, "value") else ticket_in.priority,
            "category": ticket_in.category.value if hasattr(ticket_in.category, "value") else ticket_in.category,
            "status": TicketStatus.OPEN.value,
            "created_at": now,
            "updated_at": now,
            "assigned_agent": None,
            "resolution_notes": None,
            "conversation_id": ticket_in.conversation_id,
            "user_id": ticket_in.user_id
        }
        get_tickets_collection().insert_one(ticket_doc)
        return Ticket(**ticket_doc)

    @classmethod
    def get(cls, ticket_id: int) -> Optional[Ticket]:
        """Fetch a single ticket by its integer ID from MongoDB."""
        cls._ensure_prepopulated()
        doc = get_tickets_collection().find_one({"id": ticket_id})
        if doc:
            return Ticket(**doc)
        return None

    @classmethod
    def get_by_ticket_id(cls, ticket_id_str: str) -> Optional[Ticket]:
        """Fetch a single ticket by its string ticket_id from MongoDB."""
        cls._ensure_prepopulated()
        doc = get_tickets_collection().find_one({"ticket_id": ticket_id_str})
        if doc:
            return Ticket(**doc)
        return None

    @classmethod
    def get_all(cls, status: Optional[TicketStatus] = None) -> List[Ticket]:
        """Retrieve all tickets from MongoDB, optionally filtering by status."""
        cls._ensure_prepopulated()
        query = {}
        if status:
            query["status"] = status.value if hasattr(status, "value") else status
        docs = get_tickets_collection().find(query)
        return [Ticket(**doc) for doc in docs]

    @classmethod
    def update(cls, ticket_id: int, ticket_update: TicketUpdate) -> Optional[Ticket]:
        """Update fields on a ticket in MongoDB and return the updated ticket model."""
        cls._ensure_prepopulated()
        update_data = ticket_update.model_dump(exclude_unset=True)
        if not update_data:
            return cls.get(ticket_id)
            
        for k, v in list(update_data.items()):
            if hasattr(v, "value"):
                update_data[k] = v.value
                
        update_data["updated_at"] = datetime.now(timezone.utc)
        res = get_tickets_collection().find_one_and_update(
            {"id": ticket_id},
            {"$set": update_data},
            return_document=True
        )
        if res:
            return Ticket(**res)
        return None

    @classmethod
    def delete(cls, ticket_id: int) -> bool:
        """Permanently delete a ticket from MongoDB by its ID."""
        cls._ensure_prepopulated()
        res = get_tickets_collection().delete_one({"id": ticket_id})
        return res.deleted_count > 0
