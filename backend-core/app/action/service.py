"""
ActionService — persist + route actions to devices, and collect their results.

The kernel is a TRANSPORT: it carries {action, params} to the right body; the
body decides what each action means. That keeps the vocabulary open-ended
(thousands of actions) with zero kernel changes.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.action.bus import CommandBus
from app.models.models import Device, DeviceCommand

logger = logging.getLogger("sexta-feira.action")

# Natural words the brain might use -> device kind.
_KIND_SYNONYMS = {
    "celular": "phone", "telefone": "phone", "phone": "phone", "smartphone": "phone",
    "computador": "desktop", "pc": "desktop", "desktop": "desktop", "notebook": "desktop",
    "carro": "car", "car": "car",
    "relogio": "watch", "relógio": "watch", "watch": "watch",
    "oculos": "glasses", "óculos": "glasses", "glasses": "glasses",
}


def _now() -> datetime:
    return datetime.now(UTC)


class ActionService:
    def __init__(self, bus: CommandBus):
        self.bus = bus

    # ---------- resolution ----------

    def resolve_device(self, db: Session, owner_id: str, selector: str) -> Device | None:
        """Find the target body by kind synonym or by name substring."""
        sel = (selector or "").strip().lower()
        kind = _KIND_SYNONYMS.get(sel, sel)
        active = db.query(Device).filter(
            Device.owner_id == owner_id, Device.revoked.is_(False)
        )
        by_kind = active.filter(Device.kind == kind).first()
        if by_kind:
            return by_kind
        if sel:
            for d in active.all():
                if sel in (d.name or "").lower():
                    return d
        return None

    # ---------- dispatch (brain/owner -> device) ----------

    async def dispatch(
        self, db: Session, owner_id: str, selector: str, action: str, params: dict | None
    ) -> dict:
        device = self.resolve_device(db, owner_id, selector)
        if not device:
            return {"ok": False, "error": f"Nenhum dispositivo '{selector}' pareado."}

        cmd = DeviceCommand(
            id=str(uuid.uuid4()), owner_id=owner_id, device_id=device.id,
            action=action, params=json.dumps(params or {}), status="pending",
        )
        db.add(cmd)
        db.commit()
        db.refresh(cmd)

        delivered = await self.bus.push(
            device.id, {"type": "command", "id": cmd.id, "action": action, "params": params or {}}
        )
        if delivered:
            cmd.status = "delivered"
            cmd.delivered_at = _now()
            db.commit()

        return {
            "ok": True, "command_id": cmd.id, "device": device.name,
            "status": cmd.status, "delivered": delivered,
        }

    # ---------- device side ----------

    def pending_for(self, db: Session, device_id: str) -> list[dict]:
        cmds = (
            db.query(DeviceCommand)
            .filter(
                DeviceCommand.device_id == device_id,
                DeviceCommand.status.in_(["pending", "delivered"]),
            )
            .order_by(DeviceCommand.created_at)
            .all()
        )
        return [self._to_dict(c) for c in cmds]

    def mark_delivered(self, db: Session, command_ids: list[str]) -> None:
        if not command_ids:
            return
        (
            db.query(DeviceCommand)
            .filter(DeviceCommand.id.in_(command_ids), DeviceCommand.status == "pending")
            .update({"status": "delivered", "delivered_at": _now()}, synchronize_session=False)
        )
        db.commit()

    def submit_result(
        self, db: Session, command_id: str, device_id: str,
        status: str, result: object | None, error: str | None,
    ) -> bool:
        cmd = db.query(DeviceCommand).filter(
            DeviceCommand.id == command_id, DeviceCommand.device_id == device_id
        ).first()
        if not cmd:
            return False
        cmd.status = "done" if status == "done" else "failed"
        cmd.result = json.dumps(result) if result is not None else None
        cmd.error = error
        cmd.completed_at = _now()
        db.commit()
        return True

    # ---------- history (owner) ----------

    def history(self, db: Session, owner_id: str, limit: int = 50) -> list[dict]:
        cmds = (
            db.query(DeviceCommand)
            .filter(DeviceCommand.owner_id == owner_id)
            .order_by(DeviceCommand.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._to_dict(c) for c in cmds]

    @staticmethod
    def _to_dict(c: DeviceCommand) -> dict:
        return {
            "id": c.id,
            "device_id": c.device_id,
            "action": c.action,
            "params": json.loads(c.params) if c.params else {},
            "status": c.status,
            "result": json.loads(c.result) if c.result else None,
            "error": c.error,
            "created_at": c.created_at,
        }
