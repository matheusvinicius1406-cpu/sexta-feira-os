"""
Dependency wiring for the kernel. One brain, one memory, one cognition loop.
Also bootstraps the single owner on first boot from environment variables.
"""
from __future__ import annotations

import logging
import uuid

from app.auth.jwt import hash_password
from app.automation.n8n import N8nClient
from app.brain.cognition import Cognition
from app.brain.engine import LocalBrain
from app.brain.memory import PersistentMemory
from app.brain.tools import ToolKit
from app.core.config import settings
from app.db.database import SessionLocal
from app.models.models import Owner
from app.voice.box import VoiceBox

logger = logging.getLogger("sexta-feira.di")


class Kernel:
    """Holds the singletons that make up the running brain."""

    def __init__(self) -> None:
        self.brain: LocalBrain | None = None
        self.memory: PersistentMemory | None = None
        self.cognition: Cognition | None = None
        self.voice: VoiceBox | None = None
        self.automations: N8nClient | None = None
        self._ready = False

    async def start(self) -> None:
        if self._ready:
            return
        self.brain = LocalBrain()
        self.memory = PersistentMemory(self.brain)
        self.automations = N8nClient()
        self.voice = VoiceBox()
        self.cognition = Cognition(
            self.brain, self.memory, ToolKit(self.memory, self.automations)
        )
        self._ready = True

        if await self.brain.health():
            logger.info("🧠 Local brain online (%s)", settings.brain_model)
        else:
            logger.warning(
                "🧠 Local brain OFFLINE at %s — start it with `ollama serve` and "
                "`ollama pull %s` / `ollama pull %s`. The API will boot; chat will "
                "error until the brain is up.",
                settings.ollama_endpoint, settings.brain_model, settings.embedding_model,
            )
        self._bootstrap_owner()

    def _bootstrap_owner(self) -> None:
        """Create the one owner if none exists yet (idempotent)."""
        db = SessionLocal()
        try:
            if db.query(Owner).count() > 0:
                return
            if not settings.owner_password:
                logger.warning(
                    "No owner yet and OWNER_PASSWORD is unset — set OWNER_EMAIL / "
                    "OWNER_PASSWORD in .env to create your account, then restart."
                )
                return
            owner = Owner(
                id=str(uuid.uuid4()),
                email=settings.owner_email,
                name=settings.owner_name,
                hashed_password=hash_password(settings.owner_password),
                is_active=True,
            )
            db.add(owner)
            db.commit()
            logger.info("👤 Owner created: %s", settings.owner_email)
        finally:
            db.close()

    async def stop(self) -> None:
        if self.brain:
            await self.brain.aclose()
        if self.automations:
            await self.automations.aclose()


_kernel = Kernel()


def get_kernel() -> Kernel:
    return _kernel


def get_cognition() -> Cognition:
    if not _kernel.cognition:
        raise RuntimeError("Kernel not started")
    return _kernel.cognition


def get_memory() -> PersistentMemory:
    if not _kernel.memory:
        raise RuntimeError("Kernel not started")
    return _kernel.memory


def get_voice() -> VoiceBox:
    if not _kernel.voice:
        raise RuntimeError("Kernel not started")
    return _kernel.voice


def get_automations() -> N8nClient:
    if not _kernel.automations:
        raise RuntimeError("Kernel not started")
    return _kernel.automations
