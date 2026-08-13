"""
Security controls added by the 2026-08 hardening audit:

  * security headers on every API response (CSP exempted for /docs)
  * login/pairing brute-force guard: 5 misses per IP -> 429 + Retry-After
  * unknown-email login still answers 401 (dummy argon2 verify, no crash)
  * netguard: outbound URL firewall (no loopback/private/link-local/metadata)
  * RedactingFormatter masks ?token= / ?key= / ?secret= in log lines
  * connector secrets vault never honors the dev auth bypass
"""
import logging

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.netguard import guarded_request, validate_outbound_url
from app.core.rate_limit import throttle
from app.core.security import RedactingFormatter

# ───────────────────────────────────────────────────────────── headers


def test_security_headers_present(client: TestClient):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    assert "default-src 'none'" in r.headers["Content-Security-Policy"]


def test_docs_exempt_from_csp(client: TestClient):
    r = client.get("/docs")
    assert r.status_code == 200
    assert "Content-Security-Policy" not in r.headers


# ─────────────────────────────────────────────────────── brute force


def test_login_lockout_after_five_failures(client: TestClient):
    for _ in range(5):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@test.local", "password": "errada"},
        )
        assert r.status_code == 401
    # Sixth attempt from the same IP is locked out.
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@test.local", "password": "errada"},
    )
    assert r.status_code == 429
    assert "Retry-After" in r.headers


def test_successful_login_resets_lockout(client: TestClient):
    for _ in range(4):
        client.post(
            "/api/v1/auth/login",
            json={"email": "owner@test.local", "password": "errada"},
        )
    ok = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@test.local", "password": "a-strong-test-password"},
    )
    assert ok.status_code == 200
    # Counter cleared: a wrong password now gets 401, not 429.
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@test.local", "password": "errada"},
    )
    assert r.status_code == 401


def test_pairing_lockout(client: TestClient):
    for _ in range(5):
        r = client.post(
            "/api/v1/auth/devices/pair",
            json={"pairing_code": "errada", "device_name": "x"},
        )
        assert r.status_code == 401
    r = client.post(
        "/api/v1/auth/devices/pair",
        json={"pairing_code": "errada", "device_name": "x"},
    )
    assert r.status_code == 429


def test_unknown_email_answers_401_not_500(client: TestClient):
    """The constant-time dummy verify must not crash on an unknown email."""
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "ninguem@nunca.existe", "password": "qualquer"},
    )
    assert r.status_code == 401


def test_throttle_independent_keys():
    throttle._failures.clear()
    for _ in range(5):
        throttle.register_failure("1.1.1.1")
    assert throttle.remaining_lockout("2.2.2.2") == 0   # untouched key stays free
    assert throttle.remaining_lockout("1.1.1.1") > 0    # the attacker's key is locked
    throttle._failures.clear()


# ────────────────────────────────────────────────────────── netguard


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:11434/api/version",   # the proven 2026-08 exploit
        "http://localhost:8000/",
        "http://10.0.0.5/",
        "http://192.168.1.10/",
        "http://172.16.3.4/",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata
        "http://[::1]:8000/",
        "file:///etc/passwd",
        "gopher://127.0.0.1:6379/_x",
        "http:///sem-host",
    ],
)
def test_netguard_blocks_internal_targets(url):
    with pytest.raises(ValueError):
        validate_outbound_url(url)


def test_netguard_blocks_dns_rebinding(monkeypatch):
    """A host that resolves to a private address must be refused even if the
    literal hostname is not an IP."""
    import socket

    def fake_getaddrinfo(host, port, *a, **k):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.99", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(ValueError, match="resolve para um endereço interno"):
        validate_outbound_url("http://evil-rebind.example/x")


def test_netguard_allows_public_host(monkeypatch):
    import socket

    def fake_getaddrinfo(host, port, *a, **k):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    validate_outbound_url("http://example.com/x")  # must not raise


def test_netguard_allows_explicitly_allowed_host(monkeypatch):
    import socket

    monkeypatch.setattr(settings, "teia_allowed_outbound_hosts", ["192.168.1.10"])

    def fake_getaddrinfo(host, port, *a, **k):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.10", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    validate_outbound_url("http://192.168.1.10:8080/x")  # allowlisted -> ok
    with pytest.raises(ValueError):
        validate_outbound_url("http://192.168.1.11/x")


def test_guarded_request_validates_redirect_target(monkeypatch):
    """A redirect from a public URL to a private one must be refused BEFORE the
    second request is issued."""

    class FakeResponse:
        def __init__(self, status, location=None):
            self.status_code = status
            self.headers = {"location": location} if location else {}

    calls = []

    class FakeClient:
        async def request(self, method, url, **kwargs):
            calls.append(url)
            if len(calls) == 1:
                return FakeResponse(302, "http://127.0.0.1:11434/private")
            return FakeResponse(200)

    import asyncio

    with pytest.raises(ValueError):
        asyncio.run(guarded_request(FakeClient(), "GET", "http://example.com/start"))
    assert len(calls) == 1  # the private hop was never fetched


# ─────────────────────────────────────────────── log redaction


def _make_record(message: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__, lineno=1,
        msg=message, args=(), exc_info=None,
    )


def test_redacting_formatter_masks_token():
    out = RedactingFormatter("%(message)s").format(
        _make_record('GET /api/v1/actions/stream?token=eyJhbGciOiJIUzI1NiJ9 HTTP/1.1" 200')
    )
    assert "token=" in out and "eyJhbGciOiJIUzI1NiJ9" not in out
    assert "token=***" in out


def test_redacting_formatter_masks_key_and_secret():
    out = RedactingFormatter("%(message)s").format(
        _make_record("GET /v1/connectors?key=sk-12345&secret=abc HTTP/1.1")
    )
    assert "sk-12345" not in out and "abc" not in out
    assert "key=***" in out and "secret=***" in out


def test_redacting_formatter_keeps_normal_lines():
    out = RedactingFormatter("%(message)s").format(
        _make_record("kernel started on port 8000")
    )
    assert out == "kernel started on port 8000"


# ──────────────────────────────────────────────── active defense (tripwires)


def test_brute_force_records_threat(client: TestClient, owner_headers):
    """The lockout tripwire fires: an attacker who keeps knocking is recorded
    on the threat audit trail the app's Security screen reads."""
    for _ in range(5):
        client.post(
            "/api/v1/auth/login",
            json={"email": "owner@test.local", "password": "errada"},
        )
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@test.local", "password": "errada"},
    )
    assert r.status_code == 429
    r = client.get("/api/v1/security/threats", headers=owner_headers)
    assert r.status_code == 200
    assert any("brute-force" in t["type"] for t in r.json())


def test_honeypot_secret_is_bait(client: TestClient, owner_headers):
    """A secret named honeypot.* is never returned; reading it fires a threat."""
    r = client.post(
        "/api/v1/connectors/secrets", headers=owner_headers,
        json={"name": "honeypot.api_falsa", "value": "sk-isca-que-nunca-sai"},
    )
    assert r.status_code == 200

    from app.core.di import get_kernel
    from app.db.database import SessionLocal
    from app.models.models import Owner

    db = SessionLocal()
    try:
        owner = db.query(Owner).first()
        value = get_kernel().connectors.get_secret_value(db, owner.id, "honeypot.api_falsa")
        assert value is None  # the bait is never given up
    finally:
        db.close()

    r = client.get("/api/v1/security/threats", headers=owner_headers)
    assert any("honeypot" in t["type"] for t in r.json())


def test_security_audit_reports_posture(client: TestClient, owner_headers):
    r = client.get("/api/v1/security/audit", headers=owner_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["defesas"]["netguard"]["ativo"] is True
    assert "Content-Security-Policy" in d["defesas"]["headers"]
    assert d["defesas"]["rate_limit"]["max_tentativas"] >= 1


def test_security_endpoints_require_strict_auth(client: TestClient):
    # Never the dev bypass: the security dashboard is owner-only.
    assert client.get("/api/v1/security/audit").status_code == 401
    assert client.get("/api/v1/security/threats").status_code == 401


# ────────────────────────────────────────── secrets vault vs bypass


def test_connector_secrets_never_honor_dev_bypass(client: TestClient, monkeypatch):
    """Even with AUTH_DEV_BYPASS on (loopback dev), the secrets vault must
    demand a real token — any local process reading the rest of the kernel is
    already bad, but the owner's API keys are the one thing it must not get."""
    monkeypatch.setattr(settings, "auth_dev_bypass", True)
    monkeypatch.setattr(settings, "access_mode", "loopback")
    monkeypatch.setattr(settings, "environment", "development")
    # The HostGuard only admits loopback Hosts while the bypass is on; the
    # HUD (and this test) reach the kernel as 127.0.0.1.
    loopback_headers = {"Host": "127.0.0.1"}

    # The bypass makes a normal endpoint answer without a token...
    r = client.get("/api/v1/world", headers=loopback_headers)
    assert r.status_code == 200

    # ...but the vault refuses.
    r = client.get("/api/v1/connectors/secrets", headers=loopback_headers)
    assert r.status_code == 401

    # DNS-rebinding protection: a non-loopback Host is refused outright while
    # the bypass is on — that is the signal a malicious site cannot fake.
    r = client.get("/api/v1/world", headers={"Host": "evil-rebind.example"})
    assert r.status_code == 403
