"""
SchedulerEngine — formal engine wrapping Scheduler behind IEngine.
"""
from __future__ import annotations

import logging

from app.core.di import get_kernel
from app.engines import IEngine
from app.schedule.service import Scheduler

logger = logging.getLogger("sexta-feira.engine.scheduler")


class SchedulerEngine(IEngine):
    """Formal Scheduler Engine."""

    @property
    def name(self) -> str:
        return "Scheduler"

    async def initialize(self) -> None:
        logger.info("SchedulerEngine initialized")

    async def health(self) -> bool:
        return self._scheduler is not None

    async def shutdown(self) -> None:
        logger.info("SchedulerEngine shutdown")

    @property
    def _scheduler(self) -> Scheduler | None:
        k = get_kernel()
        return k.scheduler if k else None
