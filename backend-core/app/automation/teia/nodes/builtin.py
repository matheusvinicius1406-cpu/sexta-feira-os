"""
Built-in nodes — the minimal, honest, dependency-safe starter set.

  * NoOpNode        — passes input straight through (useful for joins/fan-out).
  * SetNode         — sets/merges fields onto each item (or emits one seed item).
  * TransformNode   — deterministic field pick / rename / drop (no eval, safe).
  * IfNode          — routes each item to the "true" or "false" output port.
  * HttpRequestNode — one async HTTP call via httpx (offline-testable transport).

None of these use `eval`/`exec` or run arbitrary strings: everything is explicit
config validated by Pydantic. Anything richer (code node, AI node) arrives later
as first-class, sandboxed node types — not as a string-eval backdoor here.
"""
from __future__ import annotations

from typing import Any, ClassVar, Literal

import httpx
from pydantic import BaseModel, Field

from app.automation.teia.domain.execution import ExecutionContext, NodeInput, NodeOutput
from app.automation.teia.domain.node import Node, NodeMetadata
from app.automation.teia.registry import Registry


def _as_dict(item: Any) -> dict[str, Any]:
    """Coerce an item to a dict so field operations are well-defined."""
    if isinstance(item, dict):
        return item
    return {"value": item}


# --------------------------------------------------------------------------- #
# NoOp                                                                         #
# --------------------------------------------------------------------------- #
class NoOpNode(Node):
    metadata = NodeMetadata(
        type="noop", name="No-op", category="core",
        description="Passes input through unchanged.",
    )

    async def execute(self, context: ExecutionContext, inputs: NodeInput) -> NodeOutput:
        return NodeOutput(items={"main": list(inputs.port("main"))})


# --------------------------------------------------------------------------- #
# Set                                                                          #
# --------------------------------------------------------------------------- #
class _SetConfig(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)
    keep_input: bool = True


class SetNode(Node):
    metadata = NodeMetadata(
        type="set", name="Set", category="transform",
        description="Assigns fixed fields onto each item (merge or replace).",
    )
    config_model: ClassVar[type[BaseModel]] = _SetConfig

    async def execute(self, context: ExecutionContext, inputs: NodeInput) -> NodeOutput:
        cfg = self.parsed_config()
        assert isinstance(cfg, _SetConfig)
        items = inputs.port("main")
        if not items:
            return NodeOutput(items={"main": [dict(cfg.values)]})
        out = []
        for item in items:
            base = _as_dict(item) if cfg.keep_input else {}
            out.append({**base, **cfg.values})
        return NodeOutput(items={"main": out})


# --------------------------------------------------------------------------- #
# Transform                                                                    #
# --------------------------------------------------------------------------- #
class _TransformConfig(BaseModel):
    pick: list[str] | None = None            # keep only these keys
    rename: dict[str, str] = Field(default_factory=dict)  # old -> new
    drop: list[str] = Field(default_factory=list)


class TransformNode(Node):
    metadata = NodeMetadata(
        type="transform", name="Transform", category="transform",
        description="Deterministic field pick / rename / drop per item.",
    )
    config_model: ClassVar[type[BaseModel]] = _TransformConfig

    async def execute(self, context: ExecutionContext, inputs: NodeInput) -> NodeOutput:
        cfg = self.parsed_config()
        assert isinstance(cfg, _TransformConfig)
        out = []
        for item in inputs.port("main"):
            data = dict(_as_dict(item))
            if cfg.pick is not None:
                data = {k: v for k, v in data.items() if k in cfg.pick}
            for old, new in cfg.rename.items():
                if old in data:
                    data[new] = data.pop(old)
            for key in cfg.drop:
                data.pop(key, None)
            out.append(data)
        return NodeOutput(items={"main": out})


# --------------------------------------------------------------------------- #
# If / branch                                                                  #
# --------------------------------------------------------------------------- #
_Operator = Literal["eq", "ne", "gt", "lt", "gte", "lte", "truthy", "contains"]


class _IfConfig(BaseModel):
    field: str = "value"
    operator: _Operator = "truthy"
    value: Any = None


class IfNode(Node):
    metadata = NodeMetadata(
        type="if", name="If", category="flow",
        description="Routes each item to 'true' or 'false' by a simple condition.",
        outputs=["true", "false"],
    )
    config_model: ClassVar[type[BaseModel]] = _IfConfig

    async def execute(self, context: ExecutionContext, inputs: NodeInput) -> NodeOutput:
        cfg = self.parsed_config()
        assert isinstance(cfg, _IfConfig)
        truthy_items, falsy_items = [], []
        for item in inputs.port("main"):
            (truthy_items if self._matches(cfg, _as_dict(item)) else falsy_items).append(item)
        return NodeOutput(items={"true": truthy_items, "false": falsy_items})

    @staticmethod
    def _matches(cfg: _IfConfig, data: dict[str, Any]) -> bool:
        left = data.get(cfg.field)
        op, right = cfg.operator, cfg.value
        try:
            if op == "truthy":
                return bool(left)
            if op == "eq":
                return left == right
            if op == "ne":
                return left != right
            if op == "gt":
                return left > right
            if op == "lt":
                return left < right
            if op == "gte":
                return left >= right
            if op == "lte":
                return left <= right
            if op == "contains":
                return right in left  # type: ignore[operator]
        except TypeError:
            return False
        return False


# --------------------------------------------------------------------------- #
# HTTP request                                                                 #
# --------------------------------------------------------------------------- #
class _HttpConfig(BaseModel):
    method: str = "GET"
    url: str = Field(..., min_length=1)
    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    json_body: Any | None = None
    timeout: float = 30.0


class HttpRequestNode(Node):
    metadata = NodeMetadata(
        type="http_request", name="HTTP Request", category="io",
        description="Performs one async HTTP request and emits the response.",
    )
    config_model: ClassVar[type[BaseModel]] = _HttpConfig

    async def execute(self, context: ExecutionContext, inputs: NodeInput) -> NodeOutput:
        cfg = self.parsed_config()
        assert isinstance(cfg, _HttpConfig)
        # tests may inject a deterministic transport via the context
        transport = getattr(context, "http_transport", None)
        async with httpx.AsyncClient(transport=transport, timeout=cfg.timeout) as client:
            response = await client.request(
                cfg.method.upper(), cfg.url,
                headers=cfg.headers or None, params=cfg.params or None,
                json=cfg.json_body,
            )
        try:
            body: Any = response.json()
        except ValueError:
            body = response.text
        item = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": body,
        }
        return NodeOutput(items={"main": [item]})


def builtin_registry() -> Registry:
    """A Registry pre-populated with every built-in node type."""
    reg = Registry()
    for node_cls in (NoOpNode, SetNode, TransformNode, IfNode, HttpRequestNode):
        reg.register_node(node_cls)
    return reg
