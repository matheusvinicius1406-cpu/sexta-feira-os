"""
WorldModelProjector — the subscriber that turns EVENTS into the present.

This realizes the North Star line "Cada evento atualiza o estado do Kernel": a
curated set of event types maps to World Model facts, and any event may set a
fact explicitly via `world_key`/`world_value` in its payload. Unknown events are
ignored (graceful). Inferred signals (mood, health) are flagged as inference.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.events.bus import EventBus
from app.models.models import Event

logger = logging.getLogger("sexta-feira.events.projector")


class WorldModelProjector:
    def __init__(self, world) -> None:
        self.world = world  # WorldModel

    async def handle(self, db: Session, ev: Event) -> None:
        p = EventBus.decode_payload(ev)

        def value(*keys, default: str = "") -> str:
            for k in keys:
                if p.get(k) not in (None, ""):
                    return str(p[k])
            return default

        def set_fact(key: str, val: str, *, category: str, is_inference: bool = False) -> None:
            if val:
                self.world.set_fact(
                    db, ev.owner_id, key, val, category=category,
                    source="event", is_inference=is_inference,
                )

        t = ev.type
        if t == "usuario.acordou":
            set_fact("estado_usuario", "acordado", category="user_state")
        elif t == "usuario.dormiu":
            set_fact("estado_usuario", "dormindo", category="user_state")
        elif t == "localizacao.mudou":
            set_fact("localizacao", value("local", "value", "localizacao"), category="environment")
        elif t == "documento.aberto":
            set_fact("documento_aberto", value("documento", "value", "doc"), category="active_work")
        elif t == "projeto.compilado":
            set_fact("ultimo_build", value("projeto", "value", default="ok"), category="active_work")
        elif t in ("dispositivo.conectado", "dispositivo.desconectado"):
            estado = "conectado" if t.endswith("conectado") else "desconectado"
            nome = value("device", "nome", "value", default="dispositivo")
            set_fact(f"dispositivo:{nome}", estado, category="capabilities")
        elif t == "saude.batimento_elevado":
            set_fact("saude_alerta", value("value", default="batimento elevado"),
                     category="user_state", is_inference=True)

        # Generic escape hatch: any event can set a fact explicitly.
        if p.get("world_key") and p.get("world_value") is not None:
            self.world.set_fact(
                db, ev.owner_id, str(p["world_key"]), str(p["world_value"]),
                category=str(p.get("world_category", "context")),
                source="event", is_inference=bool(p.get("world_is_inference", False)),
            )
