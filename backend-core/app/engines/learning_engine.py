"""
LearningEngine — formal engine wrapping learning service behind IEngine.

Publishes: learning.new_pattern, learning.new_skill, learning.confidence_changed
"""
from __future__ import annotations

import logging

from app.core.di import get_kernel
from app.engines import IEngine
from app.learning.service import LearningEngine as LearningService

logger = logging.getLogger("sexta-feira.engine.learning")


class LearningEngine(IEngine):
    """Formal Learning Engine."""

    @property
    def name(self) -> str:
        return "Learning"

    async def initialize(self) -> None:
        logger.info("LearningEngine initialized")

    async def health(self) -> bool:
        return self._learning is not None

    async def shutdown(self) -> None:
        logger.info("LearningEngine shutdown")

    @property
    def _learning(self) -> LearningService | None:
        k = get_kernel()
        return k.learning if k else None
