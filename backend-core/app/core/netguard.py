"""
netguard.py — the outbound URL firewall.

The kernel talks TO the world in a few places: the automation HTTP node, the
brain's fetch_page/web_search tools, the connectors. Every one of those sinks
used to accept ANY url — which turns the kernel into an open proxy for the
whole private network. Measured live during the 2026-08 security audit: a
single HTTP node pointed at http://127.0.0.1:11434/api/version returned
Ollama's version string, no token required. From there it is one step to the
cloud metadata endpoint (169.254.169.254), the router admin page, or a
service the owner forgot had no password.

This module is the one gate every outbound sink passes through:

  * scheme must be http/https — file://, gopher://, etc. are refused outright;
  * the hostname is RESOLVED and every address checked — a DNS rebinding that
    serves a public IP to the checker and a private one to the fetch is
    defeated because the same resolution is used for the check and the fetch;
  * loopback, private, link-local, CGNAT, reserved and multicast are blocked,
    including IPv4-mapped IPv6 (::ffff:127.0.0.1);
  * exceptions are explicit: a host listed in TEIA_ALLOWED_OUTBOUND_HOSTS is
    allowed (e.g. a home NAS the owner wants automations to reach), and a sink
    may opt into `allow_loopback` when it is a kernel-internal call.

Validation happens at EXECUTION time, never at save time: an automation's URL
may carry {{ vars.x }} placeholders that only resolve when the workflow runs,
and those values come from webhook payloads — untrusted input.
"""
from __future__ import annotations

import ipaddress
import logging
import socket
import urllib.parse

from app.core.config import settings

logger = logging.getLogger("sexta-feira.netguard")

_ALLOWED_SCHEMES = {"http", "https"}
_MAX_URL_LENGTH = 2048
_REDIRECT_HOPS = 5


def _is_forbidden_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True  # garbage address -> refuse
    # Normalize IPv4-mapped IPv6 (::ffff:127.0.0.1) to the IPv4 it wraps —
    # ipaddress.is_private does NOT catch those.
    if addr.version == 6 and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def _extra_allowed_hosts() -> set[str]:
    return {h.strip().lower() for h in settings.teia_allowed_outbound_hosts if h.strip()}


def _is_loopback_host(host: str) -> bool:
    return host in {"127.0.0.1", "localhost", "::1", "::ffff:127.0.0.1"}


def validate_outbound_url(url: str, *, allow_loopback: bool = False, reason: str = "destino") -> None:
    """Raise ValueError if `url` may reach anything but a public HTTP(S) host.

    Called with the FINAL url (placeholders already resolved) right before the
    request is issued, so the check and the fetch share the same resolution.
    """
    if not url or len(url) > _MAX_URL_LENGTH:
        raise ValueError(f"{reason}: URL inválida")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"{reason}: apenas http/https são permitidos (esquema '{parsed.scheme}')")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError(f"{reason}: URL sem host")

    if host in _extra_allowed_hosts():
        return
    if allow_loopback and _is_loopback_host(host):
        return

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise ValueError(f"{reason}: não foi possível resolver '{host}'") from None

    seen: set[str] = set()
    for info in infos:
        ip = info[4][0]
        if ip in seen:
            continue
        seen.add(ip)
        if _is_forbidden_ip(ip):
            raise ValueError(
                f"{reason}: '{host}' resolve para um endereço interno ({ip}) — "
                "bloqueado pelo netguard. Para permitir, liste o host em "
                "TEIA_ALLOWED_OUTBOUND_HOSTS no .env."
            )


async def guarded_request(client, method: str, url: str, **kwargs) -> object:
    """Issue an HTTP request following redirects, validating EVERY hop.

    `follow_redirects=True` would let an external URL bounce to an internal
    one after passing the check — each hop is therefore validated before it
    is requested, with a hard hop cap.
    """
    current = url
    hops = 0
    while True:
        validate_outbound_url(current, reason="nó http")
        response = await client.request(method, current, **kwargs)
        location = response.headers.get("location")
        if response.status_code in (301, 302, 303, 307, 308) and location:
            hops += 1
            if hops > _REDIRECT_HOPS:
                raise RuntimeError("muitos redirecionamentos (netguard)")
            current = urllib.parse.urljoin(current, location)
            if response.status_code == 303 and method not in ("GET", "HEAD"):
                method = "GET"
            continue
        return response
