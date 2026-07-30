"""
Kernel Services — lifecycle, health, metrics, state, configuration, diagnostics.

All implement IEngine and are registered in DI.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings
from app.engines import IEngine

logger = logging.getLogger("sexta-feira.kernel")


# ── KernelConfiguration ───────────────────────────────────

@dataclass
class KernelConfiguration:
    """Read-only snapshot of kernel configuration."""
    environment: str
    log_level: str
    brain_model: str
    embedding_model: str
    ollama_endpoint: str
    database_url: str
    grpc_port: int
    voice_enabled: bool
    scheduler_enabled: bool
    subagents_enabled: bool
    obsidian_vault: str | None

    @classmethod
    def from_settings(cls) -> "KernelConfiguration":
        return cls(
            environment=settings.environment,
            log_level=settings.log_level,
            brain_model=settings.brain_model,
            embedding_model=settings.embedding_model,
            ollama_endpoint=settings.ollama_endpoint,
            database_url=str(settings.database_url),
            grpc_port=settings.grpc_port,
            voice_enabled=settings.voice_enabled,
            scheduler_enabled=settings.scheduler_enabled,
            subagents_enabled=settings.subagents_enabled,
            obsidian_vault=str(settings.obsidian_vault_path) if settings.obsidian_vault_path else None,
        )


# ── KernelState ───────────────────────────────────────────

@dataclass
class KernelState:
    """Observable kernel state."""
    status: str = "stopped"  # stopped, starting, running, stopping, error
    started_at: float | None = None
    uptime_seconds: float = 0.0
    memory_count: int = 0
    plugin_count: int = 0
    error: str | None = None


class KernelStateManager(IEngine):
    """Tracks and exposes kernel state."""

    def __init__(self) -> None:
        self._state = KernelState()
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        return "KernelState"

    @property
    def state(self) -> KernelState:
        return self._state

    async def initialize(self) -> None:
        async with self._lock:
            self._state.status = "starting"
            self._state.started_at = time.time()
        logger.info("KernelState initialized")

    async def health(self) -> bool:
        return self._state.status == "running"

    async def shutdown(self) -> None:
        async with self._lock:
            self._state.status = "stopped"

    async def set_running(self) -> None:
        async with self._lock:
            self._state.status = "running"

    async def set_error(self, error: str) -> None:
        async with self._lock:
            self._state.status = "error"
            self._state.error = error


# ── KernelHealth ──────────────────────────────────────────

@dataclass
class HealthReport:
    """Aggregated health of all kernel components."""
    status: str = "unknown"
    components: dict[str, bool] = field(default_factory=dict)
    uptime_seconds: float = 0.0
    memory_usage_mb: float = 0.0


class KernelHealth(IEngine):
    """Aggregates health from all registered engines."""

    def __init__(self) -> None:
        self._engines: dict[str, IEngine] = {}

    @property
    def name(self) -> str:
        return "KernelHealth"

    def register_engine(self, engine: IEngine) -> None:
        self._engines[engine.name] = engine

    async def initialize(self) -> None:
        logger.info("KernelHealth initialized")

    async def health(self) -> bool:
        return True

    async def shutdown(self) -> None:
        pass

    async def aggregate(self) -> HealthReport:
        results: dict[str, bool] = {}
        for name, engine in self._engines.items():
            try:
                results[name] = await engine.health()
            except Exception:
                results[name] = False
        overall = "ok" if all(results.values()) else "degraded" if any(results.values()) else "unhealthy"
        import os, psutil  # noqa: lazy import
        proc = psutil.Process(os.getpid())
        return HealthReport(
            status=overall,
            components=results,
            memory_usage_mb=proc.memory_info().rss / (1024 * 1024),
        )


# ── KernelMetrics ─────────────────────────────────────────

@dataclass
class KernelMetrics:
    """Runtime metric snapshot."""
    total_memories: int = 0
    total_events: int = 0
    total_chats: int = 0
    total_actions: int = 0
    avg_response_time_ms: float = 0.0
    active_plugins: int = 0


class KernelMetricsCollector(IEngine):
    """Collects runtime metrics from kernel components."""

    def __init__(self) -> None:
        self._metrics = KernelMetrics()

    @property
    def name(self) -> str:
        return "KernelMetrics"

    @property
    def metrics(self) -> KernelMetrics:
        return self._metrics

    async def initialize(self) -> None:
        logger.info("KernelMetrics initialized")

    async def health(self) -> bool:
        return True

    async def shutdown(self) -> None:
        pass

    def increment_chats(self) -> None:
        self._metrics.total_chats += 1

    def increment_actions(self) -> None:
        self._metrics.total_actions += 1


# ── KernelDiagnostics ─────────────────────────────────────

class KernelDiagnostics(IEngine):
    """Diagnostic utilities for kernel troubleshooting."""

    @property
    def name(self) -> str:
        return "KernelDiagnostics"

    async def initialize(self) -> None:
        logger.info("KernelDiagnostics initialized")

    async def health(self) -> bool:
        return True

    async def shutdown(self) -> None:
        pass

    async def run_checks(self) -> dict[str, Any]:
        return {"python_version": sys.version, "engines": list(self._diagnosed_engines)}

    _diagnosed_engines: set[str] = set()

    def register_diagnostic(self, engine_name: str) -> None:
        self._diagnosed_engines.add(engine_name)
