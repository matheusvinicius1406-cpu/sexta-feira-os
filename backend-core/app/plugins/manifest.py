"""
Advanced Plugin System — manifest, sandbox, permissions, lifecycle, hot-reload, dependency resolution.
"""
from __future__ import annotations

import hashlib
import importlib
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.plugins import IPlugin, PluginBase, PluginRegistry, PluginResult

logger = logging.getLogger("sexta-feira.plugins.system")


# ── PluginManifest ────────────────────────────────────────

@dataclass
class PluginManifest:
    """Declarative metadata for a plugin package."""
    plugin_id: str
    display_name: str
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    min_kernel_version: str = "1.0.0"
    entry_point: str = ""
    checksum: str = ""


# ── PluginPermissions ─────────────────────────────────────

class PluginPermissions:
    """Runtime permission check for plugins."""

    GRANTED: set[str] = set()

    @classmethod
    def require(cls, plugin_id: str, *permissions: str) -> None:
        """Require that a plugin has specific permissions.

        Checks for both '{plugin_id}:{perm}' and bare '{perm}' entries.
        """
        for p in permissions:
            prefixed = f"{plugin_id}:{p}"
            if prefixed not in cls.GRANTED and p not in cls.GRANTED:
                raise PermissionError(f"Plugin '{plugin_id}' missing permission: {p}")

    @classmethod
    def grant(cls, plugin_id: str, *permissions: str) -> None:
        """Grant permissions to a plugin."""
        for p in permissions:
            cls.GRANTED.add(f"{plugin_id}:{p}")
            cls.GRANTED.add(p)  # also add bare for global checks

    @classmethod
    def revoke(cls, plugin_id: str, *permissions: str) -> None:
        """Revoke permissions from a plugin."""
        for p in permissions:
            cls.GRANTED.discard(f"{plugin_id}:{p}")


# ── PluginSandbox ─────────────────────────────────────────

class PluginSandbox:
    """Executes plugin code in an isolated environment."""

    ALLOWED_BUILTINS = {"print", "len", "str", "int", "float", "list", "dict", "bool", "range"}

    def __init__(self, plugin_id: str) -> None:
        self._plugin_id = plugin_id
        self._restricted_globals: dict[str, Any] = {
            "__builtins__": {k: __builtins__[k] for k in self.ALLOWED_BUILTINS
                             if k in __builtins__},
        }

    async def execute(self, code: str, context: dict[str, Any] | None = None) -> Any:
        """Execute code in the sandbox."""
        restricted = dict(self._restricted_globals)
        if context:
            restricted.update(context)
        try:
            exec(code, restricted)
            return restricted.get("result")
        except Exception as exc:
            logger.warning("Sandbox execution error in %s: %s", self._plugin_id, exc)
            raise


# ── PluginLifecycle ───────────────────────────────────────

class PluginLifecycle:
    """Manages plugin state transitions."""

    def __init__(self) -> None:
        self._states: dict[str, str] = {}

    def get_state(self, plugin_id: str) -> str:
        return self._states.get(plugin_id, "unloaded")

    def can_transition(self, plugin_id: str, to_state: str) -> bool:
        current = self.get_state(plugin_id)
        valid = {
            "unloaded": ["loaded"],
            "loaded": ["enabled", "unloaded"],
            "enabled": ["running", "loaded"],
            "running": ["enabled", "error"],
            "error": ["loaded", "unloaded"],
        }
        return to_state in valid.get(current, [])

    def transition(self, plugin_id: str, to_state: str) -> None:
        if not self.can_transition(plugin_id, to_state):
            raise RuntimeError(
                f"Cannot transition plugin '{plugin_id}' from "
                f"'{self.get_state(plugin_id)}' to '{to_state}'"
            )
        self._states[plugin_id] = to_state
        logger.info("Plugin '%s' → %s", plugin_id, to_state)


# ── PluginHotReload ───────────────────────────────────────

class PluginHotReload:
    """Watches plugin directories and reloads changed plugins at runtime."""

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry
        self._checksums: dict[str, str] = {}

    def _compute_hash(self, filepath: Path) -> str:
        return hashlib.md5(filepath.read_bytes()).hexdigest()

    def check_and_reload(self, directory: str | Path) -> list[str]:
        """Check for changed files and reload plugins."""
        directory = Path(directory)
        reloaded: list[str] = []
        for py_file in directory.rglob("*.py"):
            current_hash = self._compute_hash(py_file)
            if self._checksums.get(str(py_file)) != current_hash:
                self._checksums[str(py_file)] = current_hash
                try:
                    spec = importlib.util.spec_from_file_location(
                        py_file.stem, py_file,
                    )
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        reloaded.append(py_file.stem)
                        logger.info("Hot-reloaded plugin: %s", py_file.stem)
                except Exception as exc:
                    logger.warning("Hot-reload failed for %s: %s", py_file, exc)
        return reloaded


# ── PluginDependencyResolver ──────────────────────────────

@dataclass
class DependencyGraph:
    """Resolved dependency graph with topological ordering."""

    nodes: list[str] = field(default_factory=list)
    edges: dict[str, list[str]] = field(default_factory=dict)


class PluginDependencyResolver:
    """Resolves plugin dependencies using topological sort."""

    def resolve(self, manifests: list[PluginManifest]) -> list[str]:
        """Return plugin IDs in dependency order (dependencies first)."""
        graph: dict[str, list[str]] = {}
        for m in manifests:
            graph[m.plugin_id] = list(m.dependencies)

        resolved: list[str] = []
        visited: set[str] = set()

        def visit(pid: str, path: set[str]) -> None:
            if pid in path:
                raise RuntimeError(f"Circular dependency detected: {pid}")
            if pid in visited:
                return
            path.add(pid)
            for dep in graph.get(pid, []):
                if dep in graph:
                    visit(dep, path)
            path.remove(pid)
            visited.add(pid)
            resolved.append(pid)

        for pid in graph:
            if pid not in visited:
                visit(pid, set())

        return resolved
