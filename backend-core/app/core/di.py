"""
Dependency wiring for the kernel. One brain, one memory, one cognition loop.
Also bootstraps the single owner on first boot from environment variables.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid

from app.action.bus import CommandBus
from app.action.service import ActionService
from app.auth.jwt import hash_password
from app.automation.n8n import N8nClient
from app.brain.cognition import Cognition
from app.brain.engine import LocalBrain
from app.brain.memory import PersistentMemory
from app.brain.subagents import SubAgentRunner
from app.brain.tools import ToolKit
from app.connectors.service import ConnectorService
from app.connectors.vault import Vault
from app.core.config import settings
from app.db.database import SessionLocal
from app.decision.service import DecisionEngine
from app.events.bus import EventBus
from app.events.projector import WorldModelProjector
from app.learning.service import LearningEngine
from app.models.models import Owner
from app.obsidian.watcher import ObsidianWatcher
from app.planning.service import PlanningEngine
from app.schedule.service import Scheduler
from app.voice.box import VoiceBox
from app.world.service import WorldModel

logger = logging.getLogger("sexta-feira.di")


class Kernel:
    """Holds the singletons that make up the running brain."""

    def __init__(self) -> None:
        self.brain: LocalBrain | None = None
        self.memory: PersistentMemory | None = None
        self.world: WorldModel | None = None
        self.events: EventBus | None = None
        self.planning: PlanningEngine | None = None
        self.decision: DecisionEngine | None = None
        self.learning: LearningEngine | None = None
        self.cognition: Cognition | None = None
        self.voice: VoiceBox | None = None
        self.automations: N8nClient | None = None
        self.action_bus: CommandBus | None = None
        self.actions: ActionService | None = None
        self.scheduler: Scheduler | None = None
        self.connectors: ConnectorService | None = None
        self._obsidian_watcher: ObsidianWatcher | None = None
        self._obsidian_watcher_task: asyncio.Task | None = None
        self._scheduler_task: asyncio.Task | None = None
        self._ready = False

    async def start(self) -> None:
        if self._ready:
            return
        self.brain = LocalBrain()
        self.memory = PersistentMemory(self.brain)
        self.world = WorldModel()
        self.events = EventBus()
        # Every event has a chance to update the present (World Model).
        self.events.subscribe("*", WorldModelProjector(self.world).handle, "world-model-projector")
        self.planning = PlanningEngine(world=self.world, events=self.events)
        self.decision = DecisionEngine(
            planning=self.planning, world=self.world, events=self.events
        )
        self.learning = LearningEngine(
            memory=self.memory, world=self.world, events=self.events
        )
        self.automations = N8nClient()
        self.action_bus = CommandBus()
        self.actions = ActionService(self.action_bus)
        self.scheduler = Scheduler(self.actions, events=self.events)
        self.connectors = ConnectorService(Vault())
        self.voice = VoiceBox()
        toolkit = ToolKit(
            self.memory, self.automations, self.actions, self.scheduler,
            self.connectors, self.world, self.planning, self.decision, self.learning,
        )
        if settings.subagents_enabled:
            toolkit.subagents = SubAgentRunner(self.brain, toolkit)
        self.cognition = Cognition(self.brain, self.memory, toolkit, world=self.world)
        self._ready = True

        # Start background watcher for Obsidian vault sync
        if settings.obsidian_vault_path:
            self._obsidian_watcher = ObsidianWatcher(self.memory)
            self._obsidian_watcher_task = asyncio.create_task(
                self._obsidian_watcher_loop()
            )
            logger.info("📁 Obsidian vault watcher started for: %s", settings.obsidian_vault_path)

        if settings.scheduler_enabled:
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            logger.info("⏰ Scheduler running (every %ss)", settings.scheduler_interval_seconds)

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

    async def _scheduler_loop(self) -> None:
        """Fire due reminders/actions on an interval. Sleeps first (never at boot)."""
        while True:
            try:
                await asyncio.sleep(settings.scheduler_interval_seconds)
                db = SessionLocal()
                try:
                    await self.scheduler.run_due(db)
                finally:
                    db.close()
            except asyncio.CancelledError:
                break
            except Exception as e:  # noqa: BLE001 — the loop must survive one bad tick
                logger.warning("scheduler tick failed: %s", e)

    async def _obsidian_watcher_loop(self) -> None:
        """Poll the vault for changes on an interval (like the scheduler)."""
        await asyncio.sleep(5)  # initial delay — let the kernel finish booting
        while True:
            try:
                await asyncio.sleep(settings.obsidian_watch_interval)
                db = SessionLocal()
                try:
                    owner = db.query(Owner).first()
                    if owner and self._obsidian_watcher:
                        await self._obsidian_watcher.poll(
                            db, owner.id, settings.obsidian_vault_path,
                        )
                finally:
                    db.close()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("obsidian watcher tick failed: %s", e)

    async def stop(self) -> None:
        if self._obsidian_watcher_task:
            self._obsidian_watcher_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._obsidian_watcher_task
        if self._scheduler_task:
            self._scheduler_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._scheduler_task
        if self.brain:
            await self.brain.aclose()
        if self.automations:
            await self.automations.aclose()
        if self.connectors:
            await self.connectors.aclose()


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


def get_world() -> WorldModel:
    if not _kernel.world:
        raise RuntimeError("Kernel not started")
    return _kernel.world


def get_events() -> EventBus:
    if not _kernel.events:
        raise RuntimeError("Kernel not started")
    return _kernel.events


def get_planning() -> PlanningEngine:
    if not _kernel.planning:
        raise RuntimeError("Kernel not started")
    return _kernel.planning


def get_decision() -> DecisionEngine:
    if not _kernel.decision:
        raise RuntimeError("Kernel not started")
    return _kernel.decision


def get_learning() -> LearningEngine:
    if not _kernel.learning:
        raise RuntimeError("Kernel not started")
    return _kernel.learning


def get_voice() -> VoiceBox:
    if not _kernel.voice:
        raise RuntimeError("Kernel not started")
    return _kernel.voice


def get_automations() -> N8nClient:
    if not _kernel.automations:
        raise RuntimeError("Kernel not started")
    return _kernel.automations


def get_action_service() -> ActionService:
    if not _kernel.actions:
        raise RuntimeError("Kernel not started")
    return _kernel.actions


def get_action_bus() -> CommandBus:
    if not _kernel.action_bus:
        raise RuntimeError("Kernel not started")
    return _kernel.action_bus


def get_scheduler() -> Scheduler:
    if not _kernel.scheduler:
        raise RuntimeError("Kernel not started")
    return _kernel.scheduler


def get_connectors() -> ConnectorService:
    if not _kernel.connectors:
        raise RuntimeError("Kernel not started")
    return _kernel.connectors


def get_obsidian_watcher() -> ObsidianWatcher | None:
    return _kernel._obsidian_watcher
