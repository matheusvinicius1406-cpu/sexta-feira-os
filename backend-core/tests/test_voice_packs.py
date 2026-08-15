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


# ── character packs (ultron, alfred) ──────────────────────


def test_character_packs_exist_with_voice_and_persona():
    for key in ("jarvis", "ultron", "alfred"):
        pack = get_pack(key)
        assert pack.voice_profile, f"{key} sem perfil de clonagem"
        assert pack.persona, f"{key} sem persona para fala aberta"
        assert "ultron" not in key or pack.tts_pitch == "-12Hz"
        assert "alfred" not in key or pack.tts_rate == "-20%"


def test_ultron_and_alfred_are_distinct_from_jarvis():
    j, u, a = get_pack("jarvis"), get_pack("ultron"), get_pack("alfred")
    assert u.tts_pitch != j.tts_pitch and u.tts_rate != j.tts_rate
    assert a.tts_rate != j.tts_rate and a.tts_rate != u.tts_rate
    assert u.persona and u.persona != j.persona
    assert a.persona and a.persona != j.persona


def test_pack_response_carries_persona_and_profile(client, owner_headers):
    r = client.get("/api/v1/voice/packs/ultron", headers=owner_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Ultron"
    assert body["voice_profile"] == "dondi-ultron"
    assert body["persona"]
    assert "Ultron" in body["persona"]


# ── switching packs reconfigures the synthesizer ──────────


class _RecordingSynth:
    """Stands in for the Edge synthesizer: records configure() calls."""

    def __init__(self):
        self.calls = []

    def configure(self, voice=None, rate=None, pitch=None, voice_profile=None):
        self.calls.append({"voice": voice, "rate": rate, "pitch": pitch, "voice_profile": voice_profile})


def test_set_pack_reconfigures_the_synthesizer():
    box = VoiceBox()
    synth = _RecordingSynth()
    box.synthesizer = synth  # not the real Edge adapter, but the same contract

    box.set_pack("friendly")
    assert synth.calls == [
        {"voice": "pt-BR-FranciscaNeural", "rate": "-5%", "pitch": "+2Hz", "voice_profile": None}
    ]

    box.set_pack("military")
    assert synth.calls[-1] == {
        "voice": "pt-BR-AntonioNeural", "rate": "-20%", "pitch": "-10Hz", "voice_profile": None
    }


def test_set_pack_passes_the_voicebox_profile():
    box = VoiceBox()
    synth = _RecordingSynth()
    box.synthesizer = synth
    box.set_pack("ultron")
    assert synth.calls[-1]["voice_profile"] == "dondi-ultron"
    box.set_pack("alfred")
    assert synth.calls[-1]["voice_profile"] == "padua-alfred"


# ── persona → open dialogue ───────────────────────────────


class _FakeMemory:
    async def recall_graph(self, db, owner_id, text):
        return []


class _FakeWorld:
    def context_digest(self, db, owner_id):
        return None


class _FakeConv:
    id = "c1"
    messages = []


def _messages(persona=None):
    import asyncio

    from app.brain.cognition import Cognition
    from app.core.config import settings

    c = Cognition(brain=None, memory=_FakeMemory(), world=_FakeWorld())
    return asyncio.run(c._build_messages(None, "owner", _FakeConv(), "oi", persona=persona)), settings


def test_persona_colors_open_dialogue(monkeypatch):
    monkeypatch.setattr("app.brain.cognition.settings.obsidian_vault_path", "")
    msgs, _ = _messages(persona=get_pack("ultron").persona)
    system = msgs[0]["content"]
    assert system.startswith(get_pack("ultron").persona)
    assert "Ultron" in system


def test_no_persona_falls_back_to_brain_persona(monkeypatch):
    monkeypatch.setattr("app.brain.cognition.settings.obsidian_vault_path", "")
    from app.core.config import settings
    msgs, _ = _messages()
    assert msgs[0]["content"] == settings.brain_persona
