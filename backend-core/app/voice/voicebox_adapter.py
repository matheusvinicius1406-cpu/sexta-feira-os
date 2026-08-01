"""
VoiceBox adapter — wraps jamiepine/voicebox REST API for TTS and STT.

VoiceBox runs as a separate process (http://127.0.0.1:17493) and exposes:
  POST /speak      — text → audio (WAV)
  POST /generate   — text + voice profile → audio
  POST /transcribe — audio → text

When voicebox_enabled=True, this adapter replaces Piper (TTS) and faster-whisper (STT)
as the primary voice engine, falling back to them when VoiceBox is unavailable.
"""
from __future__ import annotations

import asyncio
import io
import logging
from pathlib import Path

import httpx

from app.core.config import settings

logger = logging.getLogger("sexta-feira.voice.voicebox")

# VoiceBox REST API client (lazy, async)
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.voicebox_endpoint,
            timeout=httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


# ── Health check ──────────────────────────────────────────


async def is_available() -> bool:
    """Check if VoiceBox server is reachable."""
    try:
        resp = await _get_client().get("/health")
        return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException, Exception):
        return False


# ── TTS ───────────────────────────────────────────────────


async def synthesize(
    text: str,
    engine: str | None = None,
    voice_profile: str | None = None,
) -> bytes | None:
    """
    Synthesize text to WAV audio via VoiceBox.

    Returns raw WAV bytes, or None on failure.
    """
    try:
        payload: dict = {"text": text}
        if engine or settings.voicebox_tts_engine:
            payload["engine"] = engine or settings.voicebox_tts_engine
        if voice_profile or settings.voicebox_voice_profile:
            payload["voice_profile"] = voice_profile or settings.voicebox_voice_profile

        resp = await _get_client().post("/speak", json=payload)
        resp.raise_for_status()
        return resp.content
    except httpx.HTTPStatusError as e:
        logger.warning("VoiceBox TTS HTTP %s: %s", e.response.status_code, e.response.text[:200])
        return None
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning("VoiceBox TTS unavailable: %s", e)
        return None
    except Exception as e:
        logger.error("VoiceBox TTS error: %s", e)
        return None


async def synthesize_with_clone(
    text: str,
    reference_audio: bytes,
    engine: str | None = None,
) -> bytes | None:
    """
    Synthesize text using voice cloning with a reference audio sample.
    Uses VoiceBox's /generate endpoint with reference audio.
    """
    try:
        payload: dict = {"text": text}
        if engine or settings.voicebox_tts_engine:
            payload["engine"] = engine or settings.voicebox_tts_engine

        # Send reference audio as multipart form data
        files = {"reference_audio": ("reference.wav", reference_audio, "audio/wav")}
        data = {"text": text}
        if engine or settings.voicebox_tts_engine:
            data["engine"] = engine or settings.voicebox_tts_engine

        resp = await _get_client().post("/generate", data=data, files=files)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logger.warning("VoiceBox clone synthesis failed: %s", e)
        return None


# ── STT ───────────────────────────────────────────────────


async def transcribe(
    audio: bytes,
    language: str | None = None,
) -> str | None:
    """
    Transcribe audio to text via VoiceBox's Whisper integration.

    Returns transcribed text, or None on failure.
    """
    try:
        files = {"audio": ("audio.wav", audio, "audio/wav")}
        data: dict = {}
        if language:
            data["language"] = language

        resp = await _get_client().post("/transcribe", data=data, files=files)
        resp.raise_for_status()
        result = resp.json()
        return result.get("text", "")
    except httpx.HTTPStatusError as e:
        logger.warning("VoiceBox STT HTTP %s: %s", e.response.status_code, e.response.text[:200])
        return None
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning("VoiceBox STT unavailable: %s", e)
        return None
    except Exception as e:
        logger.error("VoiceBox STT error: %s", e)
        return None



