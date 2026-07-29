"""GitHub MCP server — issues, PRs, branches, commits, CI. Merge is human-only."""
from __future__ import annotations

from ..services.github import GitHubService
from ._base import load_context, require_fastmcp, tool_result


def build():
    FastMCP = require_fastmcp()
    ctx = load_context()
    svc = GitHubService(ctx)
    mcp = FastMCP("jarvis-github")

    @mcp.tool()
    @tool_result
    def list_issues(state: str = "open", limit: int = 20) -> dict:
        """List issues/PRs in the repo."""
        return svc.list_issues(state, limit)

    @mcp.tool()
    @tool_result
    def get_pull_request(number: int) -> dict:
        """Get PR metadata (state, mergeability, diff size)."""
        return svc.get_pull_request(number)

    @mcp.tool()
    @tool_result
    def ci_status(ref: str) -> dict:
        """Get CI check-run status for a commit/branch ref."""
        return svc.ci_status(ref)

    @mcp.tool()
    @tool_result
    def create_issue(title: str, body: str = "", labels: list[str] | None = None) -> dict:
        """Create a new issue (requires github.write)."""
        return svc.create_issue(title, body, labels)

    @mcp.tool()
    @tool_result
    def open_pull_request(title: str, head: str, base: str = "main", body: str = "") -> dict:
        """Open a PR from head into base (requires github.write). Does NOT merge."""
        return svc.create_pull_request(title, head, base, body)

    @mcp.tool()
    @tool_result
    def merge_pull_request(number: int) -> dict:
        """Always refused — merging requires human approval."""
        return svc.merge_pull_request(number)

    return mcp


if __name__ == "__main__":
    build().run()
