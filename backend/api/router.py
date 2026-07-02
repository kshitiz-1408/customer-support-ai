from fastapi import APIRouter
from api.v1.endpoints import kb, tickets, chat

api_router = APIRouter()

# Combine routers with prefix tags
api_router.include_router(tickets.router, prefix="/tickets", tags=["Tickets"])
api_router.include_router(kb.router, prefix="/kb", tags=["Knowledge Base"])
api_router.include_router(chat.router, prefix="/chat", tags=["Agent Chat"])
