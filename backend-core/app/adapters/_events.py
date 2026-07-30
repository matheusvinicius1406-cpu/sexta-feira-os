"""
Shared EventBus helper for adapters.

Every adapter can publish domain events by calling publish_event().
This avoids duplicating the DB-session-and-owner lookup in each adapter method.

Usage:
    from app.adapters._events import publish_event

    # Simple case -- opens its own DB session:
    await publish_event("memory.created", {"id": "abc"}, source="my_adapter")

    # With existing session (no extra DB round-trip):
    await publish_event("memory.created", {"id": "abc"},
                        source="my_adapter", db=db, owner_id=owner_id)
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.di import get_kernel
from app.db.database import SessionLocal
from app.models.models import Owner

logger = logging.getLogger("sexta-feira.adapter.events")


async def publish_event(
    event_type: str,
    payload: dict[str, Any] | None = None,
    source: str = "adapter",
    db: Session | None = None,
    owner_id: str | None = None,
) -> None:
    """Publish a domain event through the Kernel's EventBus.

    Args:
        event_type: Dot-notation event name (e.g. 'memory.created').
        payload: Serializable dict with event data.
        source: Component that produced the event (for tracing).
        db: Optional shared DB session. If omitted, a short-lived session is opened.
        owner_id: Optional resolved owner ID. Required if db is provided.

    Failures are logged but never raised -- adapters must not break
    the primary operation because of a secondary event publish.
    """
    bus = get_kernel().events
    if not bus:
        return

    # -- Case 1: no session provided -- open a short-lived one --
    if db is None:
        async def _publish_own_session() -> None:
            s = SessionLocal()
            try:
                owner = s.query(Owner).filter(Owner.is_active.is_(True)).first()
                if not owner:
                    logger.warning("Cannot publish %s: no active owner found", event_type)
                    return
                await bus.publish(
                    db=s, owner_id=owner.id, type=event_type,
                    payload=payload, source=source,
                )
            except Exception:
                logger.exception("Failed to publish event '%s'", event_type)
            finally:
                s.close()
        await _publish_own_session()
        return

    # -- Case 2: session provided by caller -- use it without closing --
    try:
        await bus.publish(
            db=db, owner_id=owner_id, type=event_type,
            payload=payload, source=source,
        )
    except Exception:
        logger.exception("Failed to publish event '%s'", event_type)
