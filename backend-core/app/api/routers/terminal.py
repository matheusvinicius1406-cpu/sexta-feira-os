"""
Terminal — what the machine's SSH surface looks like RIGHT NOW. Status only.

  GET /api/v1/terminal/ssh   port 22 listener + active remote sessions

The boundary is deliberate and non-negotiable: this kernel reports SSH
session status, and nothing else. It does not open a shell, does not proxy
SSH, does not forward ports, does not touch keys. Executing a program is the
Teia's job (a reviewed automation node), never a prompt over HTTP — that is
what the ARC's terminal/Shell panel says when it declares itself absent.

Everything here is measured from the OS via psutil: who is logged in (users()),
and whether anything listens on port 22 (net_connections). What the platform
cannot read is named in `unavailable`, same as the rest of the kernel.
"""
from __future__ import annotations

from datetime import UTC, datetime

import psutil
from fastapi import APIRouter, Depends

from app.auth.jwt import get_current_owner
from app.models.models import Owner

router = APIRouter(prefix="/api/v1/terminal", tags=["terminal"])

SSH_PORT = 22
# Local-ish hosts that are not a remote SSH peer.
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _listener_on_22() -> tuple[dict | None, str | None]:
    """Is anything listening on the SSH port — and what, when readable."""
    try:
        conns = psutil.net_connections(kind="tcp")
    except (psutil.AccessDenied, PermissionError) as e:
        return None, f"enumerar sockets exige privilégio: {e}"
    except Exception as e:  # noqa: BLE001 — an unreadable platform is a fact
        return None, f"sockets indisponíveis: {e}"

    for c in conns:
        if c.status == "LISTEN" and c.laddr and c.laddr.port == SSH_PORT:
            name = None
            if c.pid:
                try:
                    name = psutil.Process(c.pid).name()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    name = None
            return {
                "listening": True,
                "port": SSH_PORT,
                "process": name,  # "sshd" when readable; None when not
            }, None
    return {"listening": False, "port": SSH_PORT, "process": None}, None


def _sessions() -> list[dict]:
    """Who is logged in, flagged remote when the host is a real peer."""
    sessions = []
    for u in psutil.users():
        host = (u.host or "").strip()
        remote = bool(host) and host not in _LOCAL_HOSTS
        # psutil's `started` is seconds-since-epoch (float), not a datetime.
        started = datetime.fromtimestamp(u.started, tz=UTC).isoformat(
            timespec="seconds"
        ) if u.started else None
        sessions.append({
            "user": u.name,
            "host": host or None,
            "terminal": u.terminal or None,
            "remote": remote,
            "started_at": started,
        })
    return sessions


@router.get("/ssh")
async def ssh_status(owner: Owner = Depends(get_current_owner)) -> dict:
    """SSH session status of this machine. A reading, never a management claim."""
    listener, listener_note = _listener_on_22()
    try:
        sessions = _sessions()
    except Exception as e:  # noqa: BLE001
        sessions = []
        listener_note = (listener_note + " · ") if listener_note else ""
        listener_note = f"{listener_note}sessões indisponíveis: {e}"

    unavailable: dict[str, str] = {}
    if listener_note:
        unavailable["ssh"] = listener_note

    return {
        "ssh_server": listener,
        "sessions": sessions,
        "sessions_count": len(sessions),
        "remote_count": sum(1 for s in sessions if s["remote"]),
        # The boundary, stated in the payload so no panel can imply more.
        "note": "o kernel reporta sessões SSH; não abre shell, não faz proxy nem encaminha porta.",
        "unavailable": unavailable,
    }
