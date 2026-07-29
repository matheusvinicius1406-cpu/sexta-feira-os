"""Core MCP server — the factory's control plane.

Exposes read-only introspection of the factory: which servers and agents exist,
what each agent may do, and the recent audit trail. This is what an agent queries
first to discover the ecosystem.
"""
from __future__ import annotations

from ._base import load_context, require_fastmcp, tool_result


def build():
    FastMCP = require_fastmcp()
    ctx = load_context()
    mcp = FastMCP("jarvis-core")

    @mcp.tool()
    @tool_result
    def list_servers() -> dict:
        """List every MCP server in the factory and the capabilities it needs."""
        return {"servers": ctx.factory.registry.servers()}

    @mcp.tool()
    @tool_result
    def list_agents() -> dict:
        """List registered agents and their granted capabilities."""
        return {"agents": ctx.factory.registry.agents()}

    @mcp.tool()
    @tool_result
    def whoami() -> dict:
        """Report the calling agent identity and its capabilities."""
        agent = ctx.factory.config.agent(ctx.agent)
        return {"agent": agent.name, "role": agent.role, "capabilities": sorted(agent.capabilities)}

    @mcp.tool()
    @tool_result
    def can(capability: str) -> dict:
        """Evaluate whether the calling agent may use a capability (no side effect)."""
        d = ctx.factory.permissions.evaluate(ctx.agent, capability)
        return {"agent": d.agent, "capability": d.capability, "allowed": d.allowed, "reason": d.reason}

    @mcp.tool()
    @tool_result
    def audit_tail(n: int = 50) -> dict:
        """Return the last n audit-log entries."""
        return {"entries": ctx.factory.audit.tail(n)}

    return mcp


if __name__ == "__main__":
    build().run()
