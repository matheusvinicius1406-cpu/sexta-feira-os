"""
Security — the kernel's self-defense dashboard.

  GET /api/v1/security/audit     posture report: what is enforced right now
  GET /api/v1/security/threats   the threat.* audit trail (tripwires fired)

Everything is owner-only (strict token — never the dev bypass). The audit is
the "botões" backend for the app's Security screen: it tells the owner, in one
call, which defenses are armed, what was detected, and what to change.
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner_strict
from app.core.config import settings
from app.core.di import get_events
from app.core.rate_limit import throttle
from app.core.security import _SECURITY_HEADERS
from app.core.threats import HONEYPOT_PREFIX
from app.db.database import get_db
from app.events.bus import EventBus
from app.models.models import Event, Owner, Secret

router = APIRouter(prefix="/api/v1/security", tags=["security"])


def _threat_out(ev: Event) -> dict:
    return {
        "id": ev.id, "type": ev.type, "detail": (EventBus.decode_payload(ev) or {}).get("detail"),
        "source_ip": (EventBus.decode_payload(ev) or {}).get("source_ip"),
        "at": ev.created_at, "sequence": ev.sequence,
    }


@router.get("/audit")
def audit(
    owner: Owner = Depends(get_current_owner_strict),
    db: Session = Depends(get_db),
):
    """The posture report: every defense and whether it is armed."""
    threats = (
        db.query(Event)
        .filter(Event.owner_id == owner.id, Event.type.like("threat.%"))
        .order_by(Event.sequence.desc())
        .all()
    )
    honeypots = (
        db.query(Secret)
        .filter(Secret.owner_id == owner.id, Secret.name.ilike(HONEYPOT_PREFIX + "%"))
        .count()
    )
    recommendations: list[str] = []
    if settings.auth_dev_bypass:
        recommendations.append(
            "AUTH_DEV_BYPASS está ligado: qualquer processo desta máquina lê o kernel "
            "sem token. O HUD autentica sozinho — desligue a flag no .env."
        )
    if not settings.device_pairing_code:
        recommendations.append("DEVICE_PAIRING_CODE vazio: nenhum aparelho novo pode ser pareado (não é risco, é inoperância).")
    if honeypots == 0:
        recommendations.append(
            "Nenhum honeytoken armado. Crie um segredo chamado 'honeypot.api_falsa' "
            "no cofre de conectores: quem o ler dispara um alerta de ameaça."
        )
    return {
        "auditado_em": datetime.now(UTC).isoformat(),
        "acesso": {
            "access_mode": settings.access_mode,
            "auth_dev_bypass": settings.auth_dev_bypass,
        },
        "defesas": {
            "headers": sorted(_SECURITY_HEADERS) + ["Content-Security-Policy"],
            "rate_limit": {
                "max_tentativas": throttle.max_attempts,
                "janela_segundos": throttle.window,
                "lockout_segundos": throttle.lockout,
                "ips_bloqueados_agora": len(throttle._failures),
            },
            "netguard": {
                "ativo": True,
                "hosts_internos_permitidos": settings.teia_allowed_outbound_hosts,
            },
            "honeypots_armados": honeypots,
        },
        "ameacas": {
            "total": len(threats),
            "recentes": [_threat_out(t) for t in threats[:10]],
        },
        "recomendacoes": recommendations,
    }


@router.get("/threats")
def threats(
    limite: int = 50,
    owner: Owner = Depends(get_current_owner_strict),
    events: EventBus = Depends(get_events),
    db: Session = Depends(get_db),
):
    """The threat audit trail — every tripwire that fired, newest first."""
    rows = events.history(db, owner.id, min(limite, 200), type="threat.*")
    return [_threat_out(ev) for ev in rows]
