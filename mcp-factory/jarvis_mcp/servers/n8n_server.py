"""n8n MCP server — trigger/inspect automations (future-facing, guarded)."""
from __future__ import annotations

from ..services.n8n import N8nService
from ._base import load_context, require_fastmcp, tool_result


def build():
    FastMCP = require_fastmcp()
    ctx = load_context()
    svc = N8nService(ctx)
    mcp = FastMCP("jarvis-n8n")

    @mcp.tool()
    @tool_result
    def list_workflows() -> dict:
        """List n8n workflows (requires N8N_BASE_URL/N8N_API_KEY)."""
        return svc.list_workflows()

    @mcp.tool()
    @tool_result
    def trigger_webhook(webhook_path: str, payload: dict | None = None) -> dict:
        """Fire an n8n webhook (requires n8n.trigger capability)."""
        return svc.trigger_webhook(webhook_path, payload)

    return mcp


if __name__ == "__main__":
    build().run()
