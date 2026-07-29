"""Append-only structured audit log.

Every authorization decision and every tool side effect is recorded as one JSON
line: who (agent), what (server.action), on what (target), the decision, and
optional detail. Secrets are redacted before writing. The log is append-only and
never rewritten, so it is safe to tail for real-time monitoring.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path

_SECRET_RE = re.compile(
    r"(?i)(token|secret|password|api[_-]?key|authorization|bearer)\s*[:=]\s*\S+"
)


def redact(value: object) -> object:
    """Best-effort redaction of secret-looking substrings in strings/dicts."""
    if isinstance(value, str):
        return _SECRET_RE.sub(r"\1=***", value)
    if isinstance(value, dict):
        return {k: ("***" if _looks_secret(k) else redact(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value


def _looks_secret(key: str) -> bool:
    k = key.lower()
    return any(s in k for s in ("token", "secret", "password", "api_key", "apikey", "authorization"))


class AuditLog:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def record(
        self,
        *,
        agent: str,
        action: str,
        target: str = "",
        decision: str = "allow",
        detail: dict | None = None,
    ) -> dict:
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
            "pid": os.getpid(),
            "agent": agent,
            "action": action,
            "target": target,
            "decision": decision,
            "detail": redact(detail or {}),
        }
        line = json.dumps(entry, ensure_ascii=False)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        return entry

    def tail(self, n: int = 50) -> list[dict]:
        if not self.path.is_file():
            return []
        with self.path.open("r", encoding="utf-8") as fh:
            lines = fh.readlines()[-n:]
        out = []
        for ln in lines:
            ln = ln.strip()
            if ln:
                try:
                    out.append(json.loads(ln))
                except json.JSONDecodeError:
                    continue
        return out
