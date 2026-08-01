"""
Concrete pipeline steps — each is a self-contained class with execute(kernel).

Order matches the kernel startup sequence:
config → database → owner → eventbus → memory → world → learning → planning
→ decision → automation → voice → plugins → toolkit → cognition → grpc
→ background → ready
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from app.kernel.pipeline.steps import BaseStep

if TYPE_CHECKING:
    from app.core.di import Kernel

logger = logging.getLogger("sexta-feira.pipeline.steps")


class ConfigStep(BaseStep):
    name = "config"
    timeout = 5.0
    async def execute(self, kernel: Kernel) -> None:
        from app.adapters._events import publish_event
        await publish_event("config.loaded", {"source": "settings"})


class DatabaseStep(BaseStep):
    name = "database"
    timeout = 10.0
    async def execute(self, kernel: Kernel) -> None:
        from sqlalchemy import text
        from app.db.database import SessionLocal
        from app.adapters._events import publish_event
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            await publish_event("database.connected")
        finally:
            db.close()


class OwnerStep(BaseStep):
    name = "owner"
    timeout = 10.0
    async def execute(self, kernel: Kernel) -> None:
        kernel._bootstrap_owner()
        from app.adapters._events import publish_event
        await publish_event("owner.loaded")


class EventBusStep(BaseStep):
    name = "eventbus"
    timeout = 5.0
    async def execute(self, kernel: Kernel) -> None:
        from app.events.bus import EventBus
        from app.events.projector import WorldModelProjector
        from app.adapters._events import publish_event
        kernel.events = EventBus()
        if kernel.world:
            kernel.events.subscribe("*", WorldModelProjector(kernel.world).handle, "world-model-projector")
        await publish_event("eventbus.ready")


class MemoryStep(BaseStep):
    name = "memory"
    timeout = 10.0
    async def execute(self, kernel: Kernel) -> None:
        from app.brain.engine import LocalBrain
        from app.brain.memory import PersistentMemory
        from app.adapters._events import publish_event
        kernel.brain = LocalBrain()
        kernel.memory = PersistentMemory(kernel.brain)
        await publish_event("memory.ready")


class WorldModelStep(BaseStep):
    name = "world"
    timeout = 5.0
    async def execute(self, kernel: Kernel) -> None:
        from app.world.service import WorldModel
        from app.adapters._events import publish_event
        kernel.world = WorldModel()
        await publish_event("world.ready")


class LearningStep(BaseStep):
    name = "learning"
    timeout = 10.0
    async def execute(self, kernel: Kernel) -> None:
        from app.learning.service import LearningEngine
        from app.adapters._events import publish_event
        kernel.learning = LearningEngine(memory=kernel.memory, world=kernel.world, events=kernel.events)
        await publish_event("learning.ready")


class PlanningStep(BaseStep):
    name = "planning"
    timeout = 10.0
    async def execute(self, kernel: Kernel) -> None:
        from app.planning.service import PlanningEngine
        from app.briefing.service import BriefingService
        from app.adapters._events import publish_event
        kernel.planning = PlanningEngine(world=kernel.world, events=kernel.events)
        kernel.briefing = BriefingService(
            world=kernel.world, planning=kernel.planning,
            decision=kernel.decision, events=kernel.events,
            learning=kernel.learning,
        )
        await publish_event("planning.ready")


class DecisionStep(BaseStep):
    name = "decision"
    timeout = 10.0
    async def execute(self, kernel: Kernel) -> None:
        from app.decision.service import DecisionEngine
        from app.adapters._events import publish_event
        kernel.decision = DecisionEngine(planning=kernel.planning, world=kernel.world, events=kernel.events)
        await publish_event("decision.ready")


class AutomationStep(BaseStep):
    """The kernel's hands: the action bus, the scheduler, connectors and the Teia.

    The Teia gets a `Services` bag holding everything that exists at this point;
    the services built later (journal, habits, time tracking) are attached by
    CognitionStep, and the triggers are armed by BackgroundStep once the whole
    kernel is up.
    """
    name = "automation"
    timeout = 10.0
    critical = False
    async def execute(self, kernel: Kernel) -> None:
        from app.action.bus import CommandBus
        from app.action.service import ActionService
        from app.adapters._events import publish_event
        from app.automation.teia.engine.context import Services
        from app.automation.teia.nodes.files import ensure_workspace
        from app.automation.teia.service import TeiaService
        from app.connectors.service import ConnectorService
        from app.connectors.vault import Vault
        from app.schedule.service import Scheduler

        kernel.action_bus = CommandBus()
        kernel.actions = ActionService(kernel.action_bus)
        kernel.scheduler = Scheduler(kernel.actions, events=kernel.events, briefing=kernel.briefing)
        kernel.connectors = ConnectorService(Vault())

        ensure_workspace()
        kernel.automations = TeiaService(Services(
            memory=kernel.memory, world=kernel.world, events=kernel.events,
            scheduler=kernel.scheduler, actions=kernel.actions,
            connectors=kernel.connectors, planning=kernel.planning,
            decision=kernel.decision, learning=kernel.learning,
            briefing=kernel.briefing, brain=kernel.brain,
        ))
        logger.info(
            "Teia pronta — %d tipos de nó, %d de gatilho",
            len(kernel.automations.registry.node_types()),
            len(kernel.automations.registry.trigger_types()),
        )
        await publish_event("automation.ready")


class VoiceStep(BaseStep):
    name = "voice"
    timeout = 5.0
    critical = False
    async def execute(self, kernel: Kernel) -> None:
        from app.voice.box import VoiceBox
        from app.adapters._events import publish_event
        kernel.voice = VoiceBox()
        await publish_event("voice.ready")


class PluginStep(BaseStep):
    name = "plugins"
    timeout = 10.0
    critical = False
    async def execute(self, kernel: Kernel) -> None:
        from app.plugins import PluginRegistry
        from app.plugins.loader import PluginLoader
        from app.plugins.discovery import PluginDiscovery
        from app.core.config import settings
        from app.adapters._events import publish_event
        registry = PluginRegistry()
        loader = PluginLoader(registry)
        discovery = PluginDiscovery(registry)
        kernel._plugin_registry = registry
        kernel._plugin_loader = loader
        kernel._plugin_discovery = discovery
        await publish_event("plugins.ready")


class ToolkitStep(BaseStep):
    name = "toolkit"
    timeout = 15.0
    async def execute(self, kernel: Kernel) -> None:
        from app.brain.tools import ToolKit
        from app.brain.subagents import SubAgentRunner
        from app.directors.service import DirectorService
        from app.core.config import settings
        from app.adapters._events import publish_event
        toolkit = ToolKit(
            kernel.memory, kernel.automations, kernel.actions, kernel.scheduler,
            kernel.connectors, kernel.world, kernel.planning, kernel.decision, kernel.learning,
            kernel.briefing,
        )
        if kernel.brain and settings.subagents_enabled:
            toolkit.subagents = SubAgentRunner(kernel.brain, toolkit)
        kernel.directors = DirectorService(kernel.brain, toolkit, kernel.memory, events=kernel.events)
        toolkit.directors = kernel.directors
        kernel._toolkit = toolkit
        await publish_event("toolkit.ready")


class CognitionStep(BaseStep):
    name = "cognition"
    timeout = 15.0
    async def execute(self, kernel: Kernel) -> None:
        from app.brain.cognition import Cognition
        from app.brain.extractor import MemoryExtractor
        from app.journal.service import JournalService
        from app.journal.service import HabitService
        from app.timetrack.service import TimeTracker
        from app.evals.service import EvalHarness
        from app.adapters._events import publish_event
        extractor = MemoryExtractor(kernel.brain, kernel.memory, world=kernel.world, events=kernel.events)
        kernel.journal = JournalService(events=kernel.events, extractor=extractor)
        kernel.habits = HabitService(world=kernel.world, events=kernel.events)
        kernel.timetracker = TimeTracker(world=kernel.world, events=kernel.events)
        kernel.evals = EvalHarness(kernel.brain, events=kernel.events, learning=kernel.learning)
        kernel.cognition = Cognition(
            kernel.brain, kernel.memory, kernel._toolkit,
            world=kernel.world, extractor=extractor,
        )
        # Finish wiring the Teia: these services only exist from here on, and its
        # nodes reach them through the same bag AutomationStep created.
        if kernel.automations:
            services = kernel.automations.services
            services.journal = kernel.journal
            services.habits = kernel.habits
            services.timetracker = kernel.timetracker
        await publish_event("cognition.ready")


class GrpcStep(BaseStep):
    critical = False
    name = "grpc"
    timeout = 10.0
    async def execute(self, kernel: Kernel) -> None:
        from app.grpc.server import get_grpc_server
        from app.adapters._events import publish_event
        server = get_grpc_server()
        await server.start()
        kernel._grpc_server = server
        await publish_event("grpc.ready")


class BackgroundStep(BaseStep):
    name = "background"
    timeout = 10.0
    critical = False
    async def execute(self, kernel: Kernel) -> None:
        from app.core.config import settings
        from app.obsidian.watcher import ObsidianWatcher
        from app.adapters._events import publish_event

        if kernel.automations:
            _start_teia(kernel)
        if settings.scheduler_enabled and kernel.scheduler:
            kernel._scheduler_task = asyncio.create_task(kernel._scheduler_loop())
            logger.info("Scheduler running (every %ss)", settings.scheduler_interval_seconds)
        if settings.obsidian_vault_path and kernel.memory:
            kernel._obsidian_watcher = ObsidianWatcher(kernel.memory)
            kernel._obsidian_watcher_task = asyncio.create_task(kernel._obsidian_watcher_loop())
            logger.info("Obsidian vault watcher started for: %s", settings.obsidian_vault_path)
        if kernel.brain:
            if await kernel.brain.health():
                logger.info("Local brain online (%s)", settings.brain_model)
            else:
                logger.warning("Local brain OFFLINE at %s", settings.ollama_endpoint)
        await publish_event("background.ready")


def _start_teia(kernel: Kernel) -> None:
    """Seed the catalog, bridge the EventBus, arm the triggers, start the clock."""
    from app.automation.teia import catalog
    from app.core.config import settings
    from app.db.database import SessionLocal
    from app.models.models import Owner

    teia = kernel.automations
    if settings.teia_seed_catalog:
        db = SessionLocal()
        try:
            owner = db.query(Owner).first()
            if owner:
                installed = catalog.seed(teia, db, owner.id)
                if installed:
                    logger.info("Teia: catálogo instalado (%s)", ", ".join(installed))
        except Exception as e:  # noqa: BLE001 — a bad recipe never blocks the boot
            logger.warning("Teia: catálogo não pôde ser instalado: %s", e)
        finally:
            db.close()

    if kernel.events:
        # Event triggers: every kernel event is offered to the armed automations.
        kernel.events.subscribe("*", teia.triggers.on_event, "teia-triggers")

    teia.start()


class ReadyStep(BaseStep):
    name = "ready"
    timeout = 5.0
    async def execute(self, kernel: Kernel) -> None:
        from app.kernel import KernelStateManager
        from app.adapters._events import publish_event
        kernel._kernel_state = KernelStateManager()
        await kernel._kernel_state.set_running()
        await publish_event("kernel.ready", {"uptime_seconds": 0})
        logger.info("Kernel ready — all steps completed")
