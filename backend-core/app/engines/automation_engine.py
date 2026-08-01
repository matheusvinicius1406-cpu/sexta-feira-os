"""
AutomationEngine — the Teia behind the formal IEngine lifecycle.

Publishes: workflow.started, workflow.finished, workflow.failed
"""
from __future__ import annotations

import logging

from app.automation.teia.service import TeiaService
from app.core.di import get_kernel
from app.db.database import SessionLocal
from app.engines import IEngine
from app.models.models import Owner

logger = logging.getLogger("sexta-feira.engine.automation")


class AutomationEngine(IEngine):
    """Formal Automation Engine — wraps the Teia with a lifecycle."""

    @property
    def name(self) -> str:
        return "Automation"

    async def initialize(self) -> None:
        logger.info("AutomationEngine initialized")

    async def health(self) -> bool:
        """The Teia runs in this process: it is healthy iff the kernel loaded it."""
        return self._automation is not None

    async def shutdown(self) -> None:
        teia = self._automation
        if teia:
            await teia.stop()
        logger.info("AutomationEngine shutdown")

    @property
    def _automation(self) -> TeiaService | None:
        k = get_kernel()
        return k.automations if k else None

    @staticmethod
    def _owner_id() -> str | None:
        db = SessionLocal()
        try:
            owner = db.query(Owner).first()
            return owner.id if owner else None
        finally:
            db.close()

    async def trigger_workflow(self, workflow_id: str,
                               params: dict[str, str] | None = None) -> str | None:
        teia = self._automation
        if not teia:
            raise RuntimeError("Automations not loaded")
        owner_id = self._owner_id()
        if not owner_id:
            raise RuntimeError("No owner yet — pair the kernel first")
        result = await teia.run_slug(owner_id, workflow_id, dict(params or {}))
        return result.execution_id if result.ok else None

    async def list_workflows(self) -> list[dict]:
        teia = self._automation
        if not teia:
            raise RuntimeError("Automations not loaded")
        owner_id = self._owner_id()
        if not owner_id:
            return []
        db = SessionLocal()
        try:
            return [
                {"id": row["slug"], "name": row["name"], "active": row["enabled"]}
                for row in teia.list(db, owner_id)
            ]
        finally:
            db.close()
