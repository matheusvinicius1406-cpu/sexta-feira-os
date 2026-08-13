"""
Learning Engine — contract and API tests.

Deterministic (no Ollama). They prove the continuous-learning loop: an outcome is
recorded with a quality score, a durable lesson lands in graph Memory, a recurring
low-quality tag flags a difficulty in the User Model, an event is emitted, and the
Decision feedback path works. Fully local — no cloud, no external calls.
"""
import asyncio
import uuid

from app.db.database import SessionLocal
from app.events.bus import EventBus
from app.learning.service import LearningEngine
from app.world.service import WorldModel

# Shared env + `client`/`owner_headers` fixtures live in conftest.py.


class _FakeMemory:
    """Minimal PersistentMemory stand-in: records what would be remembered."""

    def __init__(self):
        self.remembered: list[str] = []

    async def remember(self, db, owner_id, content, kind="fact", importance=0.5, source="manual"):
        self.remembered.append(content)


# ---------- service ----------

def test_record_persists_and_emits_and_remembers():
    mem = _FakeMemory()
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("aprendizado.registrado", lambda db, ev: seen.append(ev.type))
    eng = LearningEngine(memory=mem, world=WorldModel(), events=bus)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        x = asyncio.run(eng.record(
            db, owner, "tentei X", observation="deu certo", quality=0.9,
            lesson="X funciona quando Y", tag="teste",
        ))
        quality = x.quality
    finally:
        db.close()
    assert quality == 0.9
    assert "X funciona quando Y" in mem.remembered   # durable lesson -> memory
    assert seen == ["aprendizado.registrado"]         # event emitted


def test_recurring_low_quality_flags_difficulty_in_user_model():
    world = WorldModel()
    eng = LearningEngine(world=world)
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(eng.record(db, owner, "erro 1", quality=0.2, tag="regex"))
        # One low-quality is not yet a pattern.
        early = world.get_attribute(db, owner, "dificuldade_regex")
        asyncio.run(eng.record(db, owner, "erro 2", quality=0.1, tag="regex"))
        # Two -> a recurring difficulty in the User Model.
        flagged = world.get_attribute(db, owner, "dificuldade_regex")
        is_inf = flagged.is_inference if flagged else None
    finally:
        db.close()
    assert early is None
    assert flagged is not None
    assert is_inf is True


def test_stats_aggregate():
    eng = LearningEngine()
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(eng.record(db, owner, "a", quality=0.4))
        asyncio.run(eng.record(db, owner, "b", quality=0.6))
        s = eng.stats(db, owner)
    finally:
        db.close()
    assert s["total"] == 2
    assert s["recent_avg_quality"] == 0.5


def test_observe_decision_links_ref():
    eng = LearningEngine()
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        x = asyncio.run(eng.observe_decision(db, owner, "dec-123", 0.8, note="foi boa"))
        ref, kind, tag = x.ref_id, x.kind, x.tag
    finally:
        db.close()
    assert ref == "dec-123"
    assert kind == "feedback"
    assert tag == "decisao"


def test_record_rejects_empty_context():
    eng = LearningEngine()
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        raised = False
        try:
            asyncio.run(eng.record(db, owner, "   "))
        except ValueError:
            raised = True
    finally:
        db.close()
    assert raised is True


# ---------- API ----------

def test_learning_requires_auth(client):
    assert client.get("/api/v1/learning").status_code == 401


def test_learning_api_roundtrip(client, owner_headers):
    r = client.post("/api/v1/learning", json={
        "context": "estudei recursão", "observation": "entendi melhor",
        "quality": 0.85, "lesson": "recursão = caso base + passo", "tag": "estudo",
    }, headers=owner_headers)
    assert r.status_code == 200
    listing = client.get("/api/v1/learning", headers=owner_headers).json()
    assert any(x["lesson"] == "recursão = caso base + passo" for x in listing)
    stats = client.get("/api/v1/learning/stats", headers=owner_headers).json()
    assert stats["total"] >= 1
