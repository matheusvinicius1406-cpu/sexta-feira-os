"""
DecisionEngine — formal engine wrapping decision service behind IEngine.

Publishes: decision.created, decision.executed
"""
from __future__ import annotations

import logging

from app.core.di import get_kernel
from app.decision.service import DecisionEngine as DecisionService
from app.engines import IEngine

logger = logging.getLogger("sexta-feira.engine.decision")


class DecisionEngine(IEngine):
    """Formal Decision Engine."""

    @property
    def name(self) -> str:
        return "Decision"

    async def initialize(self) -> None:
        logger.info("DecisionEngine initialized")

    async def health(self) -> bool:
        return self._decision is not None

    async def shutdown(self) -> None:
        logger.info("DecisionEngine shutdown")

    @property
    def _decision(self) -> DecisionService | None:
        k = get_kernel()
        return k.decision if k else None
