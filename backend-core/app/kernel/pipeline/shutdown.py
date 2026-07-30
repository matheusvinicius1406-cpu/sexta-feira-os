"""
ShutdownPipeline — graceful kernel shutdown through ordered step classes.

Publishes:
  kernel.shutdown      → when pipeline begins
  {step.name}.stopped  → after each step succeeds
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.di import Kernel

logger = logging.getLogger("sexta-feira.pipeline.shutdown")


class ShutdownStep(ABC):
    """Base class for shutdown steps."""
    @property
    @abstractmethod
    def name(self) -> str: ...
    @property
    def timeout(self) -> float:
        return 10.0
    @abstractmethod
    async def execute(self, kernel: Kernel) -> None: ...


class SaveStateStep(ShutdownStep):
    name = "save_state"
    async def execute(self, kernel: Kernel) -> None:
        from app.adapters._events import publish_event
        logger.info("Saving kernel state...")
        await publish_event("state.saved")


class StopSchedulerStep(ShutdownStep):
    name = "stop_scheduler"
    async def execute(self, kernel: Kernel) -> None:
        if kernel._scheduler_task:
            kernel._scheduler_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await kernel._scheduler_task


class StopObsidianStep(ShutdownStep):
    name = "stop_obsidian"
    async def execute(self, kernel: Kernel) -> None:
        if kernel._obsidian_watcher_task:
            kernel._obsidian_watcher_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await kernel._obsidian_watcher_task


class StopAutomationsStep(ShutdownStep):
    name = "stop_automations"
    async def execute(self, kernel: Kernel) -> None:
        if kernel.automations:
            await kernel.automations.aclose()
        if kernel.connectors:
            await kernel.connectors.aclose()


class StopBrainStep(ShutdownStep):
    name = "stop_brain"
    async def execute(self, kernel: Kernel) -> None:
        if kernel.brain:
            await kernel.brain.aclose()


class StopGrpcStep(ShutdownStep):
    name = "stop_grpc"
    async def execute(self, kernel: Kernel) -> None:
        if hasattr(kernel, "_grpc_server") and kernel._grpc_server:
            await kernel._grpc_server.stop(grace=5.0)


class ShutdownPipeline:
    """Graceful kernel shutdown through ordered step classes."""

    DEFAULT_STEPS: list[type[ShutdownStep]] = [
        StopSchedulerStep,
        StopObsidianStep,
        SaveStateStep,
        StopAutomationsStep,
        StopBrainStep,
        StopGrpcStep,
    ]

    def __init__(self, steps: list[type[ShutdownStep]] | None = None) -> None:
        self._steps = [s() for s in (steps or self.DEFAULT_STEPS)]
        self._saved: list[str] = []

    async def run(self, kernel: Kernel) -> None:
        from app.adapters._events import publish_event
        await publish_event("kernel.shutdown", {"reason": "user_request"})
        for step in self._steps:
            try:
                await asyncio.wait_for(step.execute(kernel), timeout=step.timeout)
                self._saved.append(step.name)
                await publish_event(f"{step.name}.stopped")
            except Exception as exc:
                logger.warning("[Shutdown] %s failed: %s", step.name, exc)
        logger.info("[Shutdown] Complete. Steps saved: %s", self._saved)

    @property
    def saved(self) -> list[str]:
        return list(self._saved)
