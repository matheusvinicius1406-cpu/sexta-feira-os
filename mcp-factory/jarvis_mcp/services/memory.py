"""Memory service: durable, queryable agent memory.

Stores four kinds of records — architectural *decisions*, *tasks*, project
*context*, and free *notes* — as append-only JSONL, one file per kind. Retrieval
today is keyword/tag based. The schema and the ``Embedder`` seam are designed so
a vector backend (embeddings + ANN index) can be dropped in later for RAG
without changing the tool surface: every record already reserves an ``embedding``
field and queries go through :meth:`MemoryService.search`.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from ..core.context import ExecutionContext
from ..core.errors import ValidationError

KINDS = ("decision", "task", "context", "note")


class Embedder:
    """Seam for future vector search. The default is a no-op so the factory has
    zero ML dependencies today; swap in a real embedder to enable semantic recall."""

    dim = 0

    def embed(self, text: str) -> list[float] | None:  # pragma: no cover - trivial
        return None


class MemoryService:
    def __init__(self, ctx: ExecutionContext, store_dir: Path, embedder: Embedder | None = None) -> None:
        self.ctx = ctx
        self.store = Path(store_dir)
        self.store.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder or Embedder()

    def _file(self, kind: str) -> Path:
        if kind not in KINDS:
            raise ValidationError(f"unknown memory kind '{kind}'", detail={"kinds": list(KINDS)})
        return self.store / f"{kind}.jsonl"

    def remember(self, kind: str, title: str, body: str, tags: list[str] | None = None) -> dict:
        self.ctx.authorize("memory.write", f"{kind}:{title}")
        path = self._file(kind)
        record = {
            "id": uuid.uuid4().hex[:12],
            "kind": kind,
            "title": title,
            "body": body,
            "tags": tags or [],
            "agent": self.ctx.agent,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
            "embedding": self.embedder.embed(f"{title}\n{body}"),
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.ctx.log_effect("memory.write", target=f"{kind}:{record['id']}")
        return {k: v for k, v in record.items() if k != "embedding"}

    def _load(self, kind: str) -> list[dict]:
        path = self._file(kind)
        if not path.is_file():
            return []
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out

    def recent(self, kind: str, limit: int = 20) -> dict:
        self.ctx.authorize("memory.read", kind)
        items = self._load(kind)[-limit:]
        return {"kind": kind, "count": len(items), "items": [self._public(r) for r in reversed(items)]}

    def search(self, query: str, kind: str | None = None, limit: int = 20) -> dict:
        """Keyword/tag search across memory. This is the RAG entry point; when an
        embedder is configured it can be upgraded to semantic ranking here."""
        self.ctx.authorize("memory.read", query)
        if not query:
            raise ValidationError("query must not be empty")
        kinds = [kind] if kind else list(KINDS)
        q = query.lower()
        hits: list[dict] = []
        for k in kinds:
            for r in self._load(k):
                haystack = f"{r.get('title','')} {r.get('body','')} {' '.join(r.get('tags', []))}".lower()
                if q in haystack:
                    hits.append(self._public(r))
        hits.sort(key=lambda r: r["ts"], reverse=True)
        return {"query": query, "count": len(hits[:limit]), "items": hits[:limit]}

    @staticmethod
    def _public(record: dict) -> dict:
        return {k: v for k, v in record.items() if k != "embedding"}
