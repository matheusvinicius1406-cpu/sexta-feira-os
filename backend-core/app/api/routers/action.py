"""
Actions — the brain's hands on each device (phone, computer, car...).

Owner side:
  POST /api/v1/actions/dispatch        send an action to a device
  GET  /api/v1/actions                 recent command history

Device (body) side — authenticated with a device token:
  WS   /api/v1/actions/stream?token=…  live channel: receive commands, report results
  GET  /api/v1/actions/pending         polling fallback: fetch queued commands
  POST /api/v1/actions/{id}/result     report a command's result
"""
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.action.service import ActionService
from app.auth.jwt import device_from_token, get_current_device, get_current_owner
from app.core.di import get_action_bus, get_action_service
from app.db.database import SessionLocal, get_db
from app.models.models import Device, Owner

router = APIRouter(prefix="/api/v1/actions", tags=["actions"])


class DispatchRequest(BaseModel):
    device: str = Field(..., description="target body: 'celular', 'computador', or a device name")
    action: str = Field(..., min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)


class ResultRequest(BaseModel):
    status: str = "done"          # "done" | "failed"
    result: Any | None = None
    error: str | None = None


# ---------- owner side ----------

@router.post("/dispatch")
async def dispatch(
    body: DispatchRequest,
    owner: Owner = Depends(get_current_owner),
    service: ActionService = Depends(get_action_service),
    db: Session = Depends(get_db),
):
    return await service.dispatch(db, owner.id, body.device, body.action, body.params)


@router.get("")
async def history(
    limit: int = 50,
    owner: Owner = Depends(get_current_owner),
    service: ActionService = Depends(get_action_service),
    db: Session = Depends(get_db),
):
    return service.history(db, owner.id, limit)


# ---------- device side (polling fallback) ----------

@router.get("/pending")
async def pending(
    device: Device = Depends(get_current_device),
    service: ActionService = Depends(get_action_service),
    db: Session = Depends(get_db),
):
    cmds = service.pending_for(db, device.id)
    service.mark_delivered(db, [c["id"] for c in cmds])
    return cmds


@router.post("/{command_id}/result")
async def report_result(
    command_id: str,
    body: ResultRequest,
    device: Device = Depends(get_current_device),
    service: ActionService = Depends(get_action_service),
    db: Session = Depends(get_db),
):
    if not service.submit_result(db, command_id, device.id, body.status, body.result, body.error):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comando não encontrado")
    return {"ok": True, "command_id": command_id, "status": body.status}


# ---------- device side (live WebSocket) ----------

@router.websocket("/stream")
async def stream(websocket: WebSocket, token: str = ""):
    """Device holds this open to receive commands in real time and report results."""
    bus = get_action_bus()
    service = get_action_service()
    db = SessionLocal()
    device = device_from_token(token, db)
    if not device:
        db.close()
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    bus.register(device.id, websocket)
    try:
        backlog = service.pending_for(db, device.id)
        for c in backlog:
            await websocket.send_json(
                {"type": "command", "id": c["id"], "action": c["action"], "params": c["params"]}
            )
        service.mark_delivered(db, [c["id"] for c in backlog])

        while True:
            msg = await websocket.receive_json()
            if msg.get("type") == "result" and msg.get("id"):
                ok = service.submit_result(
                    db, msg["id"], device.id,
                    msg.get("status", "done"), msg.get("result"), msg.get("error"),
                )
                await websocket.send_json({"type": "ack", "id": msg["id"], "ok": ok})
            # any other message (e.g. heartbeat) is ignored
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 — never let a socket error crash the server
        pass
    finally:
        bus.unregister(device.id, websocket)
        db.close()
