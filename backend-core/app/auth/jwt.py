"""
Authentication for the single-owner kernel.

Two token audiences, both belonging to the ONE owner:
  * "owner"  — issued on password login (the person).
  * "device" — long-lived, issued when a trusted device is paired (phone/car/...).

There is no multi-user model and no open registration. Access = the owner,
optionally acting through one of their paired devices.
"""
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.models import Device, Owner

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def dev_bypass_active() -> bool:
    """May an unauthenticated request be treated as the owner?

    Three conditions, all required — the bypass used to need only one
    (`environment == "development"`), which meant every dev kernel silently
    accepted anonymous requests, including one bound to the LAN.

      * development environment — never in production;
      * AUTH_DEV_BYPASS explicitly on — opt in, never a silent default;
      * access_mode == loopback — only when nothing off this machine can reach it.

    Convenience that survives being pointed at a network is not convenience,
    it is an open door.
    """
    return (
        settings.environment == "development"
        and settings.auth_dev_bypass
        and settings.access_mode == "loopback"
    )


# auto_error=False always, so a missing header is decided HERE rather than by
# HTTPBearer. Left to itself it answers 403 for an absent Authorization header,
# which is the wrong code: 401 means "you did not authenticate", 403 means "you
# did, and still may not". Every dependency below raises 401 for missing or bad
# credentials, and the bypass — when genuinely active — sees `credentials=None`
# and takes over.
security = HTTPBearer(auto_error=False)


# ---------- passwords ----------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------- tokens ----------

def _encode(payload: dict, expires: timedelta) -> str:
    to_encode = payload.copy()
    now = datetime.now(UTC)
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


def decode_token(token: str) -> dict | None:
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
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> Owner:
    """
    Resolve the owner from either an owner token or a paired-device token.

    With AUTH_DEV_BYPASS on (loopback development only), a request with no token
    is treated as the owner. Otherwise a token is required — see
    `dev_bypass_active`.
    """
    # ── Local development bypass, opt-in ───────────────────────
    if dev_bypass_active() and (not credentials or not credentials.credentials):
        owner = db.query(Owner).filter(Owner.is_active.is_(True)).first()
        if owner:
            return owner
        # No owner yet. Do NOT invent one here: this path used to construct an
        # Owner with a `display_name` field the model does not have and no id,
        # which raised instead of helping. Owner creation belongs to the kernel's
        # bootstrap, where OWNER_EMAIL/OWNER_PASSWORD are read.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Nenhum dono cadastrado. Defina OWNER_EMAIL e OWNER_PASSWORD no .env "
            "e reinicie o kernel.",
        )

    # ── Normal auth flow ───────────────────────────────────────
    if not credentials or not credentials.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authorization token required")

    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    # A device token is only valid if the device is still paired (not revoked).
    if payload.get("aud") == "device":
        device_id = payload.get("device_id")
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device or device.revoked:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Device not paired or revoked")
        device.last_seen_at = datetime.now(UTC)
        db.commit()

    owner = db.query(Owner).filter(Owner.id == payload.get("sub")).first()
    if not owner or not owner.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Owner not found or inactive")
    return owner


def device_from_token(token: str, db: Session) -> Device | None:
    """Resolve a live (non-revoked) device from a device-audience token, or None."""
    payload = decode_token(token)
    if not payload or payload.get("aud") != "device":
        return None
    device = db.query(Device).filter(Device.id == payload.get("device_id")).first()
    if not device or device.revoked:
        return None
    return device


def get_current_owner_strict(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> Owner:
    """Like `get_current_owner`, but NEVER subject to the dev auth bypass.

    The bypass exists so the local HUD can talk to a loopback kernel without
    ceremony. Some endpoints hold data sensitive even on that trusted surface
    (the connector secrets vault — readable by ANY local process the moment
    the bypass is on). Those endpoints must always demand a real token; this
    dependency is the difference between "any local program" and "the owner".
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authorization token required")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    if payload.get("aud") == "device":
        device_id = payload.get("device_id")
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device or device.revoked:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Device not paired or revoked")
    owner = db.query(Owner).filter(Owner.id == payload.get("sub")).first()
    if not owner or not owner.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Owner not found or inactive")
    return owner


def get_current_device(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> Device:
    """Require a paired-device token (for device-only endpoints).

    `credentials` may be None now that HTTPBearer no longer errors on a missing
    header — reading `.credentials` off it unguarded would turn a plain missing
    token into a 500.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Device token required")
    device = device_from_token(credentials.credentials, db)
    if not device:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Device token required")
    device.last_seen_at = datetime.now(UTC)
    db.commit()
    return device
