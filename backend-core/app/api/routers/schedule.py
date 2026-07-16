"""
Schedule — future intentions the brain (or you) set: reminders and timed actions.

  POST   /api/v1/schedule        create a reminder or timed action
  GET    /api/v1/schedule        list scheduled items
  DELETE /api/v1/schedule/{id}   cancel one
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.brain.tools import _compute_due
from app.core.di import get_scheduler
from app.db.database import get_db
from app.models.models import Owner
from app.schedule.service import Scheduler

router = APIRouter(prefix="/api/v1/schedule", tags=["schedule"])


class ScheduleRequest(BaseModel):
    kind: str = "reminder"                 # "reminder" | "action"
    text: str | None = None
    device: str | None = None
    action: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    at: str | None = None                  # ISO 8601
    in_minutes: float | None = None
    in_hours: float | None = None
    in_days: float | None = None
    recurrence_seconds: int | None = None


@router.post("")
async def create(
    body: ScheduleRequest,
    owner: Owner = Depends(get_current_owner),
    scheduler: Scheduler = Depends(get_scheduler),
    db: Session = Depends(get_db),
):
    due = _compute_due(body.model_dump())
    if not due:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Informe quando: 'at' (ISO) ou 'in_minutes'/'in_hours'/'in_days'.",
        )
    if body.kind == "action" and not body.action:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "kind='action' exige 'action'.")

    task = scheduler.schedule(
        db, owner.id, kind=body.kind, due_at=due, text=body.text,
        device=body.device, action=body.action, params=body.params or None,
        recurrence_seconds=body.recurrence_seconds,
    )
    return scheduler._to_dict(task)


@router.get("")
async def list_scheduled(
    include_done: bool = False,
    owner: Owner = Depends(get_current_owner),
    scheduler: Scheduler = Depends(get_scheduler),
    db: Session = Depends(get_db),
):
    return scheduler.list(db, owner.id, include_done=include_done)


@router.delete("/{task_id}")
async def cancel(
    task_id: str,
    owner: Owner = Depends(get_current_owner),
    scheduler: Scheduler = Depends(get_scheduler),
    db: Session = Depends(get_db),
):
    if not scheduler.cancel(db, owner.id, task_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agendamento não encontrado")
    return {"cancelled": task_id}
