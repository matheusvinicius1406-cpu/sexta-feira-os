"""Static registry of MCP servers and the agents known to the factory.

The server registry is the catalogue the ``core`` MCP server exposes so an agent
can discover which servers exist, what capabilities each requires, and how to
launch them. It is intentionally declarative — adding a server means adding one
entry here plus its adapter module.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import FactoryConfig


@dataclass(frozen=True)
class ServerSpec:
    name: str
    module: str  # launched via `python -m jarvis_mcp <name>`
    summary: str
    capabilities: tuple[str, ...]  # capabilities its tools require


SERVERS: tuple[ServerSpec, ...] = (
    ServerSpec("core", "core", "Registry, permissions and audit inspection.",
               ("core.read",)),
    ServerSpec("filesystem", "filesystem", "Whitelisted read/search/inspect of the project.",
               ("fs.read", "fs.search")),
    ServerSpec("github", "github", "Issues, PRs, branches, commits, CI status.",
               ("github.read", "github.write")),
    ServerSpec("memory", "memory", "Agent memory: decisions, tasks, project context (RAG-ready).",
               ("memory.read", "memory.write")),
    ServerSpec("documentation", "documentation", "Read/update docs and manage ADRs.",
               ("docs.read", "docs.write")),
    ServerSpec("testing", "testing", "Run allow-listed test commands and report results.",
               ("testing.run",)),
    ServerSpec("security", "security", "Dependency scan, permission audit, pre-exec validation.",
               ("security.scan", "security.audit")),
)

SERVERS_BY_NAME = {s.name: s for s in SERVERS}


class Registry:
    def __init__(self, config: FactoryConfig) -> None:
        self._config = config

    def servers(self) -> list[dict]:
        return [
            {"name": s.name, "summary": s.summary, "capabilities": list(s.capabilities)}
            for s in SERVERS
        ]

    def agents(self) -> list[dict]:
        return [
            {"name": a.name, "role": a.role, "capabilities": sorted(a.capabilities)}
            for a in self._config.agents.values()
        ]
