"""
CognitiveCore gRPC service — THIN GATEWAY.

Protocol translation only: protobuf → adapter → domain.
No business logic. No DB sessions. No Kernel imports.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

import grpc
from google.protobuf import timestamp_pb2

from app.adapters.action_adapter import ActionAdapter
from app.adapters.cognition_adapter import CognitionAdapter
from app.adapters.memory_adapter import MemoryAdapter
from app.adapters.voice_adapter import VoiceAdapter
from app.grpc import cognitive_core_pb2 as pb2
from app.grpc import cognitive_core_pb2_grpc as pb2_grpc

logger = logging.getLogger("sexta-feira.grpc.cognitive")


# ── Protobuf type mappers (stateless helpers) ──────────────

def _memory_kind_to_pb(kind: str) -> int:
    mapping = {
        "fact": pb2.MEMORY_KIND_FACT,
        "preference": pb2.MEMORY_KIND_PREFERENCE,
        "concept": pb2.MEMORY_KIND_CONCEPT,
        "person": pb2.MEMORY_KIND_PERSON,
        "project": pb2.MEMORY_KIND_PROJECT,
        "note": pb2.MEMORY_KIND_NOTE,
        "conversation": pb2.MEMORY_KIND_CONVERSATION,
    }
    return mapping.get(kind.lower(), pb2.MEMORY_KIND_UNSPECIFIED)


def _pb_to_memory_kind(pb_kind: int) -> str:
    mapping = {
        pb2.MEMORY_KIND_FACT: "fact",
        pb2.MEMORY_KIND_PREFERENCE: "preference",
        pb2.MEMORY_KIND_CONCEPT: "concept",
        pb2.MEMORY_KIND_PERSON: "person",
        pb2.MEMORY_KIND_PROJECT: "project",
        pb2.MEMORY_KIND_NOTE: "note",
        pb2.MEMORY_KIND_CONVERSATION: "conversation",
    }
    return mapping.get(pb_kind, "fact")


def _pb_relation_to_domain(pb_rel: int) -> str:
    mapping = {
        pb2.RELATION_RELATED: "related",
        pb2.RELATION_CREATED_BY: "created_by",
        pb2.RELATION_MENTIONS: "mentions",
        pb2.RELATION_CAUSES: "causes",
        pb2.RELATION_DEPENDS_ON: "depends_on",
        pb2.RELATION_OPPOSES: "opposes",
    }
    return mapping.get(pb_rel, "related")


def _item_to_pb(item) -> pb2.MemoryNode:
    """Convert a MemoryItem (from adapter) to protobuf."""
    ts_created = timestamp_pb2.Timestamp()
    if item.created_at:
        dt = item.created_at
        ts_created.FromDatetime(dt if dt.tzinfo else dt.replace(tzinfo=UTC))
    ts_updated = timestamp_pb2.Timestamp()
    if item.updated_at:
        dt = item.updated_at
        ts_updated.FromDatetime(dt if dt.tzinfo else dt.replace(tzinfo=UTC))
    return pb2.MemoryNode(
        id=item.id, content=item.content, title=item.title,
        kind=_memory_kind_to_pb(item.kind), importance=item.importance,
        source=item.source, created_at=ts_created, updated_at=ts_updated,
    )


def _link_dict_to_pb(link: dict) -> pb2.MemoryLink:
    return pb2.MemoryLink(
        id=link.get("id", ""),
        source_id=link.get("source_id", ""),
        target_id=link.get("target_id", ""),
        label=link.get("relation", "related"),
    )


# ── Service ───────────────────────────────────────────────

class CognitiveCoreService(pb2_grpc.CognitiveCoreServicer):
    """Thin gRPC gateway — delegates everything to adapters."""

    def __init__(self) -> None:
        self._memory = MemoryAdapter()
        self._cognition = CognitionAdapter()
        self._started_at = datetime.now(UTC)

    # ── Health ────────────────────────────────────────────

    async def CheckHealth(self, request, context) -> pb2.HealthCheckResponse:
        brain_online = await self._cognition.check_health()
        return pb2.HealthCheckResponse(
            status="ok" if brain_online else "degraded",
            version="1.0.0-kernel",
            ollama_online=brain_online,
            voice_available=VoiceAdapter().available,
            uptime_seconds=int((datetime.now(UTC) - self._started_at).total_seconds()),
        )

    # ── Chat (server streaming) ───────────────────────────

    async def Chat(self, request, context):
        try:
            async for token in self._cognition.chat_stream(
                message=request.message,
                conversation_id=request.conversation_id or None,
            ):
                yield pb2.ChatResponse(text_chunk=token)
        except Exception as exc:
            logger.error("Chat stream error: %s", exc)
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))

    # ── Memory CRUD ───────────────────────────────────────

    async def CreateMemory(self, request, context) -> pb2.MemoryNode:
        try:
            item = await self._memory.create(
                content=request.content,
                kind=_pb_to_memory_kind(request.kind),
                title=request.title or None,
            )
            return _item_to_pb(item)
        except Exception as exc:
            logger.error("CreateMemory error: %s", exc)
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))
            return pb2.MemoryNode()

    async def GetMemory(self, request, context) -> pb2.MemoryNode:
        try:
            item = await self._memory.get_by_id(request.id)
            if not item:
                await context.abort(grpc.StatusCode.NOT_FOUND, f"Memory {request.id} not found")
                return pb2.MemoryNode()
            return _item_to_pb(item)
        except Exception as exc:
            logger.error("GetMemory error: %s", exc)
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))
            return pb2.MemoryNode()

    async def DeleteMemory(self, request, context) -> pb2.DeleteMemoryResponse:
        try:
            success = await self._memory.delete(request.id)
            return pb2.DeleteMemoryResponse(success=success, deleted_id=request.id)
        except Exception as exc:
            logger.error("DeleteMemory error: %s", exc)
            return pb2.DeleteMemoryResponse(success=False, deleted_id=request.id)

    async def SearchMemory(self, request, context) -> pb2.SearchMemoryResponse:
        try:
            results = await self._memory.search(request.query, limit=request.limit or 10)
            return pb2.SearchMemoryResponse(
                results=[_item_to_pb(r) for r in results],
                total=len(results),
            )
        except Exception as exc:
            logger.error("SearchMemory error: %s", exc)
            return pb2.SearchMemoryResponse()

    async def UpdateMemory(self, request, context) -> pb2.MemoryNode:
        try:
            # Delete old + create new (current domain limitation)
            await self._memory.delete(request.id)
            item = await self._memory.create(
                content=request.content or request.id,
                kind=_pb_to_memory_kind(request.kind) if request.kind else "fact",
            )
            return _item_to_pb(item)
        except Exception as exc:
            logger.error("UpdateMemory error: %s", exc)
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))
            return pb2.MemoryNode()

    # ── Memory Graph ──────────────────────────────────────

    async def LinkMemories(self, request, context) -> pb2.MemoryLink:
        try:
            edge = await self._memory.link(
                source_id=request.source_id,
                target_id=request.target_id,
                relation=_pb_relation_to_domain(request.relation),
            )
            if not edge:
                await context.abort(grpc.StatusCode.INTERNAL, "Failed to create link")
                return pb2.MemoryLink()
            return _link_dict_to_pb(edge)
        except Exception as exc:
            logger.error("LinkMemories error: %s", exc)
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))
            return pb2.MemoryLink()

    async def UnlinkMemories(self, request, context) -> pb2.DeleteMemoryResponse:
        try:
            success = await self._memory.unlink(request.link_id)
            return pb2.DeleteMemoryResponse(success=success, deleted_id=request.link_id)
        except Exception as exc:
            logger.error("UnlinkMemories error: %s", exc)
            return pb2.DeleteMemoryResponse(success=False, deleted_id=request.link_id)

    async def GetNeighbours(self, request, context) -> pb2.NeighboursResponse:
        try:
            memory = await self._memory.get_by_id(request.memory_id)
            if not memory:
                await context.abort(grpc.StatusCode.NOT_FOUND,
                                    f"Memory {request.memory_id} not found")
                return pb2.NeighboursResponse()

            nb = await self._memory.get_neighbours(request.memory_id)

            # Convert forward links
            links = []
            neighbour_ids = set()
            for entry in nb.get("links", []):
                links.append(pb2.MemoryLink(
                    id=entry.get("id", ""),
                    source_id=request.memory_id,
                    target_id=(entry.get("target") or {}).get("id", ""),
                    label=entry.get("relation", "related"),
                ))
                tgt = entry.get("target")
                if tgt and tgt.get("id"):
                    neighbour_ids.add(tgt["id"])

            # Also add backlinks
            for entry in nb.get("backlinks", []):
                links.append(pb2.MemoryLink(
                    id=entry.get("id", ""),
                    source_id=(entry.get("source") or {}).get("id", ""),
                    target_id=request.memory_id,
                    label=entry.get("relation", "related"),
                ))
                src = entry.get("source")
                if src and src.get("id"):
                    neighbour_ids.add(src["id"])

            # Fetch neighbour details
            neighbours = []
            for nid in neighbour_ids:
                n = await self._memory.get_by_id(nid)
                if n:
                    neighbours.append(_item_to_pb(n))

            return pb2.NeighboursResponse(
                memory=_item_to_pb(memory),
                links=links,
                neighbours=neighbours,
            )
        except Exception as exc:
            logger.error("GetNeighbours error: %s", exc)
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))
            return pb2.NeighboursResponse()

    async def GetMemoryGraph(self, request, context) -> pb2.MemoryGraph:
        try:
            g = await self._memory.get_graph(max_nodes=request.max_nodes or 50)
            return pb2.MemoryGraph(
                nodes=[
                    pb2.MemoryNodeDTO(
                        id=n.get("id", ""), label=n.get("title", ""),
                        kind=_memory_kind_to_pb(n.get("kind", "fact")),
                        importance=n.get("importance", 0.5),
                    ) for n in g.get("nodes", [])
                ],
                links=[
                    pb2.MemoryLinkDTO(
                        source_id=e.get("source", ""),
                        target_id=e.get("target", ""),
                        label=e.get("relation", ""),
                    ) for e in g.get("edges", [])
                ],
            )
        except Exception as exc:
            logger.error("GetMemoryGraph error: %s", exc)
            return pb2.MemoryGraph()

    # ── Actions ───────────────────────────────────────────

    async def DispatchAction(self, request, context) -> pb2.DispatchActionResponse:
        try:
            command_id = await ActionAdapter().dispatch(
                device=request.device,
                action=request.action,
                params=dict(request.params),
            )
            return pb2.DispatchActionResponse(command_id=command_id, accepted=True)
        except Exception as exc:
            logger.error("DispatchAction error: %s", exc)
            return pb2.DispatchActionResponse(command_id="", accepted=False, error=str(exc))
