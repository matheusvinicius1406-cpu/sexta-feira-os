"""
System nodes — the kernel keeping an eye on the machine it lives in.

Disk headroom, a consistent database backup, whether the local brain is actually
answering, and (only if the owner opts in) running a program from an allowlist.
"""
from __future__ import annotations

import asyncio
import shutil
import sqlite3
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from app.automation.teia.domain.execution import NodeInput, NodeOutput
from app.automation.teia.domain.node import Node, NodeMetadata
from app.automation.teia.nodes.files import ensure_workspace, safe_path
from app.core.config import settings


class _DiskConfig(BaseModel):
    caminho: str = "."
    alerta_livre_gb: float = Field(default=5.0, ge=0.0)


class DiskUsageNode(Node):
    """Disk headroom for a path. Emits `{livre_gb, usado_pct, alerta}`."""

    metadata = NodeMetadata(
        type="disco", name="Espaço em disco", category="sistema",
        description="Mede o espaço livre e marca alerta abaixo do limite.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _DiskConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        target = Path(self.config.caminho).expanduser().resolve()
        if not target.exists():
            target = Path(settings.teia_workspace).resolve()
        usage = shutil.disk_usage(target)

        gb = 1024 ** 3
        free_gb = usage.free / gb
        used_pct = (usage.used / usage.total * 100) if usage.total else 0.0
        alert = free_gb < self.config.alerta_livre_gb
        return NodeOutput.single({
            "caminho": str(target),
            "total_gb": round(usage.total / gb, 2),
            "usado_gb": round(usage.used / gb, 2),
            "livre_gb": round(free_gb, 2),
            "usado_pct": round(used_pct, 1),
            "alerta": alert,
        })


class _BackupConfig(BaseModel):
    destino: str = "backups"
    manter: int = Field(default=7, ge=1, le=90)


class BackupDatabaseNode(Node):
    """Back up the kernel's SQLite database — consistently, and rotate old copies.

    Uses SQLite's own backup API rather than copying the file, so a snapshot taken
    while the kernel is writing is still a valid database.
    """

    metadata = NodeMetadata(
        type="backup_banco", name="Backup do banco", category="sistema",
        description="Copia o banco do kernel para a pasta de backups e rotaciona.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _BackupConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        url = settings.database_url
        if not url.startswith("sqlite"):
            raise RuntimeError(
                f"backup automático só cobre SQLite; este kernel usa {url.split(':')[0]}"
            )
        source = Path(url.split("sqlite:///")[-1]).resolve()
        if not source.exists():
            raise FileNotFoundError(f"banco não encontrado em {source}")

        ensure_workspace()
        folder = safe_path(self.config.destino)
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        target = folder / f"sexta-feira-{stamp}.db"

        await asyncio.to_thread(_sqlite_backup, source, target)

        copies = sorted(folder.glob("sexta-feira-*.db"), key=lambda p: p.stat().st_mtime)
        removed = 0
        while len(copies) > self.config.manter:
            copies.pop(0).unlink(missing_ok=True)
            removed += 1

        context.log(f"backup em {target.name} ({target.stat().st_size // 1024} KB)")
        return NodeOutput.single({
            "arquivo": str(target),
            "bytes": target.stat().st_size,
            "removidos": removed,
            "mantidos": min(len(copies), self.config.manter),
        })


def _sqlite_backup(source: Path, target: Path) -> None:
    origin = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    try:
        copy = sqlite3.connect(target)
        try:
            origin.backup(copy)
        finally:
            copy.close()
    finally:
        origin.close()


class _BrainHealthConfig(BaseModel):
    pass


class BrainHealthNode(Node):
    """Is the local brain answering? Emits `{online, modelo, endpoint, ms}`."""

    metadata = NodeMetadata(
        type="cerebro_saude", name="Saúde do cérebro", category="sistema",
        description="Verifica se o Ollama local está respondendo.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _BrainHealthConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        brain = context.services.require("brain")
        started = time.perf_counter()
        online = await brain.health()
        return NodeOutput.single({
            "online": bool(online),
            "modelo": settings.brain_model,
            "endpoint": settings.ollama_endpoint,
            "ms": int((time.perf_counter() - started) * 1000),
        })


class _RunProgramConfig(BaseModel):
    programa: str = Field(..., min_length=1)
    argumentos: list[str] = Field(default_factory=list)
    diretorio: str | None = None
    timeout_segundos: float = Field(default=60.0, gt=0, le=600)


class RunProgramNode(Node):
    """Run a program from the owner's allowlist.

    Off unless TEIA_SHELL_ENABLED is true, and even then only programs named in
    TEIA_SHELL_ALLOWLIST run. There is no shell: the program and its arguments are
    passed as a list, so nothing in an item can inject a second command.
    """

    metadata = NodeMetadata(
        type="programa", name="Executar programa", category="sistema",
        description="Roda um programa da lista permitida (desligado por padrão).",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _RunProgramConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        if not settings.teia_shell_enabled:
            raise RuntimeError(
                "execução de programas está desligada. "
                "Ligue com TEIA_SHELL_ENABLED=true e liste o programa em TEIA_SHELL_ALLOWLIST."
            )
        cfg = self.config
        allowed = [p.strip().lower() for p in settings.teia_shell_allowlist if p.strip()]
        name = Path(cfg.programa).name.lower()
        if name not in allowed and cfg.programa.strip().lower() not in allowed:
            raise RuntimeError(
                f"'{cfg.programa}' não está em TEIA_SHELL_ALLOWLIST "
                f"(permitidos: {', '.join(allowed) or 'nenhum'})"
            )

        cwd = str(safe_path(cfg.diretorio, must_exist=True)) if cfg.diretorio else None
        # Blocking subprocess.run, off the loop via to_thread — NOT
        # asyncio.create_subprocess_exec. uvicorn pins Windows to
        # WindowsSelectorEventLoopPolicy (uvicorn/loops/asyncio.py), which
        # raises a bare NotImplementedError from the asyncio subprocess API on
        # every platform this kernel ships for; this node would fail before
        # the allowlisted program ever ran. subprocess.run's own `timeout`
        # already kills the child and raises on expiry, so no manual
        # kill()/wait() is needed here the way the asyncio version needed it.
        try:
            proc = await asyncio.to_thread(
                subprocess.run, [cfg.programa, *cfg.argumentos],
                capture_output=True, cwd=cwd, timeout=cfg.timeout_segundos,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"'{cfg.programa}' passou de {cfg.timeout_segundos:g}s e foi encerrado"
            ) from None

        return NodeOutput.single({
            "codigo": proc.returncode,
            "ok": proc.returncode == 0,
            "saida": proc.stdout.decode("utf-8", "replace")[:20000],
            "erro": proc.stderr.decode("utf-8", "replace")[:5000],
        })


SYSTEM_NODES = [DiskUsageNode, BackupDatabaseNode, BrainHealthNode, RunProgramNode]
