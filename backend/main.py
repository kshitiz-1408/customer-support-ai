from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api.router import api_router
from config.config import settings
from utils.errors import register_error_handlers
from utils.logging import logger

from database.database import connect_db, close_db
from models.chat import ChatQuery, ChatResponse
from agents.intent_detector import detect_intent
from agents.router import route_query
from rag.rag_pipeline import initialize_rag_pipeline

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Customer Support AI Backend - restructured flat layout.",
    version=settings.VERSION,
    debug=settings.DEBUG,
)

@app.on_event("startup")
def startup_event():
    """
    Triggers RAG pipeline initialization and MongoDB connection pool setup on app startup.
    """
    # 1. Setup MongoDB connection pool
    try:
        connect_db()
    except Exception as e:
        logger.error(f"Error during startup MongoDB initialization: {str(e)}", exc_info=True)
        
    # 2. Setup RAG pipeline
    try:
        initialize_rag_pipeline()
    except Exception as e:
        logger.error(f"Error during startup RAG pipeline initialization: {str(e)}", exc_info=True)


@app.on_event("shutdown")
def shutdown_event():
    """
    Closes database client pools cleanly during application shutdown.
    """
    try:
        close_db()
    except Exception as e:
        logger.error(f"Error during shutdown connection cleanup: {str(e)}", exc_info=True)


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
    Service health check endpoint including lightweight database health.
    """
    from database import database
    mongodb_status = "unconfigured"
    if database.db_client:
        try:
            database.db_client.admin.command("ping")
            mongodb_status = "connected"
        except Exception:
            mongodb_status = "unavailable"
            
    return {
        "status": "ok",
        "version": settings.VERSION,
        "database": mongodb_status
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
    Delegates to versioned v1 endpoint to reuse orchestration logic.
    """
    from api.v1.endpoints.chat import process_chat
    return process_chat(query)
