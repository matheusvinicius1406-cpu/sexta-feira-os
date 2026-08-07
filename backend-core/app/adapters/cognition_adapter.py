"""
CognitionAdapter — wraps the brain (Ollama) and cognition loop.

gRPC/REST callers go through this adapter instead of accessing
LocalBrain / Cognition directly.

Publishes events: brain.thinking, brain.tool_call, brain.reply.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from app.adapters._events import publish_event
from app.core.di import get_kernel

logger = logging.getLogger("sexta-feira.adapter.cognition")


class CognitionAdapter:
    """Adapter for brain/cognition operations."""

    def __init__(self) -> None:
        self._kernel = get_kernel()

    @property
    def _cognition(self):
        return self._kernel.cognition if self._kernel else None

    @property
    def _brain(self):
        return self._kernel.brain if self._kernel else None

    async def check_health(self) -> bool:
        brain = self._brain
        if not brain:
            return False
        return await brain.health()

    async def chat_stream(self, message: str,
                          conversation_id: str | None = None) -> AsyncIterator[str]:
        """Stream chat tokens from the cognition loop.

        Publishes brain.thinking before streaming and brain.reply after.
        """
        cognition = self._cognition
        if not cognition:
            raise RuntimeError("Cognition not loaded")

        await publish_event("brain.thinking", {
            "message": message[:200],
            "conversation_id": conversation_id,
        }, source="cognition_adapter")

        reply_parts: list[str] = []
        async for token in cognition.chat_stream(
            message=message,
            conversation_id=conversation_id or None,
        ):
            reply_parts.append(token)
            yield token

        # Publish reply event after streaming completes
        full_reply = "".join(reply_parts)
        if full_reply:
            await publish_event("brain.reply", {
                "reply_length": len(full_reply),
                "reply_preview": full_reply[:200],
                "conversation_id": conversation_id,
            }, source="cognition_adapter")
