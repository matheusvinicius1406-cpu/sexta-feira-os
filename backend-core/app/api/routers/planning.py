"""
Planning — goals, decomposition, dependencies, progress (the Planning Engine).

  POST   /api/v1/planning/goals                     create a goal
  GET    /api/v1/planning/goals                      list goals (optional ?status=)
  GET    /api/v1/planning/goals/{id}                 goal detail (+ subtasks, deps)
  POST   /api/v1/planning/goals/{id}/subtasks        decompose into sub-goals
  POST   /api/v1/planning/goals/{id}/dependencies    add a dependency
  POST   /api/v1/planning/goals/{id}/progress        set progress (1.0 completes)
  POST   /api/v1/planning/goals/{id}/complete        mark done (unblocks dependents)
  DELETE /api/v1/planning/goals/{id}                 cancel
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.core.di import get_planning
from app.db.database import get_db
from app.models.models import Goal, Owner
from app.planning.service import PlanningEngine

router = APIRouter(prefix="/api/v1/planning", tags=["planning"])


class GoalRequest(BaseModel):
    title: str = Field(..., min_length=1)
    description: str | None = None
    priority: int = 2
    due_at: datetime | None = None


class SubtasksRequest(BaseModel):
    subtasks: list[str] = Field(..., min_length=1)


class DependencyRequest(BaseModel):
    depends_on_id: str = Field(..., min_length=1)


class ProgressRequest(BaseModel):
    progress: float = Field(..., ge=0.0, le=1.0)


def _goal_out(g: Goal) -> dict:
    return {
        "id": g.id, "parent_id": g.parent_id, "title": g.title, "description": g.description,
        "priority": g.priority, "status": g.status, "progress": g.progress,
        "due_at": g.due_at, "created_at": g.created_at, "completed_at": g.completed_at,
    }


@router.post("/goals")
async def create_goal(
    body: GoalRequest,
    owner: Owner = Depends(get_current_owner),
    planning: PlanningEngine = Depends(get_planning),
    db: Session = Depends(get_db),
):
    g = await planning.create_goal(
        db, owner.id, body.title, description=body.description,
        priority=body.priority, due_at=body.due_at,
    )
    return _goal_out(g)


@router.get("/goals")
def list_goals(
    status: str | None = None,
    owner: Owner = Depends(get_current_owner),
    planning: PlanningEngine = Depends(get_planning),
    db: Session = Depends(get_db),
):
    return [_goal_out(g) for g in planning.list_goals(db, owner.id, status)]


@router.get("/board")
def board(
    owner: Owner = Depends(get_current_owner),
    planning: PlanningEngine = Depends(get_planning),
    db: Session = Depends(get_db),
):
    """Kanban-style board over the goals: columns (backlog/doing/blocked/done) + stats."""
    return planning.board(db, owner.id)


@router.get("/goals/{goal_id}")
def get_goal(
    goal_id: str,
    owner: Owner = Depends(get_current_owner),
    planning: PlanningEngine = Depends(get_planning),
    db: Session = Depends(get_db),
):
    g = planning.get_goal(db, owner.id, goal_id)
    if not g:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Objetivo não encontrado")
    out = _goal_out(g)
    out["dependencies"] = planning.dependencies(db, owner.id, goal_id)
    out["subtasks"] = [
        _goal_out(c) for c in planning.list_goals(db, owner.id) if c.parent_id == goal_id
    ]
    return out


@router.post("/goals/{goal_id}/subtasks")
async def decompose(
    goal_id: str,
    body: SubtasksRequest,
    owner: Owner = Depends(get_current_owner),
    planning: PlanningEngine = Depends(get_planning),
    db: Session = Depends(get_db),
):
    try:
        children = await planning.decompose(db, owner.id, goal_id, body.subtasks)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    return [_goal_out(c) for c in children]


@router.post("/goals/{goal_id}/dependencies")
def add_dependency(
    goal_id: str,
    body: DependencyRequest,
    owner: Owner = Depends(get_current_owner),
    planning: PlanningEngine = Depends(get_planning),
    db: Session = Depends(get_db),
):
    if not planning.add_dependency(db, owner.id, goal_id, body.depends_on_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Dependência inválida")
    return _goal_out(planning.get_goal(db, owner.id, goal_id))


@router.post("/goals/{goal_id}/progress")
async def set_progress(
    goal_id: str,
    body: ProgressRequest,
    owner: Owner = Depends(get_current_owner),
    planning: PlanningEngine = Depends(get_planning),
    db: Session = Depends(get_db),
):
    g = await planning.set_progress(db, owner.id, goal_id, body.progress)
    if not g:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Objetivo não encontrado")
    return _goal_out(g)


@router.post("/goals/{goal_id}/complete")
async def complete(
    goal_id: str,
    owner: Owner = Depends(get_current_owner),
    planning: PlanningEngine = Depends(get_planning),
    db: Session = Depends(get_db),
):
    g = await planning.complete(db, owner.id, goal_id)
    if not g:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Objetivo não encontrado")
    return _goal_out(g)


@router.delete("/goals/{goal_id}")
def cancel(
    goal_id: str,
    owner: Owner = Depends(get_current_owner),
    planning: PlanningEngine = Depends(get_planning),
    db: Session = Depends(get_db),
):
    if not planning.cancel(db, owner.id, goal_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Objetivo não encontrado")
    return {"cancelled": goal_id}
