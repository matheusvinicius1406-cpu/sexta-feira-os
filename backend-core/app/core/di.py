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
from app.automation.teia.service import TeiaService
from app.brain.cognition import Cognition
from app.brain.engine import LocalBrain
from app.brain.memory import PersistentMemory
from app.briefing.service import BriefingService
from app.connectors.service import ConnectorService
from app.core.config import settings
from app.db.database import SessionLocal
from app.decision.service import DecisionEngine
from app.directors.service import DirectorService
from app.evals.service import EvalHarness
from app.events.bus import EventBus
from app.journal.service import HabitService, JournalService
from app.kernel.pipeline.startup import get_startup_pipeline
from app.learning.service import LearningEngine
from app.models.models import Owner
from app.obsidian.watcher import ObsidianWatcher
from app.planning.service import PlanningEngine
from app.schedule.service import Scheduler
from app.timetrack.service import TimeTracker
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
        self.briefing: BriefingService | None = None
        self.directors: DirectorService | None = None
        self.journal: JournalService | None = None
        self.habits: HabitService | None = None
        self.timetracker: TimeTracker | None = None
        self.evals: EvalHarness | None = None
        self.pulse = None               # CognitivePulse | None — the agent's own initiative
        self.cognition: Cognition | None = None
        self.voice: VoiceBox | None = None
        self.automations: TeiaService | None = None
        self.action_bus: CommandBus | None = None
        self.actions: ActionService | None = None
        self.scheduler: Scheduler | None = None
        self.connectors: ConnectorService | None = None
        self._scheduler_task: asyncio.Task | None = None
        self._pulse_task: asyncio.Task | None = None
        self._obsidian_watcher: ObsidianWatcher | None = None
        self._obsidian_watcher_task: asyncio.Task | None = None
        # Preloads the speech model during boot; cancelled by StopVoiceWarmupStep.
        self._voice_warm_task: asyncio.Task | None = None
        self._ready = False

    async def start(self) -> None:
        if self._ready:
            return

        pipeline = get_startup_pipeline()
        success = await pipeline.run(self)

        if success:
            self._ready = True
        else:
            logger.error("Kernel startup failed: %s", pipeline.errors)
            raise RuntimeError(f"Kernel startup failed: {'; '.join(pipeline.errors)}")

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
            except Exception as e:  # noqa: BLE001 — the loop must survive one bad tick
                logger.warning("obsidian watcher tick failed: %s", e)

    async def _pulse_loop(self) -> None:
        """The agent's heartbeat: wake on an interval and judge whether anything
        is worth doing now. Sleeps first (never thinks at boot). The cycle
        itself is a pure method (CognitivePulse.tick), so the loop is a shell.

        Exactly one sleep, at the top of the loop — matching _scheduler_loop.
        A second sleep used to sit here, before the loop, so the FIRST tick
        landed at 2x the configured interval (1200s at the 600s default)
        while every tick after it was correctly spaced.
        """
        while True:
            try:
                await asyncio.sleep(settings.agent_pulse_interval_seconds)
                db = SessionLocal()
                try:
                    owner = db.query(Owner).first()
                    if owner and self.pulse:
                        await self.pulse.tick(db, owner.id, reason="heartbeat")
                finally:
                    db.close()
            except asyncio.CancelledError:
                break
            except Exception as e:  # noqa: BLE001 — the loop must survive one bad tick
                logger.warning("pulse tick failed: %s", e)

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

    async def stop(self) -> None:
        if self._pulse_task:
            self._pulse_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._pulse_task
        if self._obsidian_watcher_task:
            self._obsidian_watcher_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._obsidian_watcher_task
        if self._scheduler_task:
            self._scheduler_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._scheduler_task
        if self.automations:
            await self.automations.stop()
        if self.brain:
            await self.brain.aclose()
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


def get_briefing() -> BriefingService:
    if not _kernel.briefing:
        raise RuntimeError("Kernel not started")
    return _kernel.briefing


def get_directors() -> DirectorService:
    if not _kernel.directors:
        raise RuntimeError("Kernel not started")
    return _kernel.directors


def get_journal() -> JournalService:
    if not _kernel.journal:
        raise RuntimeError("Kernel not started")
    return _kernel.journal


def get_habits() -> HabitService:
    if not _kernel.habits:
        raise RuntimeError("Kernel not started")
    return _kernel.habits


def get_timetracker() -> TimeTracker:
    if not _kernel.timetracker:
        raise RuntimeError("Kernel not started")
    return _kernel.timetracker


def get_evals() -> EvalHarness:
    if not _kernel.evals:
        raise RuntimeError("Kernel not started")
    return _kernel.evals


def get_obsidian_watcher() -> ObsidianWatcher | None:
    return _kernel._obsidian_watcher


def get_voice() -> VoiceBox:
    if not _kernel.voice:
        raise RuntimeError("Kernel not started")
    return _kernel.voice


def get_automations() -> TeiaService:
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


def get_pulse():
    """The Cognitive Pulse (the agent's own initiative).

    Returns None when the pulse is disabled — callers handle that by answering
    a clean "pulse desligado" instead of crashing.
    """
    return _kernel.pulse
