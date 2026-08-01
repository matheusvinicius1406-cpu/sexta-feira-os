"""
VoiceBox — the kernel's ears and mouth. Holds the (lazy) STT and TTS engines.
Building the box is cheap; heavy models load only on first use.

Engine hierarchy (when voicebox_enabled=True):
  TTS: VoiceBox (7 engines, voice cloning) → Piper (fallback)
  STT: VoiceBox (Whisper) → faster-whisper (fallback)

Voice packs provide predefined personality responses (greeting, farewell, etc.).
"""
from __future__ import annotations

import logging

from app.core.config import settings
from app.voice.stt import Transcriber, build_transcriber
from app.voice.tts import Synthesizer, build_synthesizer
from app.voice.voice_packs import VoicePack, get_pack

logger = logging.getLogger("sexta-feira.voice.box")


class VoiceBox:
    def __init__(self) -> None:
        self.transcriber: Transcriber = build_transcriber()
        self.synthesizer: Synthesizer = build_synthesizer()
        self._pack: VoicePack | None = None
        self._pack_name: str = settings.voicebox_voice_profile or "jarvis"

    @property
    def pack(self) -> VoicePack:
        """The active voice pack for personality responses."""
        if self._pack is None:
            self._pack = get_pack(self._pack_name)
        return self._pack

    def set_pack(self, name: str) -> None:
        """Switch the active voice pack."""
        self._pack = get_pack(name)
        self._pack_name = name
        logger.info("Voice pack switched to '%s'", name)

    def status(self) -> dict:
        voicebox_status = "unknown"
        if settings.voicebox_enabled:
            voicebox_status = "enabled"  # actual health checked async
        return {
            "stt_available": self.transcriber.available(),
            "tts_available": self.synthesizer.available(),
            "voicebox_enabled": settings.voicebox_enabled,
            "voicebox_status": voicebox_status,
            "tts_engine": settings.tts_engine,
            "voice_pack": self.pack.name,
        }
