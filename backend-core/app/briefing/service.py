"""
BriefingService — the proactive "reports back every morning" capstone.

It assembles, from LOCAL data only, a single briefing that ties together the five
pillars we built:
  * the present            -> World Model (WorldFact)
  * the owner              -> User Model (UserAttribute)
  * open goals & what's due -> Planning Engine
  * what to focus on now    -> Decision Engine
  * what just happened      -> Event bus history
  * what we learned         -> Learning Engine

Deterministic assembly (works offline, testable); an LLM can narrate the text
later, but the structured content never depends on a model. Concept adapted from
the local-first daily-briefing idea — "só meu", nothing leaves the machine.
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.models import Briefing


def _now() -> datetime:
    return datetime.now(UTC)


class BriefingService:
    def __init__(self, world=None, planning=None, decision=None, events=None, learning=None) -> None:
        self.world = world
        self.planning = planning
        self.decision = decision
        self.events = events
        self.learning = learning

    async def generate(self, db: Session, owner_id: str, kind: str = "on_demand") -> Briefing:
        sections = {
            "present": self._present(db, owner_id),
            "owner": self._owner(db, owner_id),
            "goals": self._goals(db, owner_id),
            "focus": await self._focus(db, owner_id),
            "recent_events": self._events(db, owner_id),
            "lessons": self._lessons(db, owner_id),
        }
        summary = self._render(sections)
        briefing = Briefing(
            id=str(uuid.uuid4()), owner_id=owner_id, kind=kind,
            summary=summary, content=json.dumps(sections, ensure_ascii=False),
        )
        db.add(briefing)
        db.commit()
        db.refresh(briefing)
        if self.events:
            await self.events.publish(
                db, owner_id, "briefing.gerado", {"kind": kind}, source="briefing",
            )
        return briefing

    # ---------- sections (each degrades gracefully if a pillar is absent) ----------

    def _present(self, db: Session, owner_id: str) -> list[dict]:
        if not self.world:
            return []
        return [
            {"key": f.key, "value": f.value, "inference": f.is_inference}
            for f in self.world.snapshot(db, owner_id, 10)
        ]

    def _owner(self, db: Session, owner_id: str) -> list[dict]:
        if not self.world:
            return []
        return [{"key": a.key, "value": a.value} for a in self.world.profile(db, owner_id, 6)]

    def _goals(self, db: Session, owner_id: str) -> list[dict]:
        if not self.planning:
            return []
        out = []
        for g in self.planning.list_goals(db, owner_id):
            if g.status in ("pending", "active", "blocked"):
                out.append({
                    "title": g.title, "status": g.status,
                    "progress": g.progress, "due_at": g.due_at.isoformat() if g.due_at else None,
                })
        return out[:10]

    async def _focus(self, db: Session, owner_id: str) -> dict | None:
        if not self.decision:
            return None
        d = await self.decision.decide_next_goal(db, owner_id)
        if not d:
            return None
        return {"goal": d.chosen_label, "rationale": d.rationale}

    def _events(self, db: Session, owner_id: str) -> list[dict]:
        if not self.events:
            return []
        return [{"type": e.type, "at": e.created_at.isoformat()} for e in self.events.history(db, owner_id, 8)]

    def _lessons(self, db: Session, owner_id: str) -> list[dict]:
        if not self.learning:
            return []
        return [
            {"lesson": x.lesson or x.context, "quality": x.quality}
            for x in self.learning.lessons(db, owner_id, 5)
        ]

    # ---------- deterministic text rendering ----------

    @staticmethod
    def _render(sections: dict) -> str:
        lines = [f"Briefing — {_now().strftime('%Y-%m-%d %H:%M')}"]

        present = sections.get("present") or []
        if present:
            lines.append("\nAgora:")
            for f in present[:6]:
                mark = " (inferência)" if f.get("inference") else ""
                lines.append(f"  • {f['key']}: {f['value']}{mark}")

        focus = sections.get("focus")
        if focus:
            lines.append(f"\nFoco sugerido: {focus['goal']} — {focus['rationale']}")

        goals = sections.get("goals") or []
        if goals:
            lines.append("\nObjetivos abertos:")
            for g in goals[:6]:
                pct = int(g["progress"] * 100)
                due = f", vence {g['due_at'][:10]}" if g.get("due_at") else ""
                lines.append(f"  • [{g['status']}] {g['title']} ({pct}%){due}")

        lessons = sections.get("lessons") or []
        if lessons:
            lines.append("\nAprendizados recentes:")
            for x in lessons[:3]:
                lines.append(f"  • {x['lesson']}")

        events = sections.get("recent_events") or []
        if events:
            kinds = ", ".join(sorted({e["type"] for e in events})[:6])
            lines.append(f"\nEventos recentes: {kinds}")

        if len(lines) == 1:
            lines.append("\nNada a reportar ainda — sem estado, objetivos ou eventos.")
        return "\n".join(lines)

    # ---------- reads ----------

    def history(self, db: Session, owner_id: str, limit: int = 30) -> list[Briefing]:
        return (
            db.query(Briefing)
            .filter(Briefing.owner_id == owner_id)
            .order_by(Briefing.created_at.desc())
            .limit(limit)
            .all()
        )

    def latest(self, db: Session, owner_id: str) -> Briefing | None:
        return (
            db.query(Briefing)
            .filter(Briefing.owner_id == owner_id)
            .order_by(Briefing.created_at.desc())
            .first()
        )
