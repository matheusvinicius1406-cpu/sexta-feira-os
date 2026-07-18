"""
EventBus — the kernel's Event-Driven backbone.

Components PUBLISH what happened; subscribers REACT. Every event is persisted as
a first-class audit trail, gets a per-owner sequence (ordering), and may update
the World Model. The bus is substitutable behind this contract (an async queue
or a broker could replace the in-process dispatch without touching callers).

Guarantees (see docs/jarvis/architecture/EVENT_ARCHITECTURE.md):
  * Auditability — every event is stored, even if a subscriber fails.
  * Idempotency — an `idempotency_key` dedupes re-delivery.
  * Ordering/correlation — per-owner `sequence` + optional `correlation_id`.
  * Graceful degradation — a failing/slow subscriber is isolated; it never
    corrupts the event nor blocks the others.
"""
from __future__ import annotations

import inspect
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Event

logger = logging.getLogger("sexta-feira.events")

Handler = Callable[[Session, Event], Any | Awaitable[Any]]


def _now() -> datetime:
    return datetime.now(UTC)


def _matcher(pattern: str) -> Callable[[str], bool]:
    """Match an event type against 'exact', a 'prefix.*' glob, or '*' (all)."""
    if pattern == "*":
        return lambda t: True
    if pattern.endswith(".*"):
        prefix = pattern[:-1]          # "dispositivo." from "dispositivo.*"
        base = pattern[:-2]            # "dispositivo"
        return lambda t: t == base or t.startswith(prefix)
    return lambda t: t == pattern


class EventBus:
    def __init__(self) -> None:
        self._subs: list[tuple[Callable[[str], bool], Handler, str]] = []

    def subscribe(self, pattern: str, handler: Handler, name: str | None = None) -> None:
        """Register an in-process subscriber for a type / 'prefix.*' / '*'."""
        self._subs.append((_matcher(pattern), handler, name or pattern))

    async def publish(
        self, db: Session, owner_id: str, type: str, payload: dict | None = None, *,
        source: str = "kernel", correlation_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Event:
        """Persist an event and dispatch it to matching subscribers (deterministic)."""
        etype = (type or "").strip()
        if not etype:
            raise ValueError("event needs a type")

        if idempotency_key:
            existing = (
                db.query(Event)
                .filter(Event.owner_id == owner_id, Event.idempotency_key == idempotency_key)
                .first()
            )
            if existing:
                return existing  # already handled — do not re-dispatch

        seq = (
            db.query(func.max(Event.sequence)).filter(Event.owner_id == owner_id).scalar() or 0
        ) + 1
        ev = Event(
            id=str(uuid.uuid4()), owner_id=owner_id, type=etype, source=source,
            payload=json.dumps(payload, ensure_ascii=False) if payload is not None else None,
            correlation_id=correlation_id, idempotency_key=idempotency_key,
            sequence=seq, status="received",
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)

        await self._dispatch(db, ev)
        return ev

    async def _dispatch(self, db: Session, ev: Event) -> None:
        errors: list[str] = []
        for match, handler, name in self._subs:
            if not match(ev.type):
                continue
            try:
                result = handler(db, ev)
                if inspect.isawaitable(result):
                    await result
            except Exception as e:  # noqa: BLE001 — isolate one bad subscriber
                logger.warning("subscriber '%s' failed on %s: %s", name, ev.type, e)
                errors.append(f"{name}: {e}")
        ev.status = "failed" if errors else "processed"
        ev.error = "; ".join(errors)[:1000] if errors else None
        ev.processed_at = _now()
        db.commit()

    def history(
        self, db: Session, owner_id: str, limit: int = 200, type: str | None = None
    ) -> list[Event]:
        """The audit trail, most recent first (by sequence)."""
        q = db.query(Event).filter(Event.owner_id == owner_id)
        if type:
            q = q.filter(Event.type == type)
        return q.order_by(Event.sequence.desc()).limit(limit).all()

    @staticmethod
    def decode_payload(ev: Event) -> dict:
        try:
            return json.loads(ev.payload) if ev.payload else {}
        except (ValueError, TypeError):
            return {}
