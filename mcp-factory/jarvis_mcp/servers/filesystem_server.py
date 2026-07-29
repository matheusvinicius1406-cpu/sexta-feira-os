"""Filesystem MCP server — whitelisted read/search/inspect."""
from __future__ import annotations

from ..services.filesystem import FilesystemService
from ._base import load_context, require_fastmcp, tool_result


def build():
    FastMCP = require_fastmcp()
    ctx = load_context()
    svc = FilesystemService(ctx)
    mcp = FastMCP("jarvis-filesystem")

    @mcp.tool()
    @tool_result
    def read_file(path: str) -> dict:
        """Read a UTF-8 text file inside an allowed directory."""
        return svc.read_file(path)

    @mcp.tool()
    @tool_result
    def list_tree(path: str = ".", max_depth: int = 3) -> dict:
        """List the project structure under an allowed directory."""
        return svc.tree(path, max_depth)

    @mcp.tool()
    @tool_result
    def search_code(pattern: str, glob: str = "**/*", max_results: int = 200) -> dict:
        """Regex-search file contents across the allowed tree."""
        return svc.search(pattern, glob, max_results)

    return mcp


if __name__ == "__main__":
    build().run()
