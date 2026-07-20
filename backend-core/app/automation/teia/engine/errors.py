"""Engine-layer errors (distinct from pure-domain errors)."""
from __future__ import annotations

from app.automation.teia.domain.errors import TeiaDomainError


class TeiaEngineError(TeiaDomainError):
    """Base class for runtime/execution errors raised by the engine."""


class NodeExecutionError(TeiaEngineError):
    """A node raised while executing. Carries the node id and original cause."""

    def __init__(self, node_id: str, node_type: str, cause: Exception):
        self.node_id = node_id
        self.node_type = node_type
        self.cause = cause
        super().__init__(f"nó '{node_id}' ({node_type}) falhou: {cause}")
