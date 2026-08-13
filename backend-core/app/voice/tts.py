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
        """Render `text` to a complete WAV in memory.

        `synthesize_wav` is the method that writes into a wave file. Piper's
        `synthesize` changed meaning in 1.3: it now takes a SynthesisConfig as
        its second argument and RETURNS an iterator of audio chunks. Calling the
        old `synthesize(text, wav)` against a modern piper therefore passes the
        wave file where a config belongs and never consumes the iterator, so
        nothing is ever written — the failure surfaces far away as
        `wave.Error: # channels not specified`, with no mention of piper.
        """
        voice = self._ensure_voice()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            voice.synthesize_wav(text, wav)
        audio = buf.getvalue()
        if not audio.startswith(b"RIFF"):
            raise VoiceUnavailable("Piper devolveu áudio sem cabeçalho WAV.")
        return audio

    async def speak(self, text: str) -> bytes:
        return await asyncio.to_thread(self._speak_sync, text)


class VoiceBoxSynthesizer(Synthesizer):
    """TTS via jamiepine/voicebox REST API — 7 engines, voice cloning, local."""

    def available(self) -> bool:
        # Optimistically report available when voicebox_enabled.
        # Actual connectivity is checked in speak(); failures
        # raise VoiceUnavailable → API returns clean 503.
        return True

    async def speak(self, text: str) -> bytes:
        from app.voice.voicebox_adapter import synthesize
        audio = await synthesize(text)
        if audio is None:
            raise VoiceUnavailable(
                "VoiceBox indisponível. Verifique se o servidor VoiceBox "
                f"está rodando em {settings.voicebox_endpoint}"
            )
        return audio


class EdgeTTSSynthesizer(Synthesizer):
    """TTS via Microsoft Edge neural voices — no GPU, works on Python 3.14."""

    def __init__(self) -> None:
        self._impl = None

    def available(self) -> bool:
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            return False

    async def speak(self, text: str) -> bytes:
        from app.voice.edge_tts_adapter import EdgeTTSSynthesizer
        if self._impl is None:
            self._impl = EdgeTTSSynthesizer()
        return await self._impl.speak(text)


def build_synthesizer() -> Synthesizer:
    from app.core.config import settings
    # Build priority list based on config
    engine = settings.tts_engine.lower()
    if engine == "voicebox" and settings.voicebox_enabled:
        return VoiceBoxSynthesizer()
    if engine == "edge":
        s = EdgeTTSSynthesizer()
        if s.available():
            return s
    if engine == "piper":
        return PiperSynthesizer()
    # Auto-detect: EdgeTTS > Piper > VoiceBox
    edge = EdgeTTSSynthesizer()
    if edge.available():
        return edge
    return PiperSynthesizer()
