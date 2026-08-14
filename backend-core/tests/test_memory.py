"""
Memory (second brain) — contract and API tests.

Deterministic (no Ollama): the kernel stores facts, lists them, forgets them,
and links them into a graph. The embedding step is skipped gracefully when the
model is offline (conftest points Ollama at a dead port), so the graph tests
use manual links, which are exactly the API surface the owner interacts with.
"""
import asyncio
import uuid

from app.db.database import SessionLocal

# ---------- API ----------

def test_memory_requires_auth(client):
    assert client.get("/api/v1/memory").status_code == 401


def test_remember_list_and_forget(client, owner_headers):
    created = client.post(
        "/api/v1/memory",
        json={"content": "O dono gosta de café sem açúcar.", "kind": "fact", "importance": 0.8},
        headers=owner_headers,
    )
    assert created.status_code == 200
    mid = created.json()["id"]

    items = client.get("/api/v1/memory", headers=owner_headers).json()
    assert any(i["id"] == mid and i["content"].startswith("O dono gosta") for i in items)

    gone = client.delete(f"/api/v1/memory/{mid}", headers=owner_headers)
    assert gone.status_code == 200
    assert not any(i["id"] == mid for i in client.get("/api/v1/memory", headers=owner_headers).json())


def test_forget_unknown_returns_404(client, owner_headers):
    r = client.delete(f"/api/v1/memory/{uuid.uuid4().hex}", headers=owner_headers)
    assert r.status_code == 404


def test_remember_validates_empty_content(client, owner_headers):
    r = client.post("/api/v1/memory", json={"content": ""}, headers=owner_headers)
    assert r.status_code == 422


def test_manual_link_and_neighbours(client, owner_headers):
    a = client.post("/api/v1/memory", json={"content": "Fato A"}, headers=owner_headers).json()
    b = client.post("/api/v1/memory", json={"content": "Fato B"}, headers=owner_headers).json()
    link = client.post(
        f"/api/v1/memory/{a['id']}/link",
        json={"target_id": b["id"], "relation": "relacionado"},
        headers=owner_headers,
    )
    assert link.status_code == 200
    assert link.json()["source"] == a["id"] and link.json()["target"] == b["id"]

    nb = client.get(f"/api/v1/memory/{a['id']}/neighbours", headers=owner_headers).json()
    # links carry the edge's own id; the neighbour node lives under `target`
    # (forward) / `source` (backlink).
    assert any(edge["target"] and edge["target"]["id"] == b["id"] for edge in nb["links"])
    assert all(n["source"] is not None for n in nb["backlinks"])


def test_unlink_removes_edge(client, owner_headers):
    a = client.post("/api/v1/memory", json={"content": "X"}, headers=owner_headers).json()
    b = client.post("/api/v1/memory", json={"content": "Y"}, headers=owner_headers).json()
    edge = client.post(
        f"/api/v1/memory/{a['id']}/link", json={"target_id": b["id"]}, headers=owner_headers
    ).json()
    r = client.delete(f"/api/v1/memory/links/{edge['id']}", headers=owner_headers)
    assert r.status_code == 200
    nb = client.get(f"/api/v1/memory/{a['id']}/neighbours", headers=owner_headers).json()
    assert nb["links"] == [] and nb["backlinks"] == []


def test_graph_endpoint_shape(client, owner_headers):
    a = client.post("/api/v1/memory", json={"content": "Nó do grafo"}, headers=owner_headers).json()
    b = client.post("/api/v1/memory", json={"content": "Outro nó"}, headers=owner_headers).json()
    client.post(f"/api/v1/memory/{a['id']}/link", json={"target_id": b["id"]}, headers=owner_headers)
    g = client.get("/api/v1/memory/graph", headers=owner_headers).json()
    assert "nodes" in g and "edges" in g
    ids = {n["id"] for n in g["nodes"]}
    assert a["id"] in ids and b["id"] in ids
    assert any(e["source"] == a["id"] and e["target"] == b["id"] for e in g["edges"])


# ---------- Service: owner isolation ----------

def test_memory_is_owner_scoped():
    from app.brain.memory import PersistentMemory

    memory = PersistentMemory(brain=None)
    a, b = f"o-{uuid.uuid4().hex}", f"o-{uuid.uuid4().hex}"
    db = SessionLocal()
    try:
        # remember is async (it computes the embedding); with brain=None the
        # embed step fails fast and the fact is stored without a vector.
        asyncio.run(memory.remember(db, a, "só da A", "fact", 0.5))
        asyncio.run(memory.remember(db, b, "só da B", "fact", 0.5))
        titles_a = {m.content for m in memory.list_all(db, a)}
    finally:
        db.close()
    assert titles_a == {"só da A"}
