"""Filesystem service: controlled read, search, and structure inspection.

All access is mediated by :class:`~jarvis_mcp.core.guard.PathGuard`, so nothing
outside the whitelisted directories — and no sensitive file — is ever readable.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..core.context import ExecutionContext
from ..core.errors import NotFound, ValidationError

# Binary/vendored directories we never descend into during search or tree walks.
_SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", "target", "build", ".gradle", ".idea"}


class FilesystemService:
    def __init__(self, ctx: ExecutionContext) -> None:
        self.ctx = ctx
        self.guard = ctx.path_guard

    def read_file(self, path: str) -> dict:
        self.ctx.authorize("fs.read", path)
        resolved = self.guard.resolve_safe(path)
        if not resolved.is_file():
            raise NotFound(f"not a file: {path}", detail={"path": path})
        self.guard.check_size(resolved)
        text = resolved.read_text(encoding="utf-8", errors="replace")
        return {
            "path": resolved.relative_to(self.guard.root).as_posix(),
            "bytes": resolved.stat().st_size,
            "content": text,
        }

    def tree(self, path: str = ".", max_depth: int = 3) -> dict:
        self.ctx.authorize("fs.read", path)
        root = self.guard.resolve_safe(path) if path not in ("", ".") else self.guard.root
        entries: list[str] = []

        def walk(d: Path, depth: int) -> None:
            if depth > max_depth:
                return
            try:
                children = sorted(d.iterdir(), key=lambda p: (p.is_file(), p.name))
            except (PermissionError, FileNotFoundError):
                return
            for child in children:
                if child.name in _SKIP_DIRS:
                    continue
                rel = child.relative_to(self.guard.root).as_posix()
                # Skip anything the guard considers sensitive.
                if self.guard.is_sensitive(rel):
                    continue
                entries.append(rel + ("/" if child.is_dir() else ""))
                if child.is_dir():
                    walk(child, depth + 1)

        walk(root, 1)
        return {"root": root.relative_to(self.guard.root).as_posix() or ".", "entries": entries}

    def search(self, pattern: str, glob: str = "**/*", max_results: int = 200) -> dict:
        self.ctx.authorize("fs.search", pattern)
        if not pattern:
            raise ValidationError("search pattern must not be empty")
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            raise ValidationError(f"invalid regex: {exc}", detail={"pattern": pattern}) from exc

        results: list[dict] = []
        for file in self.guard.root.glob(glob):
            if len(results) >= max_results:
                break
            if not file.is_file():
                continue
            if any(part in _SKIP_DIRS for part in file.parts):
                continue
            rel = file.relative_to(self.guard.root).as_posix()
            # Enforce the allow/deny policy on every candidate.
            try:
                self.guard.resolve_safe(rel)
            except Exception:
                continue
            try:
                if file.stat().st_size > self.guard.max_bytes:
                    continue
                for i, line in enumerate(file.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    if regex.search(line):
                        results.append({"path": rel, "line": i, "text": line.strip()[:300]})
                        if len(results) >= max_results:
                            break
            except OSError:
                continue
        return {"pattern": pattern, "count": len(results), "matches": results}
