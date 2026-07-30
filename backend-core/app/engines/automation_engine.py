"""
AutomationEngine — formal engine wrapping n8n behind IEngine.

Publishes: workflow.started, workflow.finished, workflow.failed
"""
from __future__ import annotations

import logging

from app.automation.n8n import N8nClient
from app.core.di import get_kernel
from app.engines import IEngine

logger = logging.getLogger("sexta-feira.engine.automation")


class AutomationEngine(IEngine):
    """Formal Automation Engine — wraps N8nClient with lifecycle."""

    @property
    def name(self) -> str:
        return "Automation"

    async def initialize(self) -> None:
        logger.info("AutomationEngine initialized")

    async def health(self) -> bool:
        auto = self._automation
        if not auto:
            return False
        try:
            await auto.list_workflows()
            return True
        except Exception:
            return False

    async def shutdown(self) -> None:
        auto = self._automation
        if auto:
            await auto.aclose()
        logger.info("AutomationEngine shutdown")

    @property
    def _automation(self) -> N8nClient | None:
        k = get_kernel()
        return k.automations if k else None

    async def trigger_workflow(self, workflow_id: str,
                               params: dict[str, str] | None = None) -> str | None:
        auto = self._automation
        if not auto:
            raise RuntimeError("Automations not loaded")
        return await auto.trigger(workflow_id=workflow_id, params=params or {})

    async def list_workflows(self) -> list[dict]:
        auto = self._automation
        if not auto:
            raise RuntimeError("Automations not loaded")
        return await auto.list_workflows()
