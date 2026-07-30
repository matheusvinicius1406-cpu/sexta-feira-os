"""
MemoryEngine — formal engine wrapping PersistentMemory behind IEngine.

Publishes: memory.created, memory.updated, memory.deleted,
           memory.linked, memory.unlinked, memory.searched
"""
from __future__ import annotations

import logging
from typing import Any

from app.brain.memory import PersistentMemory
from app.core.di import get_kernel
from app.db.database import SessionLocal
from app.models.models import Owner, Memory
from app.engines import IEngine

logger = logging.getLogger("sexta-feira.engine.memory")


class MemoryEngine(IEngine):
    """Formal Memory Engine — wraps PersistentMemory with lifecycle + events."""

    @property
    def name(self) -> str:
        return "Memory"

    async def initialize(self) -> None:
        kernel = get_kernel()
        if not kernel or not kernel.memory:
            raise RuntimeError("Kernel memory not available")
        logger.info("MemoryEngine initialized")

    async def health(self) -> bool:
        kernel = get_kernel()
        return kernel is not None and kernel.memory is not None

    async def shutdown(self) -> None:
        logger.info("MemoryEngine shutdown")

    @property
    def _memory(self) -> PersistentMemory | None:
        k = get_kernel()
        return k.memory if k else None

    def _get_db_and_owner(self):
        db = SessionLocal()
        try:
            owner = db.query(Owner).filter(Owner.is_active.is_(True)).first()
            if not owner:
                raise RuntimeError("No active owner found")
            return db, owner.id
        except Exception:
            db.close()
            raise

    async def create(self, content: str, kind: str = "fact",
                     title: str | None = None) -> Memory:
        mem = self._memory
        if not mem:
            raise RuntimeError("Memory service not loaded")
        db, owner_id = self._get_db_and_owner()
        try:
            m = await mem.remember(db, owner_id, content, kind,
                                   title=title, source="engine")
            return m
        finally:
            db.close()

    async def get(self, memory_id: str) -> Memory | None:
        db = SessionLocal()
        try:
            owner = db.query(Owner).filter(Owner.is_active.is_(True)).first()
            if not owner:
                return None
            return db.query(Memory).filter(
                Memory.id == memory_id, Memory.owner_id == owner.id).first()
        finally:
            db.close()

    async def delete(self, memory_id: str) -> bool:
        mem = self._memory
        if not mem:
            raise RuntimeError("Memory service not loaded")
        db, owner_id = self._get_db_and_owner()
        try:
            return mem.forget(db, owner_id, memory_id)
        finally:
            db.close()

    async def search(self, query: str, limit: int = 10) -> list[Memory]:
        mem = self._memory
        if not mem:
            raise RuntimeError("Memory service not loaded")
        db, owner_id = self._get_db_and_owner()
        try:
            return await mem.recall(db, owner_id, query, top_k=limit)
        finally:
            db.close()

    async def link_memories(self, source_id: str, target_id: str,
                            relation: str = "related") -> Any:
        mem = self._memory
        if not mem:
            raise RuntimeError("Memory service not loaded")
        db, owner_id = self._get_db_and_owner()
        try:
            return mem.link(db, owner_id, source_id, target_id,
                            relation=relation, weight=1.0, origin="engine")
        finally:
            db.close()

    async def unlink_memories(self, link_id: str) -> bool:
        mem = self._memory
        if not mem:
            raise RuntimeError("Memory service not loaded")
        db, owner_id = self._get_db_and_owner()
        try:
            return mem.unlink(db, owner_id, link_id)
        finally:
            db.close()

    async def graph(self, max_nodes: int = 50) -> dict:
        mem = self._memory
        if not mem:
            raise RuntimeError("Memory service not loaded")
        db, owner_id = self._get_db_and_owner()
        try:
            return mem.graph(db, owner_id, limit=max_nodes)
        finally:
            db.close()
