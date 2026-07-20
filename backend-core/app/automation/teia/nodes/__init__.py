"""Built-in node types shipped with the platform (Phase 2)."""
from app.automation.teia.nodes.builtin import (
    HttpRequestNode,
    IfNode,
    NoOpNode,
    SetNode,
    TransformNode,
    builtin_registry,
)

__all__ = [
    "HttpRequestNode",
    "IfNode",
    "NoOpNode",
    "SetNode",
    "TransformNode",
    "builtin_registry",
]
