"""Engine errors — distinct from the domain errors so callers can tell them apart."""
from __future__ import annotations

from app.automation.teia.domain.errors import TeiaDomainError


class TeiaEngineError(TeiaDomainError):
    """Base class for anything that goes wrong while RUNNING a workflow."""


class UnknownNodeType(TeiaEngineError):
    """The graph references a node type that no plugin registered."""


class NodeExecutionError(TeiaEngineError):
    """A node broke its contract (wrong return type, impossible state)."""


class WorkflowNotFound(TeiaEngineError):
    """No workflow with that slug/id belongs to this owner."""


class RunLimitExceeded(TeiaEngineError):
    """A guardrail stopped the run: too many nodes, too deep, or out of time."""
