"""
Auth — single owner + device pairing. No open registration.

  POST /api/v1/auth/login          -> owner logs in with email+password
  POST /api/v1/auth/devices/pair   -> pair a new body (phone/car/glasses/watch)
  GET  /api/v1/auth/devices        -> list paired devices
  POST /api/v1/auth/devices/{id}/revoke
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.jwt import (
    create_device_token,
    create_owner_token,
    get_current_owner,
    verify_password,
)
from app.core.config import settings
from app.db.database import get_db
from app.models.models import Device, Owner

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    owner_id: str


class PairRequest(BaseModel):
    pairing_code: str
    device_name: str
    device_kind: str = "generic"


class PairResponse(BaseModel):
    device_token: str
    device_id: str


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    owner = db.query(Owner).filter(Owner.email == body.email).first()
    if not owner or not verify_password(body.password, owner.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas")
    return TokenResponse(access_token=create_owner_token(owner.id), owner_id=owner.id)


@router.post("/devices/pair", response_model=PairResponse)
async def pair_device(body: PairRequest, db: Session = Depends(get_db)):
    """Pair a trusted body using the owner-set pairing code."""
    if not settings.device_pairing_code:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Pareamento desativado (defina DEVICE_PAIRING_CODE)")
    if body.pairing_code != settings.device_pairing_code:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Código de pareamento inválido")
    owner = db.query(Owner).first()
    if not owner:
        raise HTTPException(status.HTTP_409_CONFLICT, "Nenhum dono configurado ainda")

    device = Device(
        id=str(uuid.uuid4()), owner_id=owner.id,
        name=body.device_name, kind=body.device_kind,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return PairResponse(device_token=create_device_token(owner.id, device.id), device_id=device.id)


@router.get("/devices")
async def list_devices(owner: Owner = Depends(get_current_owner), db: Session = Depends(get_db)):
    devices = db.query(Device).filter(Device.owner_id == owner.id).all()
    return [
        {
            "id": d.id, "name": d.name, "kind": d.kind,
            "paired_at": d.paired_at, "last_seen_at": d.last_seen_at, "revoked": d.revoked,
        }
        for d in devices
    ]


@router.post("/devices/{device_id}/revoke")
async def revoke_device(
    device_id: str, owner: Owner = Depends(get_current_owner), db: Session = Depends(get_db)
):
    device = db.query(Device).filter(
        Device.id == device_id, Device.owner_id == owner.id
    ).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dispositivo não encontrado")
    device.revoked = True
    db.commit()
    return {"revoked": True, "device_id": device_id}
