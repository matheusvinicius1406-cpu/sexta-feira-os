"""
LearningEngine — the continuous-learning loop (North Star: "Aprendizado Contínuo").

    executar -> observar resultado -> avaliar qualidade -> registrar aprendizado
             -> atualizar memória -> atualizar comportamento futuro

The engine `record`s an outcome with a quality score and a durable lesson, then
*connects the pieces we already have*:
  * writes the lesson to the graph **Memory** (so future recall resurfaces it);
  * updates the **User Model** when a difficulty recurs (behavior adapts);
  * publishes `aprendizado.registrado` on the **Event** bus (audit + reactivity).

This is what makes ours more cohesive than a standalone learner: learning is wired
into memory, the owner model, decisions and events. The design of the
trace->learn->evaluate loop is adapted (reimplemented here) from the Apache-2.0
OpenJarvis learning orchestrator — see ADR-0005. No cloud/model code was copied;
the Kernel stays model-independent and "só meu".
"""
from __future__ import annotations

import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Learning

_LOW_QUALITY = 0.4
_RECURRENCE_THRESHOLD = 2  # low-quality lessons on the same tag => a recurring difficulty


def _clamp(x: float) -> float:
    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return 0.5


class LearningEngine:
    def __init__(self, memory=None, world=None, events=None) -> None:
        self.memory = memory  # PersistentMemory | None
        self.world = world    # WorldModel | None (User Model lives here)
        self.events = events  # EventBus | None

    async def record(
        self, db: Session, owner_id: str, context: str, *,
        observation: str | None = None, quality: float = 0.5, lesson: str | None = None,
        kind: str = "outcome", tag: str | None = None, ref_id: str | None = None,
        source: str = "kernel",
    ) -> Learning:
        """Register one learning and fold it into memory, the owner model and events."""
        context = (context or "").strip()
        if not context:
            raise ValueError("learning needs a context")
        q = _clamp(quality)
        entry = Learning(
            id=str(uuid.uuid4()), owner_id=owner_id, kind=kind, tag=tag, ref_id=ref_id,
            context=context, observation=observation, quality=q, lesson=lesson, source=source,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)

        # Durable lesson -> graph memory (resurfaces via recall).
        if lesson and self.memory:
            await self.memory.remember(
                db, owner_id, lesson, kind="lesson", importance=0.6, source="learning",
            )
        # Recurring difficulty -> User Model (behavior adapts).
        if tag and q < _LOW_QUALITY and self.world:
            self._maybe_flag_difficulty(db, owner_id, tag)
        # Announce it.
        if self.events:
            await self.events.publish(
                db, owner_id, "aprendizado.registrado",
                {"kind": kind, "tag": tag, "quality": q}, source="learning",
            )
        return entry

    async def observe_decision(
        self, db: Session, owner_id: str, decision_id: str, quality: float,
        note: str | None = None,
    ) -> Learning:
        """Feedback on a past decision — closes the loop with the Decision Engine."""
        return await self.record(
            db, owner_id, f"decisão {decision_id}", observation=note, quality=quality,
            kind="feedback", tag="decisao", ref_id=decision_id, source="owner",
        )

    def _maybe_flag_difficulty(self, db: Session, owner_id: str, tag: str) -> None:
        low = (
            db.query(func.count(Learning.id))
            .filter(
                Learning.owner_id == owner_id, Learning.tag == tag,
                Learning.quality < _LOW_QUALITY,
            )
            .scalar()
        ) or 0
        if low >= _RECURRENCE_THRESHOLD:
            self.world.set_attribute(
                db, owner_id, f"dificuldade_{tag}", f"dificuldade recorrente em '{tag}'",
                category="knowledge", source="learning", is_inference=True,
            )

    # ---------- reads ----------

    def lessons(
        self, db: Session, owner_id: str, limit: int = 100, tag: str | None = None
    ) -> list[Learning]:
        q = db.query(Learning).filter(Learning.owner_id == owner_id)
        if tag:
            q = q.filter(Learning.tag == tag)
        return q.order_by(Learning.created_at.desc()).limit(limit).all()

    def stats(self, db: Session, owner_id: str, recent: int = 50) -> dict:
        rows = (
            db.query(Learning.quality)
            .filter(Learning.owner_id == owner_id)
            .order_by(Learning.created_at.desc())
            .limit(recent)
            .all()
        )
        total = db.query(func.count(Learning.id)).filter(Learning.owner_id == owner_id).scalar() or 0
        qualities = [r[0] for r in rows if r[0] is not None]
        avg = round(sum(qualities) / len(qualities), 4) if qualities else None
        return {"total": int(total), "recent_avg_quality": avg, "recent_count": len(qualities)}
