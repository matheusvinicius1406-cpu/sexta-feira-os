"""
TriggerManager — what actually arms the triggers.

It keeps an in-memory view of every enabled workflow's trigger bindings and turns
the outside world into executions:

  * `tick()`      — called on an interval; fires `agenda` (cron) and `intervalo`.
  * `on_event()`  — subscribed to the kernel EventBus; fires `evento`.
  * `find_webhook()` — resolves an incoming HTTP call to a workflow.

`manual` needs no arming: the API, the CLI and the brain call the runner directly.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.automation.teia.domain.graph import TriggerBinding
from app.automation.teia.store import ExecutionStore, WorkflowStore
from app.automation.teia.triggers.cron import CronError, CronSchedule, parse_cron
from app.core.config import settings
from app.models.models import AutomationWorkflow

logger = logging.getLogger("sexta-feira.teia.triggers")


def _local_now() -> datetime:
    """Wall-clock time for cron, in the owner's timezone."""
    if settings.teia_timezone:
        try:
            from zoneinfo import ZoneInfo

            return datetime.now(ZoneInfo(settings.teia_timezone))
        except Exception as e:  # noqa: BLE001 — a bad tz must not stop the scheduler
            logger.warning(
                "TEIA_TIMEZONE='%s' inválido (%s); usando o horário local da máquina",
                settings.teia_timezone, e,
            )
    return datetime.now().astimezone()


def _matches_pattern(pattern: str, event_type: str) -> bool:
    """'*' matches everything, 'prefixo.*' matches the family, else exact."""
    if pattern == "*":
        return True
    if pattern.endswith(".*"):
        base = pattern[:-2]
        return event_type == base or event_type.startswith(f"{base}.")
    return pattern == event_type


@dataclass
class Armed:
    """One trigger binding of one workflow, ready to fire."""

    owner_id: str
    workflow_id: str
    slug: str
    binding_id: str
    type: str
    config: dict
    schedule: CronSchedule | None = None
    last_fired: datetime | None = None

    @property
    def key(self) -> str:
        return f"{self.workflow_id}:{self.binding_id}"


@dataclass
class _EventBudget:
    """Per-workflow rate limit for event triggers (loop backstop)."""

    minute: str = ""
    count: int = 0
    fields: dict = field(default_factory=dict)


class TriggerManager:
    def __init__(
        self,
        store: WorkflowStore,
        executions: ExecutionStore,
        runner,
        session_factory: Callable[[], Session],
    ):
        self.store = store
        self.executions = executions
        self.runner = runner
        self.session_factory = session_factory
        self.armed: list[Armed] = []
        self._budget: dict[str, _EventBudget] = {}
        self._tasks: set[asyncio.Task] = set()

    # ---------- arming ----------

    def reload(self) -> int:
        """Rebuild the armed list from the database. Safe to call any time."""
        previous = {a.key: a.last_fired for a in self.armed}
        armed: list[Armed] = []

        db = self.session_factory()
        try:
            rows = (
                db.query(AutomationWorkflow)
                .filter(AutomationWorkflow.enabled.is_(True))
                .all()
            )
            for row in rows:
                armed.extend(self._arm_workflow(row, previous))
        finally:
            db.close()

        self.armed = armed
        logger.info("Teia: %d gatilho(s) armado(s)", len(armed))
        return len(armed)

    def _arm_workflow(
        self, row: AutomationWorkflow, previous: dict[str, datetime | None]
    ) -> list[Armed]:
        try:
            workflow = self.store.to_workflow(row)
        except Exception as e:  # noqa: BLE001 — one broken workflow must not blind the rest
            logger.warning("automação '%s' não pôde ser lida: %s", row.slug, e)
            return []

        out: list[Armed] = []
        for binding in workflow.triggers:
            armed = self._arm_binding(row, binding)
            if armed:
                armed.last_fired = previous.get(armed.key)
                out.append(armed)
        return out

    def _arm_binding(
        self, row: AutomationWorkflow, binding: TriggerBinding
    ) -> Armed | None:
        schedule = None
        if binding.type == "agenda":
            expression = (binding.config or {}).get("cron", "")
            try:
                schedule = parse_cron(expression)
            except CronError as e:
                logger.warning(
                    "automação '%s': gatilho de agenda ignorado — %s", row.slug, e
                )
                return None
        return Armed(
            owner_id=row.owner_id, workflow_id=row.id, slug=row.slug,
            binding_id=binding.id, type=binding.type, config=binding.config or {},
            schedule=schedule,
        )

    # ---------- the clock ----------

    async def tick(self, now: datetime | None = None) -> list[str]:
        """Fire every time-based trigger that is due. Returns the slugs fired."""
        moment = now or _local_now()
        fired: list[str] = []

        for armed in list(self.armed):
            try:
                if armed.type == "agenda" and self._cron_due(armed, moment):
                    armed.last_fired = moment
                    await self._fire(armed, {"momento": moment.isoformat(timespec="minutes")})
                    fired.append(armed.slug)
                elif armed.type == "intervalo" and self._interval_due(armed, moment):
                    armed.last_fired = moment
                    await self._fire(armed, {"momento": moment.isoformat(timespec="seconds")})
                    fired.append(armed.slug)
            except Exception as e:  # noqa: BLE001 — one bad trigger never stops the tick
                logger.warning("gatilho de '%s' falhou: %s", armed.slug, e)
        return fired

    def _cron_due(self, armed: Armed, moment: datetime) -> bool:
        if not armed.schedule or not armed.schedule.matches(moment):
            return False
        minute_start = moment.replace(second=0, microsecond=0)
        if armed.last_fired and armed.last_fired >= minute_start:
            return False                    # already fired inside this minute
        # Survive a restart: the trail is the source of truth, not our memory.
        db = self.session_factory()
        try:
            already = self.executions.ran_since(
                db, armed.owner_id, armed.slug, "agenda", minute_start
            )
        finally:
            db.close()
        return not already

    @staticmethod
    def _interval_due(armed: Armed, moment: datetime) -> bool:
        seconds = int(armed.config.get("segundos", 0) or 0)
        if seconds < 30:
            return False
        if armed.last_fired is None:
            return True                     # first tick after boot: check right away
        return moment - armed.last_fired >= timedelta(seconds=seconds)

    # ---------- the event bus ----------

    def on_event(self, db: Session, event) -> None:
        """EventBus subscriber. Matching workflows run in the background.

        Deliberately non-blocking: an automation must never slow down (or fail)
        the publisher of the event that woke it.
        """
        source = getattr(event, "source", "") or ""
        for armed in list(self.armed):
            if armed.type != "evento":
                continue
            if armed.owner_id != getattr(event, "owner_id", armed.owner_id):
                continue
            if not _matches_pattern(str(armed.config.get("tipo", "")), event.type):
                continue
            if source == f"teia:{armed.slug}":
                continue                    # an automation never re-triggers itself
            if not self._within_budget(armed):
                logger.warning(
                    "automação '%s' atingiu o limite de %d disparos por minuto por evento",
                    armed.slug, settings.teia_event_fires_per_minute,
                )
                continue

            payload = {
                "evento": event.type,
                "origem": source,
                "dados": self._decode(event),
                "evento_id": getattr(event, "id", None),
            }
            self._spawn(self._fire(armed, payload))

    @staticmethod
    def _decode(event) -> dict:
        import json

        try:
            return json.loads(event.payload) if getattr(event, "payload", None) else {}
        except (ValueError, TypeError):
            return {}

    def _within_budget(self, armed: Armed) -> bool:
        minute = datetime.now(UTC).strftime("%Y%m%d%H%M")
        budget = self._budget.setdefault(armed.slug, _EventBudget())
        if budget.minute != minute:
            budget.minute, budget.count = minute, 0
        budget.count += 1
        return budget.count <= settings.teia_event_fires_per_minute

    # ---------- webhooks ----------

    def find_webhook(self, path: str) -> Armed | None:
        cleaned = (path or "").strip().strip("/")
        for armed in self.armed:
            if armed.type == "webhook" and armed.config.get("caminho") == cleaned:
                return armed
        return None

    # ---------- firing ----------

    async def _fire(self, armed: Armed, payload: dict) -> None:
        logger.info("Teia: gatilho '%s' disparou '%s'", armed.type, armed.slug)
        await self.runner.run_slug(
            armed.owner_id, armed.slug, payload, trigger_type=armed.type
        )

    def _spawn(self, coro) -> None:
        """Run a coroutine detached, keeping a reference so it isn't GC'd."""
        try:
            task = asyncio.get_running_loop().create_task(coro)
        except RuntimeError:                # no loop (a sync call path) — nothing to do
            coro.close()
            logger.debug("evento fora do event loop; automação não disparada")
            return
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def drain(self) -> None:
        """Await the event-triggered runs still in flight (used on shutdown/tests)."""
        while self._tasks:
            pending = list(self._tasks)
            await asyncio.gather(*pending, return_exceptions=True)

    async def stop(self) -> None:
        for task in list(self._tasks):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        self._tasks.clear()
