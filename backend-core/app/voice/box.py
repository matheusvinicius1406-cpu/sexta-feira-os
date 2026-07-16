"""
VoiceBox — the kernel's ears and mouth. Holds the (lazy) STT and TTS engines.
Building the box is cheap; heavy models load only on first use.
"""
from __future__ import annotations

from app.voice.stt import Transcriber, build_transcriber
from app.voice.tts import Synthesizer, build_synthesizer


class VoiceBox:
    def __init__(self) -> None:
        self.transcriber: Transcriber = build_transcriber()
        self.synthesizer: Synthesizer = build_synthesizer()

    def status(self) -> dict:
        return {
            "stt_available": self.transcriber.available(),
            "tts_available": self.synthesizer.available(),
        }
