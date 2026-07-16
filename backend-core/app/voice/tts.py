"""
Text-to-speech — speaking, done locally.

Default engine: Piper (fast, natural, fully offline). Optional extra: if the
library or the voice model (.onnx) isn't present, `available()` is False and
`speak()` raises VoiceUnavailable so the API returns a clean 503.
"""
from __future__ import annotations

import asyncio
import importlib.util
import io
import logging
import wave
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings
from app.voice.stt import VoiceUnavailable

logger = logging.getLogger("sexta-feira.voice.tts")


class Synthesizer(ABC):
    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    async def speak(self, text: str) -> bytes:
        """Return WAV audio bytes for `text`."""


class PiperSynthesizer(Synthesizer):
    def __init__(self) -> None:
        self._voice = None

    def available(self) -> bool:
        has_lib = importlib.util.find_spec("piper") is not None
        has_voice = bool(settings.tts_voice) and Path(settings.tts_voice).exists()
        return has_lib and has_voice

    def _ensure_voice(self):
        if self._voice is not None:
            return self._voice
        if importlib.util.find_spec("piper") is None:
            raise VoiceUnavailable(
                "piper-tts não instalado. Rode: pip install -r requirements-voice.txt"
            )
        if not settings.tts_voice or not Path(settings.tts_voice).exists():
            raise VoiceUnavailable(
                "Voz do Piper não configurada. Baixe um modelo .onnx e aponte "
                "TTS_VOICE para ele no .env (ex.: pt_BR-faber-medium.onnx)."
            )
        from piper import PiperVoice  # local, offline

        logger.info("Loading Piper voice: %s", settings.tts_voice)
        self._voice = PiperVoice.load(settings.tts_voice)
        return self._voice

    def _speak_sync(self, text: str) -> bytes:
        voice = self._ensure_voice()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            voice.synthesize(text, wav)
        return buf.getvalue()

    async def speak(self, text: str) -> bytes:
        return await asyncio.to_thread(self._speak_sync, text)


def build_synthesizer() -> Synthesizer:
    return PiperSynthesizer()
