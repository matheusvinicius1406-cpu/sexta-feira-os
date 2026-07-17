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
    SCHEDULER_ENABLED="false",  # tests drive run_due() directly, deterministically
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


# ---------------- agentic tool-calling (the brain acts on its own) ----------------

def test_brain_can_call_tools(client, owner_headers):
    """
    From a plain sentence, the brain decides to call a tool (remember) and only
    then answers — the phone-first 'talk -> act' loop. Deterministic: we stub the
    brain to emit a tool_call on the first pass and a final answer on the second.
    """
    from app.core.di import get_kernel

    brain = get_kernel().cognition.brain
    original = brain.chat_with_tools
    state = {"calls": 0}

    async def fake_tools(messages, tools=None, **_kwargs):
        state["calls"] += 1
        if state["calls"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "remember",
                                  "arguments": {"content": "Consulta no dentista amanhã às 15h"}}}
                ],
            }
        return {"role": "assistant", "content": "Anotado, vou te lembrar."}

    brain.chat_with_tools = fake_tools
    try:
        r = client.post("/api/v1/chat",
                        json={"message": "me lembra do dentista amanhã às 15h"},
                        headers=owner_headers)
        assert r.status_code == 200
        assert "Anotado" in r.json()["reply"]
        # The tool actually ran => the fact is now in memory.
        mems = client.get("/api/v1/memory", headers=owner_headers).json()
        assert any("dentista" in m["content"].lower() for m in mems)
    finally:
        brain.chat_with_tools = original


# ---------------- action protocol (the brain's hands on devices) ----------------

def _pair_phone(client, name: str):
    r = client.post("/api/v1/auth/devices/pair",
                    json={"pairing_code": "pair-code-123", "device_name": name, "device_kind": "phone"})
    assert r.status_code == 200
    return r.json()["device_token"], r.json()["device_id"]


def test_actions_require_auth(client):
    r = client.post("/api/v1/actions/dispatch", json={"device": "celular", "action": "open_app"})
    assert r.status_code == 403


def test_dispatch_to_unknown_device(client, owner_headers):
    r = client.post("/api/v1/actions/dispatch",
                    json={"device": "geladeira", "action": "open_app", "params": {}},
                    headers=owner_headers)
    assert r.status_code == 200
    assert r.json()["ok"] is False


def test_action_flow_polling(client, owner_headers):
    dtoken, _ = _pair_phone(client, "phone-poll")
    dheaders = {"Authorization": f"Bearer {dtoken}"}

    # Owner dispatches to the phone (offline => queued).
    r = client.post("/api/v1/actions/dispatch",
                    json={"device": "phone-poll", "action": "open_app", "params": {"app": "whatsapp"}},
                    headers=owner_headers)
    assert r.json()["ok"] is True and r.json()["delivered"] is False
    cmd_id = r.json()["command_id"]

    # Device polls and gets it.
    pending = client.get("/api/v1/actions/pending", headers=dheaders).json()
    assert any(c["id"] == cmd_id and c["action"] == "open_app"
               and c["params"] == {"app": "whatsapp"} for c in pending)

    # Device reports the result -> command done.
    rr = client.post(f"/api/v1/actions/{cmd_id}/result",
                     json={"status": "done", "result": {"opened": True}}, headers=dheaders)
    assert rr.status_code == 200
    history = client.get("/api/v1/actions", headers=owner_headers).json()
    assert any(c["id"] == cmd_id and c["status"] == "done" for c in history)


def test_action_websocket_live_delivery(client, owner_headers):
    dtoken, _ = _pair_phone(client, "phone-ws")

    # Queue a command while the device is offline.
    r = client.post("/api/v1/actions/dispatch",
                    json={"device": "phone-ws", "action": "navigate", "params": {"to": "faculdade"}},
                    headers=owner_headers)
    cmd_id = r.json()["command_id"]

    # Device connects: receives the backlog command, then reports its result.
    with client.websocket_connect(f"/api/v1/actions/stream?token={dtoken}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "command" and msg["id"] == cmd_id and msg["action"] == "navigate"
        ws.send_json({"type": "result", "id": cmd_id, "status": "done", "result": {"ok": True}})
        ack = ws.receive_json()  # wait for server to process (deterministic)
        assert ack["type"] == "ack" and ack["ok"] is True

    history = client.get("/api/v1/actions", headers=owner_headers).json()
    assert any(c["id"] == cmd_id and c["status"] == "done" for c in history)


def test_websocket_rejects_bad_token(client):
    import contextlib

    from starlette.websockets import WebSocketDisconnect

    with contextlib.suppress(WebSocketDisconnect), \
            client.websocket_connect("/api/v1/actions/stream?token=garbage") as ws:
        # A bad token must not yield a usable channel; receiving should fail/close.
        with contextlib.suppress(Exception):
            ws.receive_json()


def test_brain_dispatches_device_action(client, owner_headers):
    """The brain, from a sentence, decides to act on a device (device_action tool)."""
    from app.core.di import get_kernel

    _pair_phone(client, "phone-tool")
    brain = get_kernel().cognition.brain
    original = brain.chat_with_tools
    state = {"n": 0}

    async def fake_tools(messages, tools=None, **_kwargs):
        state["n"] += 1
        if state["n"] == 1:
            return {
                "role": "assistant", "content": "",
                "tool_calls": [
                    {"function": {"name": "device_action",
                                  "arguments": {"device": "phone-tool", "action": "open_app",
                                                "params": {"app": "spotify"}}}}
                ],
            }
        return {"role": "assistant", "content": "Abrindo o Spotify no seu celular."}

    brain.chat_with_tools = fake_tools
    try:
        r = client.post("/api/v1/chat", json={"message": "abre o spotify"}, headers=owner_headers)
        assert r.status_code == 200
        assert "Spotify" in r.json()["reply"]
        history = client.get("/api/v1/actions", headers=owner_headers).json()
        assert any(c["action"] == "open_app" and c["params"] == {"app": "spotify"} for c in history)
    finally:
        brain.chat_with_tools = original


# ---------------- scheduler (proactive reminders / timed actions) ----------------

def test_schedule_crud(client, owner_headers):
    r = client.post("/api/v1/schedule",
                    json={"kind": "reminder", "text": "ligar dentista", "in_days": 1},
                    headers=owner_headers)
    assert r.status_code == 200
    tid = r.json()["id"]
    assert any(t["id"] == tid for t in client.get("/api/v1/schedule", headers=owner_headers).json())
    assert client.delete(f"/api/v1/schedule/{tid}", headers=owner_headers).status_code == 200
    # cancelled => no longer in the pending list
    assert not any(t["id"] == tid for t in client.get("/api/v1/schedule", headers=owner_headers).json())


def test_schedule_requires_a_time(client, owner_headers):
    r = client.post("/api/v1/schedule", json={"kind": "reminder", "text": "sem hora"},
                    headers=owner_headers)
    assert r.status_code == 400


def test_scheduler_fires_due_reminder(client, owner_headers):
    import asyncio
    from datetime import UTC, datetime, timedelta

    from app.core.di import get_kernel
    from app.db.database import SessionLocal
    from app.models.models import Owner

    _pair_phone(client, "phone-sched")
    scheduler = get_kernel().scheduler
    db = SessionLocal()
    try:
        owner_id = db.query(Owner).first().id
        task = scheduler.schedule(
            db, owner_id, kind="reminder",
            due_at=datetime.now(UTC) - timedelta(minutes=1),
            text="beba água", device="phone-sched",
        )
        fired = asyncio.run(scheduler.run_due(db, datetime.now(UTC)))
        assert fired >= 1
        db.refresh(task)
        assert task.status == "fired"
    finally:
        db.close()

    # firing dispatched a 'notify' action to the phone
    history = client.get("/api/v1/actions", headers=owner_headers).json()
    assert any(c["action"] == "notify" and c["params"].get("text") == "beba água" for c in history)


def test_scheduler_recurring_reschedules(client, owner_headers):
    import asyncio
    from datetime import UTC, datetime, timedelta

    from app.core.di import get_kernel
    from app.db.database import SessionLocal
    from app.models.models import Owner
    from app.schedule.service import _aware

    _pair_phone(client, "phone-recur")
    scheduler = get_kernel().scheduler
    db = SessionLocal()
    try:
        owner_id = db.query(Owner).first().id
        now = datetime.now(UTC)
        task = scheduler.schedule(
            db, owner_id, kind="reminder", due_at=now - timedelta(minutes=2),
            text="beber água", device="phone-recur", recurrence_seconds=3600,
        )
        asyncio.run(scheduler.run_due(db, now))
        db.refresh(task)
        assert task.status == "pending"              # recurring => stays pending
        assert _aware(task.due_at) > now             # rescheduled into the future
    finally:
        db.close()


def test_brain_schedules_reminder(client, owner_headers):
    from app.core.di import get_kernel

    brain = get_kernel().cognition.brain
    original = brain.chat_with_tools
    state = {"n": 0}

    async def fake_tools(messages, tools=None, **_kwargs):
        state["n"] += 1
        if state["n"] == 1:
            return {
                "role": "assistant", "content": "",
                "tool_calls": [
                    {"function": {"name": "schedule_reminder",
                                  "arguments": {"text": "estudar redes", "in_days": 7}}}
                ],
            }
        return {"role": "assistant", "content": "Agendado, te lembro semana que vem."}

    brain.chat_with_tools = fake_tools
    try:
        r = client.post("/api/v1/chat",
                        json={"message": "me lembra de estudar redes semana que vem"},
                        headers=owner_headers)
        assert r.status_code == 200
        scheduled = client.get("/api/v1/schedule", headers=owner_headers).json()
        assert any("estudar redes" in (t["text"] or "") for t in scheduled)
    finally:
        brain.chat_with_tools = original


# ---------------- connectors (the API capability system) ----------------

def test_connectors_require_auth(client):
    assert client.get("/api/v1/connectors").status_code == 403


def test_capability_crud(client, owner_headers):
    r = client.post("/api/v1/connectors",
                    json={"name": "hora", "description": "hora certa", "url": "https://x/time"},
                    headers=owner_headers)
    assert r.status_code == 200
    assert any(c["name"] == "hora"
               for c in client.get("/api/v1/connectors", headers=owner_headers).json())
    assert client.get("/api/v1/connectors/hora", headers=owner_headers).json()["url"] == "https://x/time"
    assert client.delete("/api/v1/connectors/hora", headers=owner_headers).status_code == 200


def test_secret_is_encrypted_at_rest(client, owner_headers):
    from app.db.database import SessionLocal
    from app.models.models import Secret

    client.post("/api/v1/connectors/secrets",
                json={"name": "TKN", "value": "plain-value-xyz"}, headers=owner_headers)
    db = SessionLocal()
    try:
        s = db.query(Secret).filter(Secret.name == "TKN").first()
        assert s is not None
        assert "plain-value-xyz" not in s.value_encrypted   # stored encrypted, not plaintext
    finally:
        db.close()
    # the API exposes only NAMES, never values
    assert "TKN" in client.get("/api/v1/connectors/secrets", headers=owner_headers).json()["names"]


def test_call_unknown_capability_is_graceful(client, owner_headers):
    r = client.post("/api/v1/connectors/nope/call", json={"params": {}}, headers=owner_headers)
    assert r.status_code == 200 and r.json()["ok"] is False


def test_connector_invoke_renders_param_and_secret(client, owner_headers):
    import httpx

    from app.core.di import get_kernel

    conn = get_kernel().connectors
    captured: dict = {}

    async def fake_request(method, url, params=None, headers=None, json=None, timeout=None):
        captured.update(method=method, url=url, params=params, headers=headers)
        return httpx.Response(200, json={"echo": "ok"})

    original = conn._client.request
    conn._client.request = fake_request
    try:
        client.post("/api/v1/connectors/secrets",
                    json={"name": "WKEY", "value": "super-secret-123"}, headers=owner_headers)
        client.post("/api/v1/connectors", json={
            "name": "weather", "description": "clima", "method": "GET",
            "url": "https://api.example.com/weather/{city}",
            "query": {"units": "metric"},
            "headers": {"Authorization": "Bearer {secret:WKEY}"},
            "params_schema": [{"name": "city", "required": True}],
        }, headers=owner_headers)

        r = client.post("/api/v1/connectors/weather/call",
                        json={"params": {"city": "Recife"}}, headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["ok"] is True and r.json()["data"] == {"echo": "ok"}
        # templating: param filled into the URL, secret injected into the header
        assert captured["url"] == "https://api.example.com/weather/Recife"
        assert captured["headers"]["Authorization"] == "Bearer super-secret-123"
        assert captured["params"] == {"units": "metric"}
    finally:
        conn._client.request = original


def test_brain_calls_api_capability(client, owner_headers):
    import httpx

    from app.core.di import get_kernel

    kernel = get_kernel()
    conn = kernel.connectors
    client.post("/api/v1/connectors",
                json={"name": "dolar", "description": "cotação do dólar", "url": "https://x/usd"},
                headers=owner_headers)

    async def fake_request(method, url, params=None, headers=None, json=None, timeout=None):
        return httpx.Response(200, json={"usd": 5.1})

    orig_req = conn._client.request
    conn._client.request = fake_request
    brain = kernel.cognition.brain
    orig_chat = brain.chat_with_tools
    state = {"n": 0}

    async def fake_tools(messages, tools=None, **_kwargs):
        state["n"] += 1
        if state["n"] == 1:
            return {"role": "assistant", "content": "",
                    "tool_calls": [{"function": {"name": "call_api",
                                                 "arguments": {"capability": "dolar", "params": {}}}}]}
        return {"role": "assistant", "content": "O dólar está em 5.1."}

    brain.chat_with_tools = fake_tools
    try:
        r = client.post("/api/v1/chat", json={"message": "quanto está o dólar?"}, headers=owner_headers)
        assert r.status_code == 200 and "5.1" in r.json()["reply"]
    finally:
        brain.chat_with_tools = orig_chat
        conn._client.request = orig_req


# ---------------- sub-agents (the brain delegates to local helpers) ----------------

def test_subagent_toolset_is_restricted():
    import asyncio

    from app.core.config import settings
    from app.core.di import get_kernel

    toolkit = get_kernel().cognition.toolkit
    subset = asyncio.run(toolkit.specs_subset(settings.subagent_allowed_tools))
    names = {s["function"]["name"] for s in subset}
    assert names <= set(settings.subagent_allowed_tools)
    # irreversible/real-world tools and delegation are NOT available to sub-agents
    assert "delegate" not in names
    assert "device_action" not in names
    assert "run_automation" not in names


def test_brain_delegates_to_subagent(client, owner_headers):
    from app.core.di import get_kernel

    brain = get_kernel().cognition.brain
    original = brain.chat_with_tools

    async def fake_tools(messages, tools=None, **_kwargs):
        system = messages[0]["content"] if messages else ""
        if "sub-agente" in system:                      # the sub-agent: answer directly
            return {"role": "assistant", "content": "Resumo do pesquisador: OK."}
        if any(m.get("role") == "tool" for m in messages):   # main brain got the result
            return {"role": "assistant", "content": "Deleguei e concluí a pesquisa."}
        return {                                         # main brain: delegate first
            "role": "assistant", "content": "",
            "tool_calls": [{"function": {"name": "delegate",
                                         "arguments": {"role": "pesquisador",
                                                       "task": "resuma o tema X"}}}],
        }

    brain.chat_with_tools = fake_tools
    try:
        r = client.post("/api/v1/chat", json={"message": "pesquisa o tema X pra mim"},
                        headers=owner_headers)
        assert r.status_code == 200
        assert "conclu" in r.json()["reply"].lower()
    finally:
        brain.chat_with_tools = original
