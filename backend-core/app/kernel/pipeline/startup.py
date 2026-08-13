"""
StartupPipeline — orchestrates kernel initialization via ordered BaseStep classes.

Publishes:
  kernel.starting            → when pipeline begins
  {step.name}.ready          → after each step succeeds
  pipeline.step_failed       → if a step fails
  kernel.ready               → when all steps complete
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.di import Kernel

from app.kernel.pipeline.steps import BaseStep
from app.kernel.pipeline.steps.core_steps import (
    AgentStep,
    AutomationStep,
    BackgroundStep,
    CognitionStep,
    ConfigStep,
    DatabaseStep,
    DecisionStep,
    EventBusStep,
    GrpcStep,
    LearningStep,
    MemoryStep,
    OwnerStep,
    PlanningStep,
    PluginStep,
    ReadyStep,
    ToolkitStep,
    VoiceStep,
    WorldModelStep,
)

logger = logging.getLogger("sexta-feira.pipeline.startup")


class StartupPipeline:
    """Orchestrated kernel startup through sequential step classes."""

    DEFAULT_STEPS: list[type[BaseStep]] = [
        ConfigStep,
        DatabaseStep,
        OwnerStep,
        EventBusStep,
        MemoryStep,
        WorldModelStep,
        LearningStep,
        PlanningStep,
        DecisionStep,
        AutomationStep,
        VoiceStep,
        PluginStep,
        ToolkitStep,
        CognitionStep,
        AgentStep,
        GrpcStep,
        BackgroundStep,
        ReadyStep,
    ]

    def __init__(self, steps: list[type[BaseStep]] | None = None) -> None:
        self._steps = [s() for s in (steps or self.DEFAULT_STEPS)]
        self._current_idx: int = 0
        self._errors: list[str] = []
        self._started_at: float = 0.0

    async def run(self, kernel: Kernel) -> bool:
        # Lazy import to avoid circular: di.py → startup.py → _events.py → di.py
        from app.adapters._events import publish_event

        self._started_at = time.time()
        self._errors.clear()
        await publish_event("kernel.starting", {"timestamp": self._started_at})

        for idx, step in enumerate(self._steps):
            self._current_idx = idx
            logger.info("[Pipeline] %s...", step.name)
            try:
                await asyncio.wait_for(step.execute(kernel), timeout=step.timeout)
                await publish_event(f"{step.name}.ready")
            except TimeoutError:
                msg = f"Step '{step.name}' timed out after {step.timeout}s"
                logger.error("[Pipeline] %s", msg)
                self._errors.append(msg)
                await publish_event("pipeline.step_failed", {"step": step.name, "error": msg})
                if step.critical:
                    return False
            except Exception as exc:
                msg = f"Step '{step.name}' failed: {exc}"
                logger.error("[Pipeline] %s", msg)
                self._errors.append(msg)
                await publish_event("pipeline.step_failed", {"step": step.name, "error": str(exc)[:200]})
                if step.critical:
                    return False

        elapsed = time.time() - self._started_at
        logger.info("[Pipeline] Kernel ready in %.2fs", elapsed)
        return True

    @property
    def progress(self) -> float:
        if not self._steps:
            return 1.0
        return (self._current_idx + 1) / len(self._steps)

    @property
    def errors(self) -> list[str]:
        return list(self._errors)

    @property
    def current_step_name(self) -> str:
        if 0 <= self._current_idx < len(self._steps):
            return self._steps[self._current_idx].name
        return "done"


_default_pipeline = StartupPipeline()


def get_startup_pipeline() -> StartupPipeline:
    return _default_pipeline
