"""
System metrics — what the machine the kernel runs on is actually doing.

  GET /api/v1/system   cpu, memory, disk, battery, uptime, host

Every field here is measured. Where the platform cannot supply a reading, the
field is `null` and `unavailable` names it, rather than the endpoint inventing a
plausible number — the HUD renders `—` for null and a number for anything else,
so a fabricated value here would become a lie on screen with no way to tell.

Windows has no temperature sensor exposed through psutil (`sensors_temperatures`
does not exist on the platform at all), so `temperature` is permanently null
here. That is a fact about the platform, not a TODO.
"""
from __future__ import annotations

import os
import platform
import shutil
import time

import psutil
from fastapi import APIRouter, Depends

from app.auth.jwt import get_current_owner
from app.models.models import Owner

router = APIRouter(prefix="/api/v1/system", tags=["system"])


def _disk() -> dict:
    """Usage of the volume the kernel itself lives on."""
    usage = shutil.disk_usage(os.path.abspath(os.sep))
    return {
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "percent": round(usage.used / usage.total * 100, 1) if usage.total else None,
    }


def _battery() -> tuple[dict | None, str | None]:
    battery = psutil.sensors_battery()
    if battery is None:
        return None, "esta máquina não reporta bateria"
    # secsleft is a sentinel, not a duration, when charging or still unknown.
    remaining = battery.secsleft
    if remaining in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN) or remaining < 0:
        remaining = None
    return {
        "percent": round(battery.percent, 1),
        "plugged": battery.power_plugged,
        "seconds_left": remaining,
    }, None


def _temperature() -> tuple[None, str]:
    """Always null: no platform this kernel targets exposes it through psutil."""
    reader = getattr(psutil, "sensors_temperatures", None)
    if reader is None:
        return None, f"psutil não expõe sensor de temperatura em {platform.system()}"
    try:
        readings = reader()
    except Exception as e:  # noqa: BLE001 — a missing sensor is not an error
        return None, f"sensor de temperatura indisponível: {e}"
    if not readings:
        return None, "nenhum sensor de temperatura encontrado"
    return None, "leitura de temperatura ainda não interpretada por este kernel"


@router.get("")
async def system_metrics(owner: Owner = Depends(get_current_owner)) -> dict:
    """One read of the host. Non-blocking: cpu_percent uses the interval since
    the previous call rather than sleeping, so polling this at 1 Hz costs
    nothing and still returns a real number."""
    memory = psutil.virtual_memory()
    battery, battery_note = _battery()
    temperature, temperature_note = _temperature()

    unavailable: dict[str, str] = {}
    if battery_note:
        unavailable["battery"] = battery_note
    unavailable["temperature"] = temperature_note

    return {
        "cpu": {
            "percent": psutil.cpu_percent(interval=None),
            "cores_logical": psutil.cpu_count(logical=True),
            "cores_physical": psutil.cpu_count(logical=False),
        },
        "memory": {
            "total_bytes": memory.total,
            "used_bytes": memory.used,
            "available_bytes": memory.available,
            "percent": memory.percent,
        },
        "disk": _disk(),
        "battery": battery,
        "temperature": temperature,
        "uptime_seconds": int(time.time() - psutil.boot_time()),
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        # Named, so the HUD can say WHY a readout is dashed instead of leaving
        # the owner to wonder whether it is broken or simply not measurable.
        "unavailable": unavailable,
    }
