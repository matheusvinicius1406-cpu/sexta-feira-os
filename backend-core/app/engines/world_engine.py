"""
WorldEngine — formal engine wrapping WorldModel behind IEngine.
"""
from __future__ import annotations

import logging

from app.core.di import get_kernel
from app.engines import IEngine
from app.world.service import WorldModel

logger = logging.getLogger("sexta-feira.engine.world")


class WorldEngine(IEngine):
    """Formal World Model Engine."""

    @property
    def name(self) -> str:
        return "World"

    async def initialize(self) -> None:
        logger.info("WorldEngine initialized")

    async def health(self) -> bool:
        return self._world is not None

    async def shutdown(self) -> None:
        logger.info("WorldEngine shutdown")

    @property
    def _world(self) -> WorldModel | None:
        k = get_kernel()
        return k.world if k else None
