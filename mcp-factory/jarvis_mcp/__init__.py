"""JARVIS AI Development Factory — MCP infrastructure.

A modular set of Model Context Protocol servers that act as the nervous system
between AI agents (Claude Code, Codex, Gemini) and the project. Security-critical
logic lives in :mod:`jarvis_mcp.core` and :mod:`jarvis_mcp.services` (pure stdlib,
fully tested); :mod:`jarvis_mcp.servers` are thin FastMCP adapters.
"""

__version__ = "0.1.0"
