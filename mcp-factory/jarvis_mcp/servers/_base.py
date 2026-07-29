"""Shared plumbing for the FastMCP server adapters.

Each server module builds a :class:`FastMCP` instance whose tools delegate to a
tested service. ``tool_result`` converts any :class:`FactoryError` into a stable
structured payload instead of leaking a stack trace to the calling agent.
"""
from __future__ import annotations

from typing import Callable

from ..core.context import ExecutionContext, Factory
from ..core.errors import FactoryError


def load_context() -> ExecutionContext:
    """Build the factory from env/config and return the execution context for the
    agent identified by ``JARVIS_AGENT`` (defaults to ``architect``)."""
    return Factory.load().context()


def tool_result(fn: Callable) -> Callable:
    """Decorator: run a tool body and normalize errors to ``{"error": ...}``."""
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except FactoryError as exc:
            return exc.as_dict()
        except Exception as exc:  # defensive: never crash the server on a tool call
            return {"error": "internal_error", "message": str(exc)}

    return wrapper


def require_fastmcp():
    """Import FastMCP lazily with a clear message if the SDK is missing."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise SystemExit(
            "The 'mcp' package is required to run a server.\n"
            "Install it with:  pip install -e mcp-factory\n"
            "(the core/service layer and its tests do not need it)."
        ) from exc
    return FastMCP
