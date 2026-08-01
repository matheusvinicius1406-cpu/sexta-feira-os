"""
Teia engine (Phase 2/3) — the orchestrator, the workers and what they share.

`Orchestrator` drives one workflow run; `WorkerPool` executes the individual
nodes; `RunContext` is what a node is handed. See ADR-0013 and
docs/jarvis/architecture/AUTOMATION_PLATFORM.md.
"""
from app.automation.teia.engine.context import (
    Cancelled,
    CancelToken,
    RunContext,
    RunLimits,
    Services,
    new_execution_id,
)
from app.automation.teia.engine.errors import (
    NodeExecutionError,
    RunLimitExceeded,
    TeiaEngineError,
    UnknownNodeType,
    WorkflowNotFound,
)
from app.automation.teia.engine.expressions import ExpressionError, Resolver
from app.automation.teia.engine.orchestrator import Orchestrator, RunObserver
from app.automation.teia.engine.state import (
    ExecutionResult,
    ExecutionStatus,
    NodeJob,
    NodeResult,
    NodeStatus,
)
from app.automation.teia.engine.workers import Worker, WorkerPool

__all__ = [
    "CancelToken",
    "Cancelled",
    "ExecutionResult",
    "ExecutionStatus",
    "ExpressionError",
    "NodeExecutionError",
    "NodeJob",
    "NodeResult",
    "NodeStatus",
    "Orchestrator",
    "Resolver",
    "RunContext",
    "RunLimitExceeded",
    "RunLimits",
    "RunObserver",
    "Services",
    "TeiaEngineError",
    "UnknownNodeType",
    "Worker",
    "WorkerPool",
    "WorkflowNotFound",
    "new_execution_id",
]
