"""
Main FastAPI application for Sexta-Feira OS Backend
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.di import initialize_services, get_conversation_pipeline, get_ai_orchestrator
from app.db.database import Base, engine
from app.api.routers import health, auth, chat, memory, jarvis

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__) 

# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    
    # Create tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
    
    # Initialize services
    try:
        await initialize_services()
        logger.info("✅ Services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="An advanced personal AI assistant platform",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency overrides for injection
async def get_pipeline():
    """Inject conversation pipeline"""
    return get_conversation_pipeline()

async def get_orchestrator():
    """Inject AI orchestrator"""
    return get_ai_orchestrator()

app.dependency_overrides[lambda: None] = get_pipeline

# Include routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(jarvis.router)

# Include new chat_v2 router with streaming
from app.api.routers import chat_v2
app.include_router(chat_v2.router)

# Include tools router
from app.api.routers import tools
app.include_router(tools.router)

# Include voice router
from app.api.routers import voice
app.include_router(voice.router)

# Include android router
from app.api.routers import android
app.include_router(android.router)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors"""
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation Error",
            "detail": str(exc),
            "status_code": 400
        }
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs",
        "health": "/api/v1/health",
        "api": {
            "chat_v1": "/api/v1/chat",
            "chat_v2_rest": "/api/v2/chat/message",
            "chat_v2_ws": "ws://localhost:8000/api/v2/chat/ws/{user_id}",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug
    )

