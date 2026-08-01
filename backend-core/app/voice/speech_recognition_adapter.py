"""
SpeechRecognition adapter — lightweight STT using Google's free API.

Works on Python 3.14, no GPU needed, no heavy ML dependencies.
Uses Google's free speech recognition API (requires internet).
"""
from __future__ import annotations

import asyncio
import io
import logging

import speech_recognition as sr

from app.voice.stt import VoiceUnavailable

logger = logging.getLogger("sexta-feira.voice.speech_recognition")


class SpeechRecognitionTranscriber:
    """STT via Google's free speech recognition API."""

    def __init__(self, language: str = "pt-BR"):
        self._language = language
        self._recognizer = sr.Recognizer()

    def available(self) -> bool:
        return True

    async def transcribe(self, audio: bytes, language: str | None = None) -> str:
        lang = language or self._language
        try:
            # Convert audio bytes to AudioData
            # speech_recognition expects WAV, so we use ffmpeg to convert if needed
            wav_bytes = await self._ensure_wav(audio)
            
            audio_data = sr.AudioData(wav_bytes, sample_rate=16000, sample_width=2)
            
            # Run recognition in thread pool (blocking API call)
            text = await asyncio.to_thread(
                self._recognizer.recognize_google,
                audio_data,
                language=lang,
            )
            
            logger.info("SpeechRecognition: %d bytes -> '%s'", len(audio), text[:100])
            return text

        except sr.UnknownValueError:
            raise VoiceUnavailable("Não consegui entender o áudio. Tente falar mais alto.")
        except sr.RequestError as e:
            raise VoiceUnavailable(f"Erro no serviço de reconhecimento: {e}")
        except VoiceUnavailable:
            raise
        except Exception as e:
            raise VoiceUnavailable(f"SpeechRecognition falhou: {e}") from e

    async def _ensure_wav(self, audio: bytes) -> bytes:
        """Convert audio to WAV format if needed."""
        if audio[:4] == b'RIFF':
            return audio  # Already WAV
        
        # Use ffmpeg to convert
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-i", "pipe:0",
                "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
                "-f", "wav", "pipe:1",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate(input=audio)
            if proc.returncode == 0 and len(stdout) > 44:
                return stdout
        except FileNotFoundError:
            pass
        
        # If ffmpeg fails, try using audio as-is (might be WAV)
        return audio
