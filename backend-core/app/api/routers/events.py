"""
Events — the Event-Driven backbone, exposed.

  POST /api/v1/events     publish an event (a device/sensor/owner reports what happened)
  GET  /api/v1/events     the audit trail (most recent first)

Events are owner-scoped and authenticated. A published event may update the
World Model (via subscribers) — e.g. 'localizacao.mudou' updates 'localizacao'.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.core.di import get_events
from app.db.database import get_db
from app.events.bus import EventBus
from app.models.models import Owner

router = APIRouter(prefix="/api/v1/events", tags=["events"])


class PublishRequest(BaseModel):
    type: str = Field(..., min_length=1)          # "localizacao.mudou"
    payload: dict | None = None
    source: str = "owner"
    correlation_id: str | None = None
    idempotency_key: str | None = None


def _event_out(ev) -> dict:
    return {
        "id": ev.id, "type": ev.type, "source": ev.source,
        "payload": EventBus.decode_payload(ev), "correlation_id": ev.correlation_id,
        "sequence": ev.sequence, "status": ev.status, "error": ev.error,
        "created_at": ev.created_at, "processed_at": ev.processed_at,
    }


@router.post("")
async def publish(
    body: PublishRequest,
    owner: Owner = Depends(get_current_owner),
    events: EventBus = Depends(get_events),
    db: Session = Depends(get_db),
):
    ev = await events.publish(
        db, owner.id, body.type, body.payload, source=body.source,
        correlation_id=body.correlation_id, idempotency_key=body.idempotency_key,
    )
    return _event_out(ev)


@router.get("")
def history(
    limit: int = 200,
    type: str | None = None,
    owner: Owner = Depends(get_current_owner),
    events: EventBus = Depends(get_events),
    db: Session = Depends(get_db),
):
    return [_event_out(ev) for ev in events.history(db, owner.id, limit, type)]
