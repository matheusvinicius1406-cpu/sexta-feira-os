"""
MemoryExtractor — contract tests.

Deterministic (no Ollama): a fake brain returns canned JSON. They prove typed
facts are parsed defensively, routed to graph Memory and to the User Model,
deduplicated, capped, announced as an event — and that a failing extractor
never breaks the reply (cognition's best-effort guarantee).
"""
import asyncio
import json
import uuid

from app.brain.extractor import MemoryExtractor, _parse_candidates
from app.db.database import SessionLocal
from app.events.bus import EventBus
from app.models.models import Memory
from app.world.service import WorldModel

# Shared env + `client`/`owner_headers` fixtures live in conftest.py.


class _FakeBrain:
    """LocalBrain stand-in: returns a fixed reply from `chat`."""

    def __init__(self, reply: str):
        self.reply = reply

    async def chat(self, messages, temperature=0.1, max_tokens=400):
        return self.reply


class _FakeMemory:
    def __init__(self):
        self.saved: list[dict] = []

    async def remember(self, db, owner_id, content, kind="fact", importance=0.5, source="manual"):
        self.saved.append({"content": content, "kind": kind, "importance": importance})


# ---------- parsing (pure) ----------

def test_parse_valid_array():
    raw = json.dumps([
        {"fato": "Gosta de café forte pela manhã", "tipo": "preference", "importancia": 0.8},
        {"fato": "A irmã dele se chama Ana", "tipo": "person", "importancia": 0.7},
    ])
    out = _parse_candidates(raw)
    assert len(out) == 2
    assert out[0]["kind"] == "preference"
    assert out[1]["content"] == "A irmã dele se chama Ana"


def test_parse_tolerates_fences_and_prose():
    raw = 'Claro! Aqui está:\n```json\n[{"fato": "Estuda cálculo às terças", "tipo": "routine"}]\n```'
    out = _parse_candidates(raw)
    assert len(out) == 1
    assert out[0]["kind"] == "routine"


def test_parse_garbage_yields_nothing():
    assert _parse_candidates("NADA") == []
    assert _parse_candidates("{broken json") == []
    assert _parse_candidates('{"fato": "não é array"}') == []
    assert _parse_candidates("") == []


def test_parse_clamps_kind_importance_and_caps():
    items = [{"fato": f"Fato durável número {i}", "tipo": "invalido", "importancia": 9} for i in range(10)]
    out = _parse_candidates(json.dumps(items))
    assert len(out) == 5                      # MAX_FACTS cap
    assert all(c["kind"] == "fact" for c in out)       # unknown kind -> fact
    assert all(c["importance"] == 1.0 for c in out)    # clamped to 1.0


def test_parse_drops_short_facts():
    out = _parse_candidates(json.dumps([{"fato": "curto", "tipo": "fact"}]))
    assert out == []


# ---------- extraction + routing ----------

def test_extract_routes_to_memory_user_model_and_event():
    raw = json.dumps([
        {"fato": "Prefere Python tipado em tudo", "tipo": "preference",
         "importancia": 0.9, "chave_perfil": "estilo_programacao"},
        {"fato": "Treina na academia às 6h", "tipo": "routine", "importancia": 0.6},
    ])
    mem = _FakeMemory()
    world = WorldModel()
    bus = EventBus()
    seen: list[dict] = []
    bus.subscribe("memoria.extraida", lambda db, ev: seen.append(EventBus.decode_payload(ev)))
    ex = MemoryExtractor(_FakeBrain(raw), mem, world=world, events=bus)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        stored = asyncio.run(ex.extract(db, owner, "oi", "resposta"))
        attr = world.get_attribute(db, owner, "estilo_programacao")
        attr_val, attr_inf = (attr.value, attr.is_inference) if attr else (None, None)
    finally:
        db.close()
    assert stored == 2
    assert {m["kind"] for m in mem.saved} == {"preference", "routine"}
    assert attr_val == "Prefere Python tipado em tudo"
    assert attr_inf is True                    # extractor traits are labelled inference
    assert seen == [{"count": 2}]


def test_extract_skips_exact_duplicates():
    fact = "Gosta de música clássica no trabalho"
    raw = json.dumps([{"fato": fact, "tipo": "preference"}])
    mem = _FakeMemory()
    ex = MemoryExtractor(_FakeBrain(raw), mem)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        # Pre-existing identical memory in the real table -> extractor must skip it.
        db.add(Memory(id=str(uuid.uuid4()), owner_id=owner, content=fact, kind="preference"))
        db.commit()
        stored = asyncio.run(ex.extract(db, owner, "oi", "resposta"))
    finally:
        db.close()
    assert stored == 0
    assert mem.saved == []


def test_extract_garbage_stores_nothing_and_no_event():
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("memoria.extraida", lambda db, ev: seen.append(ev.type))
    ex = MemoryExtractor(_FakeBrain("resposta sem json nenhum"), _FakeMemory(), events=bus)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        stored = asyncio.run(ex.extract(db, owner, "oi", "resposta"))
    finally:
        db.close()
    assert stored == 0
    assert seen == []                          # no event when nothing was learned


def test_failing_extractor_never_breaks_the_reply():
    """Cognition guarantee: auto-learn is best-effort even if the extractor blows up."""
    from app.brain.cognition import Cognition

    class _Boom:
        async def extract(self, *a, **k):
            raise RuntimeError("kaboom")

    cog = Cognition(brain=None, memory=None, extractor=_Boom())
    db = SessionLocal()
    try:
        # Must not raise.
        asyncio.run(cog._auto_learn(db, "owner-x", "oi", "resposta"))
    finally:
        db.close()
