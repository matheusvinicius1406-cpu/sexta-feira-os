"""
Learning — register outcomes, recall lessons, adapt behavior (Learning Engine).

  POST /api/v1/learning                   record a learning (quality + lesson)
  GET  /api/v1/learning                    recent lessons (optional ?tag=)
  GET  /api/v1/learning/stats              aggregate (count, recent avg quality)
  POST /api/v1/learning/decision/{id}      feedback on a past decision
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.core.di import get_learning
from app.db.database import get_db
from app.learning.service import LearningEngine
from app.models.models import Owner

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])


class LearningRequest(BaseModel):
    context: str = Field(..., min_length=1)
    observation: str | None = None
    quality: float = Field(0.5, ge=0.0, le=1.0)
    lesson: str | None = None
    kind: str = "outcome"
    tag: str | None = None
    ref_id: str | None = None


class DecisionFeedback(BaseModel):
    quality: float = Field(..., ge=0.0, le=1.0)
    note: str | None = None


def _learning_out(x) -> dict:
    return {
        "id": x.id, "kind": x.kind, "tag": x.tag, "ref_id": x.ref_id,
        "context": x.context, "observation": x.observation, "quality": x.quality,
        "lesson": x.lesson, "created_at": x.created_at,
    }


@router.post("")
async def record(
    body: LearningRequest,
    owner: Owner = Depends(get_current_owner),
    learning: LearningEngine = Depends(get_learning),
    db: Session = Depends(get_db),
):
    x = await learning.record(
        db, owner.id, body.context, observation=body.observation, quality=body.quality,
        lesson=body.lesson, kind=body.kind, tag=body.tag, ref_id=body.ref_id, source="owner",
    )
    return _learning_out(x)


@router.get("/stats")
def stats(
    owner: Owner = Depends(get_current_owner),
    learning: LearningEngine = Depends(get_learning),
    db: Session = Depends(get_db),
):
    return learning.stats(db, owner.id)


@router.get("")
def lessons(
    tag: str | None = None,
    limit: int = 100,
    owner: Owner = Depends(get_current_owner),
    learning: LearningEngine = Depends(get_learning),
    db: Session = Depends(get_db),
):
    return [_learning_out(x) for x in learning.lessons(db, owner.id, limit, tag)]


@router.post("/decision/{decision_id}")
async def feedback_on_decision(
    decision_id: str,
    body: DecisionFeedback,
    owner: Owner = Depends(get_current_owner),
    learning: LearningEngine = Depends(get_learning),
    db: Session = Depends(get_db),
):
    x = await learning.observe_decision(db, owner.id, decision_id, body.quality, body.note)
    return _learning_out(x)
