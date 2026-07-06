from fastapi import APIRouter, status, HTTPException
from models.chat import ChatQuery, ChatResponse
from agents.intent_detector import detect_intent
from agents.router import route_query
from utils.logging import logger

router = APIRouter()

@router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def process_chat(query: ChatQuery):
    """
    Submits a message query to the Multi-Agent system.
    Coordinated Flow:
    1. Detect intent using Intent Detector.
    2. Route query to the correct support agent based on intent.
    """
    logger.info(f"Incoming chat request at api/v1: '{query.message}'")
    
    try:
        intent_data = detect_intent(query.message)
        intent = intent_data["intent"]
        logger.debug(f"Detected intent category: {intent}")
        
        if intent == "unknown":
            logger.warning(f"Unable to resolve intent for query: '{query.message}'")
            return ChatResponse(
                intent="unknown",
                message="Please clarify your question."
            )
            
        routing_result = route_query(intent, query.message)
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
            sources=sources_list
        )
    except Exception as e:
        logger.error(f"Internal exception during v1 chat routing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your chat request."
        )
