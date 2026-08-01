"""
TeiaService — the application layer, and the only thing the rest of the kernel
needs to know about automations.

It owns the registry (node + trigger types), the store, the orchestrator, the
trigger manager and the background tick. Everything above it — the REST API, the
CLI, the brain's ToolKit, the gRPC adapter — goes through this one object.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.automation.teia.domain.errors import WorkflowValidationError
from app.automation.teia.domain.graph import Workflow
from app.automation.teia.engine.context import (
    RunContext,
    RunLimits,
    Services,
    new_execution_id,
)
from app.automation.teia.engine.errors import WorkflowNotFound
from app.automation.teia.engine.orchestrator import Orchestrator
from app.automation.teia.engine.state import ExecutionResult, ExecutionStatus
from app.automation.teia.nodes import catalogue, register_builtins
from app.automation.teia.registry import Registry
from app.automation.teia.store import ExecutionStore, WorkflowStore, slugify
from app.automation.teia.triggers import (
    TriggerManager,
    register_builtin_triggers,
    trigger_catalogue,
)
from app.core.config import settings
from app.db.database import SessionLocal
from app.models.models import AutomationWorkflow

logger = logging.getLogger("sexta-feira.teia")


def build_registry() -> Registry:
    """A Registry with every built-in node and trigger type registered."""
    registry = Registry()
    register_builtins(registry)
    register_builtin_triggers(registry)
    return registry


class TeiaService:
    """The kernel's hands — now written in Python, running in this process."""

    def __init__(
        self,
        services: Services | None = None,
        *,
        session_factory: Callable[[], Session] = SessionLocal,
        registry: Registry | None = None,
    ):
        self.services = services or Services()
        self.session_factory = session_factory
        self.registry = registry or build_registry()
        self.store = WorkflowStore()
        self.executions = ExecutionStore(session_factory)
        self.orchestrator = Orchestrator(self.registry, observer=self.executions)
        self.triggers = TriggerManager(
            self.store, self.executions, self, session_factory
        )
        # `sub_automacao` calls back into this service to run another workflow.
        self.services.runner = self
        self._running: dict[str, RunContext] = {}
        self._tick_task: asyncio.Task | None = None

    # ================================================================ lifecycle

    def start(self) -> None:
        """Arm the triggers and start the clock."""
        self.triggers.reload()
        if settings.automations_enabled and self._tick_task is None:
            with contextlib.suppress(RuntimeError):     # no loop yet (sync context)
                self._tick_task = asyncio.get_running_loop().create_task(self._tick_loop())
                logger.info(
                    "Teia ativa — tick a cada %ss, %d gatilho(s)",
                    settings.teia_tick_seconds, len(self.triggers.armed),
                )

    async def stop(self) -> None:
        if self._tick_task:
            self._tick_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._tick_task
            self._tick_task = None
        for context in list(self._running.values()):
            context.cancel.cancel("kernel encerrando")
        await self.triggers.stop()

    async def _tick_loop(self) -> None:
        """Sleep first, so booting the kernel never fires a schedule by surprise."""
        while True:
            try:
                await asyncio.sleep(settings.teia_tick_seconds)
                await self.triggers.tick()
            except asyncio.CancelledError:
                break
            except Exception as e:  # noqa: BLE001 — the clock must survive a bad tick
                logger.warning("tick da Teia falhou: %s", e)

    # ================================================================ running

    async def run_slug(
        self,
        owner_id: str,
        slug: str,
        payload: dict | None = None,
        *,
        trigger_type: str = "manual",
        depth: int = 0,
    ) -> ExecutionResult:
        """Run a stored automation by its slug."""
        db = self.session_factory()
        try:
            row = self.store.get(db, owner_id, slug)
            if not row:
                available = ", ".join(w.slug for w in self.store.list(db, owner_id)[:15])
                raise WorkflowNotFound(
                    f"não existe automação '{slug}'. Disponíveis: {available or 'nenhuma'}"
                )
            if not row.enabled and trigger_type != "manual":
                raise WorkflowNotFound(f"a automação '{slug}' está desativada")
            workflow = self.store.to_workflow(row)
            workflow_id = row.id
        finally:
            db.close()

        return await self.run_workflow(
            owner_id, workflow, payload,
            slug=slug, workflow_id=workflow_id,
            trigger_type=trigger_type, depth=depth,
        )

    async def run_workflow(
        self,
        owner_id: str,
        workflow: Workflow,
        payload: dict | None = None,
        *,
        slug: str | None = None,
        workflow_id: str | None = None,
        trigger_type: str = "manual",
        depth: int = 0,
    ) -> ExecutionResult:
        """Run a workflow object — stored or built on the fly."""
        execution_id = new_execution_id()
        key = slug or slugify(workflow.name)

        context = RunContext(
            workflow_id=workflow_id or workflow.id,
            workflow_slug=key,
            execution_id=execution_id,
            owner_id=owner_id,
            services=self.services,
            session_factory=self.session_factory,
            trigger_type=trigger_type,
            trigger_payload=payload or {},
            limits=self._limits(workflow),
            depth=depth,
        )

        self.executions.start(
            owner_id, execution_id, key,
            workflow_id=workflow_id, trigger_type=trigger_type,
            trigger_payload=payload,
        )
        self._running[execution_id] = context
        try:
            result = await self.orchestrator.run(workflow, context)
        except WorkflowValidationError as e:
            result = ExecutionResult(
                execution_id=execution_id, workflow_slug=key,
                status=ExecutionStatus.FAILED,
                error="workflow inválido: " + "; ".join(e.problems),
            )
            await self.executions.execution_finished(context, result)
        finally:
            self._running.pop(execution_id, None)

        if workflow_id:
            db = self.session_factory()
            try:
                self.store.mark_run(db, owner_id, key)
            finally:
                db.close()

        logger.info("Teia: %s", result.summary())
        return result

    def _limits(self, workflow: Workflow) -> RunLimits:
        """Global guardrails, with per-workflow overrides from `metadata`."""
        meta = workflow.metadata or {}

        def number(key: str, fallback):
            value = meta.get(key)
            try:
                return type(fallback)(value) if value is not None else fallback
            except (TypeError, ValueError):
                return fallback

        return RunLimits(
            max_parallel=max(1, number("max_parallel", settings.teia_max_parallel)),
            max_nodes=max(1, number("max_nodes", settings.teia_max_nodes_per_run)),
            run_timeout_seconds=number("timeout_seconds", settings.teia_run_timeout_seconds),
            max_depth=settings.teia_max_depth,
        )

    def cancel(self, execution_id: str) -> bool:
        """Ask a running execution to stop at its next node boundary."""
        context = self._running.get(execution_id)
        if not context:
            return False
        context.cancel.cancel("cancelado pelo dono")
        return True

    # ================================================================ authoring

    def validate(self, workflow: Workflow) -> list[str]:
        """Problems with this graph — empty means it is runnable."""
        return workflow.validate_graph(self.registry)

    def save(
        self, db: Session, owner_id: str, workflow: Workflow, *,
        slug: str | None = None, description: str | None = None,
        enabled: bool = True, tags: list[str] | None = None, source: str = "owner",
    ):
        """Validate, then persist, then re-arm the triggers."""
        problems = self.validate(workflow)
        if problems:
            raise WorkflowValidationError(problems)
        row = self.store.save(
            db, owner_id, workflow, slug=slug, description=description,
            enabled=enabled, tags=tags, source=source,
        )
        self.triggers.reload()
        return row

    def delete(self, db: Session, owner_id: str, slug: str) -> bool:
        removed = self.store.delete(db, owner_id, slug)
        if removed:
            self.triggers.reload()
        return removed

    def set_enabled(self, db: Session, owner_id: str, slug: str, enabled: bool) -> bool:
        changed = self.store.set_enabled(db, owner_id, slug, enabled)
        if changed:
            self.triggers.reload()
        return changed

    def list(self, db: Session, owner_id: str, query: str | None = None) -> list[dict]:
        return [
            self.store.to_dict(row)
            for row in self.store.list(db, owner_id, query=query)
        ]

    def get(self, db: Session, owner_id: str, slug: str) -> dict | None:
        row = self.store.get(db, owner_id, slug)
        return self.store.to_dict(row, include_definition=True) if row else None

    # ================================================================ catalogue

    def node_types(self) -> list[dict]:
        return catalogue()

    def trigger_types(self) -> list[dict]:
        return trigger_catalogue()

    async def status(self) -> dict:
        """A health summary of the engine, for /api/v1/automations/status."""
        db = self.session_factory()
        try:
            total = db.query(AutomationWorkflow).count()
        finally:
            db.close()

        return {
            "engine": "teia",
            "enabled": settings.automations_enabled,
            "online": True,                       # in-process: if the kernel is up, it is
            "workflows": total,
            "armed_triggers": len(self.triggers.armed),
            "running": len(self._running),
            "node_types": len(self.registry.node_types()),
            "trigger_types": len(self.registry.trigger_types()),
            "max_parallel": settings.teia_max_parallel,
            "tick_seconds": settings.teia_tick_seconds,
            "timezone": settings.teia_timezone or "local",
            "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
