"""
Expressions — how one node reads what the nodes before it produced.

A node's configuration may contain `{{ ... }}` placeholders that are resolved
against the running execution just before the node executes:

    {{ trigger.texto }}            data that started the run
    {{ vars.contador }}            workflow variables (set_vars writes them)
    {{ nodes.buscar.status }}      the first item the node `buscar` emitted
    {{ all.buscar }}               every item that node emitted (a list)
    {{ item.titulo }}              the item currently being processed
    {{ now.date }}                 the clock, pre-formatted
    {{ secret.OPENWEATHER }}       a secret, decrypted from the vault at call time
    {{ vars.nome || "Chefe" }}     a fallback when the path isn't there

This is a PATH LOOKUP, never code: there is no eval(), no attribute access into
Python objects, no imports. A workflow (or a prompt that wrote one) therefore
cannot execute arbitrary code through an expression.

An unknown path is an ERROR, not a silent empty string — an automation that
quietly acts on "" is worse than one that stops and says why. Use `||` when a
value really is optional.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

# {{ path }} or {{ path || default }} — the default may be any JSON literal.
_EXPR = re.compile(r"\{\{\s*(?P<body>.*?)\s*\}\}", re.DOTALL)
_SEGMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_\-]*$")

_MISSING = object()


class ExpressionError(ValueError):
    """A `{{ ... }}` expression could not be resolved."""


def _parse_default(raw: str) -> Any:
    """The right-hand side of `||`: JSON if it parses, otherwise a bare string."""
    text = raw.strip()
    if not text:
        return ""
    try:
        return json.loads(text)
    except ValueError:
        return text


def _walk(root: Any, segments: list[str], full: str) -> Any:
    """Descend a dict/list structure by path segments. Returns _MISSING if absent."""
    current = root
    for seg in segments:
        if isinstance(current, dict):
            if seg not in current:
                return _MISSING
            current = current[seg]
        elif isinstance(current, (list, tuple)):
            if not seg.lstrip("-").isdigit():
                raise ExpressionError(
                    f"'{full}': '{seg}' não é um índice numérico para uma lista"
                )
            index = int(seg)
            if not -len(current) <= index < len(current):
                return _MISSING
            current = current[index]
        else:
            return _MISSING
    return current


def clock(now: datetime | None = None) -> dict[str, Any]:
    """The `now.*` root — the clock as plain, formatted fields."""
    moment = now or datetime.now(UTC)
    return {
        "iso": moment.isoformat(timespec="seconds"),
        "date": moment.strftime("%Y-%m-%d"),
        "time": moment.strftime("%H:%M"),
        "year": moment.year,
        "month": moment.month,
        "day": moment.day,
        "hour": moment.hour,
        "minute": moment.minute,
        "weekday": moment.isoweekday(),          # 1 = Monday .. 7 = Sunday
        "timestamp": int(moment.timestamp()),
    }


class Resolver:
    """Resolves `{{ ... }}` inside a node's configuration.

    `secret_getter` is called lazily and only for `secret.NAME` paths; every value
    it returns is remembered in `used_secrets` so the engine can scrub it out of
    anything it persists or logs.
    """

    def __init__(
        self,
        roots: dict[str, Any],
        secret_getter: Callable[[str], str | None] | None = None,
    ):
        self.roots = roots
        self._secret_getter = secret_getter
        self.used_secrets: set[str] = set()

    # ---------- public API ----------

    def resolve(self, value: Any) -> Any:
        """Resolve every expression inside a str / dict / list, recursively."""
        if isinstance(value, str):
            return self._resolve_string(value)
        if isinstance(value, dict):
            return {k: self.resolve(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.resolve(v) for v in value]
        return value

    # ---------- internals ----------

    def _resolve_string(self, text: str) -> Any:
        matches = list(_EXPR.finditer(text))
        if not matches:
            return text

        # A string that is exactly one expression keeps the value's native type,
        # so `{{ vars.n }}` can feed an int field instead of becoming "3".
        only = matches[0]
        if len(matches) == 1 and only.group(0) == text:
            return self._evaluate(only.group("body"))

        def replace(m: re.Match) -> str:
            resolved = self._evaluate(m.group("body"))
            if isinstance(resolved, str):
                return resolved
            if resolved is None:
                return ""
            if isinstance(resolved, (dict, list)):
                return json.dumps(resolved, ensure_ascii=False)
            return str(resolved)

        return _EXPR.sub(replace, text)

    def _evaluate(self, body: str) -> Any:
        path, _, raw_default = body.partition("||")
        path = path.strip()
        has_default = bool(_)
        default = _parse_default(raw_default) if has_default else _MISSING

        if not path:
            raise ExpressionError("expressão vazia: '{{ }}'")

        segments = [s.strip() for s in path.split(".")]
        for seg in segments:
            if not seg:
                raise ExpressionError(f"'{path}': caminho com segmento vazio")

        root_name, rest = segments[0], segments[1:]
        if not _SEGMENT.match(root_name):
            raise ExpressionError(f"'{path}': raiz inválida '{root_name}'")

        if root_name == "secret":
            return self._secret(rest, path, default)

        if root_name not in self.roots:
            raise ExpressionError(
                f"'{path}': raiz desconhecida '{root_name}'. "
                f"Disponíveis: {', '.join(sorted([*self.roots, 'secret']))}"
            )

        found = _walk(self.roots[root_name], rest, path)
        if found is _MISSING:
            if default is not _MISSING:
                return default
            raise ExpressionError(f"'{path}': não existe nesta execução")
        return found

    def _secret(self, rest: list[str], path: str, default: Any) -> Any:
        if len(rest) != 1:
            raise ExpressionError(f"'{path}': use secret.NOME (um único nome)")
        if self._secret_getter is None:
            raise ExpressionError(f"'{path}': cofre indisponível nesta execução")
        value = self._secret_getter(rest[0])
        if value is None:
            if default is not _MISSING:
                return default
            raise ExpressionError(
                f"'{path}': segredo '{rest[0]}' não está no cofre "
                f"(cadastre em /api/v1/connectors/secrets)"
            )
        self.used_secrets.add(value)
        return value
