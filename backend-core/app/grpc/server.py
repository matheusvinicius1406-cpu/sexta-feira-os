"""
gRPC server — Thin Gateway.

Manages lifecycle and service registration only.
No business logic, no Kernel access.
"""
from __future__ import annotations

import logging

import grpc

from app.core.config import settings
from app.grpc.automation_events_pb2_grpc import add_AutomationServiceServicer_to_server
from app.grpc.automation_service import AutomationServiceServicer
from app.grpc.cognitive_core_pb2_grpc import add_CognitiveCoreServicer_to_server
from app.grpc.cognitive_service import CognitiveCoreService
from app.grpc.voice_service import VoiceStreamService
from app.grpc.voice_stream_pb2_grpc import add_VoiceStreamServicer_to_server

logger = logging.getLogger("sexta-feira.grpc")


class GrpcServer:
    """Manages the lifecycle of the gRPC server."""

    def __init__(self) -> None:
        self._server: grpc.aio.Server | None = None
        self._port: int = settings.grpc_port

    async def start(self) -> None:
        if self._server is not None:
            return

        self._server = grpc.aio.server(
            options=[
                ("grpc.max_send_message_length", 50 * 1024 * 1024),
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),
            ],
        )

        # Register thin services — no Kernel dependency
        add_CognitiveCoreServicer_to_server(CognitiveCoreService(), self._server)
        add_VoiceStreamServicer_to_server(VoiceStreamService(), self._server)
        add_AutomationServiceServicer_to_server(AutomationServiceServicer(), self._server)

        listen_addr = f"[::]:{self._port}"
        self._server.add_insecure_port(listen_addr)
        await self._server.start()
        logger.info("gRPC thin gateway listening on %s", listen_addr)

    async def stop(self, grace: float = 5.0) -> None:
        if self._server is None:
            return
        try:
            await self._server.stop(grace)
            logger.info("gRPC thin gateway stopped")
        except Exception as exc:
            logger.warning("gRPC stop error: %s", exc)

    @property
    def running(self) -> bool:
        return self._server is not None


_grpc_server = GrpcServer()


def get_grpc_server() -> GrpcServer:
    return _grpc_server
