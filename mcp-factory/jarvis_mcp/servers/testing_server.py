"""Testing MCP server — run allow-listed test commands and report results."""
from __future__ import annotations

from ..services.testing import TestingService
from ._base import load_context, require_fastmcp, tool_result


def build():
    FastMCP = require_fastmcp()
    ctx = load_context()
    svc = TestingService(ctx)
    mcp = FastMCP("jarvis-testing")

    @mcp.tool()
    @tool_result
    def list_test_areas() -> dict:
        """List runnable areas and the allow-listed commands."""
        return svc.areas()

    @mcp.tool()
    @tool_result
    def run_tests(command: str, area: str) -> dict:
        """Run an allow-listed test command in an area (python|rust|android)."""
        return svc.run(command, area)

    return mcp


if __name__ == "__main__":
    build().run()
