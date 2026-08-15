"""
Voice packs carry the actual TTS voice — each pack defines the Edge neural
voice, rate and pitch it speaks with, and switching packs reconfigures the
synthesizer so "usar voz militar" changes how Jarvis sounds, not just phrases.
"""
from app.voice.box import VoiceBox
from app.voice.voice_packs import get_pack, list_packs

# ── pack → voice mapping ──────────────────────────────────


def test_every_pack_carries_a_tts_voice():
    for key in ("jarvis", "friendly", "military"):
        pack = get_pack(key)
        assert pack.tts_voice.startswith("pt-BR-"), key
        assert pack.tts_rate
        assert pack.tts_pitch


def test_packs_have_distinct_voices():
    jarvis = get_pack("jarvis")
    friendly = get_pack("friendly")
    military = get_pack("military")
    assert jarvis.tts_voice == "pt-BR-AntonioNeural"
    assert friendly.tts_voice == "pt-BR-FranciscaNeural"
    assert military.tts_voice == "pt-BR-AntonioNeural"
    assert military.tts_rate != jarvis.tts_rate  # deeper/slower than classic
    assert military.tts_pitch != jarvis.tts_pitch


def test_list_packs_exposes_the_voice():
    packs = {p["key"]: p for p in list_packs()}
    assert packs["friendly"]["tts_voice"] == "pt-BR-FranciscaNeural"
    assert packs["jarvis"]["tts_rate"] == "-10%"


# ── switching packs reconfigures the synthesizer ──────────


class _RecordingSynth:
    """Stands in for the Edge synthesizer: records configure() calls."""

    def __init__(self):
        self.calls = []

    def configure(self, voice=None, rate=None, pitch=None):
        self.calls.append({"voice": voice, "rate": rate, "pitch": pitch})


def test_set_pack_reconfigures_the_synthesizer():
    box = VoiceBox()
    synth = _RecordingSynth()
    box.synthesizer = synth  # not the real Edge adapter, but the same contract

    box.set_pack("friendly")
    assert synth.calls == [
        {"voice": "pt-BR-FranciscaNeural", "rate": "-5%", "pitch": "+2Hz"}
    ]

    box.set_pack("military")
    assert synth.calls[-1] == {
        "voice": "pt-BR-AntonioNeural", "rate": "-20%", "pitch": "-10Hz"
    }
