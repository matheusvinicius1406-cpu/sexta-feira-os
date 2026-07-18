"""
Decision — choose among alternatives under constraints (the Decision Engine).

  POST /api/v1/decision/next        decide what to focus on now (ranks open goals)
  GET  /api/v1/decision/history     the audit trail of decisions
  GET  /api/v1/decision/{id}        a single decision (chosen + rationale + options)
"""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.core.di import get_decision
from app.db.database import get_db
from app.decision.service import DecisionEngine
from app.models.models import Owner

router = APIRouter(prefix="/api/v1/decision", tags=["decision"])


def _decision_out(d) -> dict:
    return {
        "id": d.id, "question": d.question, "policy": d.policy,
        "chosen_id": d.chosen_id, "chosen_label": d.chosen_label,
        "rationale": d.rationale,
        "options": json.loads(d.options) if d.options else [],
        "created_at": d.created_at,
    }


@router.post("/next")
async def decide_next(
    owner: Owner = Depends(get_current_owner),
    decision: DecisionEngine = Depends(get_decision),
    db: Session = Depends(get_db),
):
    d = await decision.decide_next_goal(db, owner.id)
    if not d:
        return {"decision": None, "reason": "Nenhum objetivo elegível para focar agora."}
    return {"decision": _decision_out(d)}


@router.get("/history")
def history(
    limit: int = 100,
    owner: Owner = Depends(get_current_owner),
    decision: DecisionEngine = Depends(get_decision),
    db: Session = Depends(get_db),
):
    return [_decision_out(d) for d in decision.history(db, owner.id, limit)]


@router.get("/{decision_id}")
def get_one(
    decision_id: str,
    owner: Owner = Depends(get_current_owner),
    decision: DecisionEngine = Depends(get_decision),
    db: Session = Depends(get_db),
):
    d = decision.get_decision(db, owner.id, decision_id)
    if not d:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Decisão não encontrada")
    return _decision_out(d)
