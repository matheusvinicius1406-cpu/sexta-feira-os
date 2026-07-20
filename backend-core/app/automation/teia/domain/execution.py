"""
Execution contracts (data shapes only — no engine).

Phase 1 defines the STABLE shapes that flow through a node so the `Node.execute`
signature is fixed and forward-compatible. The engine that actually calls
`execute` and provides a concrete `ExecutionContext` arrives in Phase 2; this
module deliberately contains no execution logic.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class NodeInput(BaseModel):
    """Data arriving at a node, grouped by input port name -> list of items."""

    items: dict[str, list[Any]] = Field(default_factory=dict)

    def port(self, name: str = "main") -> list[Any]:
        return self.items.get(name, [])


class NodeOutput(BaseModel):
    """Data a node emits, grouped by output port name -> list of items."""

    items: dict[str, list[Any]] = Field(default_factory=dict)

    def port(self, name: str = "main") -> list[Any]:
        """Items emitted on `name` (empty list if the port produced nothing)."""
        return self.items.get(name, [])

    @classmethod
    def single(cls, *values: Any, port: str = "main") -> NodeOutput:
        """Convenience: emit `values` on one port."""
        return cls(items={port: list(values)})


@runtime_checkable
class ExecutionContext(Protocol):
    """What the engine will hand each node at runtime (fleshed out in Phase 2).

    Kept minimal on purpose: the domain only needs the identity of the run.
    Credentials, logger, tracer and hooks are added by the engine later, behind
    this same protocol, without changing node code.
    """

    workflow_id: str
    execution_id: str
