"""
Runtime context and result shapes for an execution.

`RunContext` is the concrete `ExecutionContext` the engine hands each node: it
carries the run identity and an optional httpx transport (so HTTP nodes can be
exercised deterministically offline in tests without changing the protocol).

`NodeResult` / `ExecutionResult` are the structured, serializable record of a
run — one entry per node plus an overall status — so a caller (API, CLI, later a
persistence layer) has a full, inspectable trace.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.automation.teia.domain.execution import NodeOutput


class NodeStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"      # a branch that received no items


class ExecutionStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"


class NodeResult(BaseModel):
    """The outcome of a single node within an execution."""

    node_id: str
    node_type: str
    status: NodeStatus
    output: NodeOutput | None = None
    error: str | None = None


class ExecutionResult(BaseModel):
    """The outcome of a whole workflow run."""

    execution_id: str
    workflow_id: str
    status: ExecutionStatus
    order: list[str] = Field(default_factory=list)
    results: dict[str, NodeResult] = Field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.status is ExecutionStatus.SUCCESS

    def output_of(self, node_id: str) -> NodeOutput | None:
        result = self.results.get(node_id)
        return result.output if result else None


class RunContext:
    """Concrete `ExecutionContext` (satisfies the domain Protocol).

    Deliberately a plain class, not a Pydantic model: it may hold live objects
    (an httpx transport now; a logger, tracer and credential vault later) that
    should never be serialized. Nodes read it structurally through the
    `ExecutionContext` protocol.
    """

    def __init__(
        self,
        workflow_id: str,
        execution_id: str,
        *,
        http_transport: Any | None = None,
        variables: dict[str, Any] | None = None,
    ) -> None:
        self.workflow_id = workflow_id
        self.execution_id = execution_id
        self.http_transport = http_transport      # optional httpx transport for tests
        self.variables: dict[str, Any] = variables or {}
