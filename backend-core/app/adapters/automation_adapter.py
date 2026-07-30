"""
AutomationAdapter — wraps n8n workflows, the EventBus, and the ActionBus.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.core.di import get_kernel

logger = logging.getLogger("sexta-feira.adapter.automation")


class AutomationAdapter:
    """Adapter for automations, events, and device commands."""

    def __init__(self) -> None:
        self._kernel = get_kernel()

    @property
    def _automations(self):
        return self._kernel.automations if self._kernel else None

    @property
    def _events(self):
        return self._kernel.events if self._kernel else None

    @property
    def _action_bus(self):
        return self._kernel.action_bus if self._kernel else None

    # ── Workflows ─────────────────────────────────────────

    async def trigger_workflow(self, workflow_id: str,
                               params: dict[str, str] | None = None) -> str | None:
        n8n = self._automations
        if not n8n:
            raise RuntimeError("Automations not loaded")
        return await n8n.trigger(
            workflow_id=workflow_id,
            params=params or {},
        )

    async def list_workflows(self) -> list[dict]:
        n8n = self._automations
        if not n8n:
            raise RuntimeError("Automations not loaded")
        return await n8n.list_workflows()

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
