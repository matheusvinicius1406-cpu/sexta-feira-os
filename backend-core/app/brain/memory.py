"""
PersistentMemory — the second brain.

Facts about you are stored in SQLite and indexed with LOCAL embeddings
(computed by Ollama). Retrieval is cosine similarity over your own vectors.
Everything survives restarts and never leaves the machine.

This is intentionally simple and dependency-light (numpy only). For very
large memory sets you can later swap the linear scan for sqlite-vec / FAISS
without changing callers.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import List, Optional

import numpy as np
from sqlalchemy.orm import Session

from app.brain.engine import LocalBrain
from app.core.config import settings
from app.models.models import Memory

logger = logging.getLogger("sexta-feira.memory")


class PersistentMemory:
    def __init__(self, brain: LocalBrain):
        self.brain = brain

    async def remember(
        self,
        db: Session,
        owner_id: str,
        content: str,
        kind: str = "fact",
        importance: float = 0.5,
        source: str = "manual",
    ) -> Memory:
        """Store a durable fact with its locally-computed embedding."""
        embedding: Optional[List[float]] = None
        try:
            embedding = await self.brain.embed(content)
        except Exception as e:  # noqa: BLE001 — memory must not crash the chat
            logger.warning("Embedding failed (stored without vector): %s", e)

        mem = Memory(
            id=str(uuid.uuid4()),
            owner_id=owner_id,
            content=content,
            kind=kind,
            importance=importance,
            source=source,
            embedding=json.dumps(embedding) if embedding else None,
        )
        db.add(mem)
        db.commit()
        db.refresh(mem)
        logger.info("Remembered (%s): %s", kind, content[:80])
        return mem

    async def recall(
        self,
        db: Session,
        owner_id: str,
        query: str,
        top_k: Optional[int] = None,
    ) -> List[Memory]:
        """Return the most relevant memories for `query` (semantic search)."""
        top_k = top_k or settings.memory_top_k
        rows = db.query(Memory).filter(Memory.owner_id == owner_id).all()
        if not rows:
            return []

        try:
            q_vec = np.asarray(await self.brain.embed(query), dtype=np.float32)
        except Exception as e:  # noqa: BLE001
            logger.warning("Query embedding failed, recall skipped: %s", e)
            return []
        if q_vec.size == 0 or not np.any(q_vec):
            return []
        q_norm = q_vec / (np.linalg.norm(q_vec) + 1e-9)

        scored = []
        for m in rows:
            if not m.embedding:
                continue
            v = np.asarray(json.loads(m.embedding), dtype=np.float32)
            if v.size != q_vec.size or not np.any(v):
                continue
            sim = float(np.dot(q_norm, v / (np.linalg.norm(v) + 1e-9)))
            if sim >= settings.memory_min_similarity:
                scored.append((sim + 0.1 * (m.importance or 0.0), m))

        scored.sort(key=lambda t: t[0], reverse=True)
        top = [m for _, m in scored[:top_k]]

        for m in top:  # track usage so we could decay/forget later
            m.access_count = (m.access_count or 0) + 1
        db.commit()
        return top

    def list_all(self, db: Session, owner_id: str, limit: int = 200) -> List[Memory]:
        return (
            db.query(Memory)
            .filter(Memory.owner_id == owner_id)
            .order_by(Memory.created_at.desc())
            .limit(limit)
            .all()
        )

    def forget(self, db: Session, owner_id: str, memory_id: str) -> bool:
        m = db.query(Memory).filter(
            Memory.id == memory_id, Memory.owner_id == owner_id
        ).first()
        if not m:
            return False
        db.delete(m)
        db.commit()
        return True
