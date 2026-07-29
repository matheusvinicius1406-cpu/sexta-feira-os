"""Per-agent capability model and enforcement.

Capabilities are ``<domain>.<action>`` strings (e.g. ``fs.read``, ``github.write``).
Each agent is granted an explicit set in ``factory.toml`` — there is no wildcard
grant. Capabilities listed as ``critical`` are never satisfied by a grant alone;
they always raise ApprovalRequired so a human stays in the loop.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import FactoryConfig
from .errors import ApprovalRequired, PermissionDenied


@dataclass(frozen=True)
class Decision:
    agent: str
    capability: str
    allowed: bool
    reason: str


class PermissionModel:
    def __init__(self, config: FactoryConfig) -> None:
        self._config = config

    def capabilities(self, agent: str) -> frozenset[str]:
        return self._config.agent(agent).capabilities

    def evaluate(self, agent: str, capability: str) -> Decision:
        cfg_agent = self._config.agent(agent)  # raises ConfigError if unknown
        if capability in self._config.critical_capabilities:
            return Decision(agent, capability, False, "critical capability requires human approval")
        if capability in cfg_agent.capabilities:
            return Decision(agent, capability, True, "granted")
        return Decision(agent, capability, False, "capability not granted to agent")

    def authorize(self, agent: str, capability: str) -> Decision:
        """Return an allowing Decision or raise. Callers should audit the result."""
        decision = self.evaluate(agent, capability)
        if decision.allowed:
            return decision
        if capability in self._config.critical_capabilities:
            raise ApprovalRequired(
                f"'{capability}' requires human approval",
                detail={"agent": agent, "capability": capability},
            )
        raise PermissionDenied(
            f"agent '{agent}' lacks capability '{capability}'",
            detail={"agent": agent, "capability": capability, "granted": sorted(self.capabilities(agent))},
        )
