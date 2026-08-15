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
# a BRAIN_MODEL from the other copy long after the root .env said otherwise.
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

# The master credentials (JWT_SECRET_KEY, VAULT_KEY, OWNER_PASSWORD,
# DEVICE_PAIRING_CODE) live in an OS-encrypted store (Windows DPAPI), NOT in
# the plaintext .env. This MUST run before Settings is built below — it feeds
# the values into os.environ so pydantic picks them up exactly as if they had
# come from .env, and on first run it migrates the plaintext copies into the
# store. See app/core/secrets.py.
from app.core.secrets import ensure_secrets_loaded  # noqa: E402

ensure_secrets_loaded()

import logging  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.api.routers import (  # noqa: E402
    action,
    auth,
    automation,
    briefing,
    browser,
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
    network,
    obsidian,
    optimize,
    planning,
    pulse,
    radio,
    schedule,
    security,
    system,
    terminal,
    timetrack,
    vision,
    voice,
    world,
)
from app.core.config import settings  # noqa: E402
from app.core.di import get_kernel  # noqa: E402
from app.core.security import (  # noqa: E402
    HostGuardMiddleware,
    RedactingFormatter,
    SecurityHeadersMiddleware,
)
from app.db.migrations import run_migrations  # noqa: E402

logging.basicConfig(level=settings.log_level)
# Every handler this process owns redacts credential query params before the
# line hits disk/console — the access log prints ?token=... in full otherwise.
for handler in logging.root.handlers:
    handler.setFormatter(RedactingFormatter())
logger = logging.getLogger("sexta-feira")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 %s v%s (access=%s)", settings.app_name, settings.app_version, settings.access_mode)
    if settings.auth_dev_bypass:
        logger.warning(
            "⚠️ AUTH_DEV_BYPASS está LIGADO: qualquer processo nesta máquina lê o kernel "
            "sem token (memórias, diário, automações). O HUD já autentica sozinho — "
            "desligue a flag no .env a menos que tenha um motivo concreto."
        )
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
# Hardened browser-facing headers (CSP, nosniff, frame/ref/policy). Added AFTER
# CORS so it wraps everything.
app.add_middleware(SecurityHeadersMiddleware)
# Anti-DNS-rebinding: only enforced while the dev auth bypass is on.
app.add_middleware(HostGuardMiddleware)

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
app.include_router(security.router)
app.include_router(connectors.router)
app.include_router(vision.router)
app.include_router(obsidian.router)
app.include_router(system.router)
app.include_router(network.router)
app.include_router(browser.router)
app.include_router(terminal.router)
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


# uvicorn's stock access log prints the full request line — including the
# device JWT the action WebSocket carries in ?token=... Swap in the redacting
# formatters so no token ever reaches the log.
_UVICORN_LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "app.core.security.RedactingDefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": None,
        },
        "access": {
            "()": "app.core.security.RedactingAccessFormatter",
            "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
    },
}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
        log_config=_UVICORN_LOG_CONFIG,
    )
