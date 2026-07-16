"""
Sexta-Feira OS — Private Local Cognitive Kernel.

One brain, running on your machine. Many trusted bodies (phone, car, glasses,
watch) connect to it over your private network. No cloud. No other LLM. No
data ever leaves this host.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load .env before importing settings-dependent modules.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import logging  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.api.routers import (  # noqa: E402
    action,
    auth,
    automation,
    chat,
    health,
    memory,
    schedule,
    voice,
)
from app.core.config import settings  # noqa: E402
from app.core.di import get_kernel  # noqa: E402
from app.db.migrations import run_migrations  # noqa: E402

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("sexta-feira")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 %s v%s (access=%s)", settings.app_name, settings.app_version, settings.access_mode)
    run_migrations()  # bring the schema up to date (versioned, Alembic)
    await get_kernel().start()
    yield
    await get_kernel().stop()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Segundo cérebro pessoal, local e privado. Roda só na sua máquina.",
    lifespan=lifespan,
)

# CORS matters only for browser clients; native apps (phone/car/glasses) ignore it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(voice.router)
app.include_router(automation.router)
app.include_router(action.router)
app.include_router(schedule.router)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "spirit": "Alfred / JARVIS — só seu, só local.",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
    )
