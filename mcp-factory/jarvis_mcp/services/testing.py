"""Testing service: run only allow-listed test commands and report results.

Commands are validated by :class:`~jarvis_mcp.core.guard.CommandGuard` (exact
allow-list + dangerous-token block) before a subprocess is ever spawned. Working
directory is chosen from ``cwd_map`` per area (python/rust/android), never from
caller input, to prevent path escapes.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from ..core.context import ExecutionContext
from ..core.errors import ValidationError


class TestingService:
    def __init__(self, ctx: ExecutionContext) -> None:
        self.ctx = ctx
        self.factory = ctx.factory
        self.policy = self.factory.config.testing

    def areas(self) -> dict:
        return {"areas": sorted(self.policy.cwd_map), "allowed_commands": sorted(self.factory.command_guard.allow)}

    def run(self, command: str, area: str) -> dict:
        self.ctx.authorize("testing.run", command)
        if area not in self.policy.cwd_map:
            raise ValidationError(
                f"unknown testing area '{area}'",
                detail={"areas": sorted(self.policy.cwd_map)},
            )
        argv = self.factory.command_guard.validate(command)  # raises GuardViolation if not allowed
        cwd = (self.factory.config.root / self.policy.cwd_map[area]).resolve()
        if not cwd.is_dir():
            raise ValidationError(f"area directory missing: {cwd}")

        self.ctx.log_effect("testing.run", target=command, detail={"area": area, "cwd": str(cwd)})
        try:
            proc = subprocess.run(
                argv,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.policy.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ValidationError(f"executable not found: {argv[0]}", detail={"command": command}) from exc
        except subprocess.TimeoutExpired:
            return {
                "command": command, "area": area, "passed": False,
                "timed_out": True, "timeout_seconds": self.policy.timeout_seconds,
            }

        return {
            "command": command,
            "area": area,
            "exit_code": proc.returncode,
            "passed": proc.returncode == 0,
            "stdout": _tail(proc.stdout),
            "stderr": _tail(proc.stderr),
        }


def _tail(text: str, limit: int = 8000) -> str:
    """Keep output bounded so a huge test log doesn't blow the MCP response."""
    if len(text) <= limit:
        return text
    return "...[truncated]...\n" + text[-limit:]
