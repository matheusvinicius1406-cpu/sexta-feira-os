"""
RunContext — everything a node is handed at runtime.

It satisfies the domain's `ExecutionContext` protocol (workflow_id +
execution_id) and adds what real work needs: the owner, the kernel services, a
fresh DB session per node, the expression roots, the vault, a cancellation flag
and a redaction pass so a secret that flowed through an expression never reaches
the database or the log.

The domain never imports this module — nodes receive it through the protocol, so
the graph stays pure Python (dependency inversion, ADR-0013 §4).
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.automation.teia.engine.expressions import Resolver, clock

logger = logging.getLogger("sexta-feira.teia.run")

REDACTED = "***"


@dataclass
class Services:
    """The kernel capabilities nodes are allowed to reach.

    Every field is optional: the engine runs (and is tested) with none of them,
    and a node that needs one it wasn't given fails with a clear message instead
    of an AttributeError.
    """

    memory: Any = None          # PersistentMemory — the graph second brain
    world: Any = None           # WorldModel — the present + the owner model
    events: Any = None          # EventBus — publish what happened
    scheduler: Any = None       # Scheduler — future intentions
    actions: Any = None         # ActionService — reach a device
    connectors: Any = None      # ConnectorService — owner-curated API calls + vault
    planning: Any = None        # PlanningEngine — goals
    decision: Any = None        # DecisionEngine — choose under constraints
    learning: Any = None        # LearningEngine — lessons
    briefing: Any = None        # BriefingService — the daily report
    journal: Any = None         # JournalService — dated notes
    habits: Any = None          # HabitService
    timetracker: Any = None     # TimeTracker
    brain: Any = None           # LocalBrain — local inference (Ollama)
    runner: Any = None          # WorkflowRunner — for the run_workflow node

    def require(self, name: str) -> Any:
        """Fetch a service or fail with a message the owner can act on."""
        value = getattr(self, name, None)
        if value is None:
            raise RuntimeError(
                f"O serviço '{name}' do kernel não está disponível nesta execução."
            )
        return value


@dataclass
class RunLimits:
    """Guardrails against a runaway automation (ADR-0013 risk R8)."""

    max_parallel: int = 4
    max_nodes: int = 200
    run_timeout_seconds: float = 900.0
    max_depth: int = 3           # how deep run_workflow may nest


class Cancelled(RuntimeError):
    """The execution was cancelled by the owner (or by the run timeout)."""


class CancelToken:
    """The stop signal shared by the orchestrator and its workers.

    Both a flag (checked between nodes) and an awaitable event, so a worker can
    race a node that is already running against it — otherwise "cancel" would
    only take effect after the current node finished, which for a 5-minute HTTP
    node is no cancellation at all.
    """

    def __init__(self) -> None:
        self._cancelled = False
        self.reason = ""
        self._event = asyncio.Event()

    def cancel(self, reason: str = "cancelado") -> None:
        self._cancelled = True
        self.reason = reason
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    async def wait(self) -> None:
        await self._event.wait()

    def raise_if_cancelled(self) -> None:
        if self._cancelled:
            raise Cancelled(self.reason)


@dataclass
class RunContext:
    """What a node sees while it runs."""

    workflow_id: str
    workflow_slug: str
    execution_id: str
    owner_id: str
    services: Services
    session_factory: Callable[[], Session]
    trigger_type: str = "manual"
    trigger_payload: dict = field(default_factory=dict)
    variables: dict = field(default_factory=dict)
    outputs: dict[str, dict[str, list[Any]]] = field(default_factory=dict)
    limits: RunLimits = field(default_factory=RunLimits)
    cancel: CancelToken = field(default_factory=CancelToken)
    depth: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    _secrets_seen: set[str] = field(default_factory=set)
    _log: list[str] = field(default_factory=list)

    # ---------- database ----------

    @contextlib.contextmanager
    def session(self) -> Iterator[Session]:
        """A short-lived session, one per node — workers never share a Session."""
        db = self.session_factory()
        try:
            yield db
        finally:
            db.close()

    # ---------- secrets ----------

    def get_secret(self, name: str) -> str | None:
        """Decrypt an owner secret from the vault (never cached across runs)."""
        connectors = self.services.connectors
        if connectors is None:
            return None
        with self.session() as db:
            return connectors.get_secret_value(db, self.owner_id, name)

    def redact(self, value: Any) -> Any:
        """Replace any secret that flowed through this run with `***`."""
        if not self._secrets_seen:
            return value
        if isinstance(value, str):
            out = value
            for secret in self._secrets_seen:
                if secret:
                    out = out.replace(secret, REDACTED)
            return out
        if isinstance(value, dict):
            return {k: self.redact(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.redact(v) for v in value]
        return value

    # ---------- expressions ----------

    @staticmethod
    def _first_item(ports: dict[str, list[Any]]) -> Any:
        """What a node produced, for `{{ nodes.<id> }}`.

        `main` when it emitted there; otherwise the first non-empty port — which
        is what makes `{{ nodes.x.error }}` readable after a node failed into its
        `error` port, and what a branch node's chosen port answers.
        """
        if ports.get("main"):
            return ports["main"][0]
        for items in ports.values():
            if items:
                return items[0]
        return None

    def expression_roots(self, *, item: Any = None, inputs: list[Any] | None = None) -> dict:
        first_items = {
            node_id: self._first_item(ports) for node_id, ports in self.outputs.items()
        }
        all_items = {
            node_id: (ports.get("main") or next((i for i in ports.values() if i), []))
            for node_id, ports in self.outputs.items()
        }
        return {
            "trigger": self.trigger_payload,
            "vars": self.variables,
            "nodes": first_items,
            "all": all_items,
            "item": item,
            "input": inputs or [],
            "now": clock(),
            "run": {
                "execution_id": self.execution_id,
                "workflow": self.workflow_slug,
                "trigger": self.trigger_type,
                "owner_id": self.owner_id,
            },
        }

    def resolve(
        self, config: Any, *, item: Any = None, inputs: list[Any] | None = None
    ) -> Any:
        """Fill a node's `{{ ... }}` placeholders from this execution's state."""
        resolver = Resolver(
            self.expression_roots(item=item, inputs=inputs),
            secret_getter=self.get_secret,
        )
        resolved = resolver.resolve(config)
        self._secrets_seen |= resolver.used_secrets
        return resolved

    # ---------- logging ----------

    def log(self, message: str) -> None:
        """Record a line on the run's own log (redacted, bounded)."""
        line = f"[{datetime.now(UTC).strftime('%H:%M:%S')}] {self.redact(message)}"
        if len(self._log) < 500:
            self._log.append(line)
        logger.debug("%s %s", self.execution_id[:8], line)

    @property
    def run_log(self) -> list[str]:
        return list(self._log)


def new_execution_id() -> str:
    return str(uuid.uuid4())
