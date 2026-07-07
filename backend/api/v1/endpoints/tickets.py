from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from models.ticket import Ticket, TicketCreate, TicketStatus, TicketUpdate
from services.ticket_service import TicketService

router = APIRouter()


@router.post("/", response_model=Ticket, status_code=status.HTTP_201_CREATED)
def create_ticket(ticket_in: TicketCreate):
    """Submit a new support ticket."""
    return TicketService.create(ticket_in)


@router.get("/", response_model=List[Ticket])
def list_tickets(status: Optional[TicketStatus] = Query(None, description="Filter by status")):
    """Retrieve all support tickets, optionally filtered by status."""
    return TicketService.get_all(status=status)


@router.get("/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: str):
    """Retrieve details for a specific support ticket by integer ID or string ticket_id."""
    try:
        val = int(ticket_id)
        ticket = TicketService.get(val)
    except ValueError:
        ticket = TicketService.get_by_ticket_id(ticket_id)
        
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID '{ticket_id}' not found"
        )
    return ticket


@router.put("/{ticket_id}", response_model=Ticket)
def update_ticket(ticket_id: str, ticket_update: TicketUpdate):
    """Update fields on a support ticket by integer ID or string ticket_id."""
    try:
        val = int(ticket_id)
        ticket = TicketService.update(val, ticket_update)
    except ValueError:
        t = TicketService.get_by_ticket_id(ticket_id)
        if t:
            ticket = TicketService.update(t.id, ticket_update)
        else:
            ticket = None
            
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID '{ticket_id}' not found"
        )
    return ticket


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket_id: str):
    """Permanently delete a support ticket by integer ID or string ticket_id."""
    try:
        val = int(ticket_id)
        deleted = TicketService.delete(val)
    except ValueError:
        t = TicketService.get_by_ticket_id(ticket_id)
        if t:
            deleted = TicketService.delete(t.id)
        else:
            deleted = False
            
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID '{ticket_id}' not found"
        )
    return None
