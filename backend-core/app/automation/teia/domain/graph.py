"""
The workflow graph — a Workflow is a Python object (a DAG of node instances).

`WorkflowNode` = an instance of a node *type* placed in a workflow (id + config).
`Connection`   = a directed edge (source port -> target port).
`TriggerBinding` = a trigger instance that starts a target node.
`Workflow`     = the graph + fluent builders + graph algorithms + validation.

The domain does NOT depend on the Registry implementation: validation accepts a
`NodeCatalog` protocol (dependency inversion), so the graph stays pure Python.
"""
from __future__ import annotations

import uuid
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field, ValidationError

from app.automation.teia.domain.errors import WorkflowCycleError
from app.automation.teia.domain.node import Node
from app.automation.teia.domain.trigger import Trigger


def _short_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@runtime_checkable
class NodeCatalog(Protocol):
    """What validation needs from a registry — not the registry itself (DIP)."""

    def get_node(self, type_id: str) -> type[Node] | None: ...
    def get_trigger(self, type_id: str) -> type[Trigger] | None: ...


class Position(BaseModel):
    """UI hint only; the engine ignores it."""

    x: float = 0.0
    y: float = 0.0


class NodePolicy(BaseModel):
    """How the engine should run a node — retries, timeout, failure handling.

    Separate from the node's own `config` so a node type never has to know about
    scheduling concerns, and so the same policy vocabulary applies to every type.
    """

    max_attempts: int = Field(default=1, ge=1, le=10)
    backoff_seconds: float = Field(default=1.0, ge=0.0, le=300.0)
    timeout_seconds: float = Field(default=60.0, gt=0.0, le=3600.0)
    # "fail" stops the whole run; "continue" marks this branch dead and lets the
    # rest of the graph finish (an `error` output port, when connected, wins over
    # both — the failure becomes data instead of an interruption).
    on_error: Literal["fail", "continue"] = "fail"


class WorkflowNode(BaseModel):
    """An instance of a node type inside a workflow."""

    id: str = Field(default_factory=lambda: _short_id("node"))
    type: str = Field(..., min_length=1)          # registered node type id
    name: str = ""
    config: dict = Field(default_factory=dict)
    policy: NodePolicy = Field(default_factory=NodePolicy)
    position: Position = Field(default_factory=Position)


class Connection(BaseModel):
    """A directed edge between two nodes' ports."""

    source: str
    source_port: str = "main"
    target: str
    target_port: str = "main"


class TriggerBinding(BaseModel):
    """A trigger instance that starts `target` when it fires."""

    id: str = Field(default_factory=lambda: _short_id("trg"))
    type: str = Field(..., min_length=1)          # registered trigger type id
    target: str                                    # WorkflowNode.id to start
    config: dict = Field(default_factory=dict)


def _as_id(node: str | WorkflowNode) -> str:
    return node.id if isinstance(node, WorkflowNode) else node


def has_placeholder(value: object) -> bool:
    """Does this config (or any part of it) still hold a `{{ ... }}` placeholder?

    A placeholder's real type is only known once the engine resolves it against a
    running execution, so a config that contains one cannot be type-checked ahead
    of time — `{{ vars.n }}` is a string here and an int at run time. Static
    validation therefore skips those nodes; the worker validates the resolved
    config instead, which is the moment the answer actually exists.
    """
    if isinstance(value, str):
        return "{{" in value
    if isinstance(value, dict):
        return any(has_placeholder(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(has_placeholder(v) for v in value)
    return False


class Workflow(BaseModel):
    """A serializable automation workflow: nodes + connections + triggers."""

    id: str = Field(default_factory=lambda: _short_id("wf"))
    name: str = Field(..., min_length=1)
    version: str = "1.0.0"
    nodes: list[WorkflowNode] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)
    triggers: list[TriggerBinding] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    # ---------- fluent builders (build a workflow in code) ----------

    def add_node(
        self, type: str, config: dict | None = None, *,
        id: str | None = None, name: str = "", position: Position | None = None,
        policy: NodePolicy | dict | None = None,
    ) -> WorkflowNode:
        node = WorkflowNode(
            id=id or _short_id("node"), type=type, name=name or type,
            config=config or {}, position=position or Position(),
            policy=NodePolicy.model_validate(policy) if policy is not None else NodePolicy(),
        )
        self.nodes.append(node)
        return node

    def connect(
        self, source: str | WorkflowNode, target: str | WorkflowNode, *,
        source_port: str = "main", target_port: str = "main",
    ) -> Workflow:
        self.connections.append(Connection(
            source=_as_id(source), source_port=source_port,
            target=_as_id(target), target_port=target_port,
        ))
        return self

    def add_trigger(
        self, type: str, target: str | WorkflowNode, config: dict | None = None,
        *, id: str | None = None,
    ) -> TriggerBinding:
        binding = TriggerBinding(
            id=id or _short_id("trg"), type=type, target=_as_id(target), config=config or {},
        )
        self.triggers.append(binding)
        return binding

    # ---------- graph access ----------

    def node(self, node_id: str) -> WorkflowNode | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def _node_ids(self) -> set[str]:
        return {n.id for n in self.nodes}

    def successors(self, node_id: str) -> list[str]:
        return [c.target for c in self.connections if c.source == node_id]

    def predecessors(self, node_id: str) -> list[str]:
        return [c.source for c in self.connections if c.target == node_id]

    def entry_nodes(self) -> list[str]:
        """Nodes with no incoming connection (candidates for the graph's start)."""
        targets = {c.target for c in self.connections}
        return [n.id for n in self.nodes if n.id not in targets]

    def topological_order(self) -> list[str]:
        """Kahn's algorithm. Raises WorkflowCycleError if the graph has a cycle."""
        ids = self._node_ids()
        indeg = {i: 0 for i in ids}
        adj: dict[str, list[str]] = {i: [] for i in ids}
        for c in self.connections:
            if c.source in ids and c.target in ids:
                adj[c.source].append(c.target)
                indeg[c.target] += 1
        queue = sorted(i for i, d in indeg.items() if d == 0)
        order: list[str] = []
        while queue:
            current = queue.pop(0)
            order.append(current)
            for nxt in adj[current]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    queue.append(nxt)
            queue.sort()
        if len(order) != len(ids):
            raise WorkflowCycleError("workflow contém ciclo")
        return order

    def has_cycle(self) -> bool:
        try:
            self.topological_order()
            return False
        except WorkflowCycleError:
            return True

    # ---------- validation ----------

    def validate_graph(self, catalog: NodeCatalog | None = None) -> list[str]:
        """Return a list of problems (empty = valid).

        Structural checks always run; type/port/config checks run only when a
        `catalog` is supplied (dependency inversion — the domain never imports
        the Registry).
        """
        problems: list[str] = []
        ids = [n.id for n in self.nodes]
        for dupe in sorted({i for i in ids if ids.count(i) > 1}):
            problems.append(f"nó duplicado: {dupe}")
        idset = set(ids)

        for c in self.connections:
            if c.source not in idset:
                problems.append(f"conexão com origem inexistente: {c.source}")
            if c.target not in idset:
                problems.append(f"conexão com destino inexistente: {c.target}")
        for t in self.triggers:
            if t.target not in idset:
                problems.append(f"gatilho '{t.id}' aponta para nó inexistente: {t.target}")

        if catalog is not None:
            self._validate_against_catalog(catalog, problems)

        if self.has_cycle():
            problems.append("o workflow contém ciclo (a Fase 1 espera um DAG)")
        return problems

    def _validate_against_catalog(self, catalog: NodeCatalog, problems: list[str]) -> None:
        for n in self.nodes:
            node_cls = catalog.get_node(n.type)
            if node_cls is None:
                problems.append(f"tipo de nó desconhecido: '{n.type}' (nó {n.id})")
                continue
            if has_placeholder(n.config):
                continue                    # checked at run time, once resolved
            try:
                node_cls.config_model.model_validate(n.config or {})
            except ValidationError as e:
                problems.append(f"config inválida no nó {n.id}: {e.error_count()} erro(s)")

        for c in self.connections:
            src = self.node(c.source)
            if src:
                sc = catalog.get_node(src.type)
                if sc and c.source_port not in sc.metadata.outputs:
                    problems.append(f"porta de saída inexistente: {src.type}.{c.source_port}")
            tgt = self.node(c.target)
            if tgt:
                tc = catalog.get_node(tgt.type)
                if tc and c.target_port not in tc.metadata.inputs:
                    problems.append(f"porta de entrada inexistente: {tgt.type}.{c.target_port}")

        for t in self.triggers:
            if catalog.get_trigger(t.type) is None:
                problems.append(f"tipo de gatilho desconhecido: '{t.type}' (gatilho {t.id})")

    def is_valid(self, catalog: NodeCatalog | None = None) -> bool:
        return not self.validate_graph(catalog)
