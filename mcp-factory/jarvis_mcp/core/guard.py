"""Safety guards: path whitelisting/sensitive-file blocking and command validation.

This is the most security-critical module in the factory. It is pure stdlib and
exhaustively unit-tested. Both the filesystem and testing servers route every
access through here before touching the disk or spawning a process.
"""
from __future__ import annotations

import re
import shlex
from pathlib import Path

from .errors import GuardViolation


def _glob_to_regex(pattern: str) -> re.Pattern:
    """Translate a path glob to an anchored regex with correct ``/`` semantics.

    ``**`` matches across directory separators (and ``**/`` is an optional prefix),
    ``*`` matches within a single path segment, ``?`` a single non-separator char.
    This is stricter and more predictable than :func:`fnmatch.fnmatch`, whose
    ``*`` crosses ``/`` and which mis-handles ``**`` tails.
    """
    out: list[str] = []
    i, n = 0, len(pattern)
    while i < n:
        c = pattern[i]
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")

# Patterns that must never be executed regardless of the testing whitelist.
# Defense in depth: even if a command sneaks past the allow-list matcher, these
# substrings hard-block it.
DANGEROUS_COMMAND_TOKENS = (
    "rm -rf",
    "rm -fr",
    ":(){",          # fork bomb
    "mkfs",
    "dd if=",
    "> /dev",
    "chmod -r 777",
    "git push --force",
    "git push -f",
    "git reset --hard",
    "git clean -fdx",
    "curl",          # no arbitrary network egress from the test runner
    "wget",
    "nc ",
)


class PathGuard:
    """Confines file access to whitelisted directories and blocks sensitive files."""

    def __init__(self, root: Path, allow: tuple[str, ...], deny: tuple[str, ...], max_bytes: int) -> None:
        self.root = root.resolve()
        self.allow = tuple(allow)
        self.deny = tuple(deny)
        self._deny_res = tuple(_glob_to_regex(p) for p in deny)
        self.max_bytes = max_bytes

    def _within_root(self, resolved: Path) -> bool:
        try:
            resolved.relative_to(self.root)
            return True
        except ValueError:
            return False

    def is_sensitive(self, rel_path: str) -> bool:
        """True if the path matches any deny glob. ``**/.env`` catches nested
        envs, ``**/.git/**`` catches anything inside a .git dir, etc."""
        posix = Path(rel_path).as_posix()
        return any(rx.match(posix) for rx in self._deny_res)

    def _in_allowlist(self, rel: Path) -> bool:
        posix = rel.as_posix()
        for allowed in self.allow:
            a = allowed.strip("/")
            if posix == a or posix.startswith(a + "/"):
                return True
        return False

    def resolve_safe(self, user_path: str) -> Path:
        """Resolve ``user_path`` (relative to root) and raise GuardViolation if it
        escapes the root, lands outside the allow-list, or hits a sensitive file."""
        candidate = (self.root / user_path).resolve()
        if not self._within_root(candidate):
            raise GuardViolation(
                "path escapes the project root",
                detail={"path": user_path},
            )
        rel = candidate.relative_to(self.root)
        if not self._in_allowlist(rel):
            raise GuardViolation(
                "path is not inside an allowed directory",
                detail={"path": rel.as_posix(), "allow": list(self.allow)},
            )
        if self.is_sensitive(rel.as_posix()):
            raise GuardViolation(
                "path matches a blocked/sensitive pattern",
                detail={"path": rel.as_posix()},
            )
        return candidate

    def check_size(self, path: Path) -> None:
        if path.is_file() and path.stat().st_size > self.max_bytes:
            raise GuardViolation(
                "file exceeds max_read_bytes",
                detail={"path": str(path), "max_bytes": self.max_bytes},
            )


class CommandGuard:
    """Allows only pre-approved test commands; blocks known-dangerous invocations."""

    def __init__(self, allow: tuple[str, ...]) -> None:
        # Normalize whitespace so " python  -m pytest " matches "python -m pytest".
        self.allow = frozenset(" ".join(cmd.split()) for cmd in allow)

    @staticmethod
    def _normalize(command: str) -> str:
        return " ".join(command.split())

    def validate(self, command: str) -> list[str]:
        """Return the argv for an approved command, or raise GuardViolation."""
        norm = self._normalize(command)
        lowered = norm.lower()
        for token in DANGEROUS_COMMAND_TOKENS:
            if token in lowered:
                raise GuardViolation(
                    "command contains a forbidden token",
                    detail={"command": norm, "token": token},
                )
        # Allow exact matches or an approved command followed by extra args
        # (e.g. "python -m pytest tests/test_x.py").
        for approved in self.allow:
            if norm == approved or norm.startswith(approved + " "):
                try:
                    return shlex.split(norm)
                except ValueError as exc:
                    raise GuardViolation(f"unparseable command: {exc}", detail={"command": norm}) from exc
        raise GuardViolation(
            "command is not on the testing allow-list",
            detail={"command": norm, "allow": sorted(self.allow)},
        )
