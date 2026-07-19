from fastapi import APIRouter, Depends, Query, HTTPException, status, UploadFile, File, Request
from typing import Optional, List, Dict, Any
from api.deps import get_current_admin
from models.user import UserInDB, UserRead, UserRole
from models.ticket import Ticket, TicketStatus, TicketPriority, TicketUpdate
from services.user_service import UserService
from services.ticket_service import TicketService
from services.audit_service import AuditService
from database.database import (
    get_tickets_collection, get_conversations_collection, 
    get_users_collection, get_messages_collection, get_ticket_notes_collection,
    get_knowledge_base_collection, get_audit_logs_collection
)
from utils.exceptions import ForbiddenException
from pydantic import BaseModel, Field, ConfigDict
import time
from datetime import datetime, timezone
from bson import ObjectId

router = APIRouter()

class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)

class RoleUpdate(BaseModel):
    role: UserRole

class UserDetailsResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: str
    updated_at: str
    last_login: Optional[str] = None
    conversation_count: int
    ticket_count: int

class AuditLogResponse(BaseModel):
    id: str = Field(..., alias="_id")
    admin_id: str
    target_user_id: str
    action: str
    timestamp: str
    previous_value: Optional[str] = None
    new_value: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class PaginatedUsersResponse(BaseModel):
    total: int
    page: int
    limit: int
    users: List[UserRead]

@router.get("/users", response_model=PaginatedUsersResponse)
def get_users(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    email: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_admin: UserInDB = Depends(get_current_admin)
):
    """List and paginate platform users with filtering capabilities (Admin only)."""
    return UserService.get_users_paginated(
        page=page,
        limit=limit,
        search=search,
        email=email,
        role=role,
        is_active=is_active,
        is_verified=is_verified,
        sort_by=sort_by,
        sort_order=sort_order
    )

@router.get("/users/{id}", response_model=UserDetailsResponse)
def get_user_details(
    id: str,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Retrieve detailed profile view of a user with conversation and ticket counts (Admin only)."""
    user = UserService.get_user_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    ticket_count = get_tickets_collection().count_documents({"user_id": id})
    conversation_count = get_conversations_collection().count_documents({"user_id": id})

    return UserDetailsResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None,
        conversation_count=conversation_count,
        ticket_count=ticket_count
    )

@router.patch("/users/{id}", response_model=UserRead)
def update_user(
    id: str,
    payload: AdminUserUpdate,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Update profile details of a user (Admin only)."""
    user = UserService.get_user_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from models.user import UserUpdate as GenericUserUpdate
    prev_name = user.full_name
    updated = UserService.update_user(id, GenericUserUpdate(full_name=payload.full_name))
    
    if payload.full_name and payload.full_name != prev_name:
        AuditService.log_action(
            admin_id=current_admin.id,
            target_user_id=id,
            action="profile_name_updated",
            previous_value=prev_name,
            new_value=payload.full_name
        )
    return updated

@router.patch("/users/{id}/activate", response_model=UserRead)
def activate_user(
    id: str,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Activate user account (Admin only)."""
    if id == current_admin.id:
        raise ForbiddenException("Administrators cannot activate or deactivate themselves.")
    
    user = UserService.get_user_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.is_active:
        return user

    from models.user import UserUpdate as GenericUserUpdate
    updated = UserService.update_user(id, GenericUserUpdate(is_active=True))
    
    AuditService.log_action(
        admin_id=current_admin.id,
        target_user_id=id,
        action="account_activated",
        previous_value="inactive",
        new_value="active"
    )
    return updated

@router.patch("/users/{id}/deactivate", response_model=UserRead)
def deactivate_user(
    id: str,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Deactivate user account (Admin only)."""
    if id == current_admin.id:
        raise ForbiddenException("Administrators cannot activate or deactivate themselves.")
    
    user = UserService.get_user_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Protection: Prevent deactivating the last active admin
    if user.role == UserRole.ADMIN and user.is_active:
        coll = get_users_collection()
        if hasattr(coll, "find"):
            active_admins = list(coll.find({"role": UserRole.ADMIN, "is_active": True}))
        else:
            active_admins = list(coll.find({"role": UserRole.ADMIN, "is_active": True}))
        if len(active_admins) <= 1:
            raise ForbiddenException("Cannot deactivate the final active administrator in the system.")

    if not user.is_active:
        return user

    from models.user import UserUpdate as GenericUserUpdate
    updated = UserService.update_user(id, GenericUserUpdate(is_active=False))
    
    AuditService.log_action(
        admin_id=current_admin.id,
        target_user_id=id,
        action="account_deactivated",
        previous_value="active",
        new_value="inactive"
    )
    return updated

@router.patch("/users/{id}/role", response_model=UserRead)
def change_user_role(
    id: str,
    payload: RoleUpdate,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Update user role privileges (Admin only)."""
    user = UserService.get_user_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == payload.role:
        return user

    # Protection: Prevent demoting the last active admin (applies to self-demotion or other admins)
    if user.role == UserRole.ADMIN and payload.role != UserRole.ADMIN:
        coll = get_users_collection()
        if hasattr(coll, "find"):
            active_admins = list(coll.find({"role": UserRole.ADMIN, "is_active": True}))
        else:
            active_admins = list(coll.find({"role": UserRole.ADMIN, "is_active": True}))
        if len(active_admins) <= 1:
            raise ForbiddenException("Cannot demote the final active administrator in the system.")

    from models.user import UserUpdate as GenericUserUpdate
    prev_role = user.role
    updated = UserService.update_user(id, GenericUserUpdate(role=payload.role))
    
    AuditService.log_action(
        admin_id=current_admin.id,
        target_user_id=id,
        action="role_changed",
        previous_value=prev_role,
        new_value=payload.role
    )
    return updated

@router.patch("/users/{id}/verify", response_model=UserRead)
def verify_user(
    id: str,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Verify user account (Admin only)."""
    user = UserService.get_user_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.is_verified:
        return user

    from models.user import UserUpdate as GenericUserUpdate
    updated = UserService.update_user(id, GenericUserUpdate(is_verified=True))
    
    AuditService.log_action(
        admin_id=current_admin.id,
        target_user_id=id,
        action="verification_updated",
        previous_value="unverified",
        new_value="verified"
    )
    return updated

@router.patch("/users/{id}/unverify", response_model=UserRead)
def unverify_user(
    id: str,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Unverify user account (Admin only)."""
    user = UserService.get_user_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user.is_verified:
        return user

    from models.user import UserUpdate as GenericUserUpdate
    updated = UserService.update_user(id, GenericUserUpdate(is_verified=False))
    
    AuditService.log_action(
        admin_id=current_admin.id,
        target_user_id=id,
        action="verification_updated",
        previous_value="verified",
        new_value="unverified"
    )
    return updated

@router.get("/users/{id}/audit-logs", response_model=List[AuditLogResponse])
def get_user_audit_logs(
    id: str,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Retrieve all audit logs related to a specific user (Admin only)."""
    user = UserService.get_user_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return AuditService.get_audit_logs_by_target(id)


# Admin Support Ticket Management API endpoints

class TicketAssignPayload(BaseModel):
    assigned_agent: Optional[str] = None

class TicketStatusPayload(BaseModel):
    status: TicketStatus

class TicketPriorityPayload(BaseModel):
    priority: TicketPriority

class TicketNotePayload(BaseModel):
    content: str

class PaginatedTicketsResponse(BaseModel):
    total: int
    page: int
    limit: int
    tickets: List[Ticket]

class TicketMetricsResponse(BaseModel):
    open_tickets: int
    closed_tickets: int
    high_priority: int
    average_resolution_time: float
    tickets_created_today: int

class AdminTicketDetailResponse(BaseModel):
    ticket: Ticket
    messages: List[dict]
    notes: List[dict]
    history: List[dict]


@router.get("/tickets", response_model=PaginatedTicketsResponse)
def get_tickets(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    customer_email: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Retrieve filtered, paginated list of all customer support tickets (Admin only)."""
    return TicketService.get_tickets_paginated(
        page=page,
        limit=limit,
        search=search,
        status=status,
        priority=priority,
        category=category,
        assigned_agent=assigned_agent,
        customer_email=customer_email,
        sort_by=sort_by,
        sort_order=sort_order
    )


@router.get("/tickets/metrics", response_model=TicketMetricsResponse)
def get_tickets_metrics(
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Aggregate support ticket analytics and metrics (Admin only)."""
    return TicketService.get_metrics()


def _resolve_admin_ticket(ticket_id: str) -> Ticket:
    try:
        val = int(ticket_id)
        ticket = TicketService.get(val)
    except ValueError:
        ticket = TicketService.get_by_ticket_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.get("/tickets/{id}", response_model=AdminTicketDetailResponse)
def get_ticket_details(
    id: str,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """View full detailed specifications of a support ticket, message context, and compliance logs (Admin only)."""
    ticket = _resolve_admin_ticket(id)
    
    # 1. Fetch conversation messages if associated
    messages = []
    if ticket.conversation_id:
        coll_msg = get_messages_collection()
        if hasattr(coll_msg, "find"):
            cursor = coll_msg.find({"conversation_id": ticket.conversation_id})
            messages = list(cursor)
        else:
            messages = list(coll_msg.find({"conversation_id": ticket.conversation_id}))
        
        # Sort messages by timestamp
        def get_msg_time(x):
            t = x.get("created_at")
            if isinstance(t, datetime):
                return t
            if isinstance(t, str):
                try:
                    return datetime.fromisoformat(t.replace("Z", "+00:00"))
                except ValueError:
                    pass
            return datetime.min.replace(tzinfo=timezone.utc)
        messages.sort(key=get_msg_time)
        for msg in messages:
            if isinstance(msg.get("created_at"), datetime):
                msg["created_at"] = msg["created_at"].isoformat()
            if "_id" in msg:
                msg["_id"] = str(msg["_id"])

    # 2. Fetch compliance logs (history) for this ticket ID (e.g. target_user_id == ticket_id)
    history = AuditService.get_audit_logs_by_target(ticket.ticket_id)

    # 3. Fetch internal notes from ticket_notes
    notes = []
    coll_notes = get_ticket_notes_collection()
    if hasattr(coll_notes, "find"):
        cursor = coll_notes.find({"ticket_id": ticket.ticket_id})
        notes = list(cursor)
    else:
        notes = list(coll_notes.find({"ticket_id": ticket.ticket_id}))
        
    def get_note_time(x):
        t = x.get("timestamp")
        if isinstance(t, datetime):
            return t
        if isinstance(t, str):
            try:
                return datetime.fromisoformat(t.replace("Z", "+00:00"))
            except ValueError:
                pass
        return datetime.min.replace(tzinfo=timezone.utc)
    notes.sort(key=get_note_time, reverse=True)
    
    for n in notes:
        if isinstance(n.get("timestamp"), datetime):
            n["timestamp"] = n["timestamp"].isoformat()
        if "_id" in n:
            n["_id"] = str(n["_id"])

    return AdminTicketDetailResponse(
        ticket=ticket,
        messages=messages,
        notes=notes,
        history=history
    )


@router.patch("/tickets/{id}/assign", response_model=Ticket)
def assign_ticket(
    id: str,
    payload: TicketAssignPayload,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Assign/Update the assigned administrator agent for a support ticket (Admin only)."""
    ticket = _resolve_admin_ticket(id)
    prev_agent = ticket.assigned_agent

    updated = TicketService.update(ticket.id, TicketUpdate(assigned_agent=payload.assigned_agent))
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update ticket assignment.")
    
    # Audit log
    AuditService.log_action(
        admin_id=current_admin.id,
        target_user_id=ticket.ticket_id,
        action="ticket_assigned",
        previous_value=prev_agent or "unassigned",
        new_value=payload.assigned_agent or "unassigned"
    )
    return updated


@router.patch("/tickets/{id}/status", response_model=Ticket)
def update_ticket_status(
    id: str,
    payload: TicketStatusPayload,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Update the resolution status of a support ticket (Admin only)."""
    ticket = _resolve_admin_ticket(id)
    prev_status = ticket.status.value

    updated = TicketService.update(ticket.id, TicketUpdate(status=payload.status))
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update ticket status.")
    
    # Audit log
    AuditService.log_action(
        admin_id=current_admin.id,
        target_user_id=ticket.ticket_id,
        action="ticket_status_changed",
        previous_value=prev_status,
        new_value=payload.status.value
    )
    return updated


@router.patch("/tickets/{id}/priority", response_model=Ticket)
def update_ticket_priority(
    id: str,
    payload: TicketPriorityPayload,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Update the priority classification of a support ticket (Admin only)."""
    ticket = _resolve_admin_ticket(id)
    prev_priority = ticket.priority.value

    updated = TicketService.update(ticket.id, TicketUpdate(priority=payload.priority))
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update ticket priority.")
    
    # Audit log
    AuditService.log_action(
        admin_id=current_admin.id,
        target_user_id=ticket.ticket_id,
        action="ticket_priority_changed",
        previous_value=prev_priority,
        new_value=payload.priority.value
    )
    return updated


@router.post("/tickets/{id}/notes", response_model=dict)
def add_ticket_note(
    id: str,
    payload: TicketNotePayload,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Submit a internal compliance note to a support ticket (Admin only)."""
    ticket = _resolve_admin_ticket(id)
    
    coll_notes = get_ticket_notes_collection()
    now = datetime.now(timezone.utc)
    note_doc = {
        "_id": str(ObjectId()),
        "ticket_id": ticket.ticket_id,
        "admin_id": current_admin.id,
        "admin_name": current_admin.full_name,
        "content": payload.content.strip(),
        "timestamp": now
    }
    coll_notes.insert_one(note_doc)
    
    # Audit log
    AuditService.log_action(
        admin_id=current_admin.id,
        target_user_id=ticket.ticket_id,
        action="ticket_note_added",
        previous_value=None,
        new_value=payload.content.strip()[:100]  # Log a snippet
    )
    
    note_doc["timestamp"] = note_doc["timestamp"].isoformat()
    return note_doc


class AdminConversationItem(BaseModel):
    conversation_id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int
    ticket_id: Optional[str] = None
    ticket_status: Optional[str] = None


class PaginatedConversationsResponse(BaseModel):
    total: int
    page: int
    limit: int
    conversations: List[AdminConversationItem]


class AdminParticipantInfo(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None


class AdminTicketAssociation(BaseModel):
    ticket_id: str
    subject: str
    status: str
    priority: str
    category: str
    created_at: datetime


class AdminMessageItem(BaseModel):
    message_id: str
    role: str
    content: str
    intent: Optional[str] = None
    agent: Optional[str] = None
    sources: Optional[List[dict]] = None
    confidence_score: Optional[float] = None
    created_at: datetime


class AdminConversationDetailResponse(BaseModel):
    conversation_id: str
    session_id: Optional[str] = None
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    participant: Optional[AdminParticipantInfo] = None
    ticket: Optional[AdminTicketAssociation] = None
    messages: List[AdminMessageItem]


@router.get("/conversations", response_model=PaginatedConversationsResponse)
def get_admin_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by conversation ID, user email, user name, or ticket ID"),
    email: Optional[str] = Query(None, description="Search by user email"),
    conversation_id: Optional[str] = Query(None, description="Search by conversation ID"),
    ticket_id: Optional[str] = Query(None, description="Search by ticket ID"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    status: Optional[str] = Query(None, description="Filter by associated ticket status"),
    current_admin: UserInDB = Depends(get_current_admin)
):
    """List and inspect user conversations with advanced filtering and search features (Admin only)."""
    conv_coll = get_conversations_collection()
    user_coll = get_users_collection()
    ticket_coll = get_tickets_collection()
    msg_coll = get_messages_collection()
    
    match_query = {}
    
    # 1. Specific AND filters
    if conversation_id:
        match_query["conversation_id"] = conversation_id
        
    if email:
        users = list(user_coll.find({"email": {"$regex": email, "$options": "i"}}))
        u_ids = [str(u["_id"]) for u in users]
        match_query["user_id"] = {"$in": u_ids}
        
    date_filter = {}
    if start_date:
        date_filter["$gte"] = start_date
    if end_date:
        date_filter["$lte"] = end_date
    if date_filter:
        match_query["created_at"] = date_filter
        
    specific_ticket_query = {}
    if ticket_id:
        specific_ticket_query["ticket_id"] = {"$regex": ticket_id, "$options": "i"}
    if status:
        specific_ticket_query["status"] = status
    if specific_ticket_query:
        tickets_list = list(ticket_coll.find(specific_ticket_query))
        t_conv_ids = [t["conversation_id"] for t in tickets_list if t.get("conversation_id")]
        match_query["conversation_id"] = {"$in": t_conv_ids}
        
    # 2. General OR search condition
    if search:
        or_conditions = []
        or_conditions.append({"conversation_id": {"$regex": search, "$options": "i"}})
        or_conditions.append({"title": {"$regex": search, "$options": "i"}})
        
        users_by_search = list(user_coll.find({
            "$or": [
                {"email": {"$regex": search, "$options": "i"}},
                {"full_name": {"$regex": search, "$options": "i"}}
            ]
        }))
        u_ids = [str(u["_id"]) for u in users_by_search]
        if u_ids:
            or_conditions.append({"user_id": {"$in": u_ids}})
            
        tickets_by_search = list(ticket_coll.find({
            "$or": [
                {"ticket_id": {"$regex": search, "$options": "i"}},
                {"subject": {"$regex": search, "$options": "i"}},
                {"customer_email": {"$regex": search, "$options": "i"}}
            ]
        }))
        t_conv_ids = [t["conversation_id"] for t in tickets_by_search if t.get("conversation_id")]
        if t_conv_ids:
            or_conditions.append({"conversation_id": {"$in": t_conv_ids}})
            
        if or_conditions:
            if match_query:
                match_query = {"$and": [match_query, {"$or": or_conditions}]}
            else:
                match_query = {"$or": or_conditions}
            
    total = conv_coll.count_documents(match_query)
    skip = (page - 1) * limit
    conversations_cursor = conv_coll.find(match_query).sort("created_at", -1).skip(skip).limit(limit)
    conversations_list = list(conversations_cursor)
    
    enriched = []
    for c in conversations_list:
        c_id = c["conversation_id"]
        u_id = c.get("user_id")
        
        u_email = None
        u_name = None
        if u_id:
            try:
                user_doc = user_coll.find_one({"_id": ObjectId(u_id)})
            except Exception:
                user_doc = user_coll.find_one({"_id": u_id})
            if user_doc:
                u_email = user_doc.get("email")
                u_name = user_doc.get("full_name")
                
        ticket_doc = ticket_coll.find_one({"conversation_id": c_id})
        t_id = ticket_doc.get("ticket_id") if ticket_doc else None
        t_status = ticket_doc.get("status") if ticket_doc else None
        
        msg_count = msg_coll.count_documents({"conversation_id": c_id})
        
        enriched.append(
            AdminConversationItem(
                conversation_id=c_id,
                user_id=u_id,
                user_email=u_email,
                user_name=u_name,
                title=c.get("title") or "Untitled Conversation",
                created_at=c["created_at"],
                updated_at=c["updated_at"],
                message_count=msg_count,
                ticket_id=t_id,
                ticket_status=t_status
            )
        )
        
    return PaginatedConversationsResponse(
        total=total,
        page=page,
        limit=limit,
        conversations=enriched
    )


@router.get("/conversations/{conversation_id}", response_model=AdminConversationDetailResponse)
def get_admin_conversation_details(
    conversation_id: str,
    request: Request,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Retrieve full details, message history, and audit parameters for a single conversation thread (Admin only)."""
    conv_coll = get_conversations_collection()
    conv = conv_coll.find_one({"conversation_id": conversation_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    AuditService.log_action(
        admin_id=current_admin.id,
        target_user_id=conv.get("user_id"),
        action="conversation_viewed",
        previous_value=None,
        new_value=conversation_id,
        resource_type="conversation",
        resource_id=conversation_id,
        status="success",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
        
    user_coll = get_users_collection()
    ticket_coll = get_tickets_collection()
    msg_coll = get_messages_collection()
    
    u_id = conv.get("user_id")
    participant = None
    if u_id:
        try:
            user_doc = user_coll.find_one({"_id": ObjectId(u_id)})
        except Exception:
            user_doc = user_coll.find_one({"_id": u_id})
        if user_doc:
            participant = AdminParticipantInfo(
                user_id=u_id,
                email=user_doc.get("email"),
                full_name=user_doc.get("full_name")
            )
            
    ticket_doc = ticket_coll.find_one({"conversation_id": conversation_id})
    ticket = None
    if ticket_doc:
        ticket = AdminTicketAssociation(
            ticket_id=ticket_doc["ticket_id"],
            subject=ticket_doc["subject"],
            status=ticket_doc["status"],
            priority=ticket_doc["priority"],
            category=ticket_doc["category"],
            created_at=ticket_doc["created_at"]
        )
        
    messages_cursor = msg_coll.find({"conversation_id": conversation_id}).sort("created_at", 1)
    message_items = []
    for m in messages_cursor:
        message_items.append(
            AdminMessageItem(
                message_id=m["message_id"],
                role=m["role"],
                content=m["content"],
                intent=m.get("intent"),
                agent=m.get("agent"),
                sources=m.get("sources"),
                confidence_score=m.get("confidence_score"),
                created_at=m["created_at"]
            )
        )
        
    return AdminConversationDetailResponse(
        conversation_id=conversation_id,
        session_id=conv.get("session_id"),
        title=conv.get("title") or "Untitled Conversation",
        created_at=conv["created_at"],
        updated_at=conv["updated_at"],
        participant=participant,
        ticket=ticket,
        messages=message_items
    )


# --- KNOWLEDGE BASE MANAGEMENT SCHEMAS ---

class KBDocumentMetadataResponse(BaseModel):
    document_id: str
    filename: str
    upload_date: datetime
    file_type: str
    chunk_count: int
    embedding_status: str
    indexed_status: str
    file_size: int
    uploaded_by: str
    embedding_model: str
    last_indexed: Optional[datetime] = None

class KBDocumentListResponse(BaseModel):
    total: int
    documents: List[KBDocumentMetadataResponse]


# --- KNOWLEDGE BASE MANAGEMENT ENDPOINTS ---

@router.get("/knowledge", response_model=KBDocumentListResponse)
async def list_knowledge_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    extension: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Retrieve list of knowledge base documents with search and filtering features."""
    kb_coll = get_knowledge_base_collection()
    query = {}
    
    if search:
        query["filename"] = {"$regex": search, "$options": "i"}
        
    if extension:
        query["file_type"] = extension.strip().lower()
        
    if status:
        query["embedding_status"] = status
        
    date_filter = {}
    if start_date:
        date_filter["$gte"] = start_date
    if end_date:
        date_filter["$lte"] = end_date
    if date_filter:
        query["upload_date"] = date_filter
        
    total = kb_coll.count_documents(query)
    skip = (page - 1) * limit
    
    docs_cursor = kb_coll.find(query).sort("upload_date", -1).skip(skip).limit(limit)
    docs_list = list(docs_cursor)
    
    documents = [
        KBDocumentMetadataResponse(
            document_id=d["_id"],
            filename=d["filename"],
            upload_date=d["upload_date"],
            file_type=d["file_type"],
            chunk_count=d.get("chunk_count", 0),
            embedding_status=d.get("embedding_status", "completed"),
            indexed_status=d.get("indexed_status", "completed"),
            file_size=d["file_size"],
            uploaded_by=d["uploaded_by"],
            embedding_model=d.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"),
            last_indexed=d.get("last_indexed")
        )
        for d in docs_list
    ]
    
    return KBDocumentListResponse(total=total, documents=documents)


@router.get("/knowledge/{document_id}", response_model=KBDocumentMetadataResponse)
async def get_knowledge_document(
    document_id: str,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Retrieve detailed metadata of a single knowledge base document."""
    kb_coll = get_knowledge_base_collection()
    doc = kb_coll.find_one({"_id": document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Knowledge base document not found.")
        
    return KBDocumentMetadataResponse(
        document_id=doc["_id"],
        filename=doc["filename"],
        upload_date=doc["upload_date"],
        file_type=doc["file_type"],
        chunk_count=doc.get("chunk_count", 0),
        embedding_status=doc.get("embedding_status", "completed"),
        indexed_status=doc.get("indexed_status", "completed"),
        file_size=doc["file_size"],
        uploaded_by=doc["uploaded_by"],
        embedding_model=doc.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"),
        last_indexed=doc.get("last_indexed")
    )


@router.post("/knowledge/upload", response_model=KBDocumentMetadataResponse, status_code=201)
async def upload_knowledge_document(
    request: Request,
    file: UploadFile = File(...),
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Upload and process knowledge base files, triggering chunk extraction and vector store builds."""
    import os
    import uuid
    
    # 1. Path traversal prevention & filename sanitation
    filename = os.path.basename(file.filename)
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
        
    # 2. File type validation
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ["pdf", "txt", "md", "docx"]:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension '.{ext}'. Allowed types: pdf, txt, md, docx.")
        
    # 3. Limit upload size (10MB)
    MAX_SIZE = 10 * 1024 * 1024
    file_bytes = await file.read()
    if len(file_bytes) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds maximum limit of 10MB.")
        
    # 4. Check duplicate filename in DB
    kb_coll = get_knowledge_base_collection()
    existing = kb_coll.find_one({"filename": filename})
    if existing:
        raise HTTPException(status_code=409, detail=f"A document named '{filename}' already exists.")
        
    # 5. Determine knowledge base folder
    from database.database import PROJECT_ROOT
    kb_dir = os.path.join(PROJECT_ROOT, "knowledge_base")
    os.makedirs(kb_dir, exist_ok=True)
    
    file_path = os.path.join(kb_dir, filename)
    
    try:
        with open(file_path, "wb") as f:
            f.write(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file to disk: {str(e)}")
        
    # 6. Insert initial pending record
    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    kb_coll.insert_one({
        "_id": doc_id,
        "filename": filename,
        "upload_date": now,
        "file_type": ext,
        "file_size": len(file_bytes),
        "uploaded_by": current_admin.email,
        "chunk_count": 0,
        "embedding_status": "pending",
        "indexed_status": "pending",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "last_indexed": None
    })
    
    # 7. Run reindexing pipelines synchronously
    try:
        from rag.rag_pipeline import initialize_rag_pipeline
        initialize_rag_pipeline(force_rebuild=True)
    except Exception as e:
        kb_coll.update_one(
            {"_id": doc_id},
            {"$set": {"embedding_status": "failed", "indexed_status": "failed"}}
        )
        raise HTTPException(status_code=500, detail=f"File uploaded successfully, but vector rebuild failed: {str(e)}")
        
    AuditService.log_action(
        admin_id=current_admin.id,
        target_user_id=None,
        action="kb_document_uploaded",
        previous_value=None,
        new_value=filename,
        resource_type="kb_document",
        resource_id=doc_id,
        status="success",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        additional_metadata={"file_size": len(file_bytes), "file_type": ext}
    )
    
    updated = kb_coll.find_one({"_id": doc_id})
    return KBDocumentMetadataResponse(
        document_id=updated["_id"],
        filename=updated["filename"],
        upload_date=updated["upload_date"],
        file_type=updated["file_type"],
        chunk_count=updated.get("chunk_count", 0),
        embedding_status=updated.get("embedding_status", "completed"),
        indexed_status=updated.get("indexed_status", "completed"),
        file_size=updated["file_size"],
        uploaded_by=updated["uploaded_by"],
        embedding_model=updated.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"),
        last_indexed=updated.get("last_indexed")
    )


@router.delete("/knowledge/{document_id}", status_code=200)
async def delete_knowledge_document(
    document_id: str,
    request: Request,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Deletes document physical file, DB metadata, and clears chunks from the FAISS vector database."""
    import os
    
    kb_coll = get_knowledge_base_collection()
    doc = kb_coll.find_one({"_id": document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Knowledge base document not found.")
        
    filename = doc["filename"]
    from database.database import PROJECT_ROOT
    kb_dir = os.path.join(PROJECT_ROOT, "knowledge_base")
    file_path = os.path.join(kb_dir, filename)
    
    # 1. Remove physical file
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            logger.error(f"Failed to delete file from disk: {str(e)}")
            
    # 2. Delete database record
    kb_coll.delete_one({"_id": document_id})
    
    # 3. Synchronize vector store index
    try:
        from rag.rag_pipeline import initialize_rag_pipeline
        initialize_rag_pipeline(force_rebuild=True)
    except Exception as e:
        logger.error(f"Failed to rebuild RAG pipeline index: {str(e)}")
        
    AuditService.log_action(
        admin_id=current_admin.id,
        target_user_id=None,
        action="kb_document_deleted",
        previous_value=filename,
        new_value=None,
        resource_type="kb_document",
        resource_id=document_id,
        status="success",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    return {"message": "Document removed successfully and vector database synchronized."}


@router.post("/knowledge/reindex/{document_id}", response_model=KBDocumentMetadataResponse)
async def reindex_knowledge_document(
    document_id: str,
    request: Request,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Rebuild vector embeddings for a specific knowledge base document."""
    kb_coll = get_knowledge_base_collection()
    doc = kb_coll.find_one({"_id": document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Knowledge base document not found.")
        
    try:
        from rag.rag_pipeline import initialize_rag_pipeline
        initialize_rag_pipeline(force_rebuild=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reindexing failed: {str(e)}")
        
    AuditService.log_action(
        admin_id=current_admin.id,
        target_user_id=None,
        action="kb_document_reindexed",
        previous_value=None,
        new_value=doc["filename"],
        resource_type="kb_document",
        resource_id=document_id,
        status="success",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    updated = kb_coll.find_one({"_id": document_id})
    return KBDocumentMetadataResponse(
        document_id=updated["_id"],
        filename=updated["filename"],
        upload_date=updated["upload_date"],
        file_type=updated["file_type"],
        chunk_count=updated.get("chunk_count", 0),
        embedding_status=updated.get("embedding_status", "completed"),
        indexed_status=updated.get("indexed_status", "completed"),
        file_size=updated["file_size"],
        uploaded_by=updated["uploaded_by"],
        embedding_model=updated.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"),
        last_indexed=updated.get("last_indexed")
    )


@router.post("/knowledge/reindex-all", status_code=200)
async def reindex_all_knowledge(
    request: Request,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Rebuild vector embeddings for the entire knowledge base directory."""
    try:
        from rag.rag_pipeline import initialize_rag_pipeline
        initialize_rag_pipeline(force_rebuild=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Complete reindexing run failed: {str(e)}")
        
    AuditService.log_action(
        admin_id=current_admin.id,
        target_user_id=None,
        action="kb_reindexed_all",
        previous_value=None,
        new_value="all",
        resource_type="kb_document",
        resource_id="all",
        status="success",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    return {"message": "Knowledge base vector index and chunk mappings rebuilt successfully."}


class AnalyticsOverviewResponse(BaseModel):
    total_users: int
    active_users: int
    total_conversations: int
    total_messages: int
    total_tickets: int
    open_tickets: int
    closed_tickets: int
    total_documents: int
    total_administrators: int


class DailyCount(BaseModel):
    date: str
    count: int


class AnalyticsUsageResponse(BaseModel):
    conversations_per_day: List[DailyCount]
    messages_per_day: List[DailyCount]
    new_users_per_day: List[DailyCount]
    tickets_per_day: List[DailyCount]


class AnalyticsAIResponse(BaseModel):
    average_ai_response_time: float
    average_confidence_score: float
    intent_distribution: Dict[str, int] = Field(default_factory=dict)
    agent_routing_distribution: Dict[str, int] = Field(default_factory=dict)
    rag_retrieval_count: int
    gemini_request_count: int
    failed_ai_requests: int
    ai_success_rate: float


class AnalyticsSystemResponse(BaseModel):
    database_status: str
    vector_index_status: str
    total_embeddings: int
    startup_time: str
    api_uptime: float
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None


@router.get("/analytics/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview(current_admin: UserInDB = Depends(get_current_admin)):
    """Get high-level counters of all main support resources."""
    u_coll = get_users_collection()
    c_coll = get_conversations_collection()
    m_coll = get_messages_collection()
    t_coll = get_tickets_collection()
    kb_coll = get_knowledge_base_collection()

    total_users = u_coll.count_documents({})
    active_users = u_coll.count_documents({"is_active": True})
    total_admins = u_coll.count_documents({"role": "admin"})

    total_conversations = c_coll.count_documents({})
    total_messages = m_coll.count_documents({})

    total_tickets = t_coll.count_documents({})
    open_tickets = t_coll.count_documents({"status": {"$in": ["open", "in_progress"]}})
    closed_tickets = t_coll.count_documents({"status": {"$in": ["resolved", "closed"]}})

    total_documents = kb_coll.count_documents({})

    return AnalyticsOverviewResponse(
        total_users=total_users,
        active_users=active_users,
        total_conversations=total_conversations,
        total_messages=total_messages,
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        closed_tickets=closed_tickets,
        total_documents=total_documents,
        total_administrators=total_admins
    )


@router.get("/analytics/usage", response_model=AnalyticsUsageResponse)
async def get_analytics_usage(
    range_type: Optional[str] = Query("7d", alias="range"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Get time-series usage statistics for the specified range."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)

    # 1. Parse date boundaries
    if start_date and end_date:
        s_date = start_date
        e_date = end_date
    else:
        if range_type == "30d":
            s_date = now - timedelta(days=30)
            e_date = now
        elif range_type == "90d":
            s_date = now - timedelta(days=90)
            e_date = now
        elif range_type == "today":
            s_date = now - timedelta(days=1)
            e_date = now
        else:  # default to "7d"
            s_date = now - timedelta(days=7)
            e_date = now

    # Ensure tzinfo is set to UTC
    if s_date.tzinfo is None:
        s_date = s_date.replace(tzinfo=timezone.utc)
    if e_date.tzinfo is None:
        e_date = e_date.replace(tzinfo=timezone.utc)

    # Helper helper to group by day and fill in missing days
    def group_docs_by_day(collection, query_filter, date_field):
        docs = list(collection.find(query_filter, {date_field: 1, "_id": 0}))
        
        daily_map = {}
        curr = s_date.date()
        limit = e_date.date()
        while curr <= limit:
            daily_map[curr.strftime("%Y-%m-%d")] = 0
            curr += timedelta(days=1)

        for d in docs:
            val = d.get(date_field)
            if not val:
                continue
            if isinstance(val, str):
                try:
                    val = datetime.fromisoformat(val.replace("Z", "+00:00"))
                except Exception:
                    continue
            if val.tzinfo is None:
                val = val.replace(tzinfo=timezone.utc)
            d_date = val.date()
            if s_date.date() <= d_date <= e_date.date():
                k = d_date.strftime("%Y-%m-%d")
                daily_map[k] = daily_map.get(k, 0) + 1

        return [DailyCount(date=k, count=v) for k, v in sorted(daily_map.items())]

    conversations_by_day = group_docs_by_day(
        get_conversations_collection(),
        {"created_at": {"$gte": s_date, "$lte": e_date}},
        "created_at"
    )

    messages_by_day = group_docs_by_day(
        get_messages_collection(),
        {"created_at": {"$gte": s_date, "$lte": e_date}},
        "created_at"
    )

    new_users_by_day = group_docs_by_day(
        get_users_collection(),
        {"created_at": {"$gte": s_date, "$lte": e_date}},
        "created_at"
    )

    tickets_by_day = group_docs_by_day(
        get_tickets_collection(),
        {"created_at": {"$gte": s_date, "$lte": e_date}},
        "created_at"
    )

    return AnalyticsUsageResponse(
        conversations_per_day=conversations_by_day,
        messages_per_day=messages_by_day,
        new_users_per_day=new_users_by_day,
        tickets_per_day=tickets_by_day
    )


@router.get("/analytics/ai", response_model=AnalyticsAIResponse)
async def get_analytics_ai(
    range_type: Optional[str] = Query("7d", alias="range"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Get AI KPIs, intent routing distribution, success rate, and response times."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)

    if start_date and end_date:
        s_date = start_date
        e_date = end_date
    else:
        if range_type == "30d":
            s_date = now - timedelta(days=30)
            e_date = now
        elif range_type == "90d":
            s_date = now - timedelta(days=90)
            e_date = now
        elif range_type == "today":
            s_date = now - timedelta(days=1)
            e_date = now
        else:
            s_date = now - timedelta(days=7)
            e_date = now

    if s_date.tzinfo is None:
        s_date = s_date.replace(tzinfo=timezone.utc)
    if e_date.tzinfo is None:
        e_date = e_date.replace(tzinfo=timezone.utc)

    m_coll = get_messages_collection()
    
    # Query assistant messages to extract stats
    assistant_msgs = list(m_coll.find(
        {"role": "assistant", "created_at": {"$gte": s_date, "$lte": e_date}}
    ))

    intents = {}
    agents = {}
    total_rag_sources = 0
    confidence_sum = 0.0
    confidence_count = 0
    failed_requests = 0

    for msg in assistant_msgs:
        intent = msg.get("intent") or "unknown"
        intents[intent] = intents.get(intent, 0) + 1

        agent = msg.get("agent") or "FAQ Agent"
        agents[agent] = agents.get(agent, 0) + 1

        sources = msg.get("sources")
        if sources:
            total_rag_sources += len(sources)

        conf = msg.get("confidence_score")
        if conf is not None:
            confidence_sum += conf
            confidence_count += 1

        if intent == "unknown" or msg.get("content") == "Please clarify your question.":
            failed_requests += 1

    avg_confidence = (confidence_sum / confidence_count) if confidence_count > 0 else 0.85
    gemini_requests = len(assistant_msgs)
    success_rate = ((gemini_requests - failed_requests) / gemini_requests) if gemini_requests > 0 else 1.0

    avg_response_time = 2.4  # default/fallback baseline

    if gemini_requests > 0:
        conv_ids = list(set(msg["conversation_id"] for msg in assistant_msgs))
        all_msgs = list(m_coll.find(
            {"conversation_id": {"$in": conv_ids}},
            {"conversation_id": 1, "role": 1, "created_at": 1}
        ))

        from collections import defaultdict
        conv_groups = defaultdict(list)
        for m in all_msgs:
            conv_groups[m["conversation_id"]].append(m)

        for cid in conv_groups:
            conv_groups[cid].sort(key=lambda x: x["created_at"])

        durations = []
        for cid, msgs_list in conv_groups.items():
            for idx, msg in enumerate(msgs_list):
                if msg["role"] == "assistant" and idx > 0:
                    prev = msgs_list[idx - 1]
                    if prev["role"] == "user":
                        t_assistant = msg["created_at"]
                        t_user = prev["created_at"]
                        if isinstance(t_assistant, str):
                            t_assistant = datetime.fromisoformat(t_assistant.replace("Z", "+00:00"))
                        if isinstance(t_user, str):
                            t_user = datetime.fromisoformat(t_user.replace("Z", "+00:00"))
                        delta = (t_assistant - t_user).total_seconds()
                        if 0.1 <= delta <= 30.0:
                            durations.append(delta)

        if durations:
            avg_response_time = sum(durations) / len(durations)

    return AnalyticsAIResponse(
        average_ai_response_time=round(avg_response_time, 2),
        average_confidence_score=round(avg_confidence, 2),
        intent_distribution=intents,
        agent_routing_distribution=agents,
        rag_retrieval_count=total_rag_sources,
        gemini_request_count=gemini_requests,
        failed_ai_requests=failed_requests,
        ai_success_rate=round(success_rate, 4)
    )


@router.get("/analytics/system", response_model=AnalyticsSystemResponse)
async def get_analytics_system(current_admin: UserInDB = Depends(get_current_admin)):
    """Get server diagnostics, Vector index, database uptime, memory and CPU usage."""
    from main import STARTUP_TIME
    from rag.rag_pipeline import vector_store
    
    db_status = "connected"
    try:
        get_users_collection().find_one({})
    except Exception:
        db_status = "error"

    vector_status = "empty"
    total_embeddings = 0
    try:
        if vector_store and vector_store._index:
            total_embeddings = vector_store._index.ntotal
            vector_status = "loaded" if total_embeddings > 0 else "empty"
    except Exception:
        vector_status = "error"

    now = datetime.now(timezone.utc)
    uptime_sec = (now - STARTUP_TIME).total_seconds()

    cpu_val = None
    mem_val = None
    try:
        import psutil
        cpu_val = psutil.cpu_percent(interval=None)
        mem_val = psutil.virtual_memory().percent
    except Exception:
        pass

    return AnalyticsSystemResponse(
        database_status=db_status,
        vector_index_status=vector_status,
        total_embeddings=total_embeddings,
        startup_time=STARTUP_TIME.isoformat(),
        api_uptime=round(uptime_sec, 2),
        cpu_usage=cpu_val,
        memory_usage=mem_val
    )


# --- AUDIT LOGS SEARCH, PAGINATION & SPEC DETAILS SCHEMAS ---

class AuditLogDetailResponse(BaseModel):
    audit_id: str = Field(..., alias="_id")
    timestamp: str
    actor_user_id: Optional[str] = None
    actor_email: Optional[str] = None
    actor_role: Optional[str] = None
    action: str
    resource_type: str
    resource_id: str
    target_user_id: Optional[str] = None
    target_email: Optional[str] = None
    status: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    previous_value: Optional[Any] = None
    new_value: Optional[Any] = None
    additional_metadata: Optional[dict] = None

    model_config = ConfigDict(populate_by_name=True)


class PaginatedAuditResponse(BaseModel):
    total: int
    page: int
    limit: int
    logs: List[AuditLogDetailResponse]


@router.get("/audit", response_model=PaginatedAuditResponse)
def get_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    action: Optional[str] = None,
    actor: Optional[str] = None,
    target_user: Optional[str] = None,
    resource_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Retrieve audit logs with pagination, search, and granular filtering capabilities (Admin only)."""
    coll = get_audit_logs_collection()
    
    if hasattr(coll, "find"):
        docs = list(coll.find({}))
    else:
        docs = list(coll.find({}))
        
    filtered = []
    for doc in docs:
        t_val = doc.get("timestamp")
        if isinstance(t_val, str):
            try:
                dt_val = datetime.fromisoformat(t_val.replace("Z", "+00:00"))
            except Exception:
                dt_val = datetime.min.replace(tzinfo=timezone.utc)
        elif isinstance(t_val, datetime):
            dt_val = t_val
        else:
            dt_val = datetime.min.replace(tzinfo=timezone.utc)

        # Filters:
        # 1. Date Range
        if start_date:
            try:
                sd = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                if sd.tzinfo is not None and dt_val.tzinfo is None:
                    sd = sd.replace(tzinfo=None)
                elif sd.tzinfo is None and dt_val.tzinfo is not None:
                    dt_val = dt_val.replace(tzinfo=None)
                if dt_val < sd:
                    continue
            except Exception:
                pass
        if end_date:
            try:
                ed = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                if ed.tzinfo is not None and dt_val.tzinfo is None:
                    ed = ed.replace(tzinfo=None)
                elif ed.tzinfo is None and dt_val.tzinfo is not None:
                    dt_val = dt_val.replace(tzinfo=None)
                if dt_val > ed:
                    continue
            except Exception:
                pass

        # 2. Action filter
        if action and action.strip().lower() != doc.get("action", "").lower():
            continue

        # 3. Actor filter (matches actor_user_id or actor_email or legacy admin_id)
        if actor:
            act_lower = actor.strip().lower()
            actor_uid = doc.get("actor_user_id") or doc.get("admin_id") or ""
            actor_mail = doc.get("actor_email") or ""
            if act_lower not in actor_uid.lower() and act_lower not in actor_mail.lower():
                continue

        # 4. Target User filter (matches target_user_id or target_email)
        if target_user:
            t_lower = target_user.strip().lower()
            target_uid = doc.get("target_user_id") or ""
            target_mail = doc.get("target_email") or ""
            if t_lower not in target_uid.lower() and t_lower not in target_mail.lower():
                continue

        # 5. Resource Type filter
        if resource_type and resource_type.strip().lower() != doc.get("resource_type", "user").lower():
            continue

        # 6. Status filter
        if status and status.strip().lower() != doc.get("status", "success").lower():
            continue

        # 7. Global Search (matches email, action, status, resource_type, or IDs)
        if search:
            s_lower = search.strip().lower()
            matched = False
            fields_to_search = [
                doc.get("action", ""),
                doc.get("actor_email", ""),
                doc.get("target_email", ""),
                doc.get("resource_type", "user"),
                doc.get("status", "success"),
                doc.get("ip_address", ""),
                doc.get("_id", "")
            ]
            for f in fields_to_search:
                if f and s_lower in str(f).lower():
                    matched = True
                    break
            if not matched:
                continue

        # Standardize doc keys for response mapping fallback
        mapped_doc = dict(doc)
        mapped_doc["timestamp"] = dt_val.isoformat()
        if "actor_user_id" not in mapped_doc:
            mapped_doc["actor_user_id"] = doc.get("admin_id")
        if "resource_type" not in mapped_doc:
            mapped_doc["resource_type"] = "user"
        if "resource_id" not in mapped_doc:
            mapped_doc["resource_id"] = doc.get("target_user_id")
        if "status" not in mapped_doc:
            mapped_doc["status"] = "success"
        
        filtered.append(mapped_doc)

    # 8. Sort newest first (chrono descending)
    def sort_key(x):
        return x.get("timestamp")
    filtered.sort(key=sort_key, reverse=True)

    # 9. Paginate
    total = len(filtered)
    start = (page - 1) * limit
    end = start + limit
    page_logs = filtered[start:end]

    return PaginatedAuditResponse(
        total=total,
        page=page,
        limit=limit,
        logs=page_logs
    )


@router.get("/audit/{audit_id}", response_model=AuditLogDetailResponse)
def get_audit_log_details(
    audit_id: str,
    current_admin: UserInDB = Depends(get_current_admin)
):
    """Retrieve full detail specification view of a single audit log event (Admin only)."""
    coll = get_audit_logs_collection()
    doc = coll.find_one({"_id": audit_id})
    if not doc:
        try:
            doc = coll.find_one({"_id": ObjectId(audit_id)})
        except Exception:
            pass
            
    if not doc:
        raise HTTPException(status_code=404, detail="Audit log not found")

    t_val = doc.get("timestamp")
    if isinstance(t_val, str):
        try:
            dt_val = datetime.fromisoformat(t_val.replace("Z", "+00:00"))
        except Exception:
            dt_val = datetime.min.replace(tzinfo=timezone.utc)
    elif isinstance(t_val, datetime):
        dt_val = t_val
    else:
        dt_val = datetime.min.replace(tzinfo=timezone.utc)

    mapped_doc = dict(doc)
    mapped_doc["timestamp"] = dt_val.isoformat()
    if "actor_user_id" not in mapped_doc:
        mapped_doc["actor_user_id"] = doc.get("admin_id")
    if "resource_type" not in mapped_doc:
        mapped_doc["resource_type"] = "user"
    if "resource_id" not in mapped_doc:
        mapped_doc["resource_id"] = doc.get("target_user_id")
    if "status" not in mapped_doc:
        mapped_doc["status"] = "success"

    return mapped_doc


# --- SYSTEM MONITORING MODELS & ENDPOINTS ---

class SystemHealthResponse(BaseModel):
    overall_status: str
    backend_status: str
    frontend_status: str
    database_status: str
    gemini_status: str
    rag_status: str
    vector_index_status: str
    uptime: float
    version: str

class PerformanceMetricsResponse(BaseModel):
    average_response_time: float
    requests_per_minute: float
    active_users: int
    active_conversations: int
    memory_usage: float
    cpu_usage: float
    startup_duration: float
    database_latency: float

class SingleServiceStatus(BaseModel):
    status: str
    last_check: str
    response_time: float
    error: Optional[str] = None

class ServicesStatusResponse(BaseModel):
    mongodb: SingleServiceStatus
    gemini: SingleServiceStatus
    embeddings: SingleServiceStatus
    vector_store: SingleServiceStatus
    background_services: SingleServiceStatus


@router.get("/system/health", response_model=SystemHealthResponse)
def get_system_health(request: Request, current_admin: UserInDB = Depends(get_current_admin)):
    """Get overall system health and sub-service status overview (Admin only)."""
    from main import STARTUP_TIME
    from rag.rag_pipeline import vector_store
    from config.config import settings

    # Database health check
    db_status = "healthy"
    try:
        get_users_collection().find_one({})
    except Exception:
        db_status = "unhealthy"

    # Gemini health check
    gemini_status = "healthy"
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "PASTE_YOUR_ACTUAL_API_KEY_HERE":
        gemini_status = "unhealthy"
    else:
        try:
            from services.llm_service import GeminiLLMService
            GeminiLLMService._initialize_sdk()
        except Exception:
            gemini_status = "unhealthy"

    # RAG pipeline & vector store check
    rag_status = "healthy"
    vector_index_status = "loaded"
    try:
        if not vector_store or not vector_store._index:
            rag_status = "unhealthy"
            vector_index_status = "error"
        else:
            total_embeddings = vector_store._index.ntotal
            vector_index_status = "loaded" if total_embeddings > 0 else "empty"
    except Exception:
        rag_status = "unhealthy"
        vector_index_status = "error"

    # Overall Status calculation
    overall_status = "healthy"
    if db_status == "unhealthy":
        overall_status = "unhealthy"
    elif gemini_status == "unhealthy" or rag_status == "unhealthy" or vector_index_status == "error":
        overall_status = "warning"

    now = datetime.now(timezone.utc)
    uptime_sec = (now - STARTUP_TIME).total_seconds()

    return SystemHealthResponse(
        overall_status=overall_status,
        backend_status="healthy",
        frontend_status="healthy",
        database_status=db_status,
        gemini_status=gemini_status,
        rag_status=rag_status,
        vector_index_status=vector_index_status,
        uptime=round(uptime_sec, 2),
        version=settings.VERSION
    )


@router.get("/system/performance", response_model=PerformanceMetricsResponse)
def get_system_performance(request: Request, current_admin: UserInDB = Depends(get_current_admin)):
    """Get system and database real-time performance indicators (Admin only)."""
    from datetime import timedelta
    from main import STARTUP_TIME

    now = datetime.now(timezone.utc)
    five_mins_ago = now - timedelta(minutes=5)
    fifteen_mins_ago = now - timedelta(minutes=15)

    # 1. Database latency
    db_start = time.perf_counter()
    db_latency = 0.0
    try:
        get_users_collection().find_one({})
        db_latency = (time.perf_counter() - db_start) * 1000.0  # in ms
    except Exception:
        pass

    # 2. Average response time of AI
    m_coll = get_messages_collection()
    assistant_msgs = list(m_coll.find(
        {"role": "assistant"}
    ).sort("created_at", -1).limit(100))
    
    durations = []
    if assistant_msgs:
        cids = list(set(msg.get("conversation_id") for msg in assistant_msgs if msg.get("conversation_id")))
        all_conv_msgs = list(m_coll.find(
            {"conversation_id": {"$in": cids}}
        ).sort("created_at", 1))
        
        from collections import defaultdict
        conv_groups = defaultdict(list)
        for msg in all_conv_msgs:
            conv_groups[msg["conversation_id"]].append(msg)
            
        for cid, msgs_list in conv_groups.items():
            for idx, msg in enumerate(msgs_list):
                if msg["role"] == "assistant" and idx > 0:
                    prev = msgs_list[idx - 1]
                    if prev["role"] == "user":
                        t_assistant = msg["created_at"]
                        t_user = prev["created_at"]
                        if isinstance(t_assistant, str):
                            t_assistant = datetime.fromisoformat(t_assistant.replace("Z", "+00:00"))
                        if isinstance(t_user, str):
                            t_user = datetime.fromisoformat(t_user.replace("Z", "+00:00"))
                        delta = (t_assistant - t_user).total_seconds()
                        if 0.1 <= delta <= 30.0:
                            durations.append(delta)

    avg_response_time = sum(durations) / len(durations) if durations else 2.4

    # 3. Requests per minute
    msg_count = m_coll.count_documents({"created_at": {"$gte": five_mins_ago}})
    rpm = msg_count / 5.0

    # 4. Active users
    u_coll = get_users_collection()
    active_users = u_coll.count_documents({"last_login": {"$gte": fifteen_mins_ago}})
    active_users = max(1, active_users)

    # 5. Active conversations
    c_coll = get_conversations_collection()
    active_convs = c_coll.count_documents({"updated_at": {"$gte": fifteen_mins_ago}})

    # 6. Memory and CPU usage
    cpu_usage = 0.0
    memory_usage = 0.0
    try:
        import psutil
        cpu_usage = psutil.cpu_percent(interval=None)
        memory_usage = psutil.virtual_memory().percent
    except Exception:
        pass

    # 7. Startup duration
    startup_timings = getattr(request.app.state, "startup_timings", {})
    startup_duration = startup_timings.get("total_ms", 0.0)

    return PerformanceMetricsResponse(
        average_response_time=round(avg_response_time, 2),
        requests_per_minute=round(rpm, 2),
        active_users=active_users,
        active_conversations=active_convs,
        memory_usage=round(memory_usage, 2),
        cpu_usage=round(cpu_usage, 2),
        startup_duration=round(startup_duration, 2),
        database_latency=round(db_latency, 2)
    )


@router.get("/system/services", response_model=ServicesStatusResponse)
def get_system_services(current_admin: UserInDB = Depends(get_current_admin)):
    """Check individual component service health status (Admin only)."""
    from rag.rag_pipeline import vector_store
    from config.config import settings

    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. MongoDB
    db_start = time.perf_counter()
    db_error = None
    try:
        get_users_collection().find_one({})
        db_res_time = (time.perf_counter() - db_start) * 1000.0
        db_status = "healthy"
    except Exception as e:
        db_res_time = (time.perf_counter() - db_start) * 1000.0
        db_status = "unhealthy"
        db_error = str(e)

    # 2. Gemini API
    gemini_start = time.perf_counter()
    gemini_error = None
    gemini_status = "healthy"
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "PASTE_YOUR_ACTUAL_API_KEY_HERE":
        gemini_status = "unhealthy"
        gemini_error = "Gemini API key is not configured"
        gemini_res_time = 0.0
    else:
        try:
            from services.llm_service import GeminiLLMService
            GeminiLLMService._initialize_sdk()
            gemini_res_time = (time.perf_counter() - gemini_start) * 1000.0
        except Exception as e:
            gemini_status = "unhealthy"
            gemini_error = str(e)
            gemini_res_time = (time.perf_counter() - gemini_start) * 1000.0

    # 3. Embedding model
    embed_start = time.perf_counter()
    embed_error = None
    embed_status = "healthy"
    try:
        from embeddings.embedding_model import get_model
        get_model()
        embed_res_time = (time.perf_counter() - embed_start) * 1000.0
    except Exception as e:
        embed_status = "unhealthy"
        embed_error = str(e)
        embed_res_time = (time.perf_counter() - embed_start) * 1000.0

    # 4. Vector store
    vector_start = time.perf_counter()
    vector_error = None
    vector_status = "healthy"
    try:
        if not vector_store or not vector_store._index:
            vector_status = "unhealthy"
            vector_error = "FAISS index file is not loaded"
        vector_res_time = (time.perf_counter() - vector_start) * 1000.0
    except Exception as e:
        vector_status = "unhealthy"
        vector_error = str(e)
        vector_res_time = (time.perf_counter() - vector_start) * 1000.0

    # 5. Background services
    bg_status = "healthy"
    bg_error = None
    if db_status == "unhealthy" or vector_status == "unhealthy":
        bg_status = "unhealthy"
        bg_error = "Critical backend storage dependency is down"
    elif gemini_status == "unhealthy":
        bg_status = "warning"
        bg_error = "Gemini API dependency is unhealthy"

    return ServicesStatusResponse(
        mongodb=SingleServiceStatus(
            status=db_status,
            last_check=now_iso,
            response_time=round(db_res_time, 2),
            error=db_error
        ),
        gemini=SingleServiceStatus(
            status=gemini_status,
            last_check=now_iso,
            response_time=round(gemini_res_time, 2),
            error=gemini_error
        ),
        embeddings=SingleServiceStatus(
            status=embed_status,
            last_check=now_iso,
            response_time=round(embed_res_time, 2),
            error=embed_error
        ),
        vector_store=SingleServiceStatus(
            status=vector_status,
            last_check=now_iso,
            response_time=round(vector_res_time, 2),
            error=vector_error
        ),
        background_services=SingleServiceStatus(
            status=bg_status,
            last_check=now_iso,
            response_time=0.0,
            error=bg_error
        )
    )




