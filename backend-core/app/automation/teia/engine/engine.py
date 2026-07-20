"""
Engine — runs a Workflow in-process, asynchronously, in topological order.

Data flow: each node's `NodeInput` is assembled from the outputs of its
predecessors, port to port, following the workflow connections. A node is
*active* when it is an entry node or at least one predecessor delivered items on
a connected port; otherwise it is *skipped* (this is what makes if/branch real —
the dead branch simply never runs and does not propagate).

Failure policy: fail-fast. The first node to raise is recorded as an error, every
not-yet-run node is marked skipped, and the run's status is `error`. Nodes are
instantiated fresh per run; the engine holds no state between runs.
"""
from __future__ import annotations

import uuid

from app.automation.teia.domain.errors import WorkflowValidationError
from app.automation.teia.domain.execution import NodeInput, NodeOutput
from app.automation.teia.domain.graph import NodeCatalog, Workflow
from app.automation.teia.engine.context import (
    ExecutionResult,
    ExecutionStatus,
    NodeResult,
    NodeStatus,
    RunContext,
)
from app.automation.teia.engine.errors import NodeExecutionError


class Engine:
    """Executes workflows. Stateless: one instance can run many workflows."""

    def __init__(self, catalog: NodeCatalog) -> None:
        self._catalog = catalog

    async def run(
        self,
        workflow: Workflow,
        *,
        execution_id: str | None = None,
        trigger_items: list | None = None,
        context: RunContext | None = None,
    ) -> ExecutionResult:
        """Validate then execute `workflow`. `trigger_items` seed the entry nodes."""
        problems = workflow.validate_graph(self._catalog)
        if problems:
            raise WorkflowValidationError(problems)

        execution_id = execution_id or f"exec_{uuid.uuid4().hex[:12]}"
        ctx = context or RunContext(workflow.id, execution_id)
        # keep ids consistent when a caller passes a bare context
        ctx.workflow_id, ctx.execution_id = workflow.id, execution_id

        order = workflow.topological_order()
        outputs: dict[str, NodeOutput] = {}
        results: dict[str, NodeResult] = {}
        entries = set(workflow.entry_nodes())
        failed = False

        for node_id in order:
            wf_node = workflow.node(node_id)
            assert wf_node is not None  # order is derived from the node set
            node_type = wf_node.type

            if failed:
                results[node_id] = NodeResult(
                    node_id=node_id, node_type=node_type, status=NodeStatus.SKIPPED
                )
                continue

            inputs = self._gather_inputs(workflow, node_id, outputs, entries, trigger_items)
            if inputs is None:
                results[node_id] = NodeResult(
                    node_id=node_id, node_type=node_type, status=NodeStatus.SKIPPED
                )
                continue

            node = self._catalog.get_node(node_type)(wf_node.config)  # type: ignore[misc]
            try:
                output = await node.execute(ctx, inputs)
            except Exception as exc:  # fail-fast: record and skip the rest
                failed = True
                results[node_id] = NodeResult(
                    node_id=node_id, node_type=node_type,
                    status=NodeStatus.ERROR, error=str(exc),
                )
                continue

            outputs[node_id] = output
            results[node_id] = NodeResult(
                node_id=node_id, node_type=node_type,
                status=NodeStatus.SUCCESS, output=output,
            )

        status = ExecutionStatus.ERROR if failed else ExecutionStatus.SUCCESS
        return ExecutionResult(
            execution_id=execution_id, workflow_id=workflow.id,
            status=status, order=order, results=results,
        )

    @staticmethod
    def _gather_inputs(
        workflow: Workflow,
        node_id: str,
        outputs: dict[str, NodeOutput],
        entries: set[str],
        trigger_items: list | None,
    ) -> NodeInput | None:
        """Assemble a node's input, or None if the node should be skipped.

        Entry nodes are always active (seeded with `trigger_items` on "main").
        Non-entry nodes are active only if a predecessor delivered ≥1 item.
        """
        if node_id in entries:
            items = list(trigger_items) if trigger_items else []
            return NodeInput(items={"main": items})

        ports: dict[str, list] = {}
        delivered = False
        for conn in workflow.connections:
            if conn.target != node_id:
                continue
            src_output = outputs.get(conn.source)
            if src_output is None:
                continue  # predecessor was skipped/failed
            payload = src_output.items.get(conn.source_port, [])
            if payload:
                delivered = True
            ports.setdefault(conn.target_port, []).extend(payload)

        if not delivered:
            return None
        return NodeInput(items=ports)


def raise_node_error(node_id: str, node_type: str, cause: Exception) -> NodeExecutionError:
    """Helper for nodes/tests that want the typed error explicitly."""
    return NodeExecutionError(node_id, node_type, cause)
