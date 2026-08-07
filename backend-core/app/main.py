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
#
# TWO files used to be in play, and the wrong one won. This loaded
# `backend-core/.env` while app/core/config.py declares the repo-root `.env` as
# its `env_file` — and because load_dotenv writes real environment variables,
# which outrank pydantic's env_file, the backend-core copy silently overrode the
# canonical one for every key it happened to define. Editing the file the config
# points at changed nothing, with no error and no log line: the kernel booted on
# BRAIN_MODEL=llava:7b long after the root .env said otherwise.
#
# So the root file is loaded LAST, with override, and is now genuinely the one
# that decides. The backend-core copy is still read first, so a key that exists
# only there (a VAULT_KEY, a pinned JWT secret) is not lost — but it can no
# longer contradict the file the owner is told to edit.
_LEGACY_ENV = Path(__file__).resolve().parents[1] / ".env"
_ENV = Path(__file__).resolve().parents[2] / ".env"

if _LEGACY_ENV.exists():
    load_dotenv(_LEGACY_ENV)
load_dotenv(_ENV, override=True)

import logging  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.api.routers import (  # noqa: E402
    action,
    auth,
    automation,
    briefing,
    chat,
    connectors,
    decision,
    directors,
    evals,
    events,
    health,
    journal,
    learning,
    memory,
    obsidian,
    optimize,
    planning,
    pulse,
    radio,
    schedule,
    system,
    timetrack,
    vision,
    voice,
    world,
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

    # Start gRPC server alongside FastAPI
    if settings.grpc_enabled:
        from app.grpc.server import get_grpc_server  # noqa: E402
        try:
            await get_grpc_server().start()
            logger.info("🧠 gRPC server started on port %d", settings.grpc_port)
        except Exception as exc:
            logger.warning("⚠️ gRPC server failed to start: %s", exc)

    yield

    # Shutdown gRPC first, then kernel
    if settings.grpc_enabled:
        from app.grpc.server import get_grpc_server  # noqa: E402
        await get_grpc_server().stop()
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
app.include_router(world.router)
app.include_router(events.router)
app.include_router(planning.router)
app.include_router(decision.router)
app.include_router(learning.router)
app.include_router(briefing.router)
app.include_router(directors.router)
app.include_router(journal.router)
app.include_router(timetrack.router)
app.include_router(evals.router)
app.include_router(voice.router)
app.include_router(radio.router)
app.include_router(automation.router)
app.include_router(action.router)
app.include_router(schedule.router)
app.include_router(connectors.router)
app.include_router(vision.router)
app.include_router(obsidian.router)
app.include_router(system.router)
app.include_router(optimize.router)
app.include_router(pulse.router)


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
