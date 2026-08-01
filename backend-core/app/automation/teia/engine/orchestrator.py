"""
The Orchestrator — o maestro.

It owns one execution of one workflow: it validates the graph, decides which
nodes are ready, hands them to the worker pool, routes each node's output down
the edges, prunes the branches a condition didn't take, enforces the run's
guardrails, and checkpoints everything as it goes.

How a node becomes ready
------------------------
Every incoming edge of a node is *resolved* exactly once — either it delivered
items, or it turned out to be dead (its source produced nothing on that port, or
its source was itself skipped). When a node's last edge resolves:

  * at least one edge delivered  -> the node runs, with those items at its ports;
  * every edge was dead          -> the node is SKIPPED, and the skip cascades.

That single rule is what makes `if`/`switch` work: the branch not taken emits no
items, so everything downstream of it is skipped rather than run with nothing.

Failure
-------
A failed node is not automatically fatal. In order of precedence:
  1. its `error` output port is connected  -> the failure becomes data and flows on;
  2. `policy.on_error == "continue"`       -> that branch dies, the rest completes;
  3. otherwise                             -> the run is aborted, in-flight nodes
     are drained, and the execution is reported FAILED with the offending node.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from typing import Any, Protocol

from app.automation.teia.domain.errors import WorkflowValidationError
from app.automation.teia.domain.graph import Workflow, WorkflowNode
from app.automation.teia.engine.context import Cancelled, RunContext
from app.automation.teia.engine.errors import RunLimitExceeded
from app.automation.teia.engine.state import (
    ExecutionResult,
    ExecutionStatus,
    NodeJob,
    NodeResult,
    NodeStatus,
)
from app.automation.teia.engine.workers import WorkerPool
from app.automation.teia.registry import Registry

logger = logging.getLogger("sexta-feira.teia.orchestrator")


class RunObserver(Protocol):
    """Where a run reports its progress (the store implements this)."""

    async def node_finished(self, context: RunContext, result: NodeResult) -> None: ...
    async def execution_finished(self, context: RunContext, result: ExecutionResult) -> None: ...


class Orchestrator:
    def __init__(self, registry: Registry, observer: RunObserver | None = None):
        self.registry = registry
        self.observer = observer

    async def run(self, workflow: Workflow, context: RunContext) -> ExecutionResult:
        """Execute a workflow to completion. Never raises for a workflow's own failure."""
        problems = workflow.validate_graph(self.registry)
        if problems:
            raise WorkflowValidationError(problems)

        started = time.perf_counter()
        run = _Run(workflow, context, self.registry, self.observer)
        try:
            await asyncio.wait_for(run.drive(), timeout=context.limits.run_timeout_seconds)
        except TimeoutError:
            context.cancel.cancel("tempo total da execução esgotado")
            run.abort(
                f"a execução passou de {context.limits.run_timeout_seconds:g}s e foi interrompida"
            )
        except Cancelled as e:
            run.cancelled(str(e))
        except RunLimitExceeded as e:
            run.abort(str(e))

        result = run.finish(int((time.perf_counter() - started) * 1000))
        if self.observer:
            try:
                await self.observer.execution_finished(context, result)
            except Exception as e:  # noqa: BLE001 — bookkeeping never breaks a run
                logger.warning("could not persist execution %s: %s", context.execution_id, e)
        return result


class _Run:
    """The mutable state of a single execution (one instance per run)."""

    def __init__(
        self,
        workflow: Workflow,
        context: RunContext,
        registry: Registry,
        observer: RunObserver | None,
    ):
        self.wf = workflow
        self.ctx = context
        self.registry = registry
        self.observer = observer

        self.nodes: dict[str, WorkflowNode] = {n.id: n for n in workflow.nodes}
        self.outgoing = defaultdict(list)
        for c in workflow.connections:
            self.outgoing[c.source].append(c)

        self.pending_edges: dict[str, int] = {n.id: 0 for n in workflow.nodes}
        for c in workflow.connections:
            if c.target in self.pending_edges:
                self.pending_edges[c.target] += 1

        self.received: dict[str, dict[str, list[Any]]] = defaultdict(dict)
        self.has_live_input: dict[str, bool] = {n.id: False for n in workflow.nodes}
        self.status: dict[str, NodeStatus] = {n.id: NodeStatus.PENDING for n in workflow.nodes}

        self.ready: deque[str] = deque(
            sorted(nid for nid, count in self.pending_edges.items() if count == 0)
        )
        self.results: list[NodeResult] = []
        self.dispatched = 0
        self.aborted = False
        self.error: str | None = None
        self.status_final: ExecutionStatus | None = None

    # ---------- the loop ----------

    async def drive(self) -> None:
        if not self.nodes:
            return
        max_parallel = max(1, min(self.ctx.limits.max_parallel, len(self.nodes)))
        in_flight = 0

        async with WorkerPool(self.registry, self.ctx, max_parallel) as pool:
            while self.ready or in_flight:
                while self.ready:
                    node_id = self.ready.popleft()
                    self.dispatched += 1
                    if self.dispatched > self.ctx.limits.max_nodes:
                        raise RunLimitExceeded(
                            f"a execução passou do limite de {self.ctx.limits.max_nodes} nós "
                            f"(possível laço infinito)"
                        )
                    node = self.nodes[node_id]
                    self.status[node_id] = NodeStatus.RUNNING
                    self.ctx.log(f"executando '{node.name or node.id}' ({node.type})")
                    await pool.submit(NodeJob(node=node, inputs=dict(self.received.get(node_id, {}))))
                    in_flight += 1

                result = await pool.next_result()
                in_flight -= 1
                await self._apply(result)

    # ---------- routing ----------

    async def _apply(self, result: NodeResult) -> None:
        self.status[result.node_id] = result.status
        self.results.append(result)
        await self._checkpoint(result)

        if self.aborted:
            return                      # draining after a fatal failure — route nothing

        if result.ok:
            self.ctx.outputs[result.node_id] = result.outputs
            self._propagate(result.node_id, result.outputs)
            return

        node = self.nodes[result.node_id]
        error_item = {
            "error": result.error,
            "node_id": result.node_id,
            "node_type": result.node_type,
            "attempts": result.attempts,
        }
        wired_to_error = any(
            c.source_port == "error" for c in self.outgoing.get(result.node_id, [])
        )
        if wired_to_error:
            self.ctx.log(f"nó '{result.node_id}' falhou; seguindo pela porta 'error'")
            self.ctx.outputs[result.node_id] = {"error": [error_item]}
            self._propagate(result.node_id, {"error": [error_item]})
            return

        if self.ctx.cancel.cancelled and not self.aborted:
            # The node didn't break — it was interrupted. Report it as such.
            self.cancelled(self.ctx.cancel.reason)
            return

        if node.policy.on_error == "continue":
            self.ctx.log(f"nó '{result.node_id}' falhou; ramo encerrado (on_error=continue)")
            self._propagate(result.node_id, {})
            return

        self.abort(f"nó '{result.node_id}' ({result.node_type}) falhou: {result.error}")

    def _propagate(self, node_id: str, outputs: dict[str, list[Any]]) -> None:
        """Resolve every outgoing edge, then release or skip the nodes downstream."""
        pending_skips: deque[str] = deque()

        for connection in self.outgoing.get(node_id, []):
            target = connection.target
            if target not in self.pending_edges:
                continue
            items = outputs.get(connection.source_port) or []
            if items:
                port = self.received[target].setdefault(connection.target_port, [])
                port.extend(items)
                self.has_live_input[target] = True
            self.pending_edges[target] -= 1
            if self.pending_edges[target] == 0:
                if self.has_live_input[target]:
                    self.ready.append(target)
                else:
                    pending_skips.append(target)

        # Skipping cascades: everything only reachable through a dead branch dies
        # with it. Iterative, so a long chain can't blow the Python stack.
        while pending_skips:
            skipped_id = pending_skips.popleft()
            self._mark_skipped(skipped_id)
            for connection in self.outgoing.get(skipped_id, []):
                target = connection.target
                if target not in self.pending_edges:
                    continue
                self.pending_edges[target] -= 1
                if self.pending_edges[target] == 0:
                    if self.has_live_input[target]:
                        self.ready.append(target)
                    else:
                        pending_skips.append(target)

    def _mark_skipped(self, node_id: str) -> None:
        node = self.nodes[node_id]
        self.status[node_id] = NodeStatus.SKIPPED
        self.results.append(
            NodeResult(node_id=node_id, node_type=node.type, status=NodeStatus.SKIPPED)
        )

    async def _checkpoint(self, result: NodeResult) -> None:
        if not self.observer:
            return
        try:
            await self.observer.node_finished(self.ctx, result)
        except Exception as e:  # noqa: BLE001 — a failed checkpoint must not stop the run
            logger.warning("could not checkpoint node %s: %s", result.node_id, e)

    # ---------- termination ----------

    def abort(self, error: str) -> None:
        """Stop routing and let the in-flight nodes drain, then report FAILED."""
        if self.aborted:
            return
        self.aborted = True
        self.error = error
        self.status_final = ExecutionStatus.FAILED
        self.ready.clear()
        self.ctx.cancel.cancel(error)
        self.ctx.log(f"execução abortada: {error}")

    def cancelled(self, reason: str) -> None:
        self.aborted = True
        self.error = reason or "cancelado"
        self.status_final = ExecutionStatus.CANCELLED
        self.ready.clear()

    def finish(self, duration_ms: int) -> ExecutionResult:
        status = self.status_final or ExecutionStatus.COMPLETED
        return ExecutionResult(
            execution_id=self.ctx.execution_id,
            workflow_slug=self.ctx.workflow_slug,
            status=status,
            output=self._terminal_output() if status is ExecutionStatus.COMPLETED else {},
            node_results=self.results,
            error=self.error,
            duration_ms=duration_ms,
            log=self.ctx.run_log,
        )

    def _terminal_output(self) -> dict[str, list[Any]]:
        """What the graph produced: the `main` items of every leaf that ran."""
        return {
            node_id: self.ctx.outputs[node_id].get("main", [])
            for node_id in self.nodes
            if not self.outgoing.get(node_id)
            and self.status.get(node_id) is NodeStatus.COMPLETED
            and self.ctx.outputs.get(node_id, {}).get("main")
        }
