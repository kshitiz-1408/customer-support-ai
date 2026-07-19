import time
from datetime import datetime, timezone
STARTUP_TIME = datetime.now(timezone.utc)
from contextlib import asynccontextmanager
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
from middleware.observability import ObservabilityMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Production-ready resource lifecycle manager.
    Handles startup pre-warming, connection pool setups, and clean shutdown releases.
    """
    logger.info("Initializing application resources via lifespan hook...")
    start_time = time.perf_counter()
    
    # 1. MongoDB pool setup
    mongo_start = time.perf_counter()
    try:
        connect_db()
        logger.info(f"MongoDB connection initialized in {(time.perf_counter() - mongo_start)*1000:.2f}ms")
    except Exception as e:
        logger.critical(f"Critical error during startup MongoDB initialization: {str(e)}", exc_info=True)
        # We do not crash here so the readiness probe can report specific connection errors
        
    # 2. Embedding Model pre-warming
    embed_start = time.perf_counter()
    try:
        from embeddings.embedding_model import get_model
        # Pre-loads SentenceTransformers cache into memory
        get_model()
        logger.info(f"SentenceTransformers embedding model warmed up in {(time.perf_counter() - embed_start)*1000:.2f}ms")
    except Exception as e:
        logger.error(f"Error pre-warming embedding model on startup: {str(e)}", exc_info=True)
        
    # 3. RAG pipeline setup
    rag_start = time.perf_counter()
    try:
        initialize_rag_pipeline()
        logger.info(f"RAG pipeline initialized in {(time.perf_counter() - rag_start)*1000:.2f}ms")
    except Exception as e:
        logger.error(f"Error initializing RAG pipeline on startup: {str(e)}", exc_info=True)
        
    # 4. Gemini SDK client pre-warming
    gemini_start = time.perf_counter()
    try:
        from services.llm_service import GeminiLLMService
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "PASTE_YOUR_ACTUAL_API_KEY_HERE":
            GeminiLLMService._initialize_sdk()
            logger.info(f"Gemini client initialized in {(time.perf_counter() - gemini_start)*1000:.2f}ms")
    except Exception as e:
        logger.error(f"Error initializing Gemini SDK on startup: {str(e)}", exc_info=True)
        
    total_startup_ms = (time.perf_counter() - start_time) * 1000
    logger.info(f"Application startup sequence completed in {total_startup_ms:.2f}ms")
    
    app.state.startup_timings = {
        "total_ms": total_startup_ms,
        "mongo_init_ms": (time.perf_counter() - mongo_start) * 1000,
        "embedding_load_ms": (time.perf_counter() - embed_start) * 1000,
        "rag_init_ms": (time.perf_counter() - rag_start) * 1000,
        "gemini_init_ms": (time.perf_counter() - gemini_start) * 1000,
    }
    
    # 5. Bootstrap initial administrator account (DEVELOPMENT ONLY)
    import os
    if settings.APP_ENV != "production" and os.getenv("DISABLE_ADMIN_BOOTSTRAP", "").lower() != "true":
        try:
            from services.user_service import UserService
            from models.user import UserCreate, UserRole, UserUpdate
            from database.database import get_users_collection
            import secrets
            import string
            from pathlib import Path
            import json
            
            coll = get_users_collection()
            admin_count = 0
            if hasattr(coll, "count_documents"):
                admin_count = coll.count_documents({"role": UserRole.ADMIN})
            else:
                admin_count = len(list(coll.find({"role": UserRole.ADMIN})))
                
            if admin_count == 0:
                logger.warning("[BOOTSTRAP] No administrator accounts detected. Bootstrapping initial admin (DEVELOPMENT ONLY)...")
                
                alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                while True:
                    pwd = "".join(secrets.choice(alphabet) for _ in range(16))
                    has_upper = any(c.isupper() for c in pwd)
                    has_lower = any(c.islower() for c in pwd)
                    has_digit = any(c.isdigit() for c in pwd)
                    has_spec = any(c in "!@#$%^&*" for c in pwd)
                    if has_upper and has_lower and has_digit and has_spec:
                        break
                        
                admin_email = "admin@example.com"
                
                existing_user = UserService.get_user_by_email(admin_email)
                if existing_user:
                    UserService.update_user(existing_user.id, UserUpdate(role=UserRole.ADMIN))
                    logger.warning(f"[BOOTSTRAP] Promoted existing user '{admin_email}' to administrator.")
                else:
                    UserService.create_user(UserCreate(
                        email=admin_email,
                        full_name="Initial Admin Bootstrap",
                        password=pwd,
                        role=UserRole.ADMIN
                    ))
                    
                logger.warning("==================================================================")
                logger.warning("[BOOTSTRAP] INITIAL ADMINISTRATOR ACCOUNT CREATED (DEVELOPMENT ONLY)")
                logger.warning(f"[BOOTSTRAP] Email: {admin_email}")
                logger.warning(f"[BOOTSTRAP] Password: {pwd}")
                logger.warning("[BOOTSTRAP] Please change this password immediately in production settings!")
                logger.warning("==================================================================")
                
                # Write to artifacts directory so our report can read and display it
                artifacts_dir = Path("C:/Users/HP/.gemini/antigravity-ide/brain/19a93036-5576-4401-8a01-827787595b36")
                if artifacts_dir.exists():
                    creds_file = artifacts_dir / "bootstrap_credentials.json"
                    with open(creds_file, "w") as f:
                        json.dump({
                            "email": admin_email,
                            "password": pwd,
                            "role": "admin"
                        }, f)
        except Exception as e:
            logger.error(f"[BOOTSTRAP] Failed to bootstrap administrator: {str(e)}", exc_info=True)

    yield
    
    # Shutdown tasks
    logger.info("Releasing connection pools and resources via lifespan hook...")
    try:
        close_db()
        logger.info("Database connection pools closed successfully.")
    except Exception as e:
        logger.error(f"Error during shutdown resource cleanup: {str(e)}", exc_info=True)


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Customer Support AI Backend - restructured flat layout.",
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Register request correlation tracing middleware
app.add_middleware(ObservabilityMiddleware)

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


@app.get("/health/live", tags=["General"])
def liveness_check():
    """
    Liveness probe. Returns HTTP 200 as long as the process is alive.
    Does not run expensive downstream dependency checks.
    """
    return {
        "status": "ok",
        "timestamp": time.time()
    }


@app.get("/health/ready", tags=["General"])
def readiness_check():
    """
    Readiness probe. Checks MongoDB connection, FAISS store index file, and
    embedding model cache state before declaring ready.
    """
    from database import database
    from embeddings import embedding_model
    from rag.rag_pipeline import vector_store
    
    errors = {}
    
    # 1. MongoDB check
    mongodb_status = "unconfigured"
    if not database.db_client:
        try:
            connect_db()
        except Exception:
            pass

    if database.db_client:
        try:
            database.db_client.admin.command("ping")
            mongodb_status = "connected"
        except Exception as e:
            mongodb_status = "unavailable"
            errors["mongodb"] = f"Failed to ping MongoDB: {str(e)}"
    else:
        mongodb_status = "unavailable"
        errors["mongodb"] = "MongoDB client pool not initialized"
        
    # 2. FAISS Index check
    try:
        if not vector_store or not vector_store._index:
            errors["faiss"] = "FAISS vector store not initialized"
    except Exception as e:
        errors["faiss"] = str(e)
        
    # 3. Embeddings model cache check
    try:
        from embeddings.embedding_model import _model
        if _model is None:
            embedding_model.get_model()
    except Exception as e:
        errors["embeddings"] = f"Embedding model failed to load: {str(e)}"
        
    if errors:
        logger.error(f"Readiness check failed: {errors}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "version": settings.VERSION,
                "database": mongodb_status,
                "errors": errors
            }
        )
        
    startup_timings = getattr(app.state, "startup_timings", {})
    return {
        "status": "ready",
        "version": settings.VERSION,
        "database": mongodb_status,
        "faiss_vectors": vector_store._index.ntotal if vector_store and vector_store._index else 0,
        "startup_timings": startup_timings
    }


@app.get("/health", tags=["General"])
def health_check():
    """
    Service health check endpoint including lightweight database health.
    Preserved for backwards compatibility with existing clients.
    """
    from database import database
    mongodb_status = "unconfigured"
    mongodb_ping_ms = 0.0
    if database.db_client:
        try:
            start_ping = time.perf_counter()
            database.db_client.admin.command("ping")
            mongodb_ping_ms = (time.perf_counter() - start_ping) * 1000.0
            mongodb_status = "connected"
        except Exception:
            mongodb_status = "unavailable"
            
    logger.info({
        "event": "mongodb_ping",
        "duration_ms": mongodb_ping_ms,
        "status": mongodb_status
    })
            
    return {
        "status": "ok",
        "version": settings.VERSION,
        "database": mongodb_status,
        "database_ping_ms": mongodb_ping_ms
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
