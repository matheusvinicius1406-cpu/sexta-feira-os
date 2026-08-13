"""
security.py — HTTP hardening for the private kernel.

  * SecurityHeadersMiddleware — sends the headers that turn off the browser
    attack surface (MIME sniffing, framing, referrer leaking, popups) and a
    strict CSP for the JSON API. Swagger/Redoc are exempted from CSP because
    their UIs need inline scripts/styles.
  * RedactingFormatter — masks `token=`, `code=`, `key=`, `secret=` and
    `password=` values in log lines (uvicorn's access log prints the full
    path, and the action WebSocket carries the device JWT in ?token=...).
"""
from __future__ import annotations

import logging
import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings

# Hardened for the JSON API only — Swagger UI needs its own (permissive) page.
_JSON_CSP = (
    "default-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'none'; "
    "form-action 'none'"
)

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "X-XSS-Protection": "0",  # modern guidance: disable the legacy auditor
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}

# Paths whose UIs embed inline scripts/styles — CSP must not break them.
_DOCS_PATHS = {"/docs", "/redoc", "/openapi.json"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for name, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.url.path not in _DOCS_PATHS:
            response.headers.setdefault("Content-Security-Policy", _JSON_CSP)
        return response


class HostGuardMiddleware(BaseHTTPMiddleware):
    """Anti-DNS-rebinding for the dev auth bypass.

    The bypass trusts the loopback source address — and a malicious website can
    DNS-rebind (evil.com resolves to 127.0.0.1 after the page loads), turning
    its requests into same-origin loopback ones the bypass happily serves. The
    one thing the browser cannot spoof is the Host header: when the bypass is
    on, only loopback hosts are accepted. With the bypass off (the safe
    default) this middleware does nothing.
    """

    @staticmethod
    def _loopback_host(request: Request) -> bool:
        host = request.headers.get("host", "").lower()
        if host.startswith("["):  # [::1]:8000
            host = host.split("]")[0][1:]
        else:
            host = host.split(":")[0]
        return host in {"127.0.0.1", "localhost", "::1"}

    async def dispatch(self, request: Request, call_next):
        if settings.auth_dev_bypass and not self._loopback_host(request):
            from fastapi.responses import JSONResponse

            # Tripwire: a non-loopback Host while the bypass is on is the DNS-
            # rebinding signature — a browser page pointing evil.com at us.
            from app.core.threats import record_threat_sync
            from app.db.database import SessionLocal

            db = SessionLocal()
            try:
                record_threat_sync(
                    db, "dns-rebinding",
                    "Host não-loopback rejeitado: " + (request.headers.get("host") or "?"),
                    source_ip=request.client.host if request.client else None,
                )
            finally:
                db.close()
            return JSONResponse({"detail": "Host não permitido"}, status_code=403)
        return await call_next(request)


_SENSITIVE = re.compile(r"(^|[?&\s])(token|code|key|secret|password)=[^&\s\"']+")


def _redact_line(line: str) -> str:
    return _SENSITIVE.sub(r"\1\2=***", line)


class RedactingFormatter(logging.Formatter):
    """Masks credential query params (token=, code=, ...) in the RENDERED line.

    The redaction runs on the final string, after %-interpolation — the record
    is never mutated, so a message that legitimately contains '%' cannot break
    formatting and the original args stay intact for other handlers.
    """

    def format(self, record: logging.LogRecord) -> str:
        return _redact_line(super().format(record))


try:
    from uvicorn.logging import (  # type: ignore[attr-defined]
        AccessFormatter as _UvicornAccessFormatter,
    )
    from uvicorn.logging import (
        DefaultFormatter as _UvicornDefaultFormatter,
    )
except ImportError:  # pragma: no cover — uvicorn is a runtime dependency
    _UvicornAccessFormatter = logging.Formatter
    _UvicornDefaultFormatter = logging.Formatter


class RedactingAccessFormatter(_UvicornAccessFormatter):
    """uvicorn's access log prints the full request line — including the
    device JWT the action WebSocket carries in ?token=... This masks it while
    keeping uvicorn's field injection (client_addr, request_line, status)."""

    def format(self, record: logging.LogRecord) -> str:
        return _redact_line(super().format(record))


class RedactingDefaultFormatter(_UvicornDefaultFormatter):
    """Same redaction for uvicorn's own log lines (startup/shutdown messages)."""

    def format(self, record: logging.LogRecord) -> str:
        return _redact_line(super().format(record))
