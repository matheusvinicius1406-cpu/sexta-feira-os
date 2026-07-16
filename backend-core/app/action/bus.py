"""
CommandBus — live delivery of action commands to connected devices.

Devices hold a WebSocket to the kernel. When the brain dispatches an action we
push it to the device's live socket(s) immediately; if the device is offline the
command still sits (persisted) in the queue and is delivered on reconnect.

Fire-and-forget by design: dispatch never blocks waiting for the device. This
keeps the conversation snappy and removes any hang/timeout bottleneck.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sexta-feira.action.bus")


class CommandBus:
    def __init__(self) -> None:
        # device_id -> set of live WebSocket connections
        self._live: dict[str, set[Any]] = {}

    def register(self, device_id: str, ws: Any) -> None:
        self._live.setdefault(device_id, set()).add(ws)

    def unregister(self, device_id: str, ws: Any) -> None:
        conns = self._live.get(device_id)
        if conns:
            conns.discard(ws)
            if not conns:
                self._live.pop(device_id, None)

    def is_online(self, device_id: str) -> bool:
        return bool(self._live.get(device_id))

    async def push(self, device_id: str, payload: dict) -> bool:
        """Send to every live socket of the device. Returns True if delivered ≥1."""
        delivered = False
        for ws in list(self._live.get(device_id, ())):
            try:
                await ws.send_json(payload)
                delivered = True
            except Exception as e:  # noqa: BLE001 — drop dead sockets
                logger.debug("dropping dead socket for %s: %s", device_id, e)
                self.unregister(device_id, ws)
        return delivered
