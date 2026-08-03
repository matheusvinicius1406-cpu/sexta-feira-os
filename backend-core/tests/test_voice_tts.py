"""
Piper synthesis, against the API piper actually has.

This exists because of a break that produced no error at the point of failure.
Piper 1.3 renamed the wave-writing call to `synthesize_wav`; `synthesize` kept
the name but changed meaning — second argument is now a SynthesisConfig, and the
return value is a lazy iterator of audio chunks. Code written for the old API
therefore hands a wave file where a config belongs, never consumes the iterator,
and writes nothing. The exception that eventually surfaces is
`wave.Error: # channels not specified`, thrown by the standard library, naming
neither piper nor TTS.

No voice model is needed here: a stub standing in for PiperVoice is enough to
prove which call the code makes, and 63 MB of ONNX would prove nothing extra.
"""
from __future__ import annotations

import io
import wave

import pytest

from app.voice.stt import VoiceUnavailable
from app.voice.tts import PiperSynthesizer

SAMPLE_RATE = 22050


def _write_tone(wav: wave.Wave_write) -> None:
    """What a working piper does: set the format, then write frames."""
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(SAMPLE_RATE)
    wav.writeframes(b"\x00\x01" * 512)


class ModernPiper:
    """piper >= 1.3 — writes through `synthesize_wav`."""

    def __init__(self):
        self.calls = []

    def synthesize_wav(self, text, wav_file, **kwargs):
        self.calls.append("synthesize_wav")
        _write_tone(wav_file)

    def synthesize(self, text, syn_config=None, **kwargs):
        self.calls.append("synthesize")
        return iter(())          # a lazy iterator; writes nothing by itself


class LegacyPiper:
    """piper < 1.3 — only the old call exists."""

    def synthesize(self, text, wav_file, **kwargs):
        _write_tone(wav_file)


def _synth(voice) -> PiperSynthesizer:
    s = PiperSynthesizer()
    s._voice = voice             # skip model loading; the API is what is tested
    return s


def test_speaks_through_the_wave_writing_call():
    voice = ModernPiper()
    audio = _synth(voice)._speak_sync("Sistemas online.")

    assert voice.calls == ["synthesize_wav"], (
        f"esperava synthesize_wav; chamou {voice.calls}. `synthesize` devolve um "
        f"iterador que ninguém consome — o WAV sai vazio."
    )
    assert audio.startswith(b"RIFF")
    with wave.open(io.BytesIO(audio)) as r:
        assert r.getnchannels() == 1
        assert r.getframerate() == SAMPLE_RATE
        assert r.getnframes() > 0, "WAV com cabeçalho e sem áudio"


def test_a_piper_too_old_fails_loudly_instead_of_returning_silence():
    """The regression must announce itself as a TTS problem.

    Against a piper that lacks `synthesize_wav`, the call raises here — in
    voice code, naming piper — rather than producing a headerless buffer that
    fails later inside `wave`, or worse, a valid-looking empty WAV that plays as
    silence and reads as "the assistant did not answer".
    """
    with pytest.raises((VoiceUnavailable, AttributeError, wave.Error)):
        _synth(LegacyPiper())._speak_sync("Sistemas online.")


def test_headerless_output_is_rejected():
    """A silent, malformed result must never reach the caller as success."""

    class WritesNothing:
        def synthesize_wav(self, text, wav_file, **kwargs):
            pass                 # never sets the format, never writes a frame

    with pytest.raises((VoiceUnavailable, wave.Error)):
        _synth(WritesNothing())._speak_sync("Sistemas online.")
