"""Typed errors for the JARVIS MCP factory.

Every error carries a stable ``code`` so MCP tool responses can be machine-checked
by calling agents without parsing prose.
"""
from __future__ import annotations


class FactoryError(Exception):
    """Base class for all factory errors."""

    code = "factory_error"

    def __init__(self, message: str, *, detail: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}

    def as_dict(self) -> dict:
        return {"error": self.code, "message": self.message, "detail": self.detail}


class ConfigError(FactoryError):
    """The factory configuration is missing or invalid."""

    code = "config_error"


class PermissionDenied(FactoryError):
    """An agent attempted a capability it was not granted."""

    code = "permission_denied"


class GuardViolation(FactoryError):
    """A path or command was blocked by a safety guard."""

    code = "guard_violation"


class ApprovalRequired(FactoryError):
    """A critical action was requested that requires explicit human approval."""

    code = "approval_required"


class NotFound(FactoryError):
    """A requested resource does not exist."""

    code = "not_found"


class ValidationError(FactoryError):
    """Input failed validation."""

    code = "validation_error"
