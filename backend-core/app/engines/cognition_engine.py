"""
CognitionEngine — formal engine wrapping brain + cognition loop behind IEngine.

Publishes: brain.started, brain.thinking, brain.tool_call,
           brain.reasoning, brain.reply, brain.finished
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from app.brain.cognition import Cognition
from app.core.di import get_kernel
from app.engines import IEngine

logger = logging.getLogger("sexta-feira.engine.cognition")


class CognitionEngine(IEngine):
    """Formal Cognition Engine — wraps Cognition with lifecycle."""

    @property
    def name(self) -> str:
        return "Cognition"

    async def initialize(self) -> None:
        kernel = get_kernel()
        if not kernel or not kernel.cognition:
            raise RuntimeError("Kernel cognition not available")
        logger.info("CognitionEngine initialized")

    async def health(self) -> bool:
        kernel = get_kernel()
        if not kernel or not kernel.brain:
            return False
        return await kernel.brain.health()

    async def shutdown(self) -> None:
        logger.info("CognitionEngine shutdown")

    @property
    def _cognition(self) -> Cognition | None:
        k = get_kernel()
        return k.cognition if k else None

    async def chat_stream(self, message: str,
                          conversation_id: str | None = None) -> AsyncIterator[str]:
        cognition = self._cognition
        if not cognition:
            raise RuntimeError("Cognition not loaded")
        async for token in cognition.chat_stream(
            message=message, conversation_id=conversation_id or None,
        ):
            yield token
