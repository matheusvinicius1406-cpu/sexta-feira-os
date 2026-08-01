"""
Persistence for the Teia — workflows in, executions out.

`WorkflowStore` is the repository for the automations themselves; `ExecutionStore`
is both the audit trail and the engine's `RunObserver`, so a run checkpoints
itself node by node without the orchestrator knowing what a database is.
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.automation.teia.domain.graph import Workflow
from app.automation.teia.engine.context import RunContext
from app.automation.teia.engine.state import ExecutionResult, NodeResult, NodeStatus
from app.models.models import AutomationExecution, AutomationNodeRun, AutomationWorkflow

logger = logging.getLogger("sexta-feira.teia.store")

MAX_STORED_OUTPUT = 16000       # chars — an audit trail, not a data warehouse


def _now() -> datetime:
    return datetime.now(UTC)


def _naive(moment: datetime) -> datetime:
    """SQLite columns are naive; store everything as naive UTC, consistently."""
    return moment.astimezone(UTC).replace(tzinfo=None) if moment.tzinfo else moment


def slugify(text: str) -> str:
    """'Briefing Matinal!' -> 'briefing-matinal'."""
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_only = normalized.encode("ascii", "ignore").decode()
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_only).strip("-").lower()
    return cleaned or "automacao"


def _dump(value: object, limit: int = MAX_STORED_OUTPUT) -> str | None:
    if value in (None, {}, []):
        return None
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = str(value)
    return text[:limit]


class WorkflowStore:
    """CRUD for the owner's automations."""

    def get(self, db: Session, owner_id: str, slug: str) -> AutomationWorkflow | None:
        return (
            db.query(AutomationWorkflow)
            .filter(AutomationWorkflow.owner_id == owner_id, AutomationWorkflow.slug == slug)
            .first()
        )

    def list(
        self, db: Session, owner_id: str, *,
        enabled_only: bool = False, query: str | None = None,
    ) -> list[AutomationWorkflow]:
        rows = (
            db.query(AutomationWorkflow)
            .filter(AutomationWorkflow.owner_id == owner_id)
            .order_by(AutomationWorkflow.name)
            .all()
        )
        if enabled_only:
            rows = [r for r in rows if r.enabled]
        needle = (query or "").strip().lower()
        if needle:
            rows = [
                r for r in rows
                if needle in r.slug.lower()
                or needle in r.name.lower()
                or needle in (r.description or "").lower()
                or needle in (r.tags or "").lower()
            ]
        return rows

    def save(
        self, db: Session, owner_id: str, workflow: Workflow, *,
        slug: str | None = None, description: str | None = None,
        enabled: bool = True, tags: list[str] | None = None, source: str = "owner",
    ) -> AutomationWorkflow:
        """Create or update by slug. The graph is stored exactly as serialized."""
        key = slugify(slug or workflow.name)
        definition = workflow.model_dump_json()
        row = self.get(db, owner_id, key)
        if row:
            row.name = workflow.name
            row.description = description if description is not None else row.description
            row.definition = definition
            row.enabled = enabled
            row.tags = json.dumps(tags or [], ensure_ascii=False)
            row.version = workflow.version
            row.source = source
        else:
            row = AutomationWorkflow(
                id=str(uuid.uuid4()), owner_id=owner_id, slug=key, name=workflow.name,
                description=description or "", definition=definition, enabled=enabled,
                tags=json.dumps(tags or [], ensure_ascii=False),
                source=source, version=workflow.version,
            )
            db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def set_enabled(self, db: Session, owner_id: str, slug: str, enabled: bool) -> bool:
        row = self.get(db, owner_id, slug)
        if not row:
            return False
        row.enabled = enabled
        db.commit()
        return True

    def delete(self, db: Session, owner_id: str, slug: str) -> bool:
        row = self.get(db, owner_id, slug)
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True

    def mark_run(self, db: Session, owner_id: str, slug: str) -> None:
        row = self.get(db, owner_id, slug)
        if row:
            row.last_run_at = _naive(_now())
            db.commit()

    # ---------- conversion ----------

    @staticmethod
    def to_workflow(row: AutomationWorkflow) -> Workflow:
        return Workflow.model_validate_json(row.definition)

    @staticmethod
    def to_dict(row: AutomationWorkflow, *, include_definition: bool = False) -> dict:
        data = {
            "slug": row.slug,
            "name": row.name,
            "description": row.description,
            "enabled": row.enabled,
            "source": row.source,
            "version": row.version,
            "tags": json.loads(row.tags) if row.tags else [],
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "last_run_at": row.last_run_at,
        }
        if include_definition:
            data["definition"] = json.loads(row.definition)
        return data


class ExecutionStore:
    """The audit trail — and the engine's checkpoint sink (`RunObserver`)."""

    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    # ---------- lifecycle ----------

    def start(
        self, owner_id: str, execution_id: str, workflow_slug: str, *,
        workflow_id: str | None, trigger_type: str, trigger_payload: dict | None,
    ) -> None:
        db = self.session_factory()
        try:
            db.add(AutomationExecution(
                id=execution_id, owner_id=owner_id, workflow_id=workflow_id,
                workflow_slug=workflow_slug, status="running", trigger_type=trigger_type,
                trigger_payload=_dump(trigger_payload, 4000),
                correlation_id=execution_id, started_at=_naive(_now()),
            ))
            db.commit()
        finally:
            db.close()

    # ---------- RunObserver ----------

    async def node_finished(self, context: RunContext, result: NodeResult) -> None:
        if result.status is NodeStatus.SKIPPED:
            return                              # a skipped node is noise in the trail
        db = self.session_factory()
        try:
            db.add(AutomationNodeRun(
                id=str(uuid.uuid4()), owner_id=context.owner_id,
                execution_id=context.execution_id, node_id=result.node_id,
                node_type=result.node_type, status=result.status.value,
                attempt=result.attempts,
                output=_dump(context.redact(result.outputs), 4000),
                error=result.error, duration_ms=result.duration_ms,
                started_at=_naive(result.started_at) if result.started_at else _naive(_now()),
                finished_at=_naive(result.finished_at) if result.finished_at else _naive(_now()),
            ))
            db.commit()
        finally:
            db.close()

    async def execution_finished(self, context: RunContext, result: ExecutionResult) -> None:
        db = self.session_factory()
        try:
            row = db.query(AutomationExecution).filter(
                AutomationExecution.id == context.execution_id
            ).first()
            if not row:
                return
            row.status = result.status.value
            row.error = result.error
            row.output = _dump(context.redact(result.output))
            row.nodes_executed = result.nodes_executed
            row.duration_ms = result.duration_ms
            row.finished_at = _naive(_now())
            db.commit()
        finally:
            db.close()

    # ---------- reading ----------

    def list(
        self, db: Session, owner_id: str, *,
        slug: str | None = None, limit: int = 50,
    ) -> list[AutomationExecution]:
        q = db.query(AutomationExecution).filter(AutomationExecution.owner_id == owner_id)
        if slug:
            q = q.filter(AutomationExecution.workflow_slug == slug)
        return q.order_by(AutomationExecution.started_at.desc()).limit(limit).all()

    def get(self, db: Session, owner_id: str, execution_id: str) -> dict | None:
        row = db.query(AutomationExecution).filter(
            AutomationExecution.owner_id == owner_id,
            AutomationExecution.id == execution_id,
        ).first()
        if not row:
            return None
        runs = (
            db.query(AutomationNodeRun)
            .filter(AutomationNodeRun.execution_id == execution_id)
            .order_by(AutomationNodeRun.started_at)
            .all()
        )
        data = self.to_dict(row)
        data["nodes"] = [
            {
                "node_id": r.node_id, "type": r.node_type, "status": r.status,
                "attempt": r.attempt, "duration_ms": r.duration_ms,
                "error": r.error,
                "output": json.loads(r.output) if r.output else None,
            }
            for r in runs
        ]
        return data

    def ran_since(
        self, db: Session, owner_id: str, slug: str, trigger_type: str, since: datetime
    ) -> bool:
        """Did this workflow already run from this trigger since `since`?

        This is what keeps a cron trigger firing exactly once per matching minute
        even if the kernel restarts inside that minute.
        """
        return db.query(AutomationExecution).filter(
            AutomationExecution.owner_id == owner_id,
            AutomationExecution.workflow_slug == slug,
            AutomationExecution.trigger_type == trigger_type,
            AutomationExecution.started_at >= _naive(since),
        ).first() is not None

    @staticmethod
    def to_dict(row: AutomationExecution) -> dict:
        return {
            "id": row.id,
            "workflow": row.workflow_slug,
            "status": row.status,
            "ok": row.status == "completed",
            "trigger": row.trigger_type,
            "error": row.error,
            "nodes_executed": row.nodes_executed,
            "duration_ms": row.duration_ms,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
            "output": json.loads(row.output) if row.output else None,
        }
