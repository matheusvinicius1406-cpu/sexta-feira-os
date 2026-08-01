"""
Execution state — the shapes the orchestrator, the workers and the store share.

`NodeJob` is what a worker is handed; `NodeResult` is what it hands back;
`ExecutionResult` is what the caller of a run receives. Plain dataclasses on
purpose: the queue between orchestrator and workers carries data, not behaviour.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.automation.teia.domain.graph import WorkflowNode


class NodeStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class NodeJob:
    """One unit of work for one worker: a node plus the data waiting at its ports."""

    node: WorkflowNode
    inputs: dict[str, list[Any]] = field(default_factory=dict)


@dataclass
class NodeResult:
    """What a worker reports back for one node."""

    node_id: str
    node_type: str
    status: NodeStatus
    outputs: dict[str, list[Any]] = field(default_factory=dict)
    error: str | None = None
    attempts: int = 1
    duration_ms: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @property
    def ok(self) -> bool:
        return self.status is NodeStatus.COMPLETED


@dataclass
class ExecutionResult:
    """The outcome of one workflow run."""

    execution_id: str
    workflow_slug: str
    status: ExecutionStatus
    output: dict[str, list[Any]] = field(default_factory=dict)
    node_results: list[NodeResult] = field(default_factory=list)
    error: str | None = None
    duration_ms: int = 0
    log: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status is ExecutionStatus.COMPLETED

    @property
    def nodes_executed(self) -> int:
        return sum(1 for r in self.node_results if r.status is not NodeStatus.SKIPPED)

    def summary(self) -> str:
        """One line a human (or the brain) can read."""
        failed = [r for r in self.node_results if r.status is NodeStatus.FAILED]
        if self.status is ExecutionStatus.COMPLETED:
            return f"'{self.workflow_slug}' concluída — {self.nodes_executed} nó(s), {self.duration_ms} ms."
        if self.status is ExecutionStatus.CANCELLED:
            return f"'{self.workflow_slug}' cancelada."
        detail = f" no nó '{failed[0].node_id}': {failed[0].error}" if failed else f": {self.error}"
        return f"'{self.workflow_slug}' falhou{detail}"

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "workflow": self.workflow_slug,
            "status": self.status.value,
            "ok": self.ok,
            "duration_ms": self.duration_ms,
            "nodes_executed": self.nodes_executed,
            "error": self.error,
            "output": self.output,
            "summary": self.summary(),
            "nodes": [
                {
                    "node_id": r.node_id,
                    "type": r.node_type,
                    "status": r.status.value,
                    "attempts": r.attempts,
                    "duration_ms": r.duration_ms,
                    "error": r.error,
                }
                for r in self.node_results
            ],
            "log": self.log,
        }
