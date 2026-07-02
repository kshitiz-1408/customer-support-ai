from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api.router import api_router
from config.config import settings
from utils.errors import register_error_handlers
from utils.logging import logger

from models.chat import ChatQuery, ChatResponse
from agents.intent_detector import detect_intent
from agents.router import route_query

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Customer Support AI Backend - restructured flat layout.",
    version=settings.VERSION,
    debug=settings.DEBUG,
)

# Initialize CORS configuration
if settings.ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.ALLOWED_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS middleware added with allowed origins: {settings.ALLOWED_ORIGINS}")
else:
    logger.warning("No CORS allowed origins setup in settings. External queries will fail.")

# Register global error handling middleware
register_error_handlers(app)

# Include APIs
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["General"])
def index():
    """
    Service landing page description.
    """
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API portal.",
        "docs_url": "/docs",
        "health_url": "/health",
        "version_url": "/version",
    }


@app.get("/health", tags=["General"])
def health_check():
    """
    Service health check endpoint.
    Returns:
        { "status": "ok", "version": "1.0" }
    """
    return {
        "status": "ok",
        "version": settings.VERSION
    }


@app.get("/version", tags=["General"])
def get_version():
    """
    Returns current API service version.
    """
    return {
        "version": settings.VERSION
    }


@app.post("/chat", response_model=ChatResponse, tags=["General"])
def chat_root(query: ChatQuery):
    """
    Direct root POST endpoint for support chats.
    Flow: Input message -> Intent Detector -> Agent Router -> Dispatched Agent Response.
    """
    logger.info(f"Incoming chat request at root: '{query.message}'")
    
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
            
        agent_response = route_query(intent, query.message)
        
        agent_names = {
            "billing": "Billing Agent",
            "technical": "Technical Agent",
            "product": "Product Agent",
            "complaint": "Complaint Agent",
            "faq": "FAQ Agent"
        }
        agent_name = agent_names.get(intent, "FAQ Agent")
        
        logger.info(f"Successfully routed to {agent_name}. Return output generated.")
        return ChatResponse(
            intent=intent,
            agent=agent_name,
            response=agent_response
        )
    except Exception as e:
        logger.error(f"Internal exception during chat routing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your chat request."
        )
