"""
Plugin system for Sexta-Feira OS Kernel.

Each plugin extends Kernel capabilities (WhatsApp, calendar, home,
browser, finance, etc.). Plugins register themselves and are discovered
by the PluginRegistry.

Every Python plugin has an exact C# counterpart in
apps/maui/CognitiveHUD/Services/IPlugin.cs
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# ── Contracts (mirror C# IPlugin.cs exactly) ──────────────


@dataclass
class PluginContext:
    """Context provided when executing a plugin action.

    Mirrors C# record PluginContext(string Action, Dictionary<string, object> Parameters).
    """
    action: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginResult:
    """Result from a plugin execution.

    Mirrors C# record PluginResult(bool Success, string? Message, Dictionary? Data).
    """
    success: bool
    message: str | None = None
    data: dict[str, Any] | None = None


@dataclass
class PluginStatus:
    """Plugin health status.

    Mirrors C# record PluginStatus(bool IsLoaded, string? Version, string? Error).
    """
    is_loaded: bool
    version: str | None = None
    error: str | None = None


class IPlugin(ABC):
    """Contract that every plugin must implement.

    Mirrors C# IPlugin interface exactly.
    """

    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """Unique plugin identifier (e.g. 'calendar', 'whatsapp')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable display name."""
        ...

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the plugin (load configs, connect external services)."""
        ...

    @abstractmethod
    async def execute(self, context: PluginContext) -> PluginResult:
        """Execute the plugin's primary action."""
        ...

    @abstractmethod
    async def get_status(self) -> PluginStatus:
        """Get current plugin health status."""
        ...


# ── Base class with sensible defaults ─────────────────────


class PluginBase(IPlugin):
    """Convenience base class that plugins can extend."""

    @property
    def plugin_id(self) -> str:
        return self.__class__.__name__.lower()

    @property
    def display_name(self) -> str:
        return self.__class__.__name__.replace("_", " ").title()

    async def initialize(self) -> None:
        pass

    async def get_status(self) -> PluginStatus:
        return PluginStatus(is_loaded=True, version="1.0.0")


# ── Registry ──────────────────────────────────────────────


class PluginRegistry:
    """Central registry for discovering and managing plugins.

    Maintained by the Kernel. Adapters and gRPC services query it
    to discover available capabilities at runtime.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, IPlugin] = {}

    def register(self, plugin: IPlugin) -> None:
        """Register a plugin by its plugin_id."""
        pid = plugin.plugin_id
        if pid in self._plugins:
            raise ValueError(f"Plugin '{pid}' is already registered")
        self._plugins[pid] = plugin

    def get(self, plugin_id: str) -> IPlugin | None:
        """Retrieve a registered plugin by ID."""
        return self._plugins.get(plugin_id)

    @property
    def all(self) -> dict[str, IPlugin]:
        """All registered plugins (read-only snapshot)."""
        return dict(self._plugins)

    @property
    def count(self) -> int:
        return len(self._plugins)

    async def initialize_all(self) -> None:
        """Initialize every registered plugin."""
        for pid, plugin in self._plugins.items():
            try:
                await plugin.initialize()
            except Exception as exc:
                raise RuntimeError(f"Plugin '{pid}' failed to initialize: {exc}") from exc
