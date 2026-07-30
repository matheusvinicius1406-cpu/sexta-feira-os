"""
ActionAdapter — wraps ActionService for dispatching device commands.
"""
from __future__ import annotations

import logging

from app.core.di import get_kernel

logger = logging.getLogger("sexta-feira.adapter.action")


class ActionAdapter:
    """Adapter for dispatching actions to devices."""

    @property
    def _actions(self):
        k = get_kernel()
        if k and k.actions:
            return k.actions
        return None

    async def dispatch(self, device: str, action: str,
                       params: dict[str, str] | None = None) -> str:
        svc = self._actions
        if not svc:
            raise RuntimeError("Action service not loaded")
        return await svc.dispatch(
            device=device,
            action=action,
            params=params or {},
        )
