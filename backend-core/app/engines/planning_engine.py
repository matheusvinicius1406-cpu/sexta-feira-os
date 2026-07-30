"""
PlanningEngine — formal engine wrapping planning service behind IEngine.

Publishes: plan.created, plan.updated, plan.completed
"""
from __future__ import annotations

import logging

from app.core.di import get_kernel
from app.engines import IEngine
from app.planning.service import PlanningEngine as PlanningService

logger = logging.getLogger("sexta-feira.engine.planning")


class PlanningEngine(IEngine):
    """Formal Planning Engine."""

    @property
    def name(self) -> str:
        return "Planning"

    async def initialize(self) -> None:
        logger.info("PlanningEngine initialized")

    async def health(self) -> bool:
        return self._planning is not None

    async def shutdown(self) -> None:
        logger.info("PlanningEngine shutdown")

    @property
    def _planning(self) -> PlanningService | None:
        k = get_kernel()
        return k.planning if k else None
