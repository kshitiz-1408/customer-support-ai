from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status, Depends, Request
from models.ticket import Ticket, TicketCreate, TicketStatus, TicketUpdate
from services.ticket_service import TicketService
from agents.conversation_memory import ConversationMemory
from api.deps import get_current_user

router = APIRouter()


@router.post("/", response_model=Ticket, status_code=status.HTTP_201_CREATED)
def create_ticket(ticket_in: TicketCreate, request: Request, current_user = Depends(get_current_user)):
    """Submit a new support ticket associated with the authenticated user."""
    if ticket_in.conversation_id:
        conv = ConversationMemory.get_conversation(ticket_in.conversation_id)
        if not conv or (conv.get("user_id") and conv["user_id"] != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to the specified conversation thread."
            )
            
    ticket_in.user_id = current_user.id
    created = TicketService.create(ticket_in)
    
    from services.audit_service import AuditService
    AuditService.log_action(
        admin_id=current_user.id,
        target_user_id=None,
        action="ticket_created",
        previous_value=None,
        new_value=created.ticket_id,
        resource_type="ticket",
        resource_id=created.ticket_id,
        status="success",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    return created


@router.get("/", response_model=List[Ticket])
def list_tickets(status: Optional[TicketStatus] = Query(None, description="Filter by status"), current_user = Depends(get_current_user)):
    """Retrieve all support tickets belonging to the authenticated user, optionally filtered by status."""
    return TicketService.get_all(status=status, user_id=current_user.id, email=current_user.email)


@router.get("/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: str, current_user = Depends(get_current_user)):
    """Retrieve details for a specific support ticket by integer ID or string ticket_id, validating ownership."""
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
        
    # Check ownership
    if ticket.user_id:
        if ticket.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this ticket."
            )
    else:
        # Fallback to customer_email comparison to maintain backward compatibility with prepopulated tickets
        if ticket.customer_email.lower().strip() != current_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this ticket."
            )
            
    return ticket


@router.put("/{ticket_id}", response_model=Ticket)
def update_ticket(ticket_id: str, ticket_update: TicketUpdate, request: Request, current_user = Depends(get_current_user)):
    """Update fields on a support ticket by integer ID or string ticket_id, validating ownership."""
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
        
    # Check ownership
    if ticket.user_id:
        if ticket.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this ticket."
            )
    else:
        if ticket.customer_email.lower().strip() != current_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this ticket."
            )
            
    # Ownership is valid, perform the update.
    # Prevent assigning to a different user_id
    if ticket_update.user_id and ticket_update.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign ticket to another user."
        )
        
    # If linking to a conversation, verify the conversation belongs to the user
    if ticket_update.conversation_id:
        conv = ConversationMemory.get_conversation(ticket_update.conversation_id)
        if not conv or (conv.get("user_id") and conv["user_id"] != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to the specified conversation thread."
            )
            
    ticket_update.user_id = current_user.id
    updated = TicketService.update(ticket.id, ticket_update)
    
    from services.audit_service import AuditService
    AuditService.log_action(
        admin_id=current_user.id,
        target_user_id=None,
        action="ticket_updated",
        previous_value=None,
        new_value=updated.ticket_id,
        resource_type="ticket",
        resource_id=updated.ticket_id,
        status="success",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    return updated


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket_id: str, request: Request, current_user = Depends(get_current_user)):
    """Permanently delete a support ticket by integer ID or string ticket_id, validating ownership."""
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
        
    # Check ownership
    if ticket.user_id:
        if ticket.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this ticket."
            )
    else:
        if ticket.customer_email.lower().strip() != current_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this ticket."
            )
            
    deleted = TicketService.delete(ticket.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID '{ticket_id}' not found"
        )
        
    from services.audit_service import AuditService
    AuditService.log_action(
        admin_id=current_user.id,
        target_user_id=None,
        action="ticket_deleted",
        previous_value=ticket.ticket_id,
        new_value=None,
        resource_type="ticket",
        resource_id=ticket.ticket_id,
        status="success",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    return None

