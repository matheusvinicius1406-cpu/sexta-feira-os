"""
Speech-to-text — hearing, done locally.

Default engine: faster-whisper (Whisper running on your machine, offline). It is
an OPTIONAL extra: if the library or model isn't present, `available()` is False
and `transcribe()` raises VoiceUnavailable so the API can return a clean 503.
"""
from __future__ import annotations

import asyncio
import importlib.util
import io
import logging
from abc import ABC, abstractmethod

from app.core.config import settings

logger = logging.getLogger("sexta-feira.voice.stt")


class VoiceUnavailable(RuntimeError):
    """Raised when a voice engine (or its model) isn't installed/loadable."""


class Transcriber(ABC):
    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    async def transcribe(self, audio: bytes, language: str | None = None) -> str: ...


class FasterWhisperTranscriber(Transcriber):
    def __init__(self) -> None:
        self._model = None  # loaded lazily on first use

    def available(self) -> bool:
        return importlib.util.find_spec("faster_whisper") is not None

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        if not self.available():
            raise VoiceUnavailable(
                "faster-whisper não instalado. Rode: "
                "pip install -r requirements-voice.txt"
            )
        from faster_whisper import WhisperModel  # local, offline

        logger.info("Loading Whisper model '%s' (%s/%s)...",
                    settings.stt_model, settings.stt_device, settings.stt_compute_type)
        self._model = WhisperModel(
            settings.stt_model,
            device=settings.stt_device,
            compute_type=settings.stt_compute_type,
        )
        return self._model

    def _transcribe_sync(self, audio: bytes, language: str | None) -> str:
        model = self._ensure_model()
        segments, _ = model.transcribe(
            io.BytesIO(audio),
            language=language or settings.stt_language,
            vad_filter=True,
        )
        return "".join(seg.text for seg in segments).strip()

    async def transcribe(self, audio: bytes, language: str | None = None) -> str:
        # Whisper is CPU/GPU heavy and blocking → run off the event loop.
        return await asyncio.to_thread(self._transcribe_sync, audio, language)


def build_transcriber() -> Transcriber:
    # Only faster-whisper today; the interface keeps it swappable (Vosk, etc.).
    return FasterWhisperTranscriber()
