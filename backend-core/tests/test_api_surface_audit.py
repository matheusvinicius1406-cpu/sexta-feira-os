"""
Audit of the ENTIRE /api/v1 surface, in the same pattern as the new-surface
hardening (test_new_surface_hardening.py) — but discovered dynamically from
the running app, so a route added tomorrow is audited tomorrow without anyone
editing this file.

  * every route must require a token — except a short, deliberate whitelist;
  * every route (whatever it answers) must carry the global security headers;
  * every read route that answers 200 must not leak a credential-shaped field;
  * a GET that 5xxes with a valid token is a bug, not a skip.

The whitelist is the whole point. login and pairing are public by design; the
webhook is the door made for other programs on this machine (armed trigger +
X-Teia-Secret); health is loopback-only anyway. A new route that answers
anything but 401 without a token fails this audit until it is either protected
or added here with a reason.
"""
import re

from fastapi.routing import APIRoute

from app.main import app  # noqa: E402  (after conftest env isolation)

# Routes that intentionally answer without a token, with the reason they may.
PUBLIC_ROUTES = {
    ("GET", "/api/v1/health"): "probe de saúde; o kernel é loopback anyway",
    ("POST", "/api/v1/auth/login"): "autenticação em si",
    ("POST", "/api/v1/auth/devices/pair"): "pareamento (código + rate limit)",
    ("POST", "/api/v1/automations/webhook/{caminho}"): "porta para programas locais; gatilho armado + X-Teia-Secret",
}

# A credential-shaped KEY ends in a credential word: access_token, api_key,
# hashed_password... `max_tokens` and `tokens_per_s` are LLM generation
# parameters, not credentials — the plural and the `_per_s` suffix are the
# tell. Matching the final segment (not a substring) is what tells them apart.
_CREDENTIAL_KEY = re.compile(
    r"(?:^|_)(?:password|passwd|passphrase|secret|token|api[_-]?key|authorization)$"
)


def _is_credential_key(name: str) -> bool:
    return bool(_CREDENTIAL_KEY.search(name.lower()))


def _api_routes():
    routes = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/v1"):
            continue
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            routes.append((method, route.path))
    return routes


def _sensitive_keys(obj, _path=""):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if _is_credential_key(k):
                hits.append(f"{_path}.{k}")
            hits.extend(_sensitive_keys(v, f"{_path}.{k}"))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            hits.extend(_sensitive_keys(item, f"{_path}[{i}]"))
    return hits


def test_every_protected_route_requires_token(client):
    public = set(PUBLIC_ROUTES)
    audited = 0
    for method, path in _api_routes():
        if (method, path) in public:
            continue
        r = client.request(method, path)
        assert r.status_code == 401, (
            f"{method} {path} respondeu {r.status_code} sem token — falta auth "
            "ou precisa de entrada deliberada no PUBLIC_ROUTES"
        )
        audited += 1
    assert audited >= 140, f"auditoria varreu só {audited} rotas protegidas — esperava a superfície inteira"


def test_every_route_carries_security_headers(client):
    for method, path in _api_routes():
        r = client.request(method, path)
        assert r.headers.get("X-Content-Type-Options") == "nosniff", f"{method} {path}"
        assert r.headers.get("X-Frame-Options") == "DENY", f"{method} {path}"
        assert "frame-ancestors 'none'" in r.headers.get("Content-Security-Policy", ""), f"{method} {path}"


def test_read_routes_leak_no_sensitive_fields(client, owner_headers):
    scanned = 0
    for method, path in _api_routes():
        if method != "GET":
            continue
        r = client.get(path, headers=owner_headers)
        if r.status_code == 200:
            leaked = _sensitive_keys(r.json())
            assert not leaked, f"GET {path} vazou campo(s) sensível(is): {leaked}"
            scanned += 1
        elif r.status_code >= 500:
            raise AssertionError(f"GET {path} respondeu 5xx com token de dono válido")
        # 4xx = precisa de estado/params — não é sinal de vazamento
    assert scanned >= 30, f"auditoria de leituras cobriu só {scanned} rotas — esperava a superfície inteira"


def test_whitelist_entries_are_genuinely_public(client):
    for (method, path), reason in PUBLIC_ROUTES.items():
        r = client.request(method, path)
        assert r.status_code != 401, (
            f"{method} {path} está na whitelist mas exige token ({r.status_code}) "
            f"— razão declarada: {reason}"
        )


def test_whitelist_cites_only_existing_routes():
    existing = set(_api_routes())
    for (method, path) in PUBLIC_ROUTES:
        assert (method, path) in existing, f"PUBLIC_ROUTES cita {method} {path}, que não existe no app"
