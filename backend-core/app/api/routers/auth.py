"""
Auth — single owner + device pairing. No open registration.

  POST /api/v1/auth/login          -> owner logs in with email+password
  POST /api/v1/auth/devices/pair   -> pair a new body (phone/car/glasses/watch)
  GET  /api/v1/auth/devices        -> list paired devices
  POST /api/v1/auth/devices/{id}/revoke

/login and /devices/pair are the ONLY routes reachable without a token, so
they are the only ones worth throttling: a sliding failure window per source
IP with lockout (HTTP 429 + Retry-After) after a handful of misses — see
app/core/rate_limit.py. Both also run a constant-time password/code check so
response TIMING cannot be used to tell a real account from a fake one.
"""
import hmac
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.jwt import (
    create_device_token,
    create_owner_token,
    get_current_owner,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.core.rate_limit import client_ip, throttle
from app.core.threats import record_threat_sync
from app.db.database import get_db
from app.models.models import Device, Owner

# Argon2 is intentionally slow; a dummy verify keeps the cost identical when
# the email does not exist, so an attacker cannot measure "unknown email" vs
# "wrong password" in login latency. Computed once at import with the same
# context that made the real hashes — guaranteed valid and same cost.
_DUMMY_HASH = hash_password("senha-de-email-inexistente")


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
async def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    key = client_ip(request)
    locked = throttle.remaining_lockout(key)
    if locked:
        # Tripwire: a locked IP keeps knocking — that is an attacker, not a typo.
        record_threat_sync(db, "brute-force", "lockout de login (IP " + key + ")", source_ip=key)
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Muitas tentativas de login. Tente novamente em {locked}s.",
            headers={"Retry-After": str(locked)},
        )
    owner = db.query(Owner).filter(Owner.email == body.email).first()
    # Constant-time: verify against a dummy hash when the email is unknown so
    # the latency is the same either way (see _DUMMY_HASH above).
    ok = bool(owner) and verify_password(body.password, owner.hashed_password)
    if not owner:
        verify_password(body.password, _DUMMY_HASH)
    if not ok:
        throttle.register_failure(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas")
    throttle.reset(key)
    return TokenResponse(access_token=create_owner_token(owner.id), owner_id=owner.id)


@router.post("/devices/pair", response_model=PairResponse)
async def pair_device(body: PairRequest, request: Request, db: Session = Depends(get_db)):
    """Pair a trusted body using the owner-set pairing code."""
    key = client_ip(request)
    locked = throttle.remaining_lockout(key)
    if locked:
        record_threat_sync(db, "brute-force", "lockout de pareamento (IP " + key + ")", source_ip=key)
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Muitas tentativas de pareamento. Tente novamente em {locked}s.",
            headers={"Retry-After": str(locked)},
        )
    if not settings.device_pairing_code:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Pareamento desativado (defina DEVICE_PAIRING_CODE)")
    # Constant-time comparison — timing must not leak how much of the code matches.
    if not hmac.compare_digest(body.pairing_code, settings.device_pairing_code):
        throttle.register_failure(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Código de pareamento inválido")
    throttle.reset(key)
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
