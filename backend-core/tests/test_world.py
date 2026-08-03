"""
World Model + User Model — contract and API tests.

Deterministic: they never touch Ollama. They prove the Kernel's sense of NOW and
of its owner is stored, upserted by key, owner-scoped, inspectable, forgettable,
and that inferences are labelled in the digest the Kernel injects.
"""
import uuid

import pytest

from app.db.database import SessionLocal
from app.world.service import WorldModel

# Shared env + `client`/`owner_headers` fixtures live in conftest.py.


# ---------- API: world facts (the present) ----------

def test_world_requires_auth(client):
    assert client.get("/api/v1/world").status_code == 401


def test_world_fact_upsert_and_snapshot(client, owner_headers):
    r = client.post(
        "/api/v1/world",
        json={"key": "foco_atual", "value": "estudando cálculo", "category": "active_work"},
        headers=owner_headers,
    )
    assert r.status_code == 200
    assert r.json()["value"] == "estudando cálculo"

    # Same key again = UPSERT (update in place, not a duplicate).
    client.post(
        "/api/v1/world",
        json={"key": "foco_atual", "value": "escrevendo código", "category": "active_work"},
        headers=owner_headers,
    )
    snap = client.get("/api/v1/world", headers=owner_headers).json()
    focos = [f for f in snap if f["key"] == "foco_atual"]
    assert len(focos) == 1
    assert focos[0]["value"] == "escrevendo código"


def test_world_forget_fact(client, owner_headers):
    client.post(
        "/api/v1/world",
        json={"key": "tmp_local", "value": "casa"},
        headers=owner_headers,
    )
    assert client.delete("/api/v1/world/tmp_local", headers=owner_headers).status_code == 200
    assert client.delete("/api/v1/world/tmp_local", headers=owner_headers).status_code == 404


# ---------- API: user attributes (the owner over time) ----------

def test_user_attribute_and_profile(client, owner_headers):
    r = client.post(
        "/api/v1/world/profile",
        json={"key": "estilo_programacao", "value": "prefere Python tipado", "category": "style"},
        headers=owner_headers,
    )
    assert r.status_code == 200
    profile = client.get("/api/v1/world/profile", headers=owner_headers).json()
    assert any(a["key"] == "estilo_programacao" for a in profile)


def test_digest_reflects_state_and_labels_inference(client, owner_headers):
    client.post(
        "/api/v1/world",
        json={"key": "humor", "value": "cansado", "category": "user_state", "is_inference": True},
        headers=owner_headers,
    )
    digest = client.get("/api/v1/world/digest", headers=owner_headers).json()["digest"]
    assert "World Model" in digest
    assert "humor: cansado (inferência)" in digest
    assert "User Model" in digest  # set by the profile test


# ---------- Service: owner-scoped isolation (unit, no HTTP) ----------

def test_world_is_owner_scoped():
    world = WorldModel()
    a, b = f"owner-a-{uuid.uuid4().hex}", f"owner-b-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        world.set_fact(db, a, "segredo", "valor-de-a", category="context")
        world.set_fact(db, b, "segredo", "valor-de-b", category="context")
        assert world.get_fact(db, a, "segredo").value == "valor-de-a"
        assert world.get_fact(db, b, "segredo").value == "valor-de-b"
        keys_a = {f.key for f in world.snapshot(db, a)}
        assert "segredo" in keys_a
        # A's snapshot never contains B's rows (they share a key but not an owner).
        assert all(f.owner_id == a for f in world.snapshot(db, a))
    finally:
        db.close()


def test_set_fact_rejects_empty_key():
    world = WorldModel()
    db = SessionLocal()
    try:
        with pytest.raises(ValueError):
            world.set_fact(db, "owner-x", "   ", "algo")
    finally:
        db.close()
