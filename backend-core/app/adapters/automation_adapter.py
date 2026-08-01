"""
AutomationAdapter — wraps the Teia, the EventBus, and the ActionBus for gRPC.

Single-owner product: gRPC callers (the desktop HUD, the car screen) are already
inside the owner's trust boundary, so the adapter resolves "the owner" from the
database rather than carrying an identity on every call.
"""
from __future__ import annotations

import asyncio
import logging

from app.core.di import get_kernel
from app.db.database import SessionLocal
from app.models.models import Owner

logger = logging.getLogger("sexta-feira.adapter.automation")


class AutomationAdapter:
    """Adapter for automations, events, and device commands."""

    def __init__(self) -> None:
        self._kernel = get_kernel()

    @property
    def _automations(self):
        return self._kernel.automations if self._kernel else None

    @staticmethod
    def _owner_id() -> str | None:
        db = SessionLocal()
        try:
            owner = db.query(Owner).first()
            return owner.id if owner else None
        finally:
            db.close()

    @property
    def _events(self):
        return self._kernel.events if self._kernel else None

    @property
    def _action_bus(self):
        return self._kernel.action_bus if self._kernel else None

    # ── Workflows ─────────────────────────────────────────

    async def trigger_workflow(self, workflow_id: str,
                               params: dict[str, str] | None = None) -> str | None:
        """Run an automation by slug. Returns the execution id, or None if it failed."""
        teia = self._automations
        if not teia:
            raise RuntimeError("Automations not loaded")
        owner_id = self._owner_id()
        if not owner_id:
            raise RuntimeError("No owner yet — pair the kernel first")

        result = await teia.run_slug(owner_id, workflow_id, dict(params or {}))
        return result.execution_id if result.ok else None

    async def list_workflows(self) -> list[dict]:
        teia = self._automations
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

    # ── Events ────────────────────────────────────────────

    async def stream_events(self, event_types: set[str] | None = None) -> asyncio.Queue:
        """Subscribe to system events and return an async queue."""
        bus = self._events
        if not bus:
            raise RuntimeError("EventBus not loaded")

        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        listener_id = f"grpc-{id(queue)}"

        async def on_event(event_type: str, payload: dict) -> None:
            if event_types and event_type not in event_types:
                return
            try:
                await queue.put((event_type, payload))
            except asyncio.QueueFull:
                pass

        bus.subscribe("*", on_event, listener_id)
        return queue, listener_id, bus

    # ── Device Commands ───────────────────────────────────

    async def stream_device_commands(self, device_id: str) -> tuple:
        bus = self._action_bus
        if not bus:
            raise RuntimeError("ActionBus not loaded")

        queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        async def on_command(command_id: str, target: str,
                             action: str, params: dict) -> None:
            if target == device_id:
                try:
                    await queue.put((command_id, action, params))
                except asyncio.QueueFull:
                    pass

        bus.subscribe_device("*", on_command)
        return queue, on_command, bus

    async def report_command_result(self, command_id: str, device_id: str,
                                    success: bool, error: str | None = None,
                                    result_data: dict | None = None) -> bool:
        bus = self._action_bus
        if not bus:
            return False
        await bus.report_result(
            command_id=command_id, success=success,
            error=error or None, result_data=result_data or {},
        )
        return True
