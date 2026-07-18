"""
PlanningEngine — the system works by GOALS (North Star: "trabalha por objetivos").

Goals carry priority, deadline, progress, dependencies and history, and big goals
are decomposed into sub-goals. The engine is deterministic; the *decision* of how
to split a goal is the brain's (a tool passes the subtask list in). Changes:
  * publish events (objetivo.criado / .concluido / tarefa.desbloqueada) — the
    Event-Driven backbone + audit trail (ADR-0002);
  * update the World Model (ADR-0001) with the current focus, so "the present"
    always reflects what the owner is working toward.

Both `world` and `events` are optional so the engine is unit-testable in isolation.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.models import Goal, GoalDependency

_ACTIVE = ("pending", "active", "blocked")
_OPEN = ("pending", "active")


def _now() -> datetime:
    return datetime.now(UTC)


def _clamp(x: float) -> float:
    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return 0.0


class PlanningEngine:
    def __init__(self, world=None, events=None) -> None:
        self.world = world    # WorldModel | None
        self.events = events  # EventBus | None

    # ---------- create / decompose ----------

    async def create_goal(
        self, db: Session, owner_id: str, title: str, *, description: str | None = None,
        priority: int = 2, due_at: datetime | None = None, parent_id: str | None = None,
    ) -> Goal:
        title = (title or "").strip()
        if not title:
            raise ValueError("goal needs a title")
        goal = Goal(
            id=str(uuid.uuid4()), owner_id=owner_id, parent_id=parent_id, title=title,
            description=description, priority=int(priority), status="pending", progress=0.0,
            due_at=due_at.astimezone(UTC).replace(tzinfo=None) if due_at else None,
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        await self._emit(db, owner_id, "objetivo.criado", {"goal_id": goal.id, "title": goal.title})
        self._sync_world(db, owner_id)
        return goal

    async def decompose(
        self, db: Session, owner_id: str, goal_id: str, subtasks: list[str]
    ) -> list[Goal]:
        """Split a goal into child sub-goals (inherit priority)."""
        parent = self.get_goal(db, owner_id, goal_id)
        if not parent:
            raise ValueError("goal not found")
        children: list[Goal] = []
        for title in subtasks:
            if not str(title).strip():
                continue
            child = Goal(
                id=str(uuid.uuid4()), owner_id=owner_id, parent_id=parent.id,
                title=str(title).strip(), priority=parent.priority, status="pending", progress=0.0,
            )
            db.add(child)
            children.append(child)
        db.commit()
        self._rollup(db, owner_id, parent)
        self._sync_world(db, owner_id)
        return children

    # ---------- dependencies ----------

    def add_dependency(self, db: Session, owner_id: str, goal_id: str, depends_on_id: str) -> bool:
        goal = self.get_goal(db, owner_id, goal_id)
        dep = self.get_goal(db, owner_id, depends_on_id)
        if not goal or not dep or goal_id == depends_on_id:
            return False
        exists = (
            db.query(GoalDependency)
            .filter(GoalDependency.goal_id == goal_id, GoalDependency.depends_on_id == depends_on_id)
            .first()
        )
        if not exists:
            db.add(GoalDependency(
                id=str(uuid.uuid4()), owner_id=owner_id,
                goal_id=goal_id, depends_on_id=depends_on_id,
            ))
            db.commit()
        self._refresh_blocked(db, owner_id, goal)
        return True

    def _unmet_deps(self, db: Session, owner_id: str, goal_id: str) -> int:
        deps = (
            db.query(GoalDependency)
            .filter(GoalDependency.owner_id == owner_id, GoalDependency.goal_id == goal_id)
            .all()
        )
        unmet = 0
        for d in deps:
            other = self.get_goal(db, owner_id, d.depends_on_id)
            if other and other.status != "done":
                unmet += 1
        return unmet

    def _refresh_blocked(self, db: Session, owner_id: str, goal: Goal) -> None:
        if goal.status in ("done", "cancelled"):
            return
        goal.status = "blocked" if self._unmet_deps(db, owner_id, goal.id) else (
            "active" if goal.progress > 0 else "pending"
        )
        db.commit()

    # ---------- progress / completion ----------

    async def set_progress(self, db: Session, owner_id: str, goal_id: str, progress: float) -> Goal | None:
        goal = self.get_goal(db, owner_id, goal_id)
        if not goal or goal.status == "cancelled":
            return goal
        p = _clamp(progress)
        if p >= 1.0:
            return await self.complete(db, owner_id, goal_id)
        goal.progress = p
        if goal.status not in ("blocked", "done"):
            goal.status = "active" if p > 0 else "pending"
        db.commit()
        self._rollup(db, owner_id, goal)
        self._sync_world(db, owner_id)
        return goal

    async def complete(self, db: Session, owner_id: str, goal_id: str) -> Goal | None:
        goal = self.get_goal(db, owner_id, goal_id)
        if not goal or goal.status in ("done", "cancelled"):
            return goal
        goal.status = "done"
        goal.progress = 1.0
        goal.completed_at = _now().replace(tzinfo=None)
        db.commit()
        await self._emit(db, owner_id, "objetivo.concluido", {"goal_id": goal.id, "title": goal.title})
        await self._unblock_dependents(db, owner_id, goal_id)
        self._rollup(db, owner_id, goal)
        self._sync_world(db, owner_id)
        return goal

    async def _unblock_dependents(self, db: Session, owner_id: str, goal_id: str) -> None:
        dependents = (
            db.query(GoalDependency)
            .filter(GoalDependency.owner_id == owner_id, GoalDependency.depends_on_id == goal_id)
            .all()
        )
        for d in dependents:
            g = self.get_goal(db, owner_id, d.goal_id)
            if not g or g.status != "blocked":
                continue
            if self._unmet_deps(db, owner_id, g.id) == 0:
                g.status = "active" if g.progress > 0 else "pending"
                db.commit()
                await self._emit(db, owner_id, "tarefa.desbloqueada",
                                 {"goal_id": g.id, "title": g.title})

    def _rollup(self, db: Session, owner_id: str, goal: Goal) -> None:
        """A parent's progress is the mean of its children's progress."""
        if not goal.parent_id:
            return
        parent = self.get_goal(db, owner_id, goal.parent_id)
        if not parent or parent.status == "cancelled":
            return
        children = db.query(Goal).filter(
            Goal.owner_id == owner_id, Goal.parent_id == parent.id,
        ).all()
        if not children:
            return
        parent.progress = round(sum(c.progress for c in children) / len(children), 4)
        if parent.status not in ("done", "cancelled"):
            parent.status = "active" if parent.progress > 0 else "pending"
        db.commit()

    def cancel(self, db: Session, owner_id: str, goal_id: str) -> bool:
        goal = self.get_goal(db, owner_id, goal_id)
        if not goal or goal.status in ("done", "cancelled"):
            return False
        goal.status = "cancelled"
        db.commit()
        self._sync_world(db, owner_id)
        return True

    # ---------- reads ----------

    def get_goal(self, db: Session, owner_id: str, goal_id: str) -> Goal | None:
        return (
            db.query(Goal)
            .filter(Goal.id == goal_id, Goal.owner_id == owner_id)
            .first()
        )

    def list_goals(self, db: Session, owner_id: str, status: str | None = None) -> list[Goal]:
        q = db.query(Goal).filter(Goal.owner_id == owner_id)
        if status:
            q = q.filter(Goal.status == status)
        return q.order_by(Goal.priority.desc(), Goal.due_at.is_(None), Goal.due_at).all()

    def dependencies(self, db: Session, owner_id: str, goal_id: str) -> list[str]:
        return [
            d.depends_on_id for d in db.query(GoalDependency).filter(
                GoalDependency.owner_id == owner_id, GoalDependency.goal_id == goal_id,
            ).all()
        ]

    # ---------- side effects ----------

    async def _emit(self, db: Session, owner_id: str, etype: str, payload: dict) -> None:
        if not self.events:
            return
        await self.events.publish(db, owner_id, etype, payload, source="planning")

    def _sync_world(self, db: Session, owner_id: str) -> None:
        """Reflect current focus in the World Model: how many active goals + the top one."""
        if not self.world:
            return
        active = [g for g in self.list_goals(db, owner_id) if g.status in _ACTIVE]
        self.world.set_fact(
            db, owner_id, "objetivos_ativos", str(len(active)),
            category="goals", source="planning",
        )
        top = next((g for g in active if g.status in _OPEN), None)
        if top:
            self.world.set_fact(
                db, owner_id, "objetivo_atual", top.title, category="goals", source="planning",
            )
        else:
            self.world.forget_fact(db, owner_id, "objetivo_atual")
