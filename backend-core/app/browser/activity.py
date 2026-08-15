"""
In-memory record of the kernel's own web searches — its "tabs".

The kernel does not control a browser, so it has no tabs to list. What it DOES
have is its own reach into the web: every search the owner runs through it.
Those are the kernel's open windows — ephemeral by nature, kept since boot and
gone when the process restarts. The panel says exactly that, because a tab
that claims to be Chrome's is a lie, and a search history that survives a
reboot is a promise about persistence this store does not make.
"""
from __future__ import annotations

import threading
from collections import deque
from datetime import UTC, datetime

_lock = threading.Lock()
_tabs: deque[dict] = deque(maxlen=25)
_started = datetime.now(UTC)


def record_search(query: str, kind: str, results: int, top_url: str | None = None) -> None:
    """Append a search the kernel just performed. Newest first."""
    with _lock:
        _tabs.appendleft({
            "query": query,
            "kind": kind,  # "search" | "search_and_fetch"
            "results": results,
            "top_url": top_url,
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
        })


def recent_tabs() -> tuple[list[dict], str]:
    """The tabs since boot, plus when this kernel process started."""
    with _lock:
        return list(_tabs), _started.isoformat(timespec="seconds")
