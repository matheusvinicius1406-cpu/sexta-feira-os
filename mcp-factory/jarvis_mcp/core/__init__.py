"""Core layer: config, guards, permissions, audit, registry, execution context.

Everything in this package is pure stdlib and unit-tested without the ``mcp``
SDK installed. The MCP server adapters (``jarvis_mcp.servers``) depend on this
layer, never the other way around.
"""
from .context import ExecutionContext, Factory
from .errors import (
    ApprovalRequired,
    ConfigError,
    FactoryError,
    GuardViolation,
    NotFound,
    PermissionDenied,
    ValidationError,
)

__all__ = [
    "Factory",
    "ExecutionContext",
    "FactoryError",
    "ConfigError",
    "PermissionDenied",
    "GuardViolation",
    "ApprovalRequired",
    "NotFound",
    "ValidationError",
]
