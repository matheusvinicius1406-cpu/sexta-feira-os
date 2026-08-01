"""
VoiceEngine — formal engine wrapping VoiceBox behind IEngine.

Publishes: voice.heard, voice.transcribing, voice.speaking, voice.finished
"""
from __future__ import annotations

import logging

from app.core.di import get_kernel
from app.engines import IEngine
from app.voice.box import VoiceBox

logger = logging.getLogger("sexta-feira.engine.voice")


class VoiceEngine(IEngine):
    """Formal Voice Engine — wraps VoiceBox with lifecycle."""

    @property
    def name(self) -> str:
        return "Voice"

    @property
    def available(self) -> bool:
        return self._voice is not None

    async def initialize(self) -> None:
        kernel = get_kernel()
        if not kernel or not kernel.voice:
            logger.warning("VoiceEngine: voice not available (may be offline)")
        else:
            logger.info("VoiceEngine initialized")

    async def health(self) -> bool:
        return self._voice is not None

    async def shutdown(self) -> None:
        logger.info("VoiceEngine shutdown")

    @property
    def _voice(self) -> VoiceBox | None:
        k = get_kernel()
        return k.voice if k else None

    async def transcribe(self, audio_bytes: bytes) -> str | None:
        voice = self._voice
        if not voice or not voice.transcriber:
            return None
        return await voice.transcriber.transcribe(audio_bytes)

    async def speak(self, text: str) -> bytes | None:
        voice = self._voice
        if not voice or not voice.synthesizer:
            return None
        return await voice.synthesizer.speak(text)
