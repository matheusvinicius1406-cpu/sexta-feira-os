"""
MemoryAdapter — wraps PersistentMemory behind a clean async interface.

Hides:
  - DB session creation/teardown (SessionLocal)
  - Owner ID lookup
  - SQLAlchemy model conversion
  - Event publishing (memory.created, deleted, linked, unlinked)

gRPC/REST callers interact only with this adapter, never with
PersistentMemory, Session, or Owner directly.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.adapters._events import publish_event
from app.brain.memory import PersistentMemory
from app.core.di import get_kernel
from app.db.database import SessionLocal
from app.models.models import Owner

logger = logging.getLogger("sexta-feira.adapter.memory")


@dataclass
class MemoryItem:
    """Lightweight DTO returned by the adapter — no SQLAlchemy dependency."""
    id: str
    content: str
    title: str
    kind: str
    importance: float
    source: str
    created_at: Any = None
    updated_at: Any = None


class MemoryAdapter:
    """Adapter for memory operations. Manages DB sessions internally."""

    def __init__(self) -> None:
        self._kernel = get_kernel()
        self._memory: PersistentMemory | None = None

    @property
    def memory(self) -> PersistentMemory | None:
        if self._memory is None and self._kernel:
            self._memory = self._kernel.memory
        return self._memory

    def _get_db_and_owner(self):
        """Open a DB session and resolve the single owner."""
        db = SessionLocal()
        try:
            owner = db.query(Owner).filter(Owner.is_active.is_(True)).first()
            if not owner:
                raise RuntimeError("No active owner found")
            return db, owner.id
        except Exception:
            db.close()
            raise

    # ── CRUD ──────────────────────────────────────────────

    async def create(self, content: str, kind: str = "fact",
                     title: str | None = None) -> MemoryItem:
        mem = self.memory
        if not mem:
            raise RuntimeError("Memory service not loaded")
        db, owner_id = self._get_db_and_owner()
        try:
            m = await mem.remember(db, owner_id, content, kind,
                                   title=title, source="grpc")
            item = MemoryItem(
                id=str(m.id), content=m.content, title=m.title or "",
                kind=m.kind, importance=getattr(m, "importance", 0.5),
                source=getattr(m, "source", ""), created_at=m.created_at,
                updated_at=m.updated_at,
            )
            await publish_event("memory.created", {
                "id": item.id, "content": item.content[:200],
                "kind": item.kind, "title": item.title,
            }, source="memory_adapter", db=db, owner_id=owner_id)
            return item
        finally:
            db.close()

    async def get_by_id(self, memory_id: str) -> MemoryItem | None:
        mem = self.memory
        if not mem:
            raise RuntimeError("Memory service not loaded")
        db, owner_id = self._get_db_and_owner()
        try:
            # Direct DB query for the memory
            from app.models.models import Memory
            m = db.query(Memory).filter(
                Memory.id == memory_id, Memory.owner_id == owner_id
            ).first()
            if not m:
                return None
            return MemoryItem(
                id=str(m.id), content=m.content, title=m.title or "",
                kind=m.kind, importance=getattr(m, "importance", 0.5),
                source=getattr(m, "source", ""), created_at=m.created_at,
                updated_at=m.updated_at,
            )
        finally:
            db.close()

    async def delete(self, memory_id: str) -> bool:
        mem = self.memory
        if not mem:
            raise RuntimeError("Memory service not loaded")
        db, owner_id = self._get_db_and_owner()
        try:
            success = mem.forget(db, owner_id, memory_id)
            if success:
                await publish_event("memory.deleted", {"id": memory_id},
                                    source="memory_adapter", db=db, owner_id=owner_id)
            return success
        finally:
            db.close()

    async def search(self, query: str, limit: int = 10) -> list[MemoryItem]:
        mem = self.memory
        if not mem:
            raise RuntimeError("Memory service not loaded")
        db, owner_id = self._get_db_and_owner()
        try:
            results = await mem.recall(db, owner_id, query, top_k=limit)
            items = [
                MemoryItem(id=str(m.id), content=m.content, title=m.title or "",
                           kind=m.kind, importance=getattr(m, "importance", 0.5),
                           source=getattr(m, "source", ""), created_at=m.created_at,
                           updated_at=m.updated_at)
                for m in results
            ]
            await publish_event("memory.searched", {
                "query": query[:100], "count": len(items),
            }, source="memory_adapter", db=db, owner_id=owner_id)
            return items
        finally:
            db.close()

    # ── Graph ─────────────────────────────────────────────

    async def link(self, source_id: str, target_id: str,
                   relation: str = "related") -> dict | None:
        mem = self.memory
        if not mem:
            raise RuntimeError("Memory service not loaded")
        db, owner_id = self._get_db_and_owner()
        try:
            edge = mem.link(db, owner_id, source_id, target_id,
                            relation=relation, weight=1.0, origin="grpc")
            if not edge:
                return None
            result = {
                "id": str(edge.id), "source_id": str(edge.source_id),
                "target_id": str(edge.target_id), "relation": edge.relation,
            }
            await publish_event("memory.linked", result,
                                source="memory_adapter", db=db, owner_id=owner_id)
            return result
        finally:
            db.close()

    async def unlink(self, link_id: str) -> bool:
        mem = self.memory
        if not mem:
            raise RuntimeError("Memory service not loaded")
        db, owner_id = self._get_db_and_owner()
        try:
            success = mem.unlink(db, owner_id, link_id)
            if success:
                await publish_event("memory.unlinked", {"link_id": link_id},
                                    source="memory_adapter", db=db, owner_id=owner_id)
            return success
        finally:
            db.close()

    async def get_neighbours(self, memory_id: str) -> dict:
        mem = self.memory
        if not mem:
            raise RuntimeError("Memory service not loaded")
        db, owner_id = self._get_db_and_owner()
        try:
            return mem.neighbours(db, owner_id, memory_id)
        finally:
            db.close()

    async def get_graph(self, max_nodes: int = 50) -> dict:
        mem = self.memory
        if not mem:
            raise RuntimeError("Memory service not loaded")
        db, owner_id = self._get_db_and_owner()
        try:
            return mem.graph(db, owner_id, limit=max_nodes)
        finally:
            db.close()
