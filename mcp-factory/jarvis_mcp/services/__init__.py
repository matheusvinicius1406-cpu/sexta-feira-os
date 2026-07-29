"""Service layer: pure business logic behind each MCP server.

Services depend only on :mod:`jarvis_mcp.core` and the stdlib. They contain no
MCP protocol code, which is what makes them straightforward to unit-test.
"""
from .documentation import DocumentationService
from .filesystem import FilesystemService
from .github import GitHubService
from .memory import MemoryService
from .n8n import N8nService
from .security import SecurityService
from .testing import TestingService

__all__ = [
    "FilesystemService",
    "MemoryService",
    "DocumentationService",
    "TestingService",
    "SecurityService",
    "GitHubService",
    "N8nService",
]
