"""
WorldModel — the present state of reality (World Model) + the model of the owner
(User Model). The Kernel consults this on every turn so that, as the North Star
says, **no request ever starts from zero**.

Two owner-scoped, typed fact stores upserted by key:
  * WorldFact     — the NOW ("localizacao", "foco_atual", "dispositivos_online").
  * UserAttribute — the OWNER over time (goals, habits, style, projects).

Both are inspectable, auditable and forgettable by the owner (sovereign
curation), and substitutable behind this contract — the storage can change
without touching the callers. Inferences (mood/energy) are labelled as such and
never presented as hard fact.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.models import UserAttribute, WorldFact

# Newest-first, but a fact updated more recently is "more present".
_WORLD_CATEGORIES = (
    "environment", "user_state", "active_work", "goals", "context", "capabilities", "other",
)
_USER_CATEGORIES = (
    "goals", "habits", "preferences", "style", "knowledge", "social", "projects", "other",
)


def _clamp(x: float) -> float:
    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return 1.0


class WorldModel:
    """The Kernel's sense of 'now' and of its owner. See module docstring."""

    # ---------- World Model (the present) ----------

    def set_fact(
        self, db: Session, owner_id: str, key: str, value: str, *,
        category: str = "other", source: str = "kernel",
        confidence: float = 1.0, is_inference: bool = False,
    ) -> WorldFact:
        """Upsert one truth about the present (one current value per key)."""
        key = (key or "").strip()
        if not key:
            raise ValueError("world fact needs a key")
        cat = category if category in _WORLD_CATEGORIES else "other"
        fact = (
            db.query(WorldFact)
            .filter(WorldFact.owner_id == owner_id, WorldFact.key == key)
            .first()
        )
        if fact:
            fact.value = str(value)
            fact.category = cat
            fact.source = source
            fact.confidence = _clamp(confidence)
            fact.is_inference = bool(is_inference)
        else:
            fact = WorldFact(
                id=str(uuid.uuid4()), owner_id=owner_id, key=key, value=str(value),
                category=cat, source=source, confidence=_clamp(confidence),
                is_inference=bool(is_inference),
            )
            db.add(fact)
        db.commit()
        db.refresh(fact)
        return fact

    def get_fact(self, db: Session, owner_id: str, key: str) -> WorldFact | None:
        return (
            db.query(WorldFact)
            .filter(WorldFact.owner_id == owner_id, WorldFact.key == (key or "").strip())
            .first()
        )

    def forget_fact(self, db: Session, owner_id: str, key: str) -> bool:
        fact = self.get_fact(db, owner_id, key)
        if not fact:
            return False
        db.delete(fact)
        db.commit()
        return True

    def snapshot(self, db: Session, owner_id: str, limit: int = 200) -> list[WorldFact]:
        """The whole present, most-recently-updated first."""
        return (
            db.query(WorldFact)
            .filter(WorldFact.owner_id == owner_id)
            .order_by(WorldFact.updated_at.desc())
            .limit(limit)
            .all()
        )

    # ---------- User Model (the owner over time) ----------

    def set_attribute(
        self, db: Session, owner_id: str, key: str, value: str, *,
        category: str = "other", source: str = "kernel",
        confidence: float = 1.0, is_inference: bool = False,
    ) -> UserAttribute:
        key = (key or "").strip()
        if not key:
            raise ValueError("user attribute needs a key")
        cat = category if category in _USER_CATEGORIES else "other"
        attr = (
            db.query(UserAttribute)
            .filter(UserAttribute.owner_id == owner_id, UserAttribute.key == key)
            .first()
        )
        if attr:
            attr.value = str(value)
            attr.category = cat
            attr.source = source
            attr.confidence = _clamp(confidence)
            attr.is_inference = bool(is_inference)
        else:
            attr = UserAttribute(
                id=str(uuid.uuid4()), owner_id=owner_id, key=key, value=str(value),
                category=cat, source=source, confidence=_clamp(confidence),
                is_inference=bool(is_inference),
            )
            db.add(attr)
        db.commit()
        db.refresh(attr)
        return attr

    def get_attribute(self, db: Session, owner_id: str, key: str) -> UserAttribute | None:
        return (
            db.query(UserAttribute)
            .filter(UserAttribute.owner_id == owner_id, UserAttribute.key == (key or "").strip())
            .first()
        )

    def forget_attribute(self, db: Session, owner_id: str, key: str) -> bool:
        attr = self.get_attribute(db, owner_id, key)
        if not attr:
            return False
        db.delete(attr)
        db.commit()
        return True

    def profile(self, db: Session, owner_id: str, limit: int = 200) -> list[UserAttribute]:
        return (
            db.query(UserAttribute)
            .filter(UserAttribute.owner_id == owner_id)
            .order_by(UserAttribute.updated_at.desc())
            .limit(limit)
            .all()
        )

    # ---------- context injection (why the Kernel never starts from zero) ----------

    def context_digest(
        self, db: Session, owner_id: str, max_world: int = 12, max_user: int = 12
    ) -> str:
        """
        A compact, human-readable summary of the present + the owner, to inject
        into the Kernel's context. Returns '' when there is nothing yet, so the
        caller only adds it when useful. Inferences are labelled '(inferência)'.
        """
        def line(row) -> str:
            mark = " (inferência)" if getattr(row, "is_inference", False) else ""
            return f"- {row.key}: {row.value}{mark}"

        parts: list[str] = []
        world = self.snapshot(db, owner_id, max_world)
        if world:
            parts.append("Situação agora (World Model):\n" + "\n".join(line(w) for w in world))
        user = self.profile(db, owner_id, max_user)
        if user:
            parts.append("Sobre o dono (User Model):\n" + "\n".join(line(u) for u in user))
        return "\n\n".join(parts)
