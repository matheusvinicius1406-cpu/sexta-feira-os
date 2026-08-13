"""
Event-Driven backbone — contract and API tests.

Deterministic (no Ollama). They prove events are persisted (audit trail), ordered
by a per-owner sequence, idempotent, isolate failing subscribers (graceful
degradation), and update the World Model via the projector.
"""
import asyncio
import uuid

from app.db.database import SessionLocal
from app.events.bus import EventBus
from app.events.projector import WorldModelProjector
from app.world.service import WorldModel

# Shared env + `client`/`owner_headers` fixtures live in conftest.py.


# ---------- API: publish / audit trail / world projection ----------

def test_events_require_auth(client):
    assert client.get("/api/v1/events").status_code == 401


def test_publish_persists_and_orders(client, owner_headers):
    a = client.post("/api/v1/events", json={"type": "teste.um"}, headers=owner_headers).json()
    b = client.post("/api/v1/events", json={"type": "teste.dois"}, headers=owner_headers).json()
    assert b["sequence"] == a["sequence"] + 1
    assert b["status"] == "processed"
    trail = client.get("/api/v1/events", headers=owner_headers).json()
    assert trail[0]["sequence"] >= b["sequence"]  # most recent first


def test_publish_updates_world_model(client, owner_headers):
    client.post(
        "/api/v1/events",
        json={"type": "localizacao.mudou", "payload": {"local": "faculdade"}},
        headers=owner_headers,
    )
    world = client.get("/api/v1/world", headers=owner_headers).json()
    loc = [f for f in world if f["key"] == "localizacao"]
    assert loc and loc[0]["value"] == "faculdade"
    assert loc[0]["source"] == "event"


def test_generic_world_key_projection(client, owner_headers):
    client.post(
        "/api/v1/events",
        json={"type": "qualquer.coisa", "payload": {"world_key": "clima", "world_value": "chuva"}},
        headers=owner_headers,
    )
    world = client.get("/api/v1/world", headers=owner_headers).json()
    assert any(f["key"] == "clima" and f["value"] == "chuva" for f in world)


def test_empty_type_is_rejected(client, owner_headers):
    r = client.post("/api/v1/events", json={"type": ""}, headers=owner_headers)
    assert r.status_code == 422


# ---------- Service: matching, idempotency, graceful degradation ----------
# The project has no async-test harness; drive coroutines with asyncio.run.

def test_prefix_and_wildcard_matching():
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("dispositivo.*", lambda db, ev: seen.append("prefix:" + ev.type))
    bus.subscribe("*", lambda db, ev: seen.append("all:" + ev.type))
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(bus.publish(db, owner, "dispositivo.conectado"))
        asyncio.run(bus.publish(db, owner, "outra.coisa"))
    finally:
        db.close()
    assert "prefix:dispositivo.conectado" in seen
    assert "all:dispositivo.conectado" in seen
    assert "all:outra.coisa" in seen
    assert "prefix:outra.coisa" not in seen  # prefix did not match


def test_idempotency_dedupes():
    bus = EventBus()
    calls: list[str] = []
    bus.subscribe("*", lambda db, ev: calls.append(ev.id))
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        first = asyncio.run(bus.publish(db, owner, "x.y", idempotency_key="k1"))
        again = asyncio.run(bus.publish(db, owner, "x.y", idempotency_key="k1"))
        first_id, again_id = first.id, again.id  # read before the session closes
    finally:
        db.close()
    assert first_id == again_id       # same event returned
    assert len(calls) == 1            # dispatched only once


def test_failing_subscriber_is_isolated():
    bus = EventBus()
    ran: list[str] = []

    def boom(db, ev):
        raise RuntimeError("kaboom")

    bus.subscribe("*", boom, "boom")
    bus.subscribe("*", lambda db, ev: ran.append("ok"), "good")
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        ev = asyncio.run(bus.publish(db, owner, "z.z"))
        status, error = ev.status, ev.error or ""  # read before the session closes
    finally:
        db.close()
    assert ran == ["ok"]              # the good subscriber still ran
    assert status == "failed"         # failure recorded, event still persisted
    assert "boom" in error


def test_projector_labels_inference():
    world = WorldModel()
    bus = EventBus()
    bus.subscribe("*", WorldModelProjector(world).handle, "proj")
    owner = f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        asyncio.run(bus.publish(db, owner, "saude.batimento_elevado", {"value": "130 bpm"}))
        fact = world.get_fact(db, owner, "saude_alerta")
        found, is_inf = fact is not None, bool(fact and fact.is_inference)
    finally:
        db.close()
    assert found
    assert is_inf is True
