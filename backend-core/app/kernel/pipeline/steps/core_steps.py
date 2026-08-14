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

        from app.adapters._events import publish_event
        from app.db.database import SessionLocal
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
        from app.adapters._events import publish_event
        from app.auth.jwt import dev_bypass_active

        kernel._bootstrap_owner()
        if dev_bypass_active():
            # Loud on purpose. An auth bypass that runs silently is how one ends
            # up shipping with it on.
            logger.warning(
                "AUTH_DEV_BYPASS ligado — requisições sem token valem como o dono. "
                "Só vale em loopback+development; desligue no .env quando não precisar."
            )
        await publish_event("owner.loaded")


class EventBusStep(BaseStep):
    name = "eventbus"
    timeout = 5.0
    async def execute(self, kernel: Kernel) -> None:
        from app.adapters._events import publish_event
        from app.events.bus import EventBus

        # The World Model projector is NOT subscribed here: this step runs before
        # WorldModelStep, so `kernel.world` is still None. Subscribing here was a
        # silent no-op that left every event unprojected — the World Model simply
        # never learned anything. WorldModelStep owns that wiring now.
        kernel.events = EventBus()
        await publish_event("eventbus.ready")


class MemoryStep(BaseStep):
    name = "memory"
    timeout = 30.0
    async def execute(self, kernel: Kernel) -> None:
        from app.adapters._events import publish_event
        from app.brain.engine import LocalBrain
        from app.brain.memory import PersistentMemory
        kernel.brain = LocalBrain()
        kernel.memory = PersistentMemory(kernel.brain)
        await _report_missing_models(kernel.brain)
        await publish_event("memory.ready")


def model_present(name: str, have: set[str]) -> bool:
    """Is `name` among the models Ollama reports?

    Tag handling is the whole job. Ollama lists a model by its full tag, so a
    config saying `nomic-embed-text` must match a listed `nomic-embed-text:latest`
    — a plain `in` check calls a present model missing and cries wolf at every
    boot, which is how a real warning gets ignored. The reverse must hold too:
    `qwen3-vl:2b` is NOT satisfied by having `qwen3-vl:4b` installed.
    """
    if name in have:
        return True
    if ":" in name:
        return False                      # an explicit tag must match exactly
    return f"{name}:latest" in have or any(h.split(":", 1)[0] == name for h in have)


def wanted_models() -> dict[str, list[str]]:
    """The models this kernel needs, keyed by name, listing the roles each fills.

    Keyed by MODEL, not by role, because one model now fills several: the brain
    talks, acts and sees. Keyed by role instead, an absent qwen3-vl:2b would be
    reported twice as two separate problems, and a `ollama pull` line would be
    printed twice for the same download.
    """
    from app.core.config import settings

    roles: dict[str, list[str]] = {}
    roles.setdefault(settings.brain_model, []).append("conversa e ferramentas")
    if settings.vision_enabled:
        roles.setdefault(settings.vision_model_resolved, []).append("visão")
    roles.setdefault(settings.embedding_model, []).append("memória semântica")
    return roles


async def _report_brain_capabilities(brain) -> None:
    """Say at boot whether the one brain can actually act and see.

    A single model holding three jobs is only a simplification while it really
    does all three. Point BRAIN_MODEL at a model with no "tools" and the
    assistant still answers — it just quietly stops being an agent, which is
    exactly the failure this kernel keeps rediscovering the expensive way. With
    no "vision" and no separate VISION_MODEL, every camera frame instead fails
    later and individually, deep inside the vision router.

    Both are said once, here, at the moment the owner can act on them.
    """
    from app.core.config import settings

    caps = await brain.capabilities()
    if not caps:
        # An Ollama too old to report capabilities. Silence beats a false alarm:
        # a warning at every boot about a model that works is how a real warning
        # gets trained away.
        return

    if "tools" not in caps:
        logger.warning(
            "%s não tem 'tools': o Jarvis conversa mas não age — nada de gravar "
            "memória, criar lembrete ou disparar automação. Use um modelo com "
            "ferramentas (ex.: qwen3-vl:2b) em BRAIN_MODEL.",
            settings.brain_model,
        )
    if settings.vision_enabled and settings.vision_shares_the_brain and "vision" not in caps:
        logger.warning(
            "%s não enxerga, e VISION_MODEL está vazio (= 'use o cérebro'). "
            "Câmera, OCR e anexos vão falhar. Use um modelo com visão em "
            "BRAIN_MODEL ou aponte VISION_MODEL para um.",
            settings.brain_model,
        )
    if {"tools", "vision"} <= caps and settings.vision_shares_the_brain:
        logger.info(
            "Cérebro único: %s conversa, age e enxerga — um só modelo na RAM.",
            settings.brain_model,
        )


async def _report_missing_models(brain=None) -> None:
    """Say at boot which configured models Ollama does not actually have.

    A model named in settings but absent from Ollama fails LATER, once, deep in
    whatever asked for it. That is how `nomic-embed-text` went missing without
    anyone noticing: every memory write logged
    `Embedding failed (stored without vector): 404` mid-use and carried on, so
    memories were saved with no vector and semantic recall quietly returned
    nothing — no error, no empty-state, just worse answers.

    This never fails the boot. A kernel with no embedding model still runs; the
    owner simply gets told, once, at the moment they can act on it.
    """
    import httpx

    from app.core.config import settings

    wanted = wanted_models()

    try:
        async with httpx.AsyncClient(base_url=settings.ollama_endpoint, timeout=10.0) as c:
            r = await c.get("/api/tags")
            r.raise_for_status()
            have = {m["name"] for m in r.json().get("models", [])}
    except Exception as e:  # noqa: BLE001 — Ollama being down is reported elsewhere
        logger.warning("Não deu para listar os modelos do Ollama (%s); seguindo assim mesmo.", e)
        return

    missing = {name: roles for name, roles in wanted.items() if not model_present(name, have)}
    for name, roles in missing.items():
        logger.warning(
            "Modelo ausente para %s: '%s'. Rode: ollama pull %s",
            " + ".join(roles), name, name,
        )
    if not missing:
        logger.info(
            "Modelos prontos — %s",
            ", ".join(f"{n} ({' + '.join(roles)})" for n, roles in wanted.items()),
        )
        # Only worth asking once the model is actually there: /api/show on a
        # model Ollama does not have just fails, and the pull warning above
        # already said the useful thing.
        if brain is not None:
            await _report_brain_capabilities(brain)
        if not settings.brain_num_ctx:
            logger.info(
                "BRAIN_NUM_CTX não medido — a compressão de prompt usa um teto "
                "padrão de %d tokens em vez do real desta máquina. Rode "
                "POST /api/v1/optimize/full uma vez para medir e ajustar.",
                settings.prompt_compression_max_tokens,
            )


class WorldModelStep(BaseStep):
    name = "world"
    timeout = 5.0
    async def execute(self, kernel: Kernel) -> None:
        from app.adapters._events import publish_event
        from app.events.projector import WorldModelProjector
        from app.world.service import WorldModel

        kernel.world = WorldModel()
        # Wire the projector here, where BOTH the bus and the world exist. This
        # is what makes an event change the present: 'localizacao.mudou' is only
        # a fact in the world because this subscriber puts it there.
        if kernel.events:
            kernel.events.subscribe(
                "*", WorldModelProjector(kernel.world).handle, "world-model-projector"
            )
        await publish_event("world.ready")


class LearningStep(BaseStep):
    name = "learning"
    timeout = 10.0
    async def execute(self, kernel: Kernel) -> None:
        from app.adapters._events import publish_event
        from app.learning.service import LearningEngine
        kernel.learning = LearningEngine(memory=kernel.memory, world=kernel.world, events=kernel.events)
        await publish_event("learning.ready")


class PlanningStep(BaseStep):
    name = "planning"
    timeout = 10.0
    async def execute(self, kernel: Kernel) -> None:
        from app.adapters._events import publish_event
        from app.planning.service import PlanningEngine
        kernel.planning = PlanningEngine(world=kernel.world, events=kernel.events)
        # The briefing is NOT built here. It needs the Decision Engine, and this
        # step runs before DecisionStep — so `decision=kernel.decision` handed it
        # None, and `_focus()` returns None for a falsy decision while `_render`
        # simply omits the line. Result: "Foco sugerido", one of the briefing's
        # five advertised pillars, never appeared in any kernel and nothing ever
        # raised. DecisionStep owns it now, where both engines exist.
        await publish_event("planning.ready")


class DecisionStep(BaseStep):
    name = "decision"
    timeout = 10.0
    async def execute(self, kernel: Kernel) -> None:
        from app.adapters._events import publish_event
        from app.briefing.service import BriefingService
        from app.decision.service import DecisionEngine
        kernel.decision = DecisionEngine(planning=kernel.planning, world=kernel.world, events=kernel.events)
        kernel.briefing = BriefingService(
            world=kernel.world, planning=kernel.planning,
            decision=kernel.decision, events=kernel.events,
            learning=kernel.learning,
        )
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
        from app.adapters._events import publish_event
        from app.voice.box import VoiceBox
        kernel.voice = VoiceBox()

        # Load the speech model in the background. It takes ~2 minutes on CPU,
        # and whoever pays that cost pays it staring at a HUD that looks deaf —
        # so the kernel pays it, during boot, without blocking this step. The
        # task is parked on the kernel so shutdown can cancel it instead of
        # leaving a thread loading a model into a process that is going away.
        from app.core.config import settings

        warm = getattr(kernel.voice.transcriber, "warm", None)
        if warm and settings.stt_warm_on_boot:
            async def _warm() -> None:
                try:
                    await warm()
                    logger.info("Modelo de escuta pronto — a primeira fala já responde rápido.")
                except Exception as e:  # noqa: BLE001 — warming is best-effort
                    logger.warning("Não deu para pré-carregar o modelo de escuta: %s", e)

            kernel._voice_warm_task = asyncio.create_task(_warm())

        await publish_event("voice.ready")


class PluginStep(BaseStep):
    name = "plugins"
    timeout = 10.0
    critical = False
    async def execute(self, kernel: Kernel) -> None:
        from app.adapters._events import publish_event
        from app.plugins import PluginRegistry
        from app.plugins.discovery import PluginDiscovery
        from app.plugins.loader import PluginLoader
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
        from app.adapters._events import publish_event
        from app.brain.subagents import SubAgentRunner
        from app.brain.tools import ToolKit
        from app.brain.vision import VisionEngine
        from app.brain.web_search import WebSearch
        from app.core.config import settings
        from app.directors.service import DirectorService
        toolkit = ToolKit(
            kernel.memory, kernel.automations, kernel.actions, kernel.scheduler,
            kernel.connectors, kernel.world, kernel.planning, kernel.decision, kernel.learning,
            kernel.briefing,
            # web_search/vision were left unwired here, so the brain's own
            # web_search/fetch_page/analyze_image tools answered "indisponível"
            # even though the API routes could search fine. Same singletons the
            # routes use (cheap to construct; model detection is lazy).
            vision=VisionEngine(),
            web_search=WebSearch(),
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
        from app.adapters._events import publish_event
        from app.brain.cognition import Cognition
        from app.brain.extractor import MemoryExtractor
        from app.core.config import settings
        from app.evals.service import EvalHarness
        from app.journal.service import HabitService, JournalService
        from app.timetrack.service import TimeTracker
        # Mirror every learned fact into the Obsidian vault. This used to live on
        # Cognition's single-fact fallback path — which the kernel never takes,
        # because it always has an extractor. The auto-export simply never ran.
        def mirror_to_vault(content: str, kind: str) -> None:
            if not settings.obsidian_vault_path:
                return
            from app.obsidian.exporter import export_auto_learned_fact
            export_auto_learned_fact(
                vault_path=settings.obsidian_vault_path,
                title=content[:80], content=content, kind=kind,
            )

        extractor = MemoryExtractor(
            kernel.brain, kernel.memory, world=kernel.world, events=kernel.events,
            on_stored=mirror_to_vault,
        )
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


class AgentStep(BaseStep):
    """The kernel's own initiative: the Cognitive Pulse.

    Runs after CognitionStep (so the journal exists for the diary) and before
    BackgroundStep (which starts its asyncio heartbeat). The pulse is the agent
    half of the system: on an interval it judges whether anything is worth
    doing NOW, executes read/reversible tools, and proposes world-changing
    actions for the owner to approve — the "age com confirmação" mode.
    """
    name = "agent"
    timeout = 10.0
    critical = False

    async def execute(self, kernel: Kernel) -> None:
        from app.adapters._events import publish_event
        from app.agent.pulse import CognitivePulse
        from app.core.config import settings

        if not (settings.agent_pulse_enabled and kernel.brain and kernel._toolkit):
            await publish_event("agent.ready", {"pulse": False})
            return

        kernel.pulse = CognitivePulse(
            brain=kernel.brain, toolkit=kernel._toolkit,
            world=kernel.world, planning=kernel.planning, decision=kernel.decision,
            learning=kernel.learning, events=kernel.events, journal=kernel.journal,
        )
        logger.info(
            "Agente próprio pronto (pulse a cada %ss — age ou propõe, nunca sem confirmação)",
            settings.agent_pulse_interval_seconds,
        )
        await publish_event("agent.ready", {"pulse": True})


class GrpcStep(BaseStep):
    critical = False
    name = "grpc"
    timeout = 10.0
    async def execute(self, kernel: Kernel) -> None:
        from app.adapters._events import publish_event
        from app.grpc.server import get_grpc_server
        server = get_grpc_server()
        await server.start()
        kernel._grpc_server = server
        await publish_event("grpc.ready")


class BackgroundStep(BaseStep):
    name = "background"
    timeout = 10.0
    critical = False
    async def execute(self, kernel: Kernel) -> None:
        from app.adapters._events import publish_event
        from app.core.config import settings
        from app.obsidian.watcher import ObsidianWatcher

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
        if kernel.pulse:
            kernel._pulse_task = asyncio.create_task(kernel._pulse_loop())
            logger.info("Pulse cognitivo rodando (a cada %ss)", settings.agent_pulse_interval_seconds)
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
        from app.adapters._events import publish_event
        from app.kernel import KernelStateManager
        kernel._kernel_state = KernelStateManager()
        await kernel._kernel_state.set_running()
        await publish_event("kernel.ready", {"uptime_seconds": 0})
        logger.info("Kernel ready — all steps completed")
