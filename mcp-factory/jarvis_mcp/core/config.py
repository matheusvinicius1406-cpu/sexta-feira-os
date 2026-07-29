"""Load and validate the factory configuration (``config/factory.toml``).

The config is the single source of truth for: which project directories are
readable, which files are always off-limits, which shell commands the testing
server may run, and what each agent is allowed to do. It is read-only at runtime
and parsed with the stdlib ``tomllib`` — no third-party dependency.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigError


@dataclass(frozen=True)
class FilesystemPolicy:
    allow: tuple[str, ...]
    deny: tuple[str, ...]
    max_read_bytes: int


@dataclass(frozen=True)
class TestingPolicy:
    allow: tuple[str, ...]
    timeout_seconds: int
    cwd_map: dict[str, str]


@dataclass(frozen=True)
class AgentConfig:
    name: str
    role: str
    capabilities: frozenset[str]


@dataclass(frozen=True)
class FactoryConfig:
    name: str
    root: Path
    audit_log: Path
    memory_store: Path
    filesystem: FilesystemPolicy
    testing: TestingPolicy
    agents: dict[str, AgentConfig]
    # Capabilities that are never auto-granted; they always demand human approval.
    critical_capabilities: frozenset[str] = field(default_factory=frozenset)

    def agent(self, name: str) -> AgentConfig:
        try:
            return self.agents[name]
        except KeyError as exc:
            raise ConfigError(
                f"unknown agent '{name}'",
                detail={"known_agents": sorted(self.agents)},
            ) from exc


def _require(table: dict, key: str, ctx: str):
    if key not in table:
        raise ConfigError(f"missing '{key}' in [{ctx}]")
    return table[key]


def load_config(path: str | Path) -> FactoryConfig:
    """Parse and validate ``factory.toml``. Paths are resolved relative to the
    config file's parent so the factory is portable regardless of CWD."""
    path = Path(path).resolve()
    if not path.is_file():
        raise ConfigError(f"config not found: {path}")

    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from exc

    base = path.parent
    factory = _require(raw, "factory", "root")

    root = (base / _require(factory, "root", "factory")).resolve()

    fs = _require(raw, "filesystem", "root")
    filesystem = FilesystemPolicy(
        allow=tuple(fs.get("allow", ())),
        deny=tuple(fs.get("deny", ())),
        max_read_bytes=int(fs.get("max_read_bytes", 1_048_576)),
    )

    tst = raw.get("testing", {})
    testing = TestingPolicy(
        allow=tuple(tst.get("allow", ())),
        timeout_seconds=int(tst.get("timeout_seconds", 900)),
        cwd_map=dict(tst.get("cwd_map", {})),
    )

    agents_raw = _require(raw, "agents", "root")
    if not agents_raw:
        raise ConfigError("at least one agent must be defined under [agents.*]")
    agents: dict[str, AgentConfig] = {}
    for name, spec in agents_raw.items():
        agents[name] = AgentConfig(
            name=name,
            role=str(spec.get("role", "")),
            capabilities=frozenset(spec.get("capabilities", ())),
        )

    return FactoryConfig(
        name=str(factory.get("name", "JARVIS AI Factory")),
        root=root,
        audit_log=(base / factory.get("audit_log", ".jarvis/audit.log")).resolve(),
        memory_store=(base / factory.get("memory_store", ".jarvis/memory")).resolve(),
        filesystem=filesystem,
        testing=testing,
        agents=agents,
        critical_capabilities=frozenset(factory.get("critical_capabilities", ())),
    )
