"""
Shared constants used across the kernel and its bodies (clients).
Single local brain — no cloud providers exist in this product.
"""

# Device kinds — the "bodies" of the one brain
class DeviceKind:
    PHONE = "phone"
    CAR = "car"
    GLASSES = "glasses"
    WATCH = "watch"
    DESKTOP = "desktop"
    GENERIC = "generic"

    AVAILABLE = [PHONE, CAR, GLASSES, WATCH, DESKTOP, GENERIC]


# Message roles
class Role:
    OWNER = "owner"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# Memory kinds
class MemoryKind:
    FACT = "fact"
    PREFERENCE = "preference"
    PERSON = "person"
    ROUTINE = "routine"
    NOTE = "note"


# Access modes (privacy)
class AccessMode:
    LOOPBACK = "loopback"   # só esta máquina
    LAN = "lan"             # rede local
    TUNNEL = "tunnel"       # via WireGuard/Tailscale, ainda privado


# API
API_VERSION = "v1"
API_BASE_PATH = f"/api/{API_VERSION}"

# Limits
MAX_MESSAGE_LENGTH = 8000
DEFAULT_MEMORY_TOP_K = 6


# Error codes
class ErrorCode:
    INVALID_CREDENTIALS = "invalid_credentials"
    INVALID_TOKEN = "invalid_token"
    DEVICE_NOT_PAIRED = "device_not_paired"
    BRAIN_UNAVAILABLE = "brain_unavailable"
    SERVER_ERROR = "server_error"
