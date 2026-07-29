"""
Journal & Habits — daily notes and recurring practices.

  POST /api/v1/journal              write an entry (optionally with mood)
  GET  /api/v1/journal              recent entries
  GET  /api/v1/habits               habits with current streaks
  POST /api/v1/habits/check         mark a habit done today (creates it if new)
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.core.di import get_habits, get_journal
from app.db.database import get_db
from app.journal.service import HabitService, JournalService
from app.models.models import Owner

router = APIRouter(prefix="/api/v1", tags=["journal"])


class EntryRequest(BaseModel):
    content: str = Field(..., min_length=1)
    mood: str | None = None


class CheckRequest(BaseModel):
    name: str = Field(..., min_length=1)


@router.post("/journal")
async def add_entry(
    body: EntryRequest,
    owner: Owner = Depends(get_current_owner),
    journal: JournalService = Depends(get_journal),
    db: Session = Depends(get_db),
):
    e = await journal.add(db, owner.id, body.content, body.mood)
    return {"id": e.id, "content": e.content, "mood": e.mood, "created_at": e.created_at}


@router.get("/journal")
def list_entries(
    limit: int = 50,
    owner: Owner = Depends(get_current_owner),
    journal: JournalService = Depends(get_journal),
    db: Session = Depends(get_db),
):
    return [
        {"id": e.id, "content": e.content, "mood": e.mood, "created_at": e.created_at}
        for e in journal.list(db, owner.id, limit)
    ]


@router.get("/habits")
def list_habits(
    owner: Owner = Depends(get_current_owner),
    habits: HabitService = Depends(get_habits),
    db: Session = Depends(get_db),
):
    return habits.list(db, owner.id)


@router.post("/habits/check")
async def check_habit(
    body: CheckRequest,
    owner: Owner = Depends(get_current_owner),
    habits: HabitService = Depends(get_habits),
    db: Session = Depends(get_db),
):
    return await habits.check(db, owner.id, body.name)
