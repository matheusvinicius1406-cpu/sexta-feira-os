"""
Authentication for the single-owner kernel.

Two token audiences, both belonging to the ONE owner:
  * "owner"  — issued on password login (the person).
  * "device" — long-lived, issued when a trusted device is paired (phone/car/...).

There is no multi-user model and no open registration. Access = the owner,
optionally acting through one of their paired devices.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.models import Owner, Device

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
security = HTTPBearer(auto_error=True)


# ---------- passwords ----------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------- tokens ----------

def _encode(payload: dict, expires: timedelta) -> str:
    to_encode = payload.copy()
    now = datetime.now(timezone.utc)
    to_encode.update({"iat": now, "exp": now + expires})
    return jwt.encode(to_encode, settings.resolve_jwt_secret(), algorithm=settings.jwt_algorithm)


def create_owner_token(owner_id: str) -> str:
    return _encode(
        {"sub": owner_id, "aud": "owner"},
        timedelta(hours=settings.jwt_expiration_hours),
    )


def create_device_token(owner_id: str, device_id: str) -> str:
    # Devices get a long life so your watch/car don't nag you to re-login.
    return _encode(
        {"sub": owner_id, "aud": "device", "device_id": device_id},
        timedelta(days=365),
    )


def decode_token(token: str) -> Optional[dict]:
    for audience in ("owner", "device"):
        try:
            return jwt.decode(
                token, settings.resolve_jwt_secret(),
                algorithms=[settings.jwt_algorithm], audience=audience,
            )
        except JWTError:
            continue
    return None


# ---------- dependencies ----------

def get_current_owner(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Owner:
    """Resolve the owner from either an owner token or a paired-device token."""
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    # A device token is only valid if the device is still paired (not revoked).
    if payload.get("aud") == "device":
        device_id = payload.get("device_id")
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device or device.revoked:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Device not paired or revoked")
        device.last_seen_at = datetime.now(timezone.utc)
        db.commit()

    owner = db.query(Owner).filter(Owner.id == payload.get("sub")).first()
    if not owner or not owner.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Owner not found or inactive")
    return owner
