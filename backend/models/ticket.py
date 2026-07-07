from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketCategory(str, Enum):
    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    GENERAL = "general"


# Shared properties
class TicketBase(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100)
    customer_email: str
    subject: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    priority: TicketPriority = TicketPriority.MEDIUM
    category: TicketCategory = TicketCategory.GENERAL
    conversation_id: Optional[str] = Field(None, description="Optional associated conversation thread ID.")
    user_id: Optional[str] = Field(None, description="Optional associated user ID.")


# Properties to receive on ticket creation
class TicketCreate(TicketBase):
    pass


# Properties to receive on ticket update
class TicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    category: Optional[TicketCategory] = None
    assigned_agent: Optional[str] = None
    resolution_notes: Optional[str] = None
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None


# Properties shared by models stored in DB
class TicketInDBBase(TicketBase):
    id: int
    ticket_id: Optional[str] = Field(None, description="Stable string ticket ID, e.g. TKT-0004.")
    status: TicketStatus
    created_at: datetime
    updated_at: datetime
    assigned_agent: Optional[str] = None
    resolution_notes: Optional[str] = None

    class Config:
        from_attributes = True


# Properties to return to client
class Ticket(TicketInDBBase):
    pass
