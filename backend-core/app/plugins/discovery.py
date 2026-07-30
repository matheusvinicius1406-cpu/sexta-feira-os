"""
PluginDiscovery — runtime discovery of plugin capabilities.

Enables the Kernel and AI agents to discover what plugins exist
and what actions they support, without hardcoding references.
"""
from __future__ import annotations

import logging
from typing import Any

from app.plugins import IPlugin, PluginRegistry, PluginContext, PluginResult

logger = logging.getLogger("sexta-feira.plugins.discovery")


class PluginDiscovery:
    """Runtime discovery of plugin capabilities."""

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def list_capabilities(self) -> list[dict[str, Any]]:
        """Return a manifest of all registered plugins and their capabilities."""
        return [
            {
                "plugin_id": p.plugin_id,
                "display_name": p.display_name,
                "type": p.__class__.__name__,
            }
            for p in self._registry.all.values()
        ]

    def find(self, capability: str) -> list[IPlugin]:
        """Find plugins that match a capability keyword."""
        cap_lower = capability.lower()
        return [
            p for p in self._registry.all.values()
            if cap_lower in p.plugin_id.lower()
            or cap_lower in p.display_name.lower()
        ]

    async def execute(self, plugin_id: str, action: str,
                      parameters: dict[str, Any] | None = None) -> PluginResult | None:
        """Execute a plugin action by ID."""
        plugin = self._registry.get(plugin_id)
        if not plugin:
            return None
        ctx = PluginContext(action=action, parameters=parameters or {})
        return await plugin.execute(ctx)
