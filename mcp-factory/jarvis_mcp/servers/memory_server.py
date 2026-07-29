"""Memory MCP server — durable agent memory (decisions/tasks/context/notes)."""
from __future__ import annotations

from ..services.memory import MemoryService
from ._base import load_context, require_fastmcp, tool_result


def build():
    FastMCP = require_fastmcp()
    ctx = load_context()
    svc = MemoryService(ctx, ctx.factory.config.memory_store)
    mcp = FastMCP("jarvis-memory")

    @mcp.tool()
    @tool_result
    def remember(kind: str, title: str, body: str, tags: list[str] | None = None) -> dict:
        """Store a memory. kind: decision | task | context | note."""
        return svc.remember(kind, title, body, tags)

    @mcp.tool()
    @tool_result
    def recall_recent(kind: str, limit: int = 20) -> dict:
        """Return the most recent memories of a kind."""
        return svc.recent(kind, limit)

    @mcp.tool()
    @tool_result
    def search_memory(query: str, kind: str | None = None, limit: int = 20) -> dict:
        """Keyword/tag search across memory (RAG entry point)."""
        return svc.search(query, kind, limit)

    return mcp


if __name__ == "__main__":
    build().run()
