"""
Scheduler — the brain's sense of time.

Stores future intentions and fires them when due, through the Action Protocol:
  * reminder -> a `notify` action to the owner's body (phone), carrying the text.
  * action   -> the stored device action, at the scheduled time.

`run_due` is a pure, deterministic method (no sleeping) so firing is trivial to
test; the background loop just calls it on an interval.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.action.service import ActionService
from app.models.models import ScheduledTask

logger = logging.getLogger("sexta-feira.schedule")


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime) -> datetime:
    """SQLite may return naive datetimes; treat them as UTC for safe comparison."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


class Scheduler:
    def __init__(self, actions: ActionService):
        self.actions = actions

    # ---------- create / manage ----------

    def schedule(
        self, db: Session, owner_id: str, *, kind: str, due_at: datetime,
        text: str | None = None, device: str | None = None,
        action: str | None = None, params: dict | None = None,
        recurrence_seconds: int | None = None,
    ) -> ScheduledTask:
        task = ScheduledTask(
            id=str(uuid.uuid4()), owner_id=owner_id, kind=kind,
            due_at=due_at.astimezone(UTC).replace(tzinfo=None),  # store naive-UTC
            text=text, device_selector=device, action=action,
            params=json.dumps(params) if params else None,
            recurrence_seconds=recurrence_seconds, status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def list(self, db: Session, owner_id: str, include_done: bool = False) -> list[dict]:
        q = db.query(ScheduledTask).filter(ScheduledTask.owner_id == owner_id)
        if not include_done:
            q = q.filter(ScheduledTask.status == "pending")
        return [self._to_dict(t) for t in q.order_by(ScheduledTask.due_at).all()]

    def cancel(self, db: Session, owner_id: str, task_id: str) -> bool:
        t = db.query(ScheduledTask).filter(
            ScheduledTask.id == task_id, ScheduledTask.owner_id == owner_id,
            ScheduledTask.status == "pending",
        ).first()
        if not t:
            return False
        t.status = "cancelled"
        db.commit()
        return True

    # ---------- firing ----------

    async def run_due(self, db: Session, now: datetime | None = None) -> int:
        """Fire every pending task whose time has come. Returns how many fired."""
        now = now or _now()
        cutoff = now.astimezone(UTC).replace(tzinfo=None)
        due = (
            db.query(ScheduledTask)
            .filter(ScheduledTask.status == "pending", ScheduledTask.due_at <= cutoff)
            .order_by(ScheduledTask.due_at)
            .all()
        )
        fired = 0
        for task in due:
            try:
                await self._fire(db, task)
            except Exception as e:  # noqa: BLE001 — one bad task must not stop the rest
                logger.warning("scheduled task %s failed to fire: %s", task.id, e)
            self._advance(db, task, now)
            fired += 1
        return fired

    async def _fire(self, db: Session, task: ScheduledTask) -> None:
        if task.kind == "action" and task.action:
            params = json.loads(task.params) if task.params else {}
            await self.actions.dispatch(
                db, task.owner_id, task.device_selector or "celular", task.action, params
            )
        else:  # reminder
            await self.actions.dispatch(
                db, task.owner_id, task.device_selector or "celular",
                "notify", {"text": task.text or "Lembrete"},
            )

    def _advance(self, db: Session, task: ScheduledTask, now: datetime) -> None:
        if task.recurrence_seconds:
            base = _aware(task.due_at)
            next_due = base + timedelta(seconds=task.recurrence_seconds)
            # don't fall behind: skip missed cycles
            while next_due <= now:
                next_due += timedelta(seconds=task.recurrence_seconds)
            task.due_at = next_due.astimezone(UTC).replace(tzinfo=None)
        else:
            task.status = "fired"
            task.fired_at = now.astimezone(UTC).replace(tzinfo=None)
        db.commit()

    @staticmethod
    def _to_dict(t: ScheduledTask) -> dict:
        return {
            "id": t.id, "kind": t.kind, "due_at": t.due_at, "text": t.text,
            "device": t.device_selector, "action": t.action,
            "params": json.loads(t.params) if t.params else None,
            "recurrence_seconds": t.recurrence_seconds, "status": t.status,
        }
