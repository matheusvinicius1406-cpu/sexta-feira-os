"""
PluginLoader — discovers and loads plugins from designated directories.

Scans plugin folders, imports them dynamically, and registers
them with the PluginRegistry.
"""
from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

from app.plugins import IPlugin, PluginBase, PluginRegistry

logger = logging.getLogger("sexta-feira.plugins.loader")


class PluginLoader:
    """Discovers and loads plugin modules from filesystem paths."""

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def load_from_path(self, path: str | Path) -> list[str]:
        """Scan a directory for plugin modules and load them."""
        path = Path(path)
        if not path.is_dir():
            logger.warning("Plugin path not found: %s", path)
            return []

        loaded: list[str] = []
        for entry in path.iterdir():
            if entry.is_dir() and (entry / "__init__.py").exists():
                try:
                    module = importlib.import_module(entry.name)
                    self._discover_in_module(module, loaded)
                except Exception as exc:
                    logger.warning("Failed to load plugin from %s: %s", entry, exc)
            elif entry.suffix == ".py" and entry.stem != "__init__":
                try:
                    spec = importlib.util.spec_from_file_location(entry.stem, entry)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        self._discover_in_module(module, loaded)
                except Exception as exc:
                    logger.warning("Failed to load plugin %s: %s", entry, exc)

        return loaded

    def _discover_in_module(self, module: Any, loaded: list[str]) -> None:
        """Find all IPlugin subclasses in a module and register them."""
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) and issubclass(obj, IPlugin)
                    and obj not in (IPlugin, PluginBase)):
                try:
                    instance: IPlugin = obj()
                    self._registry.register(instance)
                    loaded.append(instance.plugin_id)
                    logger.info("Loaded plugin: %s (%s)", instance.plugin_id, name)
                except Exception as exc:
                    logger.warning("Failed to instantiate plugin %s: %s", name, exc)
