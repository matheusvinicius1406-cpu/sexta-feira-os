"""
Network — what the machine the kernel runs on is actually sending/receiving.

  GET /api/v1/network/traffic   counters since boot, live rates, interfaces
  GET /api/v1/network/vpn       VPN presence, by what the OS reports

Every number is measured: the counters come straight from psutil's
net_io_counters (the OS's own accounting), and the rates are real deltas
between two reads of those counters. The first read has no previous sample,
so `rate` is null and the panel says so — nothing here is invented.

The kernel does NOT manage VPNs — it does not connect or disconnect anything;
that is a privileged, out-of-band action. What it CAN do is report what the
operating system already knows: which interfaces are up, which of them look
like tunnels (by the names the OS itself gives them), and which interface
carries the default route. The `method` field says exactly that this is a
name-based heuristic, so the reading is never mistaken for a guarantee.

Two honest limitations, reported in `unavailable` like the rest of the kernel:
  * on some platforms psutil needs privileges to enumerate active connections
  * a platform that refuses to report counters at all

The rate sampler lives in this module because it belongs to the read: a rate
only exists between two reads of the same counters.
"""
from __future__ import annotations

import sys
import threading
import time

import psutil
from fastapi import APIRouter, Depends

from app.auth.jwt import get_current_owner
from app.models.models import Owner

router = APIRouter(prefix="/api/v1/network", tags=["network"])

# Interface names the OS uses for tunnels/VPNs. A heuristic, stated as such:
# the kernel measures what is up; it does not claim these are guarantees.
_VPN_HINTS = (
    "tun", "tap", "wg", "utun", "ppp", "nordlynx", "tailscale",
    "openvpn", "wireguard", "zerotier",
)


def _looks_like_vpn(name: str) -> bool:
    lower = name.lower()
    if any(lower.startswith(h) for h in _VPN_HINTS):
        return True
    return "vpn" in lower or "tunnel" in lower


# ── Rate sampler ─────────────────────────────────────────────
# The kernel is async; two overlapping reads must not corrupt the sample.
_lock = threading.Lock()
_last: tuple[float, psutil._common.snetio] | None = None


def _io(d) -> dict:
    """The eight OS counters, named as psutil names them."""
    return {
        "bytes_sent": d.bytes_sent,
        "bytes_recv": d.bytes_recv,
        "packets_sent": d.packets_sent,
        "packets_recv": d.packets_recv,
        "errin": d.errin,
        "errout": d.errout,
        "dropin": d.dropin,
        "dropout": d.dropout,
    }


def _connections() -> tuple[dict | None, str | None]:
    """Active TCP/UDP connections + a count by state. Needs privileges on
    some platforms — that is a fact about the platform, reported as such."""
    try:
        conns = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, PermissionError) as e:
        return None, f"enumerar conexões exige privilégio: {e}"
    except Exception as e:  # noqa: BLE001 — an unreadable platform is not an error
        return None, f"conexões indisponíveis: {e}"
    by_state: dict[str, int] = {}
    for c in conns:
        by_state[c.status] = by_state.get(c.status, 0) + 1
    return {"count": len(conns), "by_state": by_state}, None


@router.get("/traffic")
async def network_traffic(owner: Owner = Depends(get_current_owner)) -> dict:
    """One read of the network. Rates are deltas since the previous read."""
    global _last

    try:
        total = psutil.net_io_counters()
        pernic = psutil.net_io_counters(pernic=True)
    except Exception as e:  # noqa: BLE001 — a platform that cannot report is a fact
        return {
            "since_boot": None,
            "rate": None,
            "interfaces": [],
            "connections": None,
            "unavailable": {"traffic": f"psutil não conseguiu ler os contadores de rede: {e}"},
        }

    since_boot = _io(total)
    interfaces = [
        {"name": name, **_io(c)}
        for name, c in sorted(
            pernic.items(),
            key=lambda kv: kv[1].bytes_recv + kv[1].bytes_sent,
            reverse=True,
        )
    ]

    # Rate: only exists once there is a previous sample to compare against.
    rate = None
    now = time.monotonic()
    with _lock:
        if _last is not None:
            prev_t, prev = _last
            dt = now - prev_t
            if dt > 0:
                rate = {
                    "bytes_sent_per_s": round(max(0, since_boot["bytes_sent"] - prev.bytes_sent) / dt, 1),
                    "bytes_recv_per_s": round(max(0, since_boot["bytes_recv"] - prev.bytes_recv) / dt, 1),
                    "packets_sent_per_s": round(max(0, since_boot["packets_sent"] - prev.packets_sent) / dt, 1),
                    "packets_recv_per_s": round(max(0, since_boot["packets_recv"] - prev.packets_recv) / dt, 1),
                    "measured_over_s": round(dt, 1),
                }
        _last = (now, total)

    connections, conn_note = _connections()
    unavailable: dict[str, str] = {}
    if conn_note:
        unavailable["connections"] = conn_note

    return {
        "since_boot": since_boot,
        "rate": rate,
        "interfaces": interfaces,
        "connections": connections,
        "unavailable": unavailable,
    }


# ── VPN presence ─────────────────────────────────────────────


def _default_route_interface() -> str | None:
    """The interface behind the default route, Linux only. /proc/net/route
    lists one line per route as hex fields; the default route is the row with
    destination 00000000. Other platforms have no equivalent that is readable
    without spawning a privileged command, so they return None honestly."""
    if not sys.platform.startswith("linux"):
        return None
    try:
        with open("/proc/net/route", encoding="ascii") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 3 and parts[1] == "00000000":
                    return parts[0]
    except OSError:
        return None
    return None


@router.get("/vpn")
async def network_vpn(owner: Owner = Depends(get_current_owner)) -> dict:
    """What the OS reports about tunnels right now. Never a management claim."""
    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
    except Exception as e:  # noqa: BLE001 — an unreadable platform is a fact
        return {
            "vpn_active": None,
            "vpn_interfaces": [],
            "default_route_interface": None,
            "method": "heuristic por nome de interface (o kernel mede; não conecta VPN)",
            "unavailable": {"vpn": f"psutil não conseguiu ler as interfaces: {e}"},
        }

    vpn_interfaces = []
    for name in sorted(addrs):
        if not _looks_like_vpn(name):
            continue
        up = bool(stats.get(name) and stats[name].isup)
        addresses = [
            a.address for a in addrs[name]
            if a.address and a.family in (psutil.AF_INET, psutil.AF_INET6)
        ]
        vpn_interfaces.append({"name": name, "up": up, "addresses": addresses})

    default_iface = _default_route_interface()
    active = [v for v in vpn_interfaces if v["up"] and v["addresses"]]
    vpn_active = bool(active)
    if default_iface and _looks_like_vpn(default_iface) and not active:
        vpn_active = True  # rota padrão saindo por um túnel, mesmo sem nome conhecido

    return {
        "vpn_active": vpn_active,
        "vpn_interfaces": vpn_interfaces,
        "default_route_interface": default_iface,
        "method": "heuristic por nome de interface (o kernel mede; não conecta VPN)",
        "unavailable": {},
    }
