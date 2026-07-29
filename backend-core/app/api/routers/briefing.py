"""
Briefing — the proactive "morning report" that weaves the five pillars.

  POST /api/v1/briefing            generate a briefing now
  GET  /api/v1/briefing            history of briefings
  GET  /api/v1/briefing/latest     the most recent briefing
  POST /api/v1/briefing/schedule   schedule a recurring daily briefing (?hour=)
"""
import json
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.briefing.service import BriefingService
from app.core.di import get_briefing, get_scheduler
from app.db.database import get_db
from app.models.models import Owner
from app.schedule.service import Scheduler

router = APIRouter(prefix="/api/v1/briefing", tags=["briefing"])


class ScheduleRequest(BaseModel):
    hour: int = Field(7, ge=0, le=23)          # local-ish hour of day for the report
    device: str | None = None


def _briefing_out(b) -> dict:
    return {
        "id": b.id, "kind": b.kind, "summary": b.summary,
        "content": json.loads(b.content) if b.content else {},
        "created_at": b.created_at,
    }


@router.post("")
async def generate(
    owner: Owner = Depends(get_current_owner),
    briefing: BriefingService = Depends(get_briefing),
    db: Session = Depends(get_db),
):
    b = await briefing.generate(db, owner.id, kind="on_demand")
    return _briefing_out(b)


@router.get("/latest")
def latest(
    owner: Owner = Depends(get_current_owner),
    briefing: BriefingService = Depends(get_briefing),
    db: Session = Depends(get_db),
):
    b = briefing.latest(db, owner.id)
    if not b:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nenhum briefing ainda")
    return _briefing_out(b)


@router.get("")
def history(
    limit: int = 30,
    owner: Owner = Depends(get_current_owner),
    briefing: BriefingService = Depends(get_briefing),
    db: Session = Depends(get_db),
):
    return [_briefing_out(b) for b in briefing.history(db, owner.id, limit)]


@router.post("/schedule")
def schedule_daily(
    body: ScheduleRequest,
    owner: Owner = Depends(get_current_owner),
    scheduler: Scheduler = Depends(get_scheduler),
    db: Session = Depends(get_db),
):
    """Schedule a recurring daily briefing at ~`hour` (fires every 24h)."""
    now = datetime.now(UTC)
    first = now.replace(minute=0, second=0, microsecond=0)
    target = first.replace(hour=body.hour)
    if target <= now:
        target += timedelta(days=1)
    task = scheduler.schedule(
        db, owner.id, kind="briefing", due_at=target,
        device=body.device, recurrence_seconds=86400,
    )
    return {"scheduled": task.id, "next_at": task.due_at, "recurrence_seconds": 86400}
