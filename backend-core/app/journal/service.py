"""
JournalService & HabitService — daily notes and recurring practices.

Concept adapted from local-first daily tools (journal, habits — ADR-0009), wired
into our pillars instead of standing alone:
  * a journal entry publishes `diario.registrado` and (best-effort) runs the
    MemoryExtractor, so durable facts land in the graph / User Model;
  * a habit check-in publishes `habito.marcado` and reflects the streak in the
    World Model (`habito:<nome>` = "streak de N dias") — the present knows.

Everything deterministic and local; check-ins are idempotent (one per day).
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import Habit, HabitCheck, JournalEntry

logger = logging.getLogger("sexta-feira.journal")


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


class JournalService:
    def __init__(self, events=None, extractor=None):
        self.events = events        # EventBus | None
        self.extractor = extractor  # MemoryExtractor | None (best-effort distillation)

    async def add(
        self, db: Session, owner_id: str, content: str, mood: str | None = None
    ) -> JournalEntry:
        content = (content or "").strip()
        if not content:
            raise ValueError("journal entry needs content")
        entry = JournalEntry(
            id=str(uuid.uuid4()), owner_id=owner_id, content=content, mood=mood,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        if self.events:
            await self.events.publish(
                db, owner_id, "diario.registrado", {"mood": mood}, source="journal",
            )
        if self.extractor:
            try:  # a failed distillation never breaks the entry
                await self.extractor.extract(db, owner_id, content, "")
            except Exception as e:  # noqa: BLE001
                logger.debug("journal distillation skipped: %s", e)
        return entry

    def list(self, db: Session, owner_id: str, limit: int = 50) -> list[JournalEntry]:
        return (
            db.query(JournalEntry)
            .filter(JournalEntry.owner_id == owner_id)
            .order_by(JournalEntry.created_at.desc())
            .limit(limit)
            .all()
        )


class HabitService:
    def __init__(self, world=None, events=None):
        self.world = world    # WorldModel | None
        self.events = events  # EventBus | None

    def create(self, db: Session, owner_id: str, name: str) -> Habit:
        slug = (name or "").strip().lower()
        if not slug:
            raise ValueError("habit needs a name")
        habit = (
            db.query(Habit)
            .filter(Habit.owner_id == owner_id, Habit.name == slug)
            .first()
        )
        if not habit:
            habit = Habit(id=str(uuid.uuid4()), owner_id=owner_id, name=slug)
            db.add(habit)
            db.commit()
            db.refresh(habit)
        return habit

    async def check(
        self, db: Session, owner_id: str, name: str, day: str | None = None
    ) -> dict:
        """Mark a habit done for `day` (default today). Idempotent per day."""
        habit = self.create(db, owner_id, name)
        day = day or _today()
        exists = (
            db.query(HabitCheck)
            .filter(HabitCheck.habit_id == habit.id, HabitCheck.day == day)
            .first()
        )
        if not exists:
            db.add(HabitCheck(
                id=str(uuid.uuid4()), owner_id=owner_id, habit_id=habit.id, day=day,
            ))
            db.commit()
        streak = self.streak(db, owner_id, habit.name, today=day)
        if self.world:
            self.world.set_fact(
                db, owner_id, f"habito:{habit.name}", f"streak de {streak} dias",
                category="user_state", source="habits",
            )
        if self.events and not exists:
            await self.events.publish(
                db, owner_id, "habito.marcado",
                {"habit": habit.name, "day": day, "streak": streak}, source="habits",
            )
        return {"habit": habit.name, "day": day, "streak": streak, "already": bool(exists)}

    def streak(self, db: Session, owner_id: str, name: str, today: str | None = None) -> int:
        """Consecutive days done, ending at `today` (deterministic, from checks)."""
        habit = (
            db.query(Habit)
            .filter(Habit.owner_id == owner_id, Habit.name == (name or "").strip().lower())
            .first()
        )
        if not habit:
            return 0
        days = {
            c.day for c in db.query(HabitCheck).filter(HabitCheck.habit_id == habit.id).all()
        }
        cursor = datetime.strptime(today or _today(), "%Y-%m-%d")
        streak = 0
        while cursor.strftime("%Y-%m-%d") in days:
            streak += 1
            cursor -= timedelta(days=1)
        return streak

    def list(self, db: Session, owner_id: str) -> list[dict]:
        habits = (
            db.query(Habit)
            .filter(Habit.owner_id == owner_id, Habit.enabled.is_(True))
            .order_by(Habit.name)
            .all()
        )
        return [
            {"id": h.id, "name": h.name, "schedule": h.schedule,
             "streak": self.streak(db, owner_id, h.name)}
            for h in habits
        ]
