"""FastMCP server adapters. Thin wiring over :mod:`jarvis_mcp.services`.

Each module exposes ``build()`` returning a configured ``FastMCP`` instance.
Importing this package does not import the ``mcp`` SDK; that happens lazily
inside each ``build()`` so the core/service tests run without the dependency.
"""

BUILDERS = {
    "core": "jarvis_mcp.servers.core_server",
    "filesystem": "jarvis_mcp.servers.filesystem_server",
    "github": "jarvis_mcp.servers.github_server",
    "memory": "jarvis_mcp.servers.memory_server",
    "documentation": "jarvis_mcp.servers.documentation_server",
    "testing": "jarvis_mcp.servers.testing_server",
    "security": "jarvis_mcp.servers.security_server",
    "n8n": "jarvis_mcp.servers.n8n_server",
}

__all__ = ["BUILDERS"]
