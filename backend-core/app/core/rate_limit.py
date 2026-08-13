"""
rate_limit.py — brute-force guard for the few unauthenticated endpoints.

/login and /devices/pair are the only routes reachable without a token, so
they are the only ones worth throttling. A sliding window per source IP: after
N failures the IP is locked for M seconds (HTTP 429 + Retry-After). In-memory
and per-process — a kernel restart clears the counter, exactly as a restart
already invalidates every development token.
"""
from __future__ import annotations

import threading
import time

from fastapi import Request


class LoginThrottle:
    """Sliding-window failure counter with lockout, safe for concurrent calls."""

    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: int = 900,
        lockout_seconds: int = 900,
    ):
        self.max_attempts = max(1, max_attempts)
        self.window = max(1, window_seconds)
        self.lockout = max(1, lockout_seconds)
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    # ── internals ─────────────────────────────────────────

    def _prune(self, key: str, now: float) -> None:
        bucket = self._failures.get(key)
        if not bucket:
            return
        alive = [t for t in bucket if now - t < self.window]
        if alive:
            self._failures[key] = alive
        else:
            self._failures.pop(key, None)

    # ── public API ────────────────────────────────────────

    def remaining_lockout(self, key: str) -> int:
        """Seconds still locked for `key`, 0 if free.

        Only clears the failure bucket when a lockout has FULLY expired —
        checking must never wipe the counter it is supposed to read (that bug
        made the throttle count to 1 and then forget, every single time).
        """
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            bucket = self._failures.get(key)
            if not bucket:
                return 0
            if len(bucket) >= self.max_attempts:
                # Locked from the FIRST failure in the window — a burst of 100
                # tries does not get to retry later than a careful 5.
                until = bucket[0] + self.lockout
                if until > now:
                    return int(until - now) + 1
                # Lockout fully expired -> clean slate.
                self._failures.pop(key, None)
            return 0

    def register_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            self._failures.setdefault(key, []).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


# The one instance every auth endpoint shares.
throttle = LoginThrottle()


def client_ip(request: Request) -> str:
    """The peer's IP. We deliberately do NOT trust X-Forwarded-For: the kernel
    is a private single-owner service and is never meant to sit behind a
    reverse proxy, so the socket peer IS the attacker."""
    return request.client.host if request.client else "unknown"
