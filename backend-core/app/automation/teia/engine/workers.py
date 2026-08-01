"""
The workers — os operários.

A fixed pool of asyncio workers pulls `NodeJob`s off a queue, executes exactly
one node each, and pushes a `NodeResult` back. Everything a single node needs to
survive contact with the real world lives here and nowhere else:

  * config resolution (`{{ ... }}`) against the live execution,
  * validation of the resolved config against the node type's Pydantic schema,
  * a hard per-node timeout,
  * retries with exponential backoff,
  * turning any exception into a `NodeResult`, never into a crashed pool.

The orchestrator decides WHAT runs and WHEN; a worker only knows HOW to run one
node well. That split is what lets the same engine run in-process today and
behind a broker later (ADR-0013 §3) without any node changing.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from datetime import UTC, datetime

from pydantic import ValidationError

from app.automation.teia.domain.execution import NodeInput, NodeOutput
from app.automation.teia.engine.context import Cancelled, RunContext
from app.automation.teia.engine.errors import NodeExecutionError, UnknownNodeType
from app.automation.teia.engine.state import NodeJob, NodeResult, NodeStatus
from app.automation.teia.registry import Registry

logger = logging.getLogger("sexta-feira.teia.worker")


class Worker:
    """One operário. Owns no state beyond its name — everything comes in the job."""

    def __init__(self, name: str, registry: Registry, context: RunContext):
        self.name = name
        self.registry = registry
        self.context = context

    async def run_job(self, job: NodeJob) -> NodeResult:
        """Execute one node, with retries and a timeout. Never raises."""
        node = job.node
        started = datetime.now(UTC)
        clock_start = time.perf_counter()
        policy = node.policy
        last_error: str | None = None
        attempt = 0

        while attempt < policy.max_attempts:
            attempt += 1
            try:
                self.context.cancel.raise_if_cancelled()
                outputs = await self._attempt(job, policy.timeout_seconds)
                return NodeResult(
                    node_id=node.id, node_type=node.type, status=NodeStatus.COMPLETED,
                    outputs=outputs, attempts=attempt,
                    duration_ms=int((time.perf_counter() - clock_start) * 1000),
                    started_at=started, finished_at=datetime.now(UTC),
                )
            except Cancelled as e:
                last_error = str(e) or "cancelado"
                break                       # cancellation is never retried
            except TimeoutError:
                last_error = (
                    f"tempo esgotado após {policy.timeout_seconds:g}s "
                    f"(ajuste policy.timeout_seconds do nó)"
                )
            except (UnknownNodeType, ValidationError) as e:
                # Bad wiring / bad config: retrying cannot help.
                last_error = self._describe(e)
                break
            except Exception as e:  # noqa: BLE001 — a node failing is normal operation
                last_error = self._describe(e)

            if attempt < policy.max_attempts and not self.context.cancel.cancelled:
                delay = policy.backoff_seconds * (2 ** (attempt - 1))
                self.context.log(
                    f"nó '{node.id}' falhou (tentativa {attempt}/{policy.max_attempts}): "
                    f"{last_error} — nova tentativa em {delay:g}s"
                )
                await asyncio.sleep(delay)

        return NodeResult(
            node_id=node.id, node_type=node.type, status=NodeStatus.FAILED,
            error=self.context.redact(last_error or "falha desconhecida"),
            attempts=attempt,
            duration_ms=int((time.perf_counter() - clock_start) * 1000),
            started_at=started, finished_at=datetime.now(UTC),
        )

    # ---------- one attempt ----------

    async def _attempt(self, job: NodeJob, timeout: float) -> dict[str, list]:
        """Run the node, racing it against the timeout AND the cancel signal.

        `asyncio.wait_for` alone would only cover the timeout; a node already
        awaiting a slow HTTP call has to be actively cancelled, or "cancel" means
        "cancel eventually".
        """
        work = asyncio.ensure_future(self._execute_once(job))
        stop = asyncio.ensure_future(self.context.cancel.wait())
        try:
            done, _pending = await asyncio.wait(
                {work, stop}, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
            )
            if work in done:
                return work.result()
            work.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await work
            if self.context.cancel.cancelled:
                raise Cancelled(self.context.cancel.reason)
            raise TimeoutError
        finally:
            stop.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await stop

    async def _execute_once(self, job: NodeJob) -> dict[str, list]:
        node = job.node
        node_cls = self.registry.get_node(node.type)
        if node_cls is None:
            raise UnknownNodeType(
                f"tipo de nó desconhecido: '{node.type}'. "
                f"Conhecidos: {', '.join(self.registry.node_types()[:20])}"
            )

        incoming = job.inputs.get("main", [])
        resolved = self.context.resolve(node.config, inputs=incoming)
        config = node_cls.config_model.model_validate(resolved or {})

        instance = node_cls(config)
        result = await instance.execute(self.context, NodeInput(items=job.inputs))
        if not isinstance(result, NodeOutput):
            raise NodeExecutionError(
                f"o nó '{node.type}' devolveu {type(result).__name__}, esperava NodeOutput"
            )
        return dict(result.items)

    @staticmethod
    def _describe(error: Exception) -> str:
        if isinstance(error, ValidationError):
            problems = "; ".join(
                f"{'.'.join(str(p) for p in e['loc']) or 'config'}: {e['msg']}"
                for e in error.errors()[:4]
            )
            return f"configuração inválida — {problems}"
        text = str(error).strip()
        return f"{type(error).__name__}: {text}" if text else type(error).__name__


class WorkerPool:
    """A bounded set of workers consuming one job queue.

    `max_parallel` is the real concurrency limit of an execution: it is what keeps
    a fan-out of fifty HTTP nodes from opening fifty sockets at once.
    """

    def __init__(self, registry: Registry, context: RunContext, size: int):
        self.registry = registry
        self.context = context
        self.size = max(1, int(size))
        self.jobs: asyncio.Queue[NodeJob] = asyncio.Queue()
        self.results: asyncio.Queue[NodeResult] = asyncio.Queue()
        self._tasks: list[asyncio.Task] = []

    async def __aenter__(self) -> WorkerPool:
        self._tasks = [
            asyncio.create_task(self._loop(Worker(f"operario-{i + 1}", self.registry, self.context)))
            for i in range(self.size)
        ]
        return self

    async def __aexit__(self, *_exc_info) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []

    async def submit(self, job: NodeJob) -> None:
        await self.jobs.put(job)

    async def next_result(self) -> NodeResult:
        return await self.results.get()

    async def _loop(self, worker: Worker) -> None:
        while True:
            job = await self.jobs.get()
            try:
                result = await worker.run_job(job)
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 — the pool must outlive any single job
                logger.exception("worker %s crashed on node %s", worker.name, job.node.id)
                result = NodeResult(
                    node_id=job.node.id, node_type=job.node.type,
                    status=NodeStatus.FAILED, error=f"falha interna do operário: {e}",
                )
            await self.results.put(result)
