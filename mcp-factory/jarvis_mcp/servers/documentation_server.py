"""Documentation MCP server — read docs, append sections, manage ADRs."""
from __future__ import annotations

from ..services.documentation import DocumentationService
from ._base import load_context, require_fastmcp, tool_result


def build():
    FastMCP = require_fastmcp()
    ctx = load_context()
    svc = DocumentationService(ctx)
    mcp = FastMCP("jarvis-documentation")

    @mcp.tool()
    @tool_result
    def read_doc(path: str) -> dict:
        """Read a Markdown doc under docs/."""
        return svc.read(path)

    @mcp.tool()
    @tool_result
    def list_docs() -> dict:
        """List all Markdown docs."""
        return svc.list_docs()

    @mcp.tool()
    @tool_result
    def append_doc_section(path: str, heading: str, body: str) -> dict:
        """Append a new ## section to an existing doc (never overwrites)."""
        return svc.append_section(path, heading, body)

    @mcp.tool()
    @tool_result
    def create_adr(title: str, context: str = "", decision: str = "") -> dict:
        """Create the next-numbered Architecture Decision Record."""
        return svc.create_adr(title, context, decision)

    @mcp.tool()
    @tool_result
    def list_adrs() -> dict:
        """List existing ADRs."""
        return svc.list_adrs()

    return mcp


if __name__ == "__main__":
    build().run()
