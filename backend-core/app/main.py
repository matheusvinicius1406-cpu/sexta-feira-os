"""
Main FastAPI application for Sexta-Feira OS Backend
Jarvis Stable Core Boot
"""

# =========================
# BOOTSTRAP CRÍTICO (.env)
# =========================
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

# =========================
# IMPORTS (APÓS ENV LOADED)
# =========================
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.di import (
    initialize_services,
    get_conversation_pipeline,
    get_ai_orchestrator
)

from app.db.database import Base, engine

from app.api.routers import (
    health,
    auth,
    chat,
    memory,
    jarvis,
    chat_v2,
    voice
)

from app.api import tool_router


# =========================
# LOGGING
# =========================
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("jarvis")


# =========================
# LIFESPAN (BOOT CONTROLLED)
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")

    # Database init
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database ready")
    except Exception as e:
        logger.critical(f"DB init failed: {e}")
        raise

    # Core services init
    try:
        await initialize_services()
        logger.info("Jarvis core initialized")
    except Exception as e:
        logger.critical(f"CRITICAL: Service initialization failed: {e}")
        raise

    yield

    logger.info("Shutting down Jarvis...")


# =========================
# APP INIT
# =========================
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Sexta-Feira OS - Jarvis AI Core",
    lifespan=lifespan
)


# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# DEPENDENCY INJECTION FIX
# =========================
async def get_pipeline():
    return get_conversation_pipeline()


async def get_orchestrator():
    return get_ai_orchestrator()


# CORREÇÃO: overrides corretos (SEM lambda bugado)
app.dependency_overrides[get_conversation_pipeline] = get_pipeline
app.dependency_overrides[get_ai_orchestrator] = get_orchestrator


# =========================
# ROUTERS
# =========================
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(jarvis.router)
app.include_router(chat_v2.router)
app.include_router(tool_router.router)
app.include_router(voice.router)


# =========================
# EXCEPTION HANDLER
# =========================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation Error",
            "detail": str(exc),
            "status_code": 400
        }
    )


# =========================
# ROOT
# =========================
@app.get("/")
async def root():
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


# =========================
# ENTRYPOINT
# =========================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug
    )