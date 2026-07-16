"""
End-to-end tests for the private local kernel.

These run without Ollama: chat degrades gracefully to 503, and memory is
stored without an embedding. They prove the auth + memory + device + privacy
surface actually works. Run with:  pytest -q
"""
import os
import uuid

import pytest
from fastapi.testclient import TestClient

# Configure an isolated, ephemeral kernel BEFORE importing the app.
os.environ.update(
    ENVIRONMENT="development",
    LOG_LEVEL="CRITICAL",
    OWNER_EMAIL="owner@test.local",
    OWNER_NAME="Test Owner",
    OWNER_PASSWORD="a-strong-test-password",
    DEVICE_PAIRING_CODE="pair-code-123",
    DATABASE_URL=f"sqlite:////tmp/sexta_test_{uuid.uuid4().hex}.db",
)

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def owner_headers(client):
    r = client.post("/api/v1/auth/login",
                    json={"email": "owner@test.local", "password": "a-strong-test-password"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert "brain_online" in body


def test_chat_requires_auth(client):
    assert client.post("/api/v1/chat", json={"message": "oi"}).status_code == 403


def test_login_rejects_wrong_password(client):
    r = client.post("/api/v1/auth/login",
                    json={"email": "owner@test.local", "password": "wrong"})
    assert r.status_code == 401


def test_memory_persists(client, owner_headers):
    r = client.post("/api/v1/memory",
                    json={"content": "Gosto de café forte", "kind": "preference"},
                    headers=owner_headers)
    assert r.status_code == 200
    listing = client.get("/api/v1/memory", headers=owner_headers).json()
    assert any("café forte" in m["content"] for m in listing)


def test_device_pairing_and_access(client):
    r = client.post("/api/v1/auth/devices/pair",
                    json={"pairing_code": "pair-code-123",
                          "device_name": "Pixel", "device_kind": "phone"})
    assert r.status_code == 200
    dtoken = r.json()["device_token"]
    # A paired device acts on behalf of the owner.
    r2 = client.get("/api/v1/memory", headers={"Authorization": f"Bearer {dtoken}"})
    assert r2.status_code == 200


def test_bad_pairing_code_rejected(client):
    r = client.post("/api/v1/auth/devices/pair",
                    json={"pairing_code": "nope", "device_name": "x"})
    assert r.status_code == 401


def test_chat_degrades_gracefully_without_brain(client, owner_headers):
    # Ollama isn't running in CI => a clean 503, not a crash.
    r = client.post("/api/v1/chat", json={"message": "oi"}, headers=owner_headers)
    assert r.status_code == 503


# ---------------- knowledge graph (networked thought) ----------------

def test_wikilink_creates_graph_edge(client, owner_headers):
    # Writing [[Café]] inside a memory should auto-create a concept node + edge,
    # even with no embeddings (Ollama offline).
    r = client.post("/api/v1/memory",
                    json={"content": "Tomo [[Café]] toda manhã", "kind": "routine"},
                    headers=owner_headers)
    assert r.status_code == 200
    node_id = r.json()["id"]

    graph = client.get("/api/v1/memory/graph", headers=owner_headers).json()
    titles = {n["title"] for n in graph["nodes"]}
    assert "Café" in titles                      # concept node was created
    assert len(graph["edges"]) >= 1              # at least the wikilink edge

    nb = client.get(f"/api/v1/memory/{node_id}/neighbours", headers=owner_headers).json()
    assert any(link["relation"] == "wikilink" for link in nb["links"])


def test_manual_link_and_backlink(client, owner_headers):
    a = client.post("/api/v1/memory", json={"content": "Gosto de jazz"},
                    headers=owner_headers).json()["id"]
    b = client.post("/api/v1/memory", json={"content": "Toco saxofone"},
                    headers=owner_headers).json()["id"]

    r = client.post(f"/api/v1/memory/{a}/link",
                    json={"target_id": b, "relation": "about"}, headers=owner_headers)
    assert r.status_code == 200

    # b should see a as a backlink
    nb = client.get(f"/api/v1/memory/{b}/neighbours", headers=owner_headers).json()
    assert any(bl["source"]["id"] == a for bl in nb["backlinks"])


def test_forget_cascades_edges(client, owner_headers):
    node = client.post("/api/v1/memory",
                       json={"content": "Nota com [[Projeto X]]"},
                       headers=owner_headers).json()["id"]
    assert client.delete(f"/api/v1/memory/{node}", headers=owner_headers).status_code == 200
    # No dangling edges referencing the deleted node.
    graph = client.get("/api/v1/memory/graph", headers=owner_headers).json()
    assert all(e["source"] != node and e["target"] != node for e in graph["edges"])


def test_networked_recall_expands_along_links(client, owner_headers):
    """
    THE Obsidian effect: a query matches ONE node, but a linked node that does
    NOT match the query is still surfaced by following the connection.
    Uses deterministic fake embeddings so it runs without Ollama.
    """
    from app.core.di import get_kernel

    async def fake_embed(text: str):
        return [1.0, 0.0] if "alpha" in text.lower() else [0.0, 1.0]

    kernel = get_kernel()
    original = kernel.memory.brain.embed
    kernel.memory.brain.embed = fake_embed
    try:
        m1 = client.post("/api/v1/memory", json={"content": "alpha node"},
                         headers=owner_headers).json()["id"]
        m2 = client.post("/api/v1/memory", json={"content": "beta node"},
                         headers=owner_headers).json()["id"]
        # Connect them by hand (they are NOT semantically similar).
        client.post(f"/api/v1/memory/{m1}/link",
                    json={"target_id": m2, "relation": "related"}, headers=owner_headers)

        # Networked recall: query matches only alpha, but beta rides along the link.
        got = client.post("/api/v1/memory/recall",
                          json={"query": "alpha", "networked": True},
                          headers=owner_headers).json()
        ids = {r["id"] for r in got}
        assert m1 in ids and m2 in ids

        # Plain semantic recall: only the matching node.
        got_plain = client.post("/api/v1/memory/recall",
                                json={"query": "alpha", "networked": False},
                                headers=owner_headers).json()
        plain_ids = {r["id"] for r in got_plain}
        assert m1 in plain_ids and m2 not in plain_ids
    finally:
        kernel.memory.brain.embed = original


# ---------------- voice (local, optional extra) ----------------

def test_voice_status(client, owner_headers):
    body = client.get("/api/v1/voice/status", headers=owner_headers).json()
    assert "stt_available" in body and "tts_available" in body


def test_transcribe_degrades_gracefully(client, owner_headers):
    # Force the engine-unavailable path deterministically (independent of whether
    # faster-whisper happens to be installed) => the API must return a clean 503.
    from app.core.di import get_kernel
    from app.voice.stt import VoiceUnavailable

    voice = get_kernel().voice
    original = voice.transcriber.transcribe

    async def boom(*_a, **_k):
        raise VoiceUnavailable("engine not installed")

    voice.transcriber.transcribe = boom
    try:
        r = client.post(
            "/api/v1/voice/transcribe",
            files={"file": ("clip.wav", b"RIFF0000WAVE", "audio/wav")},
            headers=owner_headers,
        )
        assert r.status_code == 503
    finally:
        voice.transcriber.transcribe = original


def test_speak_degrades_gracefully(client, owner_headers):
    from app.core.di import get_kernel
    from app.voice.stt import VoiceUnavailable

    voice = get_kernel().voice
    original = voice.synthesizer.speak

    async def boom(*_a, **_k):
        raise VoiceUnavailable("piper voice not configured")

    voice.synthesizer.speak = boom
    try:
        r = client.post("/api/v1/voice/speak", json={"text": "olá"}, headers=owner_headers)
        assert r.status_code == 503
    finally:
        voice.synthesizer.speak = original


def test_voice_endpoints_require_auth(client):
    assert client.get("/api/v1/voice/status").status_code == 403


# ---------------- knowledge graph: smart relation labels ----------------

def test_auto_links_get_named_relations(client, owner_headers):
    """
    When the brain is available, a semantic auto-link is NAMED (e.g. 'trabalha em')
    instead of the generic 'related'. Deterministic via stubbed embed + chat.
    """
    from app.core.di import get_kernel

    kernel = get_kernel()
    orig_embed = kernel.memory.brain.embed
    orig_chat = kernel.memory.brain.chat

    async def fake_embed(_text: str):
        return [1.0, 0.0]  # everything is mutually similar -> auto-links

    async def fake_chat(_messages, **_kwargs):
        return "trabalha em"

    kernel.memory.brain.embed = fake_embed
    kernel.memory.brain.chat = fake_chat
    try:
        client.post("/api/v1/memory", json={"content": "Sou engenheiro"},
                    headers=owner_headers)
        b = client.post("/api/v1/memory", json={"content": "Trabalho na Acme"},
                        headers=owner_headers).json()["id"]
        nb = client.get(f"/api/v1/memory/{b}/neighbours", headers=owner_headers).json()
        relations = [link["relation"] for link in nb["links"]]
        assert "trabalha em" in relations
    finally:
        kernel.memory.brain.embed = orig_embed
        kernel.memory.brain.chat = orig_chat


# ---------------- automations (n8n bridge) ----------------

def test_automations_require_auth(client):
    assert client.get("/api/v1/automations/status").status_code == 403


def test_automations_status_reports_offline(client, owner_headers):
    # No n8n in CI => status returns 200 with online=False (not a crash).
    body = client.get("/api/v1/automations/status", headers=owner_headers).json()
    assert body["online"] is False
    assert "endpoint" in body


def test_list_automations_degrades_gracefully(client, owner_headers):
    # No API key / no n8n => clean 503.
    r = client.get("/api/v1/automations", headers=owner_headers)
    assert r.status_code == 503


def test_trigger_degrades_gracefully(client, owner_headers):
    # n8n unreachable in CI => clean 503.
    r = client.post("/api/v1/automations/trigger",
                    json={"webhook": "meu-fluxo", "payload": {"x": 1}},
                    headers=owner_headers)
    assert r.status_code == 503


def test_trigger_succeeds_when_n8n_up(client, owner_headers):
    # Deterministic success via a stubbed n8n client.
    from app.core.di import get_kernel

    n8n = get_kernel().automations
    original = n8n.trigger

    async def fake_trigger(webhook, payload=None):
        return {"ok": True, "status_code": 200, "result": {"received": payload}}

    n8n.trigger = fake_trigger
    try:
        r = client.post("/api/v1/automations/trigger",
                        json={"webhook": "meu-fluxo", "payload": {"hello": "world"}},
                        headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert r.json()["result"]["received"] == {"hello": "world"}
    finally:
        n8n.trigger = original
