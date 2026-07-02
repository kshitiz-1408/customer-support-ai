from datetime import datetime, timezone
from typing import List, Optional
from models.ticket import Ticket, TicketCreate, TicketStatus, TicketUpdate


class TicketService:
    # Class-level mock database
    _db: List[Ticket] = []
    _counter: int = 0

    @classmethod
    def create(cls, ticket_in: TicketCreate) -> Ticket:
        cls._counter += 1
        now = datetime.now(timezone.utc)
        ticket = Ticket(
            id=cls._counter,
            customer_name=ticket_in.customer_name,
            customer_email=ticket_in.customer_email,
            subject=ticket_in.subject,
            description=ticket_in.description,
            priority=ticket_in.priority,
            category=ticket_in.category,
            status=TicketStatus.OPEN,
            created_at=now,
            updated_at=now,
            assigned_agent=None,
            resolution_notes=None,
        )
        cls._db.append(ticket)
        return ticket

    @classmethod
    def get(cls, ticket_id: int) -> Optional[Ticket]:
        for ticket in cls._db:
            if ticket.id == ticket_id:
                return ticket
        return None

    @classmethod
    def get_all(cls, status: Optional[TicketStatus] = None) -> List[Ticket]:
        if status:
            return [t for t in cls._db if t.status == status]
        return cls._db

    @classmethod
    def update(cls, ticket_id: int, ticket_update: TicketUpdate) -> Optional[Ticket]:
        ticket = cls.get(ticket_id)
        if not ticket:
            return None
        
        update_data = ticket_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(ticket, key, value)
            
        ticket.updated_at = datetime.now(timezone.utc)
        return ticket

    @classmethod
    def delete(cls, ticket_id: int) -> bool:
        ticket = cls.get(ticket_id)
        if not ticket:
            return False
        cls._db.remove(ticket)
        return True


# Pre-populate mock tickets
TicketService.create(
    TicketCreate(
        customer_name="Alice Johnson",
        customer_email="alice@example.com",
        subject="Unable to access billing history",
        description="Every time I click on 'Billing History', the app crashes with a 500 error page. Please help.",
        priority="high",
        category="billing"
    )
)
TicketService.create(
    TicketCreate(
        customer_name="Bob Smith",
        customer_email="bob@example.com",
        subject="Request for custom API integration documentation",
        description="We are looking to integrate the customer-support dashboard with our internal logging system. Is there a webhooks specification available?",
        priority="medium",
        category="technical"
    )
)
TicketService.create(
    TicketCreate(
        customer_name="Charlie Brown",
        customer_email="charlie@example.com",
        subject="Password reset link not arriving",
        description="I have requested a password reset link three times but it has not arrived in my inbox or spam folder.",
        priority="urgent",
        category="account"
    )
)
