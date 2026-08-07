"""
Agent — the kernel's own initiative (Cognitive Pulse).

  GET  /api/v1/agent/pulse                status of the agent (enabled, last cycle)
  POST /api/v1/agent/pulse/run            make the agent think NOW (on demand)
  GET  /api/v1/agent/proposals            the confirmation gate — what it wants to do
  POST /api/v1/agent/proposals/{id}/approve   the owner says yes → it executes
  POST /api/v1/agent/proposals/{id}/reject    the owner says no

Everything degrades cleanly: with the pulse disabled (AGENT_PULSE_ENABLED=false)
every endpoint answers 503 with a plain message — the kernel simply has no agent.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agent.pulse import CognitivePulse
from app.auth.jwt import get_current_owner
from app.core.di import get_pulse
from app.db.database import get_db
from app.models.models import Owner

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


def _require_pulse(pulse) -> CognitivePulse:
    if pulse is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Pulse desligado (AGENT_PULSE_ENABLED=false).",
        )
    return pulse


def _proposal_out(p) -> dict:
    import json

    return {
        "id": p.id, "kind": p.kind, "status": p.status, "title": p.title,
        "reason": p.reason, "tool": p.tool,
        "tool_args": json.loads(p.tool_args) if p.tool_args else None,
        "result": p.result, "error": p.error,
        "created_at": p.created_at, "decided_at": p.decided_at, "executed_at": p.executed_at,
    }


@router.get("/pulse")
def pulse_status(
    owner: Owner = Depends(get_current_owner),
    pulse: CognitivePulse | None = Depends(get_pulse),
    db: Session = Depends(get_db),
):
    if pulse is None:
        return {"enabled": False, "last_report": None, "pending_proposals": 0}
    return {
        "enabled": True,
        "last_report": pulse.last_report,
        "pending_proposals": len(pulse.list_proposals(db, owner.id, status="pending")),
    }


@router.post("/pulse/run")
async def pulse_run(
    owner: Owner = Depends(get_current_owner),
    pulse: CognitivePulse | None = Depends(get_pulse),
    db: Session = Depends(get_db),
):
    _require_pulse(pulse)
    return await pulse.tick(db, owner.id, reason="manual")


@router.get("/proposals")
def list_proposals(
    status_filter: str | None = None,
    owner: Owner = Depends(get_current_owner),
    pulse: CognitivePulse | None = Depends(get_pulse),
    db: Session = Depends(get_db),
):
    _require_pulse(pulse)
    return [
        _proposal_out(p)
        for p in pulse.list_proposals(db, owner.id, status=status_filter)
    ]


@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    owner: Owner = Depends(get_current_owner),
    pulse: CognitivePulse | None = Depends(get_pulse),
    db: Session = Depends(get_db),
):
    _require_pulse(pulse)
    try:
        p = await pulse.execute_proposal(db, owner.id, proposal_id)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Proposta não encontrada") from e
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    return _proposal_out(p)


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(
    proposal_id: str,
    owner: Owner = Depends(get_current_owner),
    pulse: CognitivePulse | None = Depends(get_pulse),
    db: Session = Depends(get_db),
):
    _require_pulse(pulse)
    try:
        p = pulse.reject_proposal(db, owner.id, proposal_id)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Proposta não encontrada") from e
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    return _proposal_out(p)
