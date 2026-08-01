"""
VoiceAdapter — wraps the VoiceBox (STT + TTS) behind a clean interface.

Publishes events: voice.heard, voice.speaking.
"""
from __future__ import annotations

import logging

from app.adapters._events import publish_event
from app.core.di import get_kernel

logger = logging.getLogger("sexta-feira.adapter.voice")


class VoiceAdapter:
    """Adapter for voice (STT/TTS) operations."""

    def __init__(self) -> None:
        self._kernel = get_kernel()

    @property
    def _voice(self):
        return self._kernel.voice if self._kernel else None

    @property
    def available(self) -> bool:
        return self._voice is not None

    async def transcribe(self, audio_bytes: bytes) -> str | None:
        voice = self._voice
        if not voice or not voice.transcriber:
            return None
        transcript = await voice.transcriber.transcribe(audio_bytes)
        if transcript:
            await publish_event("voice.heard", {
                "transcript": transcript[:200],
                "confidence": getattr(voice.transcriber, "last_confidence", None),
            }, source="voice_adapter")
        return transcript

    async def speak(self, text: str) -> bytes | None:
        voice = self._voice
        if not voice or not voice.synthesizer:
            return None
        await publish_event("voice.speaking", {
            "text_length": len(text),
            "text_preview": text[:200],
        }, source="voice_adapter")
        return await voice.synthesizer.speak(text)

    async def chat(self, audio_bytes: bytes) -> dict | None:
        """Full voice cycle: transcribe → think → speak. Returns transcript + audio."""
        voice = self._voice
        if not voice:
            return None

        # STT
        transcript = await self.transcribe(audio_bytes)
        if not transcript:
            return None

        # Brain reply
        from app.core.di import get_cognition
        cognition = get_cognition()
        reply = ""
        if cognition:
            async for token in cognition.chat_stream(message=transcript):
                reply += token

        # TTS
        audio_reply = await self.speak(reply) if reply else None

        return {"transcript": transcript, "reply": reply, "audio": audio_reply}
