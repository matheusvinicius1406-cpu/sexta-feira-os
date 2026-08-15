"""
Terminal SSH status — GET /api/v1/terminal/ssh.

The contract is deliberately narrow: session status, never a shell. The
endpoint must always answer 200 with a reading (or named limitations), and it
must never expose anything that could be mistaken for remote execution.
"""
import psutil


def test_ssh_status_shape(client, owner_headers):
    r = client.get("/api/v1/terminal/ssh", headers=owner_headers)
    assert r.status_code == 200
    body = r.json()

    # Listener: a real answer (listening/not) or a named limitation — never
    # absent silently.
    server = body["ssh_server"]
    assert server is None or server["port"] == 22
    assert "process" in (server or {})

    # Sessions: each with the four fields, remote flagged honestly.
    assert isinstance(body["sessions"], list)
    for s in body["sessions"]:
        assert {"user", "host", "terminal", "remote", "started_at"} <= set(s)
        assert isinstance(s["remote"], bool)
    assert body["sessions_count"] == len(body["sessions"])
    assert 0 <= body["remote_count"] <= body["sessions_count"]

    # The boundary is stated in the payload itself.
    assert "não abre shell" in body["note"]
    assert "unavailable" in body


def test_sessions_match_psutil_users(client, owner_headers):
    """The reading must agree with what psutil reports — nothing invented."""
    body = client.get("/api/v1/terminal/ssh", headers=owner_headers).json()
    users = psutil.users()
    assert body["sessions_count"] == len(users)
    remote = [u for u in users if (u.host or "").strip()]
    assert body["remote_count"] == len(remote)


def test_ssh_requires_owner_token(client):
    assert client.get("/api/v1/terminal/ssh").status_code == 401
