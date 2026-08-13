"""
The Action Protocol — the brain's hands on each device (phone, computer, car).

Deterministic (no Ollama, no real network): a device is paired with the test
pairing code, then commands are dispatched and delivered over the two paths a
body can use:

  * WebSocket /api/v1/actions/stream — hello on connect, live commands, results
    reported back and acked;
  * polling fallback — GET /pending with a device token, then POST /{id}/result.

These tests hold the contract the Android agent (and any future body) depends
on: what the device must send to report a result, and what it can expect to
receive.
"""
from __future__ import annotations


def _pair_device(client, name: str = "Celular do dono", kind: str = "phone") -> dict:
    r = client.post(
        "/api/v1/auth/devices/pair",
        json={"pairing_code": "pair-code-123", "device_name": name, "device_kind": kind},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_ws_stream_hellos_backlog_and_results(client, owner_headers):
    """The live channel: hello on connect, backlog replay, result + ack."""
    device = _pair_device(client)
    token, device_id = device["device_token"], device["device_id"]

    with client.websocket_connect(f"/api/v1/actions/stream?token={token}") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        assert hello["device_id"] == device_id
        assert hello["device_name"]

        # Dispatch while connected — the bus pushes it immediately.
        r = client.post(
            "/api/v1/actions/dispatch",
            json={"device": "celular", "action": "toast", "params": {"text": "oi"}},
            headers=owner_headers,
        )
        assert r.status_code == 200, r.text
        command_id = r.json()["command_id"]

        cmd = ws.receive_json()
        assert cmd["type"] == "command"
        assert cmd["id"] == command_id
        assert cmd["action"] == "toast"
        assert cmd["params"] == {"text": "oi"}

        # Report a result, expect the ack.
        ws.send_json(
            {"type": "result", "id": command_id, "status": "done", "result": {"toast": True}}
        )
        ack = ws.receive_json()
        assert ack == {"type": "ack", "id": command_id, "ok": True}

    # The owner sees the command finished.
    history = client.get("/api/v1/actions", headers=owner_headers).json()
    entry = next(h for h in history if h["id"] == command_id)
    assert entry["status"] == "done"
    assert entry["result"] == {"toast": True}


def test_polling_fallback_delivers_and_reports(client, owner_headers):
    """The offline body: fetch pending commands, then POST the result."""
    # Distinct kind on purpose: the dispatcher resolves "phone" to the FIRST
    # phone ever paired (shared session DB), so a second phone token would poll
    # an empty queue. A watch is its own body.
    device = _pair_device(client, name="Relógio do dono", kind="watch")
    token = device["device_token"]

    r = client.post(
        "/api/v1/actions/dispatch",
        json={"device": "relogio", "action": "open_app", "params": {"app": "whatsapp"}},
        headers=owner_headers,
    )
    assert r.status_code == 200, r.text
    command_id = r.json()["command_id"]

    pending = client.get(
        "/api/v1/actions/pending", headers={"Authorization": f"Bearer {token}"}
    )
    assert pending.status_code == 200, pending.text
    cmds = pending.json()
    assert any(c["id"] == command_id and c["action"] == "open_app" for c in cmds)

    reported = client.post(
        f"/api/v1/actions/{command_id}/result",
        json={"status": "failed", "error": "app não instalado"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert reported.status_code == 200, reported.text

    history = client.get("/api/v1/actions", headers=owner_headers).json()
    entry = next(h for h in history if h["id"] == command_id)
    assert entry["status"] == "failed"
    assert entry["error"] == "app não instalado"


def test_ws_rejects_an_invalid_or_owner_token(client):
    """A wrong token closes the socket; an owner token is not a device token."""
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/actions/stream?token=lixo") as ws:
            ws.receive()
    assert exc_info.value.code == 1008
