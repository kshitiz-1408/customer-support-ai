from typing import List, Optional
from fastapi import APIRouter, status, HTTPException
from models.chat import ChatQuery, ChatResponse, ConversationCreate, ConversationResponse, MessageResponse
from agents.intent_detector import detect_intent
from agents.router import route_query
from agents.conversation_memory import ConversationMemory
from utils.logging import logger

router = APIRouter()


@router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def process_chat(query: ChatQuery):
    """
    Submits a message query to the Multi-Agent system.
    Coordinated Flow:
    1. Resolve/create conversation thread in MongoDB.
    2. Persist the incoming user message to the messages collection.
    3. Detect intent using intent keyword heuristics.
    4. Fetch context and run RAG grounded response generation.
    5. Save the assistant's generated response to the database.
    6. Return unified API response to client.
    """
    logger.info(f"Incoming chat request at api/v1: '{query.message}'")
    
    try:
        # 1. Resolve or create conversation
        conversation_id = ConversationMemory.get_or_create_conversation(
            conversation_id=query.conversation_id,
            session_id=query.session_id
        )
        
        # 2. Persist incoming user message
        ConversationMemory.add_message(
            conversation_id=conversation_id,
            role="user",
            content=query.message
        )
        
        # 3. Detect intent using Intent Detector
        intent_data = detect_intent(query.message)
        intent = intent_data["intent"]
        logger.debug(f"Detected intent category: {intent}")
        
        if intent == "unknown":
            # Check conversation history to verify if this is an active follow-up query
            history = ConversationMemory.get_conversation_history(conversation_id)
            # Exclude current user message turn when checking for prior conversational logs
            if len(history) > 1:
                logger.info(f"Unknown intent query '{query.message}' detected as follow-up for active conversation '{conversation_id}'. Routing to FAQ Agent.")
                intent = "faq"
            else:
                logger.warning(f"Unable to resolve intent for query: '{query.message}'")
                # Persist assistant fallback response
                ConversationMemory.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content="Please clarify your question.",
                    intent="unknown"
                )
                return ChatResponse(
                    intent="unknown",
                    message="Please clarify your question.",
                    conversation_id=conversation_id
                )
            
        # 4. Route query and trigger grounded response generation
        routing_result = route_query(intent, query.message, conversation_id, query.session_id)
        response_text = routing_result.get("response")
        sources_list = routing_result.get("sources")
        
        agent_names = {
            "billing": "Billing Agent",
            "technical": "Technical Agent",
            "product": "Product Agent",
            "complaint": "Complaint Agent",
            "faq": "FAQ Agent"
        }
        agent_name = agent_names.get(intent, "FAQ Agent")
        
        logger.info(f"Successfully routed to {agent_name} at api/v1. Return output generated.")
        return ChatResponse(
            intent=intent,
            agent=agent_name,
            response=response_text,
            sources=sources_list,
            conversation_id=conversation_id
        )
    except Exception as e:
        logger.error(f"Internal exception during v1 chat routing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your chat request."
        )


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED, tags=["Conversations"])
def create_conversation(conv_in: ConversationCreate):
    """Create a new conversation thread thread for tracking state."""
    return ConversationMemory.create_conversation(
        session_id=conv_in.session_id,
        user_id=conv_in.user_id,
        title=conv_in.title
    )


@router.get("/conversations", response_model=List[ConversationResponse], status_code=status.HTTP_200_OK, tags=["Conversations"])
def list_conversations(session_id: Optional[str] = None, user_id: Optional[str] = None):
    """List active conversation threads, optionally filtering by session_id or user_id."""
    return ConversationMemory.list_conversations(
        user_id=user_id,
        session_id=session_id
    )


@router.get("/conversations/{conversation_id}/history", response_model=List[MessageResponse], status_code=status.HTTP_200_OK, tags=["Conversations"])
def get_conversation_history(conversation_id: str, limit: int = 20):
    """Retrieve the chronological message logs for a conversation thread."""
    history = ConversationMemory.get_conversation_history(conversation_id, limit=limit)
    if not history and not ConversationMemory.get_conversation(conversation_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation thread '{conversation_id}' not found."
        )
    return history
