"""
Registry — the in-memory catalog of node and trigger *types*.

Maps a type id ("http_request") to the Python class that implements it. It
satisfies the `NodeCatalog` protocol, so it can be passed straight to
`Workflow.validate_graph`. Phase 4 will populate it automatically from plugin
entry points; here it is a plain, explicit registry.
"""
from __future__ import annotations

from app.automation.teia.domain.node import Node
from app.automation.teia.domain.trigger import Trigger


class Registry:
    def __init__(self) -> None:
        self._nodes: dict[str, type[Node]] = {}
        self._triggers: dict[str, type[Trigger]] = {}

    # ---------- registration (usable as a decorator: returns the class) ----------

    def register_node(self, node_cls: type[Node]) -> type[Node]:
        meta = getattr(node_cls, "metadata", None)
        if meta is None:
            raise ValueError(f"{node_cls.__name__} não define `metadata`")
        self._nodes[meta.type] = node_cls
        return node_cls

    def register_trigger(self, trigger_cls: type[Trigger]) -> type[Trigger]:
        meta = getattr(trigger_cls, "metadata", None)
        if meta is None:
            raise ValueError(f"{trigger_cls.__name__} não define `metadata`")
        self._triggers[meta.type] = trigger_cls
        return trigger_cls

    # ---------- lookup (NodeCatalog protocol) ----------

    def get_node(self, type_id: str) -> type[Node] | None:
        return self._nodes.get(type_id)

    def get_trigger(self, type_id: str) -> type[Trigger] | None:
        return self._triggers.get(type_id)

    # ---------- introspection ----------

    def node_types(self) -> list[str]:
        return sorted(self._nodes)

    def trigger_types(self) -> list[str]:
        return sorted(self._triggers)

    def __len__(self) -> int:
        return len(self._nodes) + len(self._triggers)
