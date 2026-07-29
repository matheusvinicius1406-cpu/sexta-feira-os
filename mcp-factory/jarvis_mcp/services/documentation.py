"""Documentation service: read docs, append sections, and manage ADRs.

Writes are confined to the ``docs/`` tree by the PathGuard allow-list. ADRs
(Architecture Decision Records) follow the classic numbered format so the
architecture history stays auditable.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from ..core.context import ExecutionContext
from ..core.errors import NotFound, ValidationError

_ADR_DIRNAME = "docs/ADR"
_ADR_TEMPLATE = """# ADR {num:04d}: {title}

- Status: Proposed
- Date: {date}
- Deciders: {agent}

## Context

{context}

## Decision

{decision}

## Consequences

_To be documented._
"""


class DocumentationService:
    def __init__(self, ctx: ExecutionContext) -> None:
        self.ctx = ctx
        self.guard = ctx.path_guard

    def read(self, path: str) -> dict:
        self.ctx.authorize("docs.read", path)
        resolved = self.guard.resolve_safe(path)
        if not resolved.is_file():
            raise NotFound(f"doc not found: {path}", detail={"path": path})
        self.guard.check_size(resolved)
        return {"path": path, "content": resolved.read_text(encoding="utf-8", errors="replace")}

    def list_docs(self) -> dict:
        self.ctx.authorize("docs.read", "docs/")
        docs_dir = self.guard.root / "docs"
        if not docs_dir.is_dir():
            return {"count": 0, "docs": []}
        docs = [
            p.relative_to(self.guard.root).as_posix()
            for p in sorted(docs_dir.rglob("*.md"))
        ]
        return {"count": len(docs), "docs": docs}

    def append_section(self, path: str, heading: str, body: str) -> dict:
        """Append a new ``## heading`` section to an existing doc (never overwrites)."""
        self.ctx.authorize("docs.write", path)
        resolved = self.guard.resolve_safe(path)
        if not resolved.is_file():
            raise NotFound(f"doc not found: {path}", detail={"path": path})
        section = f"\n\n## {heading}\n\n{body}\n"
        with resolved.open("a", encoding="utf-8") as fh:
            fh.write(section)
        self.ctx.log_effect("docs.write", target=path, detail={"heading": heading})
        return {"path": path, "appended_heading": heading}

    def _next_adr_number(self, adr_dir: Path) -> int:
        highest = 0
        if adr_dir.is_dir():
            for p in adr_dir.glob("*.md"):
                m = re.match(r"(\d+)", p.name)
                if m:
                    highest = max(highest, int(m.group(1)))
        return highest + 1

    def create_adr(self, title: str, context: str = "", decision: str = "") -> dict:
        self.ctx.authorize("docs.write", f"ADR:{title}")
        if not title.strip():
            raise ValidationError("ADR title must not be empty")
        adr_dir = self.guard.root / _ADR_DIRNAME
        adr_dir.mkdir(parents=True, exist_ok=True)
        num = self._next_adr_number(adr_dir)
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        filename = f"{num:04d}-{slug}.md"
        rel = f"{_ADR_DIRNAME}/{filename}"
        # Route the final write through the guard to honor the allow/deny policy.
        target = self.guard.resolve_safe(rel)
        target.write_text(
            _ADR_TEMPLATE.format(
                num=num, title=title, date=time.strftime("%Y-%m-%d"),
                agent=self.ctx.agent, context=context or "_To be documented._",
                decision=decision or "_To be documented._",
            ),
            encoding="utf-8",
        )
        self.ctx.log_effect("docs.write", target=rel, detail={"adr": num})
        return {"path": rel, "number": num, "title": title}

    def list_adrs(self) -> dict:
        self.ctx.authorize("docs.read", _ADR_DIRNAME)
        adr_dir = self.guard.root / _ADR_DIRNAME
        if not adr_dir.is_dir():
            return {"count": 0, "adrs": []}
        adrs = [p.name for p in sorted(adr_dir.glob("*.md"))]
        return {"count": len(adrs), "adrs": adrs}
