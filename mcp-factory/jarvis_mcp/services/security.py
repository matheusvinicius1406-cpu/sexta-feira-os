"""Security service: dependency scanning, permission auditing, pre-exec validation.

Pure static analysis over files already inside the guard's allow-list. It never
executes anything; it advises. The ``validate_command`` tool is meant to be
called by other agents *before* they run something, giving a second opinion that
mirrors the CommandGuard rules.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..core.context import ExecutionContext
from ..core.guard import DANGEROUS_COMMAND_TOKENS

# Patterns that look like committed secrets. Deliberately conservative.
_SECRET_PATTERNS = {
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private_key_block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "generic_api_key": re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]"),
}


class SecurityService:
    def __init__(self, ctx: ExecutionContext) -> None:
        self.ctx = ctx
        self.guard = ctx.path_guard

    # --- pre-execution validation -----------------------------------------
    def validate_command(self, command: str) -> dict:
        self.ctx.authorize("security.audit", command)
        lowered = " ".join(command.split()).lower()
        hits = [t for t in DANGEROUS_COMMAND_TOKENS if t in lowered]
        return {
            "command": command,
            "safe": not hits,
            "flagged_tokens": hits,
            "recommendation": "block" if hits else "allow",
        }

    # --- permission audit --------------------------------------------------
    def audit_permissions(self) -> dict:
        self.ctx.authorize("security.audit", "permissions")
        cfg = self.ctx.factory.config
        findings = []
        for name, agent in cfg.agents.items():
            writey = sorted(c for c in agent.capabilities if c.endswith((".write", ".trigger", ".run")))
            if len(writey) > 4:
                findings.append({
                    "agent": name,
                    "issue": "broad write/execute surface",
                    "capabilities": writey,
                })
        return {
            "agents": [
                {"name": n, "role": a.role, "capabilities": sorted(a.capabilities)}
                for n, a in cfg.agents.items()
            ],
            "critical_capabilities": sorted(cfg.critical_capabilities),
            "findings": findings,
        }

    # --- dependency scan ---------------------------------------------------
    def scan_dependencies(self) -> dict:
        self.ctx.authorize("security.scan", "dependencies")
        root = self.guard.root
        results: list[dict] = []

        req = root / "backend-core" / "requirements.txt"
        if req.is_file():
            for line in req.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                pinned = bool(re.search(r"==\s*\d", s))
                results.append({"file": "backend-core/requirements.txt", "package": s, "pinned": pinned})

        cargo = root / "Cargo.toml"
        if cargo.is_file():
            in_deps = False
            for line in cargo.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if s.startswith("["):
                    in_deps = "dependencies" in s
                    continue
                if in_deps and "=" in s:
                    results.append({"file": "Cargo.toml", "package": s, "pinned": '"' in s})

        unpinned = [r for r in results if not r["pinned"]]
        return {
            "total": len(results),
            "unpinned": len(unpinned),
            "unpinned_items": unpinned,
            "dependencies": results,
        }

    # --- secret scan -------------------------------------------------------
    def scan_secrets(self, glob: str = "**/*") -> dict:
        self.ctx.authorize("security.scan", "secrets")
        findings: list[dict] = []
        for file in self.guard.root.glob(glob):
            if not file.is_file():
                continue
            rel = file.relative_to(self.guard.root).as_posix()
            try:
                self.guard.resolve_safe(rel)  # skip anything blocked/sensitive
            except Exception:
                continue
            try:
                if file.stat().st_size > self.guard.max_bytes:
                    continue
                text = file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for name, pat in _SECRET_PATTERNS.items():
                if pat.search(text):
                    findings.append({"file": rel, "kind": name})
        return {"count": len(findings), "findings": findings}
