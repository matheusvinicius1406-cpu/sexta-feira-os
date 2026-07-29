"""The factory container and per-request execution context.

``Factory`` wires config → guards → permissions → audit → registry once at
startup. ``ExecutionContext`` is the object every service receives; its
``authorize`` method is the single chokepoint where a capability is checked and
the decision is written to the audit log. If it returns, the action is allowed.
"""
from __future__ import annotations

import os
from pathlib import Path

from .audit import AuditLog
from .config import FactoryConfig, load_config
from .errors import FactoryError
from .guard import CommandGuard, PathGuard
from .permissions import Decision, PermissionModel
from .registry import Registry

DEFAULT_CONFIG_ENV = "JARVIS_FACTORY_CONFIG"
DEFAULT_AGENT_ENV = "JARVIS_AGENT"
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "factory.toml"


class Factory:
    def __init__(self, config: FactoryConfig) -> None:
        self.config = config
        self.path_guard = PathGuard(
            root=config.root,
            allow=config.filesystem.allow,
            deny=config.filesystem.deny,
            max_bytes=config.filesystem.max_read_bytes,
        )
        self.command_guard = CommandGuard(config.testing.allow)
        self.permissions = PermissionModel(config)
        self.audit = AuditLog(config.audit_log)
        self.registry = Registry(config)

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "Factory":
        path = config_path or os.environ.get(DEFAULT_CONFIG_ENV) or _DEFAULT_CONFIG_PATH
        return cls(load_config(path))

    def context(self, agent: str | None = None) -> "ExecutionContext":
        agent = agent or os.environ.get(DEFAULT_AGENT_ENV, "architect")
        # Validate the agent exists up front (raises ConfigError otherwise).
        self.config.agent(agent)
        return ExecutionContext(self, agent)


class ExecutionContext:
    def __init__(self, factory: Factory, agent: str) -> None:
        self.factory = factory
        self.agent = agent

    @property
    def path_guard(self) -> PathGuard:
        return self.factory.path_guard

    @property
    def command_guard(self) -> CommandGuard:
        return self.factory.command_guard

    def authorize(self, capability: str, target: str = "") -> Decision:
        """Check a capability, audit the outcome, and return the Decision.

        Raises PermissionDenied/ApprovalRequired (both audited) when not allowed.
        """
        try:
            decision = self.factory.permissions.authorize(self.agent, capability)
        except FactoryError as exc:
            self.factory.audit.record(
                agent=self.agent, action=capability, target=target,
                decision="deny", detail=exc.as_dict(),
            )
            raise
        self.factory.audit.record(
            agent=self.agent, action=capability, target=target, decision="allow",
        )
        return decision

    def log_effect(self, action: str, target: str = "", detail: dict | None = None) -> None:
        """Record a side effect that already passed authorization (e.g. a write)."""
        self.factory.audit.record(
            agent=self.agent, action=action, target=target, decision="effect", detail=detail,
        )
