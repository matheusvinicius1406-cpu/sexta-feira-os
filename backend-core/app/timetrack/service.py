"""
TimeTracker — track where time goes, optionally tied to a Planning goal.

Single-active-timer model (ADR-0010): starting a timer closes any open one
(deterministic, no orphan spans). Wired into the pillars:
  * `tempo.iniciado` / `tempo.parado` on the Event bus (audit trail);
  * the World Model carries `atividade_atual` while a timer runs — the present
    always knows what the owner is doing — and forgets it on stop.

All local, owner-scoped, deterministic (an injectable clock keeps tests exact).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.models import Goal, TimeEntry


def _now() -> datetime:
    return datetime.now(UTC)


def _naive(dt: datetime) -> datetime:
    return dt.astimezone(UTC).replace(tzinfo=None) if dt.tzinfo else dt


class TimeTracker:
    def __init__(self, world=None, events=None, now=None):
        self.world = world    # WorldModel | None
        self.events = events  # EventBus | None
        self._now = now or _now  # injectable clock for deterministic tests

    async def start(
        self, db: Session, owner_id: str, label: str, goal_id: str | None = None
    ) -> TimeEntry:
        label = (label or "").strip()
        if not label:
            raise ValueError("timer needs a label")
        if goal_id:
            goal = db.query(Goal).filter(
                Goal.id == goal_id, Goal.owner_id == owner_id,
            ).first()
            if not goal:
                goal_id = None  # unknown goal: keep the label, drop the link
        await self.stop(db, owner_id)  # single active timer
        entry = TimeEntry(
            id=str(uuid.uuid4()), owner_id=owner_id, goal_id=goal_id, label=label,
            started_at=_naive(self._now()),
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        if self.world:
            self.world.set_fact(
                db, owner_id, "atividade_atual", label,
                category="active_work", source="timetracker",
            )
        if self.events:
            await self.events.publish(
                db, owner_id, "tempo.iniciado", {"label": label}, source="timetracker",
            )
        return entry

    async def stop(self, db: Session, owner_id: str) -> dict | None:
        """Close the open timer, if any. Returns {label, seconds} or None."""
        open_entry = self.current(db, owner_id)
        if not open_entry:
            return None
        open_entry.ended_at = _naive(self._now())
        db.commit()
        seconds = int((open_entry.ended_at - open_entry.started_at).total_seconds())
        if self.world:
            self.world.forget_fact(db, owner_id, "atividade_atual")
        if self.events:
            await self.events.publish(
                db, owner_id, "tempo.parado",
                {"label": open_entry.label, "seconds": seconds}, source="timetracker",
            )
        return {"label": open_entry.label, "seconds": seconds}

    def current(self, db: Session, owner_id: str) -> TimeEntry | None:
        return (
            db.query(TimeEntry)
            .filter(TimeEntry.owner_id == owner_id, TimeEntry.ended_at.is_(None))
            .order_by(TimeEntry.started_at.desc())
            .first()
        )

    def summary(self, db: Session, owner_id: str, limit_entries: int = 500) -> list[dict]:
        """Total seconds per label (closed entries), most time first."""
        rows = (
            db.query(TimeEntry)
            .filter(TimeEntry.owner_id == owner_id, TimeEntry.ended_at.isnot(None))
            .order_by(TimeEntry.started_at.desc())
            .limit(limit_entries)
            .all()
        )
        totals: dict[str, int] = {}
        for r in rows:
            totals[r.label] = totals.get(r.label, 0) + int(
                (r.ended_at - r.started_at).total_seconds()
            )
        return [
            {"label": label, "seconds": secs}
            for label, secs in sorted(totals.items(), key=lambda kv: -kv[1])
        ]
