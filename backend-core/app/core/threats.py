"""
threats.py — active defense: detect, record, alert. Never attack back.

When something smells like an attack (brute-force lockout, DNS-rebinding
probe, SSRF attempt, honeytoken touched), the kernel:

  1. RECORDS a persisted `threat.*` event on the audit trail — survives
     restarts, visible via GET /api/v1/events?type=threat.* (the HUD and the
     app's Security screen read exactly this);
  2. ALERTS the owner on paired devices (notification via ActionService) —
     the Android agent shows it as a push;
  3. FAILS CLOSED: the attempt that triggered the detection is refused
     (429/403/blocked URL/empty honeytoken value).

It does NOT retaliate. Hacking back is illegal in every jurisdiction, and it
is technically unsound: source IPs are spoofable, attackers route through
proxies and third-party honeypots, so "the attacker" is unknowable — you would
be attacking a stranger's machine. The record + alert is the effective
counter: the intruder gets nothing, and the owner knows within seconds.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.di import get_action_service, get_events
from app.models.models import Owner

logger = logging.getLogger("sexta-feira.threats")

# Honeytokens: secrets with this prefix are BAIT. No real connector is named
# like this; touching one is by definition an intruder probing the vault.
# The value is NEVER returned and the attempt is recorded as a threat.
HONEYPOT_PREFIX = "honeypot."

_THREAT_TYPES = {"brute-force", "dns-rebinding", "ssrf", "honeypot", "port-scan"}


def _owner_id(db: Session) -> str | None:
    owner = db.query(Owner).first()
    return owner.id if owner else None


def record_threat_sync(
    db: Session, kind: str, detail: str, source_ip: str | None = None
) -> None:
    """Persist a threat.* event without awaiting subscribers.

    Used from synchronous request paths (auth lockout, host-guard 403, vault
    read) where there is no event loop to await on. The audit trail is the
    contract; threat.* has no subscribers to miss.
    """
    owner_id = _owner_id(db)
    if not owner_id:
        return
    try:
        get_events().sync_publish(
            db, owner_id, f"threat.{kind}",
            payload={
                "detail": detail,
                "source_ip": source_ip or "",
                "at": datetime.now(UTC).isoformat(),
            },
            source="threat-guard",
        )
    except Exception as e:  # noqa: BLE001 — detection must never break the request
        logger.warning("falha ao registrar ameaça %s: %s", kind, e)


async def record_threat_async(
    db: Session, kind: str, detail: str, source_ip: str | None = None
) -> None:
    """Persist the threat AND push an owner alert on paired devices.

    Best-effort end to end: a broken subscriber or a device without a
    connection must not raise into the request that detected the attack.
    """
    owner_id = _owner_id(db)
    if not owner_id:
        return
    try:
        await get_events().publish(
            db, owner_id, f"threat.{kind}",
            payload={
                "detail": detail,
                "source_ip": source_ip or "",
                "at": datetime.now(UTC).isoformat(),
            },
            source="threat-guard",
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("falha ao registrar ameaça %s: %s", kind, e)
        return
    await _alert_owner(db, owner_id, detail)


async def _alert_owner(db: Session, owner_id: str, detail: str) -> None:
    """Send a notification to every paired phone/desktop — the owner's pager."""
    try:
        actions = get_action_service()
    except Exception:  # noqa: BLE001 — kernel not started (tests of pure units)
        return
    text = f"⚠️ Alerta de segurança: {detail}"
    try:
        for kind in ("celular", "computador"):
            await actions.dispatch(db, owner_id, kind, "notify", {"texto": text})
    except Exception as e:  # noqa: BLE001
        logger.warning("falha ao alertar o dono: %s", e)


def is_honeypot(name: str) -> bool:
    """Is this secret name a honeytoken? (case-insensitive, prefix match)."""
    return (name or "").strip().lower().startswith(HONEYPOT_PREFIX)
