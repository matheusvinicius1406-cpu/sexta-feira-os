"""
Teia engine (Phase 2) — the in-process, asynchronous, topological executor.

The engine takes a domain `Workflow` plus a `NodeCatalog` (the Registry) and
actually runs it: it orders the DAG, moves data along the connections port to
port, executes each node's async `execute`, and returns a structured
`ExecutionResult`. It is pure in-process asyncio — no queue, no DB, no network
of its own (nodes may do I/O). Durability and distribution arrive in later phases.
"""
from app.automation.teia.engine.context import (
    ExecutionResult,
    ExecutionStatus,
    NodeResult,
    NodeStatus,
    RunContext,
)
from app.automation.teia.engine.engine import Engine
from app.automation.teia.engine.errors import NodeExecutionError, TeiaEngineError

__all__ = [
    "Engine",
    "ExecutionResult",
    "ExecutionStatus",
    "NodeExecutionError",
    "NodeResult",
    "NodeStatus",
    "RunContext",
    "TeiaEngineError",
]
