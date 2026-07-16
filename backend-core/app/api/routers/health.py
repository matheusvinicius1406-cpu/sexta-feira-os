"""Health & status — no auth (loopback only anyway)."""
from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import settings
from app.core.di import get_kernel

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health():
    kernel = get_kernel()
    brain_ok = await kernel.brain.health() if kernel.brain else False
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "brain_online": brain_ok,
        "brain_model": settings.brain_model,
        "access_mode": settings.access_mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
