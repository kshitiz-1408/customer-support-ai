import uuid
from typing import List, Optional
from fastapi import APIRouter, status, HTTPException, Depends
from models.chat import ChatQuery, ChatResponse, ConversationCreate, ConversationResponse, MessageResponse
from agents.intent_detector import detect_intent
from agents.router import route_query
from agents.conversation_memory import ConversationMemory
from utils.logging import logger
from utils.tracing import pipeline_tracker_var, trace_stage
from api.deps import get_current_user

router = APIRouter()


@router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def process_chat(query: ChatQuery, current_user = Depends(get_current_user)):
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
    import time
    start_time = time.perf_counter()
    
    logger.info({
        "event": "chat_request_received",
        "conversation_id": query.conversation_id,
        "message_length": len(query.message) if query.message else 0
    })
    
    tracker = pipeline_tracker_var.get()
    
    try:
        with trace_stage("chat_endpoint"):
            # 1. Resolve or create conversation
            conversation_id = None
            with trace_stage("conversation_resolution"):
                if query.conversation_id:
                    conv = ConversationMemory.get_conversation(query.conversation_id)
                    if not conv:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Conversation thread '{query.conversation_id}' not found."
                        )
                    # Check ownership
                    if conv.get("user_id") and conv["user_id"] != current_user.id:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied to this conversation thread."
                        )
                    conversation_id = query.conversation_id
                else:
                    conversation_id = ConversationMemory.get_or_create_conversation(
                        conversation_id=None,
                        session_id=query.session_id,
                        user_id=current_user.id
                    )
            
            if tracker:
                tracker.conversation_id = conversation_id
                
            logger.info({
                "event": "conversation_resolved",
                "conversation_id": conversation_id
            })
            
            # 2. Persist incoming user message
            try:
                with trace_stage("user_persistence"):
                    ConversationMemory.add_message(
                        conversation_id=conversation_id,
                        role="user",
                        content=query.message,
                        user_id=current_user.id
                    )
            except Exception as db_err:
                logger.error({
                    "event": "persistence_failed",
                    "operation": "persist_user_message",
                    "conversation_id": conversation_id,
                    "exception_type": type(db_err).__name__,
                    "error_detail": str(db_err)
                })
                
            # 3. Detect intent using Intent Detector
            with trace_stage("intent_detection"):
                intent_data = detect_intent(query.message)
                intent = intent_data["intent"]
            
            if tracker:
                tracker.intent = intent
                
            logger.info({
                "event": "intent_detected",
                "conversation_id": conversation_id,
                "intent": intent
            })
            
            # Handle unknown/fallback intent
            if intent == "unknown":
                # Check conversation history to verify if this is an active follow-up query
                history = []
                try:
                    # History loading as part of fallback check
                    with trace_stage("history_loading"):
                        history = ConversationMemory.get_conversation_history(conversation_id)
                except Exception as db_err:
                    logger.error({
                        "event": "persistence_failed",
                        "operation": "get_history_for_fallback",
                        "conversation_id": conversation_id,
                        "exception_type": type(db_err).__name__,
                        "error_detail": str(db_err)
                    })
                    
                # Exclude current user message turn when checking for prior conversational logs
                if len(history) > 1:
                    logger.info({
                        "event": "intent_detected",
                        "conversation_id": conversation_id,
                        "intent": "faq",
                        "detail": "resolved as follow-up faq"
                    })
                    intent = "faq"
                    if tracker:
                        tracker.intent = intent
                else:
                    logger.warning({
                        "event": "intent_resolution_failed",
                        "conversation_id": conversation_id,
                        "detail": "Unknown intent query, sending clarification prompt."
                    })
                    # Persist assistant fallback response
                    try:
                        with trace_stage("assistant_persistence"):
                            ConversationMemory.add_message(
                                conversation_id=conversation_id,
                                role="assistant",
                                content="Please clarify your question.",
                                intent="unknown",
                                user_id=current_user.id,
                                confidence_score=0.5
                            )
                    except Exception as db_err:
                        logger.error({
                            "event": "persistence_failed",
                            "operation": "persist_clarification_response",
                            "conversation_id": conversation_id,
                            "exception_type": type(db_err).__name__,
                            "error_detail": str(db_err)
                        })
                    
                    agent_name = "FAQ Agent"
                    if tracker:
                        tracker.agent = agent_name
                        
                    with trace_stage("response_serialization"):
                        res_obj = ChatResponse(
                            intent="unknown",
                            agent=agent_name,
                            message="Please clarify your question.",
                            conversation_id=conversation_id
                        )
                    return res_obj
            
            # 4. Route query and trigger grounded response generation
            agent_names = {
                "billing": "Billing Agent",
                "technical": "Technical Agent",
                "product": "Product Agent",
                "complaint": "Complaint Agent",
                "faq": "FAQ Agent"
            }
            agent_name = agent_names.get(intent, "FAQ Agent")
            if tracker:
                tracker.agent = agent_name
                
            routing_result = None
            with trace_stage("agent_routing"):
                routing_result = route_query(intent, query.message, conversation_id, query.session_id)
                
            response_text = routing_result.get("response")
            sources_list = routing_result.get("sources")
            
            if tracker:
                tracker.retrieval_count = len(sources_list) if sources_list else 0
            
            logger.info({
                "event": "agent_selected",
                "conversation_id": conversation_id,
                "agent": agent_name
            })
            
            # 5. Persist assistant response
            persistence_success = True
            conf = 0.85
            if sources_list:
                conf = sum(s.get("score", 0.90) for s in sources_list) / len(sources_list)
            conf = max(0.1, min(1.0, conf))
            try:
                with trace_stage("assistant_persistence"):
                    ConversationMemory.add_message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=response_text or "",
                        intent=intent,
                        agent=agent_name,
                        sources=sources_list,
                        user_id=current_user.id,
                        confidence_score=conf
                    )
            except Exception as db_err:
                persistence_success = False
                logger.error({
                    "event": "persistence_failed",
                    "operation": "persist_assistant_response",
                    "conversation_id": conversation_id,
                    "exception_type": type(db_err).__name__,
                    "error_detail": str(db_err)
                })
                
            logger.info({
                "event": "assistant_message_persisted",
                "conversation_id": conversation_id,
                "persistence_success": persistence_success
            })
            
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info({
                "event": "chat_request_completed",
                "conversation_id": conversation_id,
                "intent": intent,
                "agent": agent_name,
                "retrieval_count": len(sources_list) if sources_list else 0,
                "duration_ms": duration_ms
            })
            
            with trace_stage("response_serialization"):
                res_obj = ChatResponse(
                    intent=intent,
                    agent=agent_name,
                    response=response_text,
                    sources=sources_list,
                    conversation_id=conversation_id
                )
            return res_obj
            
    except HTTPException as http_exc:
        # Re-raise HTTPExceptions (like 404) directly
        raise http_exc
    except Exception as e:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.error({
            "event": "chat_request_failed",
            "exception_type": type(e).__name__,
            "error_detail": str(e),
            "duration_ms": duration_ms
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your chat request."
        )


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED, tags=["Conversations"])
def create_conversation(conv_in: ConversationCreate, current_user = Depends(get_current_user)):
    """Create a new conversation thread thread for tracking state."""
    return ConversationMemory.create_conversation(
        session_id=conv_in.session_id,
        user_id=current_user.id,
        title=conv_in.title
    )


@router.get("/conversations", response_model=List[ConversationResponse], status_code=status.HTTP_200_OK, tags=["Conversations"])
def list_conversations(session_id: Optional[str] = None, current_user = Depends(get_current_user)):
    """List active conversation threads, optionally filtering by session_id."""
    return ConversationMemory.list_conversations(
        user_id=current_user.id,
        session_id=session_id
    )


@router.get("/conversations/{conversation_id}/history", response_model=List[MessageResponse], status_code=status.HTTP_200_OK, tags=["Conversations"])
def get_conversation_history(conversation_id: str, limit: int = 20, current_user = Depends(get_current_user)):
    """Retrieve the chronological message logs for a conversation thread, validating ownership."""
    conv = ConversationMemory.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation thread '{conversation_id}' not found."
        )
    # Check ownership
    if conv.get("user_id") and conv["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation thread."
        )
        
    history = ConversationMemory.get_conversation_history(conversation_id, limit=limit)
    return history

