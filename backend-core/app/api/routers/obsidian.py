"""
Obsidian — import your vault notes into the knowledge graph.

Endpoints:
  POST /api/v1/obsidian/import    scan a vault dir and import notes
  POST /api/v1/obsidian/export    write graph nodes back as .md notes
  POST /api/v1/obsidian/watch     start/stop/status of auto-sync watcher
  GET  /api/v1/obsidian/status    current vault import stats

Every note becomes a Memory node; every [[wikilink]] becomes a MemoryLink
edge — so the brain reasons about your notes like a connected graph.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.brain.memory import PersistentMemory
from app.core.config import settings
from app.core.di import get_kernel, get_memory
from app.db.database import get_db
from app.models.models import Memory, MemoryLink, Owner
from app.obsidian.exporter import ObsidianExporter
from app.obsidian.importer import ObsidianImporter
from app.obsidian.watcher import ObsidianWatcher

logger = logging.getLogger("sexta-feira.api.obsidian")
router = APIRouter(prefix="/api/v1/obsidian", tags=["obsidian"])


class WatchRequest(BaseModel):
    vault_path: str | None = Field(
        None,
        description="Path to watch. Uses obsidian_vault_path from config if not set.",
    )
    interval: int = Field(30, ge=10, le=3600)
    action: str = Field("start", pattern="^(start|stop|status)$")


class ImportRequest(BaseModel):
    vault_path: str = Field(
        ...,
        description="Absolute path to the Obsidian vault directory",
        min_length=1,
        examples=["/home/user/meu-vault", "C:\\Users\\meu\\vault"],
    )


class ImportResponse(BaseModel):
    ok: bool
    message: str
    stats: dict | None = None


class ExportRequest(BaseModel):
    vault_path: str = Field(
        ...,
        description="Absolute path to the Obsidian vault directory",
        min_length=1,
    )
    include_all: bool = Field(
        True,
        description="If True, export ALL memories. If False, only vault-imported notes.",
    )


# ── Endpoints ────────────────────────────────────────────────────────


@router.post("/import", response_model=ImportResponse)
async def import_vault(
    body: ImportRequest,
    owner: Owner = Depends(get_current_owner),
    memory: PersistentMemory = Depends(get_memory),
    db: Session = Depends(get_db),
):
    """Walk an Obsidian vault, parse .md notes + [[wikilinks]],
    and create memory nodes + edges in the knowledge graph."""
    importer = ObsidianImporter(memory)

    try:
        stats = await importer.import_vault(db, owner.id, body.vault_path)
    except NotADirectoryError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e)) from e
    except Exception as e:
        logger.exception("Vault import failed")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Import failed: {e}",
        ) from e

    msg = (
        f"Importado {stats.notes_imported} notas, "
        f"{stats.links_created} ligações wikilink criadas "
        f"(de {stats.wikilinks_found} wikilinks encontrados)."
    )
    if stats.errors:
        msg += f" {len(stats.errors)} erros (veja stats.errors)."

    return ImportResponse(ok=True, message=msg, stats=stats.summary())


@router.post("/export", response_model=ImportResponse)
async def export_vault(
    body: ExportRequest,
    owner: Owner = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """Write memory graph nodes back to the Obsidian vault as .md notes.

    For notes imported from the vault, preserves original file paths.
    For brain-created memories, writes to a __sexta__ subfolder.
    Generates frontmatter (title, tags, dates) and [[wikilinks]].
    """
    exporter = ObsidianExporter()

    try:
        stats = exporter.export_vault(db, owner.id, body.vault_path, body.include_all)
    except NotADirectoryError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e)) from e
    except Exception as e:
        logger.exception("Vault export failed")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Export failed: {e}",
        ) from e

    msg = (
        f"Exportadas {stats.notes_written} novas notas, "
        f"{stats.notes_updated} atualizadas, "
        f"{stats.links_referenced} links wikilink incluídos."
    )
    if stats.errors:
        msg += f" {len(stats.errors)} erros (veja stats.errors)."

    return ImportResponse(ok=True, message=msg, stats=stats.summary())


@router.post("/watch")
async def watch_vault(
    body: WatchRequest,
    owner: Owner = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """Start, stop, or check status of the vault auto-sync watcher."""
    kernel = get_kernel()
    watcher = kernel._obsidian_watcher

    if body.action == "status":
        if watcher:
            return {"ok": True, **watcher.stats.summary()}
        return {"ok": True, "is_running": False, "message": "Watcher not initialized"}

    if body.action == "start":
        vault = body.vault_path or settings.obsidian_vault_path
        if not vault:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "vault_path is required. Set obsidian_vault_path in config or pass in body.",
            )
        if watcher and watcher.stats.is_running:
            return {"ok": True, "message": "Watcher already running"}

        # Create and start the watcher
        if not kernel._obsidian_watcher:
            kernel._obsidian_watcher = ObsidianWatcher(kernel.memory)

        kernel._obsidian_watcher_task = asyncio.ensure_future(
            kernel._obsidian_watcher_loop()
        )
        kernel._obsidian_watcher.stats.is_running = True
        kernel._obsidian_watcher.stats.vault_path = vault
        return {"ok": True, "message": f"Watcher started for {vault}"}

    if body.action == "stop":
        if kernel._obsidian_watcher_task:
            kernel._obsidian_watcher_task.cancel()
            kernel._obsidian_watcher_task = None
            if watcher:
                watcher.stats.is_running = False
            return {"ok": True, "message": "Watcher stopped"}
        return {"ok": True, "message": "Watcher was not running"}

    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown action: {body.action}")


@router.get("/status")
async def vault_status(
    owner: Owner = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """Show how many notes from the vault are currently in the knowledge graph."""
    total_notes = (
        db.query(Memory)
        .filter(Memory.owner_id == owner.id, Memory.source == "obsidian")
        .count()
    )
    total_links = (
        db.query(MemoryLink)
        .filter(MemoryLink.owner_id == owner.id, MemoryLink.origin == "obsidian")
        .count()
    )
    vault_path = settings.obsidian_vault_path or ""

    return {
        "vault_path": vault_path,
        "notes_imported": total_notes,
        "wikilinks_created": total_links,
        "default_path_configured": bool(vault_path),
    }
