"""Security MCP server — dependency scan, permission audit, pre-exec validation."""
from __future__ import annotations

from ..services.security import SecurityService
from ._base import load_context, require_fastmcp, tool_result


def build():
    FastMCP = require_fastmcp()
    ctx = load_context()
    svc = SecurityService(ctx)
    mcp = FastMCP("jarvis-security")

    @mcp.tool()
    @tool_result
    def validate_command(command: str) -> dict:
        """Advise whether a shell command is safe to run (second opinion)."""
        return svc.validate_command(command)

    @mcp.tool()
    @tool_result
    def audit_permissions() -> dict:
        """Report agent capability grants and flag over-privilege."""
        return svc.audit_permissions()

    @mcp.tool()
    @tool_result
    def scan_dependencies() -> dict:
        """Scan requirements.txt / Cargo.toml for unpinned dependencies."""
        return svc.scan_dependencies()

    @mcp.tool()
    @tool_result
    def scan_secrets(glob: str = "**/*") -> dict:
        """Scan the allowed tree for committed secret-looking strings."""
        return svc.scan_secrets(glob)

    return mcp


if __name__ == "__main__":
    build().run()
