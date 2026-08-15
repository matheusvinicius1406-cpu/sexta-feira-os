"""
Hardening of the 2026-08-15 API surface — network, browser, terminal.

The three new routers joined the kernel with the same posture as the rest of
the system-metrics surface (/system, /radio): owner-token reads, wrapped by
the global security headers, and covered by the dev bypass only when it is
genuinely active (development + opt-in + loopback). They are NOT secrets —
those live behind `get_current_owner_strict` (the connector secrets vault) —
and this file pins that boundary so a future route added to this surface
cannot silently drift toward either side.
"""
import pytest

# Every route the new surface exposes, with its method.
NEW_SURFACE = [
    ("GET", "/api/v1/network/traffic"),
    ("GET", "/api/v1/network/vpn"),
    ("GET", "/api/v1/browser/tabs"),
    ("GET", "/api/v1/browser/marks"),
    ("POST", "/api/v1/browser/marks"),
    ("GET", "/api/v1/terminal/ssh"),
]

# Field names that must never appear in any response of this surface. The
# values are the point (a search query, an interface name); the SHAPE must
# never carry credentials.
SENSITIVE_KEYS = ("password", "secret", "token", "api_key", "authorization", "access_token")


def _sensitive_keys(obj, _path=""):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if any(s in k.lower() for s in SENSITIVE_KEYS):
                hits.append(f"{_path}.{k}")
            hits.extend(_sensitive_keys(v, f"{_path}.{k}"))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            hits.extend(_sensitive_keys(item, f"{_path}[{i}]"))
    return hits


@pytest.mark.parametrize("method,path", NEW_SURFACE)
def test_new_surface_requires_token(client, method, path):
    """Without a token (bypass off in the suite), every route answers 401 —
    a route that returns data anonymously is a route that forgot auth."""
    r = client.request(method, path)
    assert r.status_code == 401


@pytest.mark.parametrize("method,path", NEW_SURFACE)
def test_new_surface_carries_security_headers(client, owner_headers, method, path):
    """The global middleware must wrap the new surface, not just /health."""
    kwargs = {"headers": owner_headers}
    if method == "POST":
        kwargs["json"] = {"url": "https://exemplo.com", "title": "hardening"}
    r = client.request(method, path, **kwargs)
    assert r.status_code in (200, 201)
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'none'" in r.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]


@pytest.mark.parametrize("method,path", NEW_SURFACE)
def test_new_surface_leaks_no_sensitive_fields(client, owner_headers, method, path):
    """Responses may carry content the owner searched or saved — never a
    credential-shaped field name. Catches a future echo of the wrong thing."""
    kwargs = {"headers": owner_headers}
    if method == "POST":
        kwargs["json"] = {"url": "https://exemplo.com/segredo-x", "title": "titulo-y"}
    r = client.request(method, path, **kwargs)
    assert r.status_code in (200, 201)
    leaked = _sensitive_keys(r.json())
    assert not leaked, f"{path} vazou campo(s) sensível(is): {leaked}"


def test_dev_bypass_posture_system_not_secrets(client, monkeypatch):
    """With the bypass genuinely active (development + opt-in + loopback), the
    new surface answers without a token exactly like /system does — but the
    secrets vault still demands a real token. That difference IS the boundary,
    and it is deliberate: session/user/network data is the owner's own machine
    status, like CPU load; vault values are the one thing no local process may
    read without presenting real credentials."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "auth_dev_bypass", True)
    monkeypatch.setattr(settings, "access_mode", "loopback")

    # With the bypass on, the HostGuard rejects non-loopback Hosts (the DNS-
    # rebinding tripwire) — the TestClient sends `testserver`, so speak loopback.
    loopback = {"Host": "127.0.0.1:8000"}

    for path in ("/api/v1/system", "/api/v1/network/traffic", "/api/v1/terminal/ssh"):
        r = client.get(path, headers=loopback)
        assert r.status_code == 200, f"{path} deveria aceitar o bypass de dev"

    # And the HostGuard is live under the bypass: a foreign Host is refused.
    r = client.get("/api/v1/network/traffic", headers={"Host": "evil.example"})
    assert r.status_code == 403, "host não-loopback deve ser recusado com o bypass ligado"

    r = client.get("/api/v1/connectors/secrets", headers=loopback)
    assert r.status_code == 401, "o cofre nunca honra o bypass de dev"
