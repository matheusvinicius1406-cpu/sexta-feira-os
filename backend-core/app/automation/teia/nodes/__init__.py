"""
The built-in node library — the toolbox the operários work with.

`register_builtins` fills a Registry with every node type shipped with the
kernel. Plugins add to the same Registry later (Phase 4) without this module
knowing about them.
"""
from app.automation.teia.nodes.ai import AI_NODES
from app.automation.teia.nodes.core import CORE_NODES
from app.automation.teia.nodes.data import DATA_NODES
from app.automation.teia.nodes.files import FILE_NODES
from app.automation.teia.nodes.flow import FLOW_NODES
from app.automation.teia.nodes.http import HTTP_NODES
from app.automation.teia.nodes.kernel import KERNEL_NODES
from app.automation.teia.nodes.system import SYSTEM_NODES
from app.automation.teia.registry import Registry

BUILTIN_NODES = [
    *CORE_NODES,
    *DATA_NODES,
    *FLOW_NODES,
    *HTTP_NODES,
    *AI_NODES,
    *KERNEL_NODES,
    *FILE_NODES,
    *SYSTEM_NODES,
]


def register_builtins(registry: Registry) -> Registry:
    """Register every built-in node type. Idempotent — re-registering replaces."""
    for node_cls in BUILTIN_NODES:
        registry.register_node(node_cls)
    return registry


def catalogue() -> list[dict]:
    """Machine-readable description of every built-in node (for the API and docs)."""
    return [
        {
            "type": node.metadata.type,
            "name": node.metadata.name,
            "category": node.metadata.category,
            "description": node.metadata.description,
            "inputs": node.metadata.inputs,
            "outputs": node.metadata.outputs,
            "config_schema": node.config_model.model_json_schema(),
        }
        for node in BUILTIN_NODES
    ]


__all__ = ["BUILTIN_NODES", "catalogue", "register_builtins"]
