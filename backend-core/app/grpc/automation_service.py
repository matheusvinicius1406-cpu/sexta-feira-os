"""
AutomationService gRPC implementation — thin gateway.

Delegates to AutomationAdapter. No Kernel imports.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import grpc
from google.protobuf import timestamp_pb2

from app.adapters.automation_adapter import AutomationAdapter
from app.grpc import automation_events_pb2 as pb2
from app.grpc import automation_events_pb2_grpc as pb2_grpc

logger = logging.getLogger("sexta-feira.grpc.automation")


class AutomationServiceServicer(pb2_grpc.AutomationServiceServicer):
    """gRPC servicer for automations — delegates to AutomationAdapter."""

    def __init__(self) -> None:
        self._auto = AutomationAdapter()

    def _now_timestamp(self) -> timestamp_pb2.Timestamp:
        ts = timestamp_pb2.Timestamp()
        ts.FromDatetime(datetime.now(timezone.utc))
        return ts

    async def TriggerWorkflow(self, request, context) -> pb2.TriggerWorkflowResponse:
        try:
            execution_id = await self._auto.trigger_workflow(
                workflow_id=request.workflow_id,
                params=dict(request.params),
            )
            return pb2.TriggerWorkflowResponse(
                execution_id=execution_id or "",
                accepted=bool(execution_id),
            )
        except Exception as exc:
            logger.error("TriggerWorkflow error: %s", exc)
            return pb2.TriggerWorkflowResponse(execution_id="", accepted=False)

    async def ListWorkflows(self, request, context) -> pb2.ListWorkflowsResponse:
        try:
            workflows = await self._auto.list_workflows()
            return pb2.ListWorkflowsResponse(workflows=[
                pb2.WorkflowInfo(id=w["id"], name=w["name"],
                                 active=w.get("active", False))
                for w in workflows
            ])
        except Exception as exc:
            logger.error("ListWorkflows error: %s", exc)
            return pb2.ListWorkflowsResponse()

    async def StreamEvents(self, request, context):
        event_types = set(request.event_types) if request.event_types else set()
        try:
            queue, listener_id, bus = await self._auto.stream_events(
                event_types or None,
            )
        except Exception as exc:
            await context.abort(grpc.StatusCode.UNAVAILABLE, str(exc))
            return

        try:
            while True:
                try:
                    event_type, payload = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield pb2.SystemEvent(
                        event=_event_type_to_pb(event_type),
                        timestamp=self._now_timestamp(),
                        payload_json=json.dumps(payload, default=str),
                    )
                except asyncio.TimeoutError:
                    yield pb2.SystemEvent(
                        event=pb2.EVENT_UNSPECIFIED,
                        timestamp=self._now_timestamp(),
                        payload_json="{}",
                    )
        except grpc.RpcError:
            pass
        finally:
            bus.unsubscribe("*", listener_id)

    async def StreamDeviceCommands(self, request, context):
        device_id = request.device_id
        logger.info("Device connected: %s", device_id)
        try:
            queue, on_command, bus = await self._auto.stream_device_commands(device_id)
        except Exception as exc:
            await context.abort(grpc.StatusCode.UNAVAILABLE, str(exc))
            return

        try:
            while True:
                try:
                    cmd_id, action, params = await asyncio.wait_for(queue.get(), timeout=60.0)
                    yield pb2.DeviceCommand(
                        command_id=cmd_id, action=action,
                        params=params, issued_at=self._now_timestamp(),
                    )
                except asyncio.TimeoutError:
                    continue
        except grpc.RpcError:
            pass
        finally:
            bus.unsubscribe_device("*", on_command)

    async def ReportCommandResult(self, request, context) -> pb2.CommandResultAck:
        await self._auto.report_command_result(
            command_id=request.command_id,
            device_id=request.device_id,
            success=request.success,
            error=request.error or None,
            result_data=dict(request.result_data),
        )
        return pb2.CommandResultAck(received=True)


def _event_type_to_pb(event_type: str) -> int:
    mapping = {
        "brain_status_changed": pb2.EVENT_BRAIN_STATUS_CHANGED,
        "memory_created": pb2.EVENT_MEMORY_CREATED,
        "memory_deleted": pb2.EVENT_MEMORY_DELETED,
        "workflow_started": pb2.EVENT_WORKFLOW_STARTED,
        "workflow_completed": pb2.EVENT_WORKFLOW_COMPLETED,
        "device_connected": pb2.EVENT_DEVICE_CONNECTED,
        "device_disconnected": pb2.EVENT_DEVICE_DISCONNECTED,
        "action_dispatched": pb2.EVENT_ACTION_DISPATCHED,
        "reminder_fired": pb2.EVENT_REMINDER_FIRED,
    }
    return mapping.get(event_type, pb2.EVENT_UNSPECIFIED)
