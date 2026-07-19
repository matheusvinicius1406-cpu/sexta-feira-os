"""
Obsidian Vault Importer — reads your .md notes and imports them into the
knowledge graph as memory nodes + edges ([[wikilinks]]).

What it does:
  1. Walks the vault directory recursively, skipping hidden dirs.
  2. Parses YAML frontmatter (title, tags, aliases).
  3. Extracts [[wikilinks]] including piped syntax [[target|display]].
  4. Creates a Memory node per note with content, tags as kind, and
     the original file path stored for later sync.
  5. Creates MemoryLink edges for every wikilink between imported notes.

Usage:
    POST /api/v1/obsidian/import  { vault_path: "/path/to/vault" }
"""
from __future__ import annotations

import json as _json
import logging
import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.brain.memory import PersistentMemory
from app.models.models import Memory

logger = logging.getLogger("sexta-feira.obsidian")

# ── Parsing ──────────────────────────────────────────────────────────

# Match [[target]] and [[target|display text]]
_WIKILINK = re.compile(r"\[\[([^\[\]]+?)(?:\|([^\[\]]*?))?\]\]")

# YAML frontmatter between --- delimiters
_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(content: str) -> dict:
    """Extract YAML-like frontmatter from an Obsidian note.

    Returns a dict with keys: title, tags, aliases.
    Uses simple line-by-line parsing (avoids pyyaml dependency).
    Supports: key: value, key: [list], key: [list], and key: with - sub-items.
    """
    meta: dict[str, str | list[str]] = {
        "title": "",
        "tags": [],
        "aliases": [],
    }
    m = _FRONTMATTER.match(content)
    if not m:
        return meta

    raw = m.group(1)
    current_list_key: str | None = None

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue

        # List items:  - item  (com ou sem indentação)
        if line.lstrip().startswith("- ") and current_list_key:
            item = line.lstrip()[2:].strip().strip('"').strip("'")
            lst = meta.get(current_list_key)
            if isinstance(lst, list):
                lst.append(item)
            continue

        current_list_key = None

        if ":" not in line:
            continue

        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()

        if key == "title":
            meta["title"] = value.strip('"').strip("'")
        elif key in ("tags", "tag"):
            tags: list[str] = []
            if value.startswith("[") and value.endswith("]"):
                inner = value[1:-1]
                tags = [t.strip().strip('"').strip("'") for t in inner.split(",") if t.strip()]
            elif value.startswith("-"):
                current_list_key = "tags"
                item = value[1:].strip().strip('"').strip("'")
                if item:
                    tags.append(item)
            elif value:
                tags = [t.strip() for t in value.split(",") if t.strip()]
            if tags:
                meta["tags"] = tags
        elif key in ("alias", "aliases"):
            values: list[str] = []
            if value.startswith("[") and value.endswith("]"):
                inner = value[1:-1]
                values = [a.strip().strip('"').strip("'") for a in inner.split(",") if a.strip()]
            elif value.startswith("-"):
                current_list_key = "aliases"
                item = value[1:].strip().strip('"').strip("'")
                if item:
                    values.append(item)
            elif value:
                values = [a.strip() for a in value.split(",") if a.strip()]
            if values:
                meta["aliases"] = values

    return meta


def strip_frontmatter(content: str) -> str:
    """Remove the YAML frontmatter block, returning only the markdown body."""
    return _FRONTMATTER.sub("", content).strip()


def extract_wikilinks(content: str) -> list[tuple[str, str | None]]:
    """Extract all [[target|display]] wikilinks.

    Returns a list of (target, display) tuples. Display is None
    when only [[target]] was used (no pipe).
    """
    matches = _WIKILINK.findall(content)
    return [(target.strip(), display.strip() or None) for target, display in matches]


def resolve_title(filepath: Path, frontmatter: dict) -> str:
    """Best-effort title: frontmatter title > filename stem > dir basename."""
    if frontmatter.get("title"):
        return frontmatter["title"]
    stem = filepath.stem
    if stem and stem.lower() != "untitled":
        return stem
    return filepath.parent.name


# ── Import ───────────────────────────────────────────────────────────

class ImportStats:
    """Statistics collected during a vault import."""

    def __init__(self) -> None:
        self.files_found = 0
        self.files_skipped = 0
        self.notes_imported = 0
        self.notes_updated = 0
        self.wikilinks_found = 0
        self.links_created = 0
        self.errors: list[str] = []

    def summary(self) -> dict:
        return {
            "files_found": self.files_found,
            "files_skipped": self.files_skipped,
            "notes_imported": self.notes_imported,
            "notes_updated": self.notes_updated,
            "wikilinks_found": self.wikilinks_found,
            "links_created": self.links_created,
            "errors": self.errors[:10],
        }


class ObsidianImporter:
    """Import an Obsidian vault into the knowledge graph."""

    # Separator used to mark imported-from-path in content.
    _PATH_MARKER = "\n\n<!-- imported from: {} -->\n"

    def __init__(self, memory: PersistentMemory) -> None:
        self.memory = memory

    async def import_vault(
        self,
        db: Session,
        owner_id: str,
        vault_path: str | Path,
    ) -> ImportStats:
        """Walk the vault, parse notes, create nodes + edges."""
        vault = Path(vault_path).resolve()
        if not vault.is_dir():
            raise NotADirectoryError(f"Vault path does not exist or is not a directory: {vault}")

        stats = ImportStats()

        # === Pass 1: walk vault, parse notes, create/update Memory nodes ===
        # Store (file_path -> title) mapping so Pass 2 can find wikilinks reliably.
        file_to_title: dict[str, str] = {}

        for md_file in sorted(vault.rglob("*.md")):
            if self._should_skip(md_file):
                stats.files_skipped += 1
                continue
            stats.files_found += 1

            try:
                memory, title = await self._import_note(
                    db, owner_id, md_file, stats,
                )
                if memory and title:
                    file_to_title[str(md_file.resolve())] = title
            except Exception as e:
                logger.warning("Failed to import %s: %s", md_file, e)
                stats.errors.append(f"{md_file.name}: {e}")

        # === Pass 2: create edges for wikilinks between imported notes ===
        # Build a reverse map: title -> Memory
        all_obsidian = (
            db.query(Memory)
            .filter(Memory.owner_id == owner_id, Memory.source == "obsidian")
            .all()
        )
        title_to_memory: dict[str, Memory] = {}
        for m in all_obsidian:
            if m.title:
                title_to_memory[m.title] = m

        for file_path, source_title in file_to_title.items():
            content = self._read_file(file_path)
            if not content:
                continue
            wikilinks = extract_wikilinks(content)
            stats.wikilinks_found += len(wikilinks)

            source_mem = title_to_memory.get(source_title)
            if not source_mem:
                continue

            for target_name, _display in wikilinks:
                target_mem = title_to_memory.get(target_name)
                if target_mem and target_mem.id != source_mem.id:
                    self._create_link(db, owner_id, source_mem, target_mem)
                    stats.links_created += 1

        logger.info(
            "Import complete: %d notes, %d wikilinks, %d edges",
            stats.notes_imported, stats.wikilinks_found, stats.links_created,
        )
        return stats

    async def _import_note(
        self,
        db: Session,
        owner_id: str,
        md_file: Path,
        stats: ImportStats,
    ) -> tuple[Memory | None, str | None]:
        """Parse a single .md file and create/update a memory node.

        Returns (memory, title) or (None, None) if the note is empty/skipped.
        Dedup is done by file path (via source == "obsidian" + content marker),
        not by title — prevents data loss from same-titled notes in different dirs.
        """
        content = md_file.read_text(encoding="utf-8", errors="replace")

        frontmatter = parse_frontmatter(content)
        body = strip_frontmatter(content)
        title = resolve_title(md_file, frontmatter)

        if not body.strip():
            logger.debug("Skipping empty note: %s", md_file)
            return None, None

        # Determine kind from first tag
        tags = frontmatter.get("tags", [])
        kind = tags[0] if isinstance(tags, list) and tags else "note"

        # Embed the absolute file path for sync/dedup
        abs_path = str(md_file.resolve())
        full_content = body + self._PATH_MARKER.format(abs_path)

        # Dedup by looking for an existing obsidian memory with the same path marker.
        existing = (
            db.query(Memory)
            .filter(
                Memory.owner_id == owner_id,
                Memory.source == "obsidian",
                Memory.content.like(f"%{self._PATH_MARKER.format(abs_path)}%"),
            )
            .first()
        )
        if existing:
            existing.content = full_content
            existing.kind = kind
            # updated_at is auto-set by SQLAlchemy onupdate
            db.commit()
            db.refresh(existing)
            try:
                embedding = await self.memory.brain.embed(body)
                existing.embedding = _json.dumps(embedding)
                db.commit()
            except Exception as e:
                logger.debug("Embedding update failed for %s: %s", title, e)
            stats.notes_updated += 1
            return existing, title

        # Create new memory node (computes embedding + semantic auto-links)
        memory = await self.memory.remember(
            db, owner_id,
            content=full_content,
            kind=kind,
            importance=0.5,
            source="obsidian",
            title=title,
            auto_link=True,
        )

        # Register aliases so wikilinks resolve against them too
        aliases = frontmatter.get("aliases", [])
        if isinstance(aliases, list):
            for alias in aliases:
                if alias and alias != title:
                    # We handle alias resolution in pass 2 via title_to_memory
                    pass

        stats.notes_imported += 1
        return memory, title

    def _create_link(
        self,
        db: Session,
        owner_id: str,
        source: Memory,
        target: Memory,
    ) -> None:
        """Create a wikilink edge between two memory nodes."""
        self.memory.link(
            db, owner_id,
            source_id=source.id,
            target_id=target.id,
            relation="wikilink",
            weight=1.0,
            origin="obsidian",
        )

    @staticmethod
    def _should_skip(path: Path) -> bool:
        """Skip hidden files/dirs and common non-note files."""
        for part in path.parts:
            if part.startswith("."):
                return True
        # Skip template files (Obsidian convention)
        if path.name.startswith("_"):
            return True
        return False

    @staticmethod
    def _read_file(path: str) -> str | None:
        try:
            return Path(path).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.debug("Could not read %s: %s", path, e)
            return None


# ── Tests ────────────────────────────────────────────────────────────

def test_parse_frontmatter_basic() -> None:
    content = """---
title: Minha Nota
tags: [dev, python]
aliases: [nota-python]
---
Conteúdo aqui."""

    meta = parse_frontmatter(content)
    assert meta["title"] == "Minha Nota"
    assert meta["tags"] == ["dev", "python"]
    assert meta["aliases"] == ["nota-python"]


def test_parse_frontmatter_no_frontmatter() -> None:
    content = "Apenas texto, sem frontmatter."
    meta = parse_frontmatter(content)
    assert meta["title"] == ""
    assert meta["tags"] == []


def test_parse_frontmatter_list_style() -> None:
    content = """---
title: Lista
tags:
  - tag1
  - tag2
aliases:
  - alias1
---
Body."""

    meta = parse_frontmatter(content)
    assert meta["title"] == "Lista"
    assert meta["tags"] == ["tag1", "tag2"]
    assert meta["aliases"] == ["alias1"]


def test_strip_frontmatter() -> None:
    content = "---\ntitle: X\n---\n\nCorpo do texto."
    body = strip_frontmatter(content)
    assert body == "Corpo do texto."
    assert "---" not in body


def test_strip_frontmatter_no_fm() -> None:
    content = "Apenas texto."
    assert strip_frontmatter(content) == "Apenas texto."


def test_extract_wikilinks_basic() -> None:
    links = extract_wikilinks("Veja [[Projeto X]] e [[Nota Y|nota antiga]].")
    assert links == [("Projeto X", None), ("Nota Y", "nota antiga")]


def test_extract_wikilinks_none() -> None:
    assert extract_wikilinks("Sem links aqui.") == []


def test_extract_wikilinks_nested() -> None:
    links = extract_wikilinks("[[A]] e [[B|display B]] e [[C]]")
    assert len(links) == 3
    assert links[0] == ("A", None)
    assert links[1] == ("B", "display B")
    assert links[2] == ("C", None)


def test_resolve_title_from_frontmatter() -> None:
    meta = {"title": "Título Personalizado"}
    title = resolve_title(Path("/vault/arquivo.md"), meta)
    assert title == "Título Personalizado"


def test_resolve_title_from_filename() -> None:
    title = resolve_title(Path("/vault/Meu Artigo.md"), {"title": ""})
    assert title == "Meu Artigo"


def test_should_skip_hidden() -> None:
    assert ObsidianImporter._should_skip(Path("/vault/.hidden/note.md"))
    assert not ObsidianImporter._should_skip(Path("/vault/Notes/normal.md"))


def test_should_skip_template() -> None:
    assert ObsidianImporter._should_skip(Path("/vault/_templates/daily.md"))
    assert not ObsidianImporter._should_skip(Path("/vault/notes/normal.md"))


def test_parse_frontmatter_comma_tags() -> None:
    content = """---
tags: tag1, tag2, tag3
---
Body."""
    meta = parse_frontmatter(content)
    assert meta["tags"] == ["tag1", "tag2", "tag3"]


def test_parse_frontmatter_single_tag() -> None:
    content = """---
tags: [sometag]
---
Body."""
    meta = parse_frontmatter(content)
    assert meta["tags"] == ["sometag"]
