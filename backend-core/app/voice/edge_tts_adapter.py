"""
EdgeTTS adapter — Microsoft Edge neural voices via edge-tts.

This is the most practical TTS option for the Sexta-Feira kernel:
  - Works on Python 3.14 (no numpy/Cython issues)
  - No GPU required
  - Supports Portuguese (pt-BR-AntonioNeural, pt-BR-FranciscaNeural)
  - Natural-sounding neural voices
  - Free, no API key needed

Requires: pip install edge-tts
"""
from __future__ import annotations

import asyncio
import logging
import subprocess

import edge_tts

from app.voice.stt import VoiceUnavailable

logger = logging.getLogger("sexta-feira.voice.edge_tts")

DEFAULT_VOICE = "pt-BR-AntonioNeural"

# JARVIS MCU voice settings: calm, authoritative, slightly deeper
JARVIS_RATE = "-10%"  # Slightly slower
JARVIS_PITCH = "-5Hz"  # Slightly deeper




class EdgeTTSSynthesizer:
    """TTS via Microsoft Edge neural voices — fast, natural, offline-capable after first call."""

    def __init__(self, voice: str = DEFAULT_VOICE, rate: str = JARVIS_RATE, pitch: str = JARVIS_PITCH):
        self._voice = voice
        self._rate = rate
        self._pitch = pitch

    def available(self) -> bool:
        """Always available if edge-tts is installed."""
        return True

    async def speak(self, text: str) -> bytes:
        """Synthesize text to WAV audio bytes.

        JARVIS MCU voice characteristics:
        - Slightly deeper pitch (-5Hz)
        - Slightly slower rate (-10%)
        - Male, authoritative, calm tone (pt-BR-AntonioNeural)
        """
        try:
            communicate = edge_tts.Communicate(
                text, self._voice,
                rate=self._rate,
                pitch=self._pitch,
            )
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            if not audio_data:
                raise VoiceUnavailable("EdgeTTS returned no audio")

            # edge-tts returns MP3; convert to WAV for compatibility
            wav_bytes = await self._convert_to_wav(audio_data)
            logger.info("EdgeTTS: %d chars -> %d bytes WAV", len(text), len(wav_bytes))
            return wav_bytes

        except VoiceUnavailable:
            raise
        except Exception as e:
            raise VoiceUnavailable(f"EdgeTTS failed: {e}") from e

    async def _convert_to_wav(self, mp3_bytes: bytes) -> bytes:
        """Convert MP3 bytes to WAV using ffmpeg. Returns WAV bytes.
        Raises VoiceUnavailable if ffmpeg is missing or conversion fails."""
        try:
            return await asyncio.to_thread(self._convert_to_wav_sync, mp3_bytes)
        except VoiceUnavailable:
            raise
        except Exception as e:
            raise VoiceUnavailable(f"MP3->WAV conversion failed: {e}") from e

    def _convert_to_wav_sync(self, mp3_bytes: bytes) -> bytes:
        """Runs off the event loop (see _convert_to_wav): uvicorn pins Windows to
        `WindowsSelectorEventLoopPolicy` (uvicorn/loops/asyncio.py), which does not
        implement `asyncio.create_subprocess_exec` — every call raised a bare
        `NotImplementedError()` (empty message) before ffmpeg ever ran, on every
        platform this kernel actually ships for. The blocking `subprocess` module
        has no such restriction; `asyncio.to_thread` is what keeps it off the loop.
        """
        try:
            proc = subprocess.run(
                ["ffmpeg", "-i", "pipe:0",
                 "-ar", "24000", "-ac", "1", "-sample_fmt", "s16",
                 "-f", "wav", "pipe:1"],
                input=mp3_bytes, capture_output=True, check=False,
            )
        except FileNotFoundError:
            raise VoiceUnavailable("ffmpeg not found — install ffmpeg for WAV output") from None
        if proc.returncode == 0 and len(proc.stdout) > 44 and proc.stdout[:4] == b'RIFF':
            return proc.stdout
        raise VoiceUnavailable(f"ffmpeg conversion failed (code {proc.returncode})")

    def set_voice(self, voice: str) -> None:
        """Switch the active voice."""
        self._voice = voice
        logger.info("EdgeTTS voice switched to %s", voice)


def build_edge_tts() -> EdgeTTSSynthesizer:
    """Build an EdgeTTS synthesizer with the default Portuguese voice."""
    return EdgeTTSSynthesizer()
