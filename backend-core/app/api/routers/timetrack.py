"""
Time Tracker — where the owner's time goes.

  POST /api/v1/time/start     start a timer (closes any open one)
  POST /api/v1/time/stop      stop the open timer
  GET  /api/v1/time/current   the running timer, if any
  GET  /api/v1/time/summary   total seconds per label
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.core.di import get_timetracker
from app.db.database import get_db
from app.models.models import Owner
from app.timetrack.service import TimeTracker

router = APIRouter(prefix="/api/v1/time", tags=["time"])


class StartRequest(BaseModel):
    label: str = Field(..., min_length=1)
    goal_id: str | None = None


@router.post("/start")
async def start(
    body: StartRequest,
    owner: Owner = Depends(get_current_owner),
    tracker: TimeTracker = Depends(get_timetracker),
    db: Session = Depends(get_db),
):
    e = await tracker.start(db, owner.id, body.label, body.goal_id)
    return {"id": e.id, "label": e.label, "goal_id": e.goal_id, "started_at": e.started_at}


@router.post("/stop")
async def stop(
    owner: Owner = Depends(get_current_owner),
    tracker: TimeTracker = Depends(get_timetracker),
    db: Session = Depends(get_db),
):
    out = await tracker.stop(db, owner.id)
    return out or {"stopped": None, "reason": "Nenhum timer aberto."}


@router.get("/current")
def current(
    owner: Owner = Depends(get_current_owner),
    tracker: TimeTracker = Depends(get_timetracker),
    db: Session = Depends(get_db),
):
    e = tracker.current(db, owner.id)
    if not e:
        return {"running": None}
    return {"running": {"id": e.id, "label": e.label, "started_at": e.started_at}}


@router.get("/summary")
def summary(
    owner: Owner = Depends(get_current_owner),
    tracker: TimeTracker = Depends(get_timetracker),
    db: Session = Depends(get_db),
):
    return tracker.summary(db, owner.id)
