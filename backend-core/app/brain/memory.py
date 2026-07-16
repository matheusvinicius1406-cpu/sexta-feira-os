"""
PersistentMemory — the second brain, as a KNOWLEDGE GRAPH.

Not a flat list of facts: every memory is a NODE, and nodes CONNECT to each
other via edges (MemoryLink), the way Obsidian links notes. Connections form
three ways:

  * [[wikilinks]] you write inside a memory        -> explicit edges
  * semantic similarity (local embeddings)          -> automatic edges
  * by hand (POST /memory/{id}/link)                -> manual edges

Recall is "networked thought": we find seed nodes by similarity, then EXPAND
along the edges to pull in connected context — so the brain surfaces things
that are related even when they don't match the query word-for-word.

Everything is local (SQLite + Ollama embeddings) and survives restarts.
"""
from __future__ import annotations

import json
import logging
import re
import uuid

import numpy as np
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.brain.engine import LocalBrain
from app.core.config import settings
from app.models.models import Memory, MemoryLink

logger = logging.getLogger("sexta-feira.memory")

_WIKILINK = re.compile(r"\[\[([^\[\]]+)\]\]")


class PersistentMemory:
    def __init__(self, brain: LocalBrain):
        self.brain = brain

    # ================= storing / nodes =================

    async def remember(
        self,
        db: Session,
        owner_id: str,
        content: str,
        kind: str = "fact",
        importance: float = 0.5,
        source: str = "manual",
        title: str | None = None,
        auto_link: bool | None = None,
    ) -> Memory:
        """Store a node, compute its local embedding, and weave it into the graph."""
        embedding: list[float] | None = None
        try:
            embedding = await self.brain.embed(content)
        except Exception as e:  # noqa: BLE001 — memory must never crash the chat
            logger.warning("Embedding failed (stored without vector): %s", e)

        mem = Memory(
            id=str(uuid.uuid4()),
            owner_id=owner_id,
            title=(title or content[:60]),
            content=content,
            kind=kind,
            importance=importance,
            source=source,
            embedding=json.dumps(embedding) if embedding else None,
        )
        db.add(mem)
        db.commit()
        db.refresh(mem)

        if settings.graph_autolink if auto_link is None else auto_link:
            await self._auto_link(db, owner_id, mem)
        logger.info("Remembered (%s): %s", kind, content[:80])
        return mem

    def _find_or_create_concept(self, db: Session, owner_id: str, title: str) -> Memory:
        title = title.strip()
        existing = (
            db.query(Memory)
            .filter(Memory.owner_id == owner_id, Memory.title == title)
            .first()
        )
        if existing:
            return existing
        node = Memory(
            id=str(uuid.uuid4()), owner_id=owner_id, title=title,
            content=title, kind="concept", importance=0.4, source="wikilink",
        )
        db.add(node)
        db.commit()
        db.refresh(node)
        return node

    async def _auto_link(self, db: Session, owner_id: str, mem: Memory) -> None:
        # 1) explicit [[wikilinks]] written in the content
        for name in _WIKILINK.findall(mem.content):
            target = self._find_or_create_concept(db, owner_id, name)
            if target.id != mem.id:
                self.link(db, owner_id, mem.id, target.id, relation="wikilink",
                          weight=1.0, origin="wikilink")

        # 2) semantic neighbours (needs an embedding)
        if not mem.embedding:
            return
        for target, sim in self._semantic_neighbours(db, owner_id, mem, settings.graph_autolink_k):
            relation = await self._label_relation(mem, target)
            self.link(db, owner_id, mem.id, target.id, relation=relation,
                      weight=round(sim, 4), origin="semantic")

    async def _label_relation(self, source: Memory, target: Memory) -> str:
        """Ask the local brain to name the connection (best-effort; 'related' on failure)."""
        if not settings.graph_relation_labels:
            return "related"
        try:
            prompt = [
                {"role": "system", "content":
                    "Nomeie em 1 a 3 palavras a relação entre A e B, do ponto de vista "
                    "do dono (ex.: 'trabalha em', 'gosta de', 'mora em', 'é amigo de'). "
                    "Responda SÓ a relação, em minúsculas, sem pontuação. Se não houver "
                    "relação clara, responda 'related'."},
                {"role": "user", "content": f"A: {source.content}\nB: {target.content}"},
            ]
            raw = await self.brain.chat(prompt, temperature=0.1, max_tokens=12)
            label = raw.strip().splitlines()[0].strip().strip(".").lower() if raw else ""
            return label[:40] or "related"
        except Exception as e:  # noqa: BLE001 — labeling must never break remembering
            logger.debug("relation labeling skipped: %s", e)
            return "related"

    def _semantic_neighbours(
        self, db: Session, owner_id: str, mem: Memory, k: int
    ) -> list[tuple[Memory, float]]:
        v = np.asarray(json.loads(mem.embedding), dtype=np.float32)
        if v.size == 0 or not np.any(v):
            return []
        v = v / (np.linalg.norm(v) + 1e-9)
        scored: list[tuple[Memory, float]] = []
        rows = db.query(Memory).filter(
            Memory.owner_id == owner_id, Memory.id != mem.id, Memory.embedding.isnot(None)
        ).all()
        for other in rows:
            ov = np.asarray(json.loads(other.embedding), dtype=np.float32)
            if ov.size != v.size or not np.any(ov):
                continue
            sim = float(np.dot(v, ov / (np.linalg.norm(ov) + 1e-9)))
            if sim >= settings.graph_link_min_similarity:
                scored.append((other, sim))
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:k]

    # ================= edges =================

    def link(
        self, db: Session, owner_id: str, source_id: str, target_id: str,
        relation: str = "related", weight: float = 1.0, origin: str = "manual",
    ) -> MemoryLink | None:
        """Create an edge (idempotent for the same source/target/relation)."""
        if source_id == target_id:
            return None
        existing = db.query(MemoryLink).filter(
            MemoryLink.owner_id == owner_id,
            MemoryLink.source_id == source_id,
            MemoryLink.target_id == target_id,
            MemoryLink.relation == relation,
        ).first()
        if existing:
            existing.weight = max(existing.weight or 0.0, weight)
            db.commit()
            return existing
        edge = MemoryLink(
            id=str(uuid.uuid4()), owner_id=owner_id, source_id=source_id,
            target_id=target_id, relation=relation, weight=weight, origin=origin,
        )
        db.add(edge)
        db.commit()
        db.refresh(edge)
        return edge

    def unlink(self, db: Session, owner_id: str, link_id: str) -> bool:
        edge = db.query(MemoryLink).filter(
            MemoryLink.id == link_id, MemoryLink.owner_id == owner_id
        ).first()
        if not edge:
            return False
        db.delete(edge)
        db.commit()
        return True

    def neighbours(self, db: Session, owner_id: str, memory_id: str) -> dict[str, list]:
        """Forward links + backlinks for a node."""
        forward = db.query(MemoryLink).filter(
            MemoryLink.owner_id == owner_id, MemoryLink.source_id == memory_id
        ).all()
        back = db.query(MemoryLink).filter(
            MemoryLink.owner_id == owner_id, MemoryLink.target_id == memory_id
        ).all()

        def node(mid: str) -> dict | None:
            m = db.query(Memory).filter(Memory.id == mid).first()
            return {"id": m.id, "title": m.title, "kind": m.kind} if m else None

        return {
            "links": [
                {"id": e.id, "relation": e.relation, "weight": e.weight,
                 "origin": e.origin, "target": node(e.target_id)} for e in forward
            ],
            "backlinks": [
                {"id": e.id, "relation": e.relation, "weight": e.weight,
                 "origin": e.origin, "source": node(e.source_id)} for e in back
            ],
        }

    def graph(self, db: Session, owner_id: str, limit: int = 500) -> dict[str, list]:
        """The whole graph — nodes + edges — for a visualization (Obsidian-style)."""
        nodes = db.query(Memory).filter(Memory.owner_id == owner_id).limit(limit).all()
        node_ids = {n.id for n in nodes}
        edges = db.query(MemoryLink).filter(MemoryLink.owner_id == owner_id).all()
        return {
            "nodes": [
                {"id": n.id, "title": n.title, "kind": n.kind, "importance": n.importance}
                for n in nodes
            ],
            "edges": [
                {"source": e.source_id, "target": e.target_id,
                 "relation": e.relation, "weight": e.weight}
                for e in edges if e.source_id in node_ids and e.target_id in node_ids
            ],
        }

    # ================= retrieval =================

    async def _seed_by_similarity(
        self, db: Session, owner_id: str, query: str, top_k: int
    ) -> list[tuple[Memory, float]]:
        rows = db.query(Memory).filter(
            Memory.owner_id == owner_id, Memory.embedding.isnot(None)
        ).all()
        if not rows:
            return []
        try:
            q = np.asarray(await self.brain.embed(query), dtype=np.float32)
        except Exception as e:  # noqa: BLE001
            logger.warning("Query embedding failed: %s", e)
            return []
        if q.size == 0 or not np.any(q):
            return []
        q = q / (np.linalg.norm(q) + 1e-9)
        scored: list[tuple[Memory, float]] = []
        for m in rows:
            v = np.asarray(json.loads(m.embedding), dtype=np.float32)
            if v.size != q.size or not np.any(v):
                continue
            sim = float(np.dot(q, v / (np.linalg.norm(v) + 1e-9)))
            if sim >= settings.memory_min_similarity:
                scored.append((m, sim + 0.1 * (m.importance or 0.0)))
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:top_k]

    async def recall(
        self, db: Session, owner_id: str, query: str, top_k: int | None = None
    ) -> list[Memory]:
        """Plain semantic recall (seed nodes only)."""
        top_k = top_k or settings.memory_top_k
        seeds = await self._seed_by_similarity(db, owner_id, query, top_k)
        self._touch(db, [m for m, _ in seeds])
        return [m for m, _ in seeds]

    async def recall_graph(
        self, db: Session, owner_id: str, query: str, top_k: int | None = None
    ) -> list[Memory]:
        """
        Networked recall: semantic seeds, then EXPAND along edges (backlinks
        included) so connected context comes along for the ride.
        """
        top_k = top_k or settings.memory_top_k
        seeds = await self._seed_by_similarity(db, owner_id, query, top_k)
        if not seeds:
            return []

        scores: dict[str, float] = {}
        nodes: dict[str, Memory] = {}
        for m, s in seeds:
            scores[m.id] = s
            nodes[m.id] = m

        frontier = [m.id for m, _ in seeds]
        decay = settings.graph_expand_decay
        for _ in range(max(0, settings.graph_expand_hops)):
            if not frontier:
                break
            edges = db.query(MemoryLink).filter(
                MemoryLink.owner_id == owner_id,
                or_(MemoryLink.source_id.in_(frontier), MemoryLink.target_id.in_(frontier)),
            ).all()
            next_frontier: list[str] = []
            for e in edges:
                for near_id, far_id in ((e.source_id, e.target_id), (e.target_id, e.source_id)):
                    if near_id in scores and far_id not in scores:
                        m = db.query(Memory).filter(Memory.id == far_id).first()
                        if not m:
                            continue
                        nodes[far_id] = m
                        scores[far_id] = scores[near_id] * decay * (e.weight or 1.0)
                        next_frontier.append(far_id)
            frontier = next_frontier

        ranked = sorted(nodes.values(), key=lambda m: scores.get(m.id, 0.0), reverse=True)
        result = ranked[: top_k + settings.graph_autolink_k]
        self._touch(db, result)
        return result

    def _touch(self, db: Session, mems: list[Memory]) -> None:
        for m in mems:
            m.access_count = (m.access_count or 0) + 1
        if mems:
            db.commit()

    # ================= misc =================

    def list_all(self, db: Session, owner_id: str, limit: int = 200) -> list[Memory]:
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
        db.delete(m)  # edges cascade via FK ondelete
        db.commit()
        return True
