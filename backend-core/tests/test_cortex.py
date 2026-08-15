"""
Cortex — the hand-built brain. These tests pin the deterministic grammar:
same phrase, same intent, every time. No statistics, no model — if a pattern
matches, the intent is born with a trace; otherwise the cortex says "não
entendi" and lists what it knows.
"""
from app.cortex import VERBS, parse
from app.cortex.intent import Intent


def _p(text: str) -> Intent | None:
    return parse(VERBS, text)


# ── música / rádio ────────────────────────────────────────


def test_playlist_cases_before_generic_play():
    it = _p("tocar a playlist treino")
    assert it and it.verb == "tocar_playlist" and it.target == "treino"

    it = _p("toca playlist foco")
    assert it and it.verb == "tocar_playlist" and it.target == "foco"


def test_preset_cases_before_generic_play():
    it = _p("tocar o preset 3")
    assert it and it.verb == "tocar_preset" and it.target == "3"

    it = _p("estação 7")
    assert it and it.verb == "tocar_preset" and it.target == "7"


def test_generic_play_catches_music_search():
    it = _p("tocar rock clássico")
    assert it and it.verb == "tocar" and it.target == "rock clássico"

    it = _p("pode tocar lo-fi para estudar")
    assert it and it.verb == "tocar" and it.target == "lo-fi para estudar"


def test_colar_link():
    it = _p("colar https://youtu.be/abc123")
    assert it and it.verb == "colar" and it.target.startswith("http")


def test_volume_modes():
    it = _p("volume 50")
    assert it and it.verb == "volume" and it.target == "50"

    it = _p("aumenta o volume")
    assert it and it.verb == "volume" and it.target is None

    it = _p("abaixar o som")
    assert it and it.verb == "volume"


def test_skip_and_stop():
    it = _p("pular")
    assert it and it.verb == "pular"

    it = _p("próxima música")
    assert it and it.verb == "pular"

    it = _p("para a música")
    assert it and it.verb == "parar"


def test_save_playlist_and_modes():
    it = _p("salvar playlist treino")
    assert it and it.verb == "salvar_playlist" and it.target == "treino"

    it = _p("embaralhar")
    assert it and it.verb == "modo" and it.target == "embaralhar"

    it = _p("adblock ligar")
    assert it and it.verb == "modo" and it.target == "ligar"


# ── voz / persona ─────────────────────────────────────────


def test_voice_pack_switching():
    it = _p("usar voz ultron")
    assert it and it.verb == "voz" and it.target == "ultron"

    it = _p("fala como o alfred")
    assert it and it.verb == "voz" and it.target == "alfred"

    it = _p("voz jarvis")
    assert it and it.verb == "voz" and it.target == "jarvis"


def test_falar_open_text():
    it = _p("fala bom dia")
    assert it and it.verb == "falar" and it.target == "bom dia"

    it = _p("diga que o café está pronto")
    assert it and it.verb == "falar" and it.target == "que o café está pronto"


# ── memória / metas ───────────────────────────────────────


def test_memory_verbs():
    it = _p("guarda que tenho reunião às 9")
    assert it and it.verb == "guardar" and "reunião" in it.target

    it = _p("esquece que tenho reunião às 9")
    assert it and it.verb == "esquecer" and "reunião" in it.target


def test_goal_verbs():
    it = _p("criar meta ler 20 páginas por dia")
    assert it and it.verb == "criar_meta" and it.target == "ler 20 páginas por dia"

    it = _p("concluir meta ler 20 páginas")
    assert it and it.verb == "concluir_meta"


# ── informação e honestidade ──────────────────────────────


def test_hora_and_status():
    it = _p("que horas são")
    assert it and it.verb == "hora"

    it = _p("como está o sistema")
    assert it and it.verb == "status"


def test_unknown_text_returns_none_honestly():
    assert _p("escreve um poema sobre o mar") is None
    assert _p("conte uma piada") is None
    assert _p("") is None


def test_punctuation_and_case_are_cleaned():
    it = _p("TOQUE ROCK!")
    assert it and it.verb == "tocar" and it.target.lower() == "rock"


def test_intent_carries_trace():
    it = _p("tocar a playlist treino")
    assert it.trace and it.trace[0].startswith("tocar_playlist:padrão")


# ── API ───────────────────────────────────────────────────


def test_cortex_verbs_endpoint(client, owner_headers):
    r = client.get("/api/v1/cortex/verbs", headers=owner_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["engine"] == "symbolic"
    assert body["count"] == len(VERBS) > 10
    names = {v["name"] for v in body["verbs"]}
    assert {"tocar", "voz", "hora", "guardar", "criar_meta"} <= names


def test_cortex_intent_understood(client, owner_headers):
    r = client.post("/api/v1/cortex/intent", json={"text": "que horas são"}, headers=owner_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["understood"] is True
    assert body["verb"] == "hora"
    assert body["response"]  # honest answer text
    assert body["trace"]


def test_cortex_intent_unknown_is_honest(client, owner_headers):
    r = client.post(
        "/api/v1/cortex/intent", json={"text": "escreve um poema"}, headers=owner_headers
    )
    assert r.status_code == 200
    body = r.json()
    assert body["understood"] is False
    assert body["known"]  # lists what it can do
    assert body["response"] is None
