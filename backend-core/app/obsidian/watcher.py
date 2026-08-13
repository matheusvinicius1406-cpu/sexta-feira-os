"""
Obsidian Vault Watcher — monitors the vault for changes and auto-syncs.

Uses a simple polling approach (no watchdog dependency):
  - Tracks file modification times in memory (mtime cache)
  - Every N seconds, scans the vault for new/modified/deleted .md files
  - New files → imports into the knowledge graph
  - Modified files → reimports (updates content + embedding)
  - Deleted files → removes the corresponding memory nodes

Designed to run as an asyncio background task inside the Kernel (like Scheduler).

Usage:
    watcher = ObsidianWatcher(memory)
    await watcher.start(db, owner_id, vault_path, interval=30)
    # ... runs in background ...
    await watcher.stop()
"""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.brain.memory import PersistentMemory
from app.models.models import Memory
from app.obsidian.exporter import _recover_vault_path
from app.obsidian.importer import ImportStats, ObsidianImporter

logger = logging.getLogger("sexta-feira.obsidian.watcher")


class WatcherStats:
    """Statistics collected during vault watching."""

    def __init__(self) -> None:
        self.files_imported = 0
        self.files_updated = 0
        self.files_deleted = 0
        self.errors: list[str] = []
        self.last_poll: float = 0.0
        self.is_running: bool = False
        self.vault_path: str = ""

    def summary(self) -> dict:
        return {
            "files_imported": self.files_imported,
            "files_updated": self.files_updated,
            "files_deleted": self.files_deleted,
            "errors": self.errors[:10],
            "last_poll": self.last_poll,
            "is_running": self.is_running,
            "vault_path": self.vault_path,
        }


class ObsidianWatcher:
    """Poll-based watcher that syncs vault changes to the knowledge graph."""

    def __init__(self, memory: PersistentMemory) -> None:
        self.memory = memory
        self.importer = ObsidianImporter(memory)
        # mtime cache: file_path -> last_mtime
        self._mtime_cache: dict[str, float] = {}
        self._vault_path: str | None = None
        self._owner_id: str | None = None
        self._interval: float = 30.0
        self._running = False
        self.stats = WatcherStats()

    def _seed_cache_from_db(self, db: Session, owner_id: str) -> None:
        """Prime the mtime cache from what the DB already knows was imported,
        so the first poll after a restart only treats genuinely new or
        changed files as new or changed.

        A file's on-disk mtime is trusted as "already synced" only when it is
        NOT newer than the row's own last write (`Memory.updated_at`) — a
        file touched AFTER we last imported it is genuinely stale, and must
        fall through to the normal new/modified handling on this first poll,
        same as it would on any later one. Both sides compare as naive UTC:
        SQLite round-trips DateTime columns without tzinfo, so an aware
        `_now()`-derived value never actually attached to the row we read
        back (see the same pattern in agent/pulse.py::_scan).
        """
        rows = (
            db.query(Memory)
            .filter(Memory.owner_id == owner_id, Memory.source == "obsidian")
            .all()
        )
        for mem in rows:
            path = _recover_vault_path(mem.content)
            if not path:
                continue
            try:
                disk_mtime = Path(path).stat().st_mtime
            except OSError:
                continue  # gone from disk; the delete-detection path handles it once seeded
            disk_modified_at = datetime.fromtimestamp(disk_mtime, tz=UTC).replace(tzinfo=None)
            if mem.updated_at and disk_modified_at <= mem.updated_at:
                self._mtime_cache[str(Path(path).resolve())] = disk_mtime

    async def poll(self, db: Session, owner_id: str, vault_path: str) -> None:
        """Single poll cycle: detect changes and sync them."""
        vault = Path(vault_path).resolve()
        if not vault.is_dir():
            logger.warning("Vault path does not exist, skipping poll: %s", vault)
            return

        if not self._mtime_cache:
            # First poll since this ObsidianWatcher was built — which is
            # every kernel boot, since the cache lives only in this
            # process's memory. Left empty, every file in the vault looks
            # "new" below, so a plain restart re-imported (and re-embedded
            # — one brain.embed() call per note) the WHOLE vault, every
            # time, even when nothing had changed since the last run.
            self._seed_cache_from_db(db, owner_id)

        self.stats.last_poll = time.time()
        current_files: dict[str, float] = {}

        # Scan all .md files in the vault
        for md_file in vault.rglob("*.md"):
            if ObsidianImporter._should_skip(md_file):
                continue
            file_path = str(md_file.resolve())
            mtime = md_file.stat().st_mtime
            current_files[file_path] = mtime

            cached_mtime = self._mtime_cache.get(file_path)

            if file_path not in self._mtime_cache:
                # New file — import
                logger.info("New vault note detected: %s", md_file.name)
                await self._import_file(db, owner_id, md_file, is_new=True)

            elif abs(mtime - cached_mtime) > 0.5:
                # Modified (0.5s tolerance for filesystem resolution)
                logger.info("Vault note modified: %s", md_file.name)
                await self._import_file(db, owner_id, md_file, is_new=False)

        # Detect deleted files
        for file_path in list(self._mtime_cache.keys()):
            if file_path not in current_files:
                logger.info("Vault note deleted: %s", Path(file_path).name)
                await self._delete_file(db, owner_id, file_path)

        # Update cache
        self._mtime_cache = current_files

    async def _import_file(
        self, db: Session, owner_id: str, md_file: Path, is_new: bool,
    ) -> None:
        """Import or reimport a single .md file into the graph."""
        try:
            memory, _title = await self.importer._import_note(
                db, owner_id, md_file, ImportStats(),
            )
            if memory:
                if is_new:
                    self.stats.files_imported += 1
                else:
                    self.stats.files_updated += 1

                # Re-create wikilink edges for this node (delete + recreate)
                self._refresh_wikilinks(db, owner_id, memory, md_file)
        except Exception as e:
            logger.warning("Failed to import %s: %s", md_file.name, e)
            self.stats.errors.append(f"{md_file.name}: {e}")

    def _refresh_wikilinks(
        self, db: Session, owner_id: str, memory: Memory, md_file: Path,
    ) -> None:
        """Recompute wikilink edges for a memory node based on current content."""
        from app.models.models import MemoryLink

        # Remove existing wikilink edges from this node
        existing = (
            db.query(MemoryLink)
            .filter(
                MemoryLink.owner_id == owner_id,
                MemoryLink.source_id == memory.id,
                MemoryLink.origin == "obsidian",
            )
            .all()
        )
        for edge in existing:
            db.delete(edge)
        db.commit()

        # Re-parse wikilinks and create edges
        from app.obsidian.importer import extract_wikilinks

        content = md_file.read_text(encoding="utf-8", errors="replace")
        wikilinks = extract_wikilinks(content)

        for target_name, _display in wikilinks:
            # Find the target memory by title
            title_slug = target_name.strip().lower()
            target = (
                db.query(Memory)
                .filter(
                    Memory.owner_id == owner_id,
                    Memory.title.ilike(f"%{title_slug}%"),
                )
                .first()
            )
            if target and target.id != memory.id:
                self.memory.link(
                    db, owner_id,
                    source_id=memory.id,
                    target_id=target.id,
                    relation="wikilink",
                    weight=1.0,
                    origin="obsidian",
                )

    async def _delete_file(self, db: Session, owner_id: str, file_path: str) -> None:
        """Remove the memory node corresponding to a deleted vault note."""
        path_marker = f"<!-- imported from: {file_path} -->"
        memory = (
            db.query(Memory)
            .filter(
                Memory.owner_id == owner_id,
                Memory.source == "obsidian",
                Memory.content.like(f"%{path_marker}%"),
            )
            .first()
        )
        if memory:
            self.memory.forget(db, owner_id, memory.id)
            self.stats.files_deleted += 1
            logger.info("Removed memory for deleted note: %s", memory.title)


# ── Tests ────────────────────────────────────────────────────────────

def test_watcher_stats_defaults() -> None:
    stats = WatcherStats()
    s = stats.summary()
    assert s["files_imported"] == 0
    assert s["files_updated"] == 0
    assert s["files_deleted"] == 0
    assert s["is_running"] is False
    assert s["errors"] == []


def test_watcher_stats_summary() -> None:
    stats = WatcherStats()
    stats.files_imported = 5
    stats.files_updated = 3
    stats.files_deleted = 1
    stats.is_running = True
    stats.vault_path = "/vault"
    s = stats.summary()
    assert s["files_imported"] == 5
    assert s["files_updated"] == 3
    assert s["files_deleted"] == 1
    assert s["is_running"] is True
    assert s["vault_path"] == "/vault"
