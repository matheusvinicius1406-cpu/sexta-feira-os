"""
Obsidian Vault Exporter — writes your knowledge graph as .md notes.

What it does:
  1. Reads all Memory nodes from the graph (or just source="obsidian").
  2. For obsidian-imported notes: recovers original path from content marker,
     preserving the original vault structure.
  3. For brain-created memories (auto_learned, tool, manual): creates new
     .md files under `__sexta__/` subfolder.
  4. Generates proper YAML frontmatter (title, tags, created, updated).
  5. Adds [[wikilinks]] to connected memory nodes.
  6. Creates/updates the .md files in the vault directory.

Usage:
    POST /api/v1/obsidian/export  { vault_path: "/path/to/vault" }
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.models import Memory, MemoryLink

logger = logging.getLogger("sexta-feira.obsidian")

# ── Module-level constants ───────────────────────────────────────────

# Subfolder for brain-created memories (not from vault)
_BRAIN_FOLDER = "__sexta__"
# Subfolder within __sexta__ for auto-learned facts
_AUTO_FOLDER = "auto-learned"

# ── Helpers ──────────────────────────────────────────────────────────

# Matcher for the import path marker embedded in imported notes.
_PATH_MARKER_RE = re.compile(r"<!-- imported from:\s*(.+?)\s*-->")


def _recover_vault_path(content: str) -> str | None:
    """Extract the original vault file path from the import marker."""
    m = _PATH_MARKER_RE.search(content)
    return m.group(1).strip() if m else None


def _strip_path_marker(content: str) -> str:
    """Remove the import path marker from content for clean output."""
    return _PATH_MARKER_RE.sub("", content).strip()


def _build_frontmatter(
    title: str,
    kind: str,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    source: str = "sexta-feira",
) -> str:
    """Build YAML frontmatter string."""
    lines = ["---"]
    lines.append(f"title: \"{_escape_yaml(title)}\"")
    lines.append(f"tags: [{kind}]")
    lines.append(f"source: {source}")
    if created_at:
        lines.append(f"created_at: {created_at.isoformat()}")
    if updated_at:
        lines.append(f"updated_at: {updated_at.isoformat()}")
    lines.append("---")
    return "\n".join(lines)


def _escape_yaml(value: str) -> str:
    """Escape a string for YAML single-line value."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _slugify(title: str) -> str:
    """Turn a title into a safe filename."""
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9\u00e0-\u00ff\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug[:120]


# ── Stats ────────────────────────────────────────────────────────────

class ExportStats:
    """Statistics collected during a vault export."""

    def __init__(self) -> None:
        self.notes_written = 0
        self.notes_updated = 0
        self.notes_skipped = 0
        self.links_referenced = 0
        self.errors: list[str] = []

    def summary(self) -> dict:
        return {
            "notes_written": self.notes_written,
            "notes_updated": self.notes_updated,
            "notes_skipped": self.notes_skipped,
            "links_referenced": self.links_referenced,
            "errors": self.errors[:10],
        }


# ── Exporter ─────────────────────────────────────────────────────────

class ObsidianExporter:
    """Export memory graph nodes as Obsidian .md notes."""

    def __init__(self) -> None:
        pass

    def export_vault(
        self,
        db: Session,
        owner_id: str,
        vault_path: str | Path,
        include_all: bool = True,
    ) -> ExportStats:
        """Write memory nodes as .md files into the vault.

        Args:
            db: Database session.
            owner_id: The owner's id.
            vault_path: Absolute path to the Obsidian vault directory.
            include_all: If True, export ALL memory nodes. If False, only
                         those with source="obsidian".

        Returns:
            ExportStats with summary.
        """
        vault = Path(vault_path).resolve()
        vault.mkdir(parents=True, exist_ok=True)

        stats = ExportStats()

        # Query memory nodes
        query = db.query(Memory).filter(Memory.owner_id == owner_id)
        if not include_all:
            query = query.filter(Memory.source == "obsidian")

        memories = query.order_by(Memory.created_at).all()
        if not memories:
            logger.info("No memories to export.")
            return stats

        # Build a map of id -> title for wikilink resolution
        id_to_title: dict[str, str] = {}
        for m in memories:
            id_to_title[m.id] = m.title or m.content[:60]

        # Also include linked nodes that might be outside the export set
        # so [[wikilinks]] point to existing notes
        all_ids = {m.id for m in memories}
        links = (
            db.query(MemoryLink)
            .filter(
                MemoryLink.owner_id == owner_id,
                or_(
                    MemoryLink.source_id.in_(all_ids),
                    MemoryLink.target_id.in_(all_ids),
                ),
            )
            .all()
        )
        # Collect target nodes that are NOT in the export set
        for link in links:
            if link.target_id not in all_ids:
                target = db.query(Memory).filter(Memory.id == link.target_id).first()
                if target:
                    id_to_title[target.id] = target.title or target.content[:60]

        # Write each note
        for mem in memories:
            try:
                self._write_note(db, owner_id, vault, mem, links, id_to_title, stats)
            except Exception as e:
                logger.warning("Failed to export %s: %s", mem.title, e)
                stats.errors.append(f"{mem.title}: {e}")

        logger.info(
            "Export complete: %d written, %d updated, %d links referenced",
            stats.notes_written, stats.notes_updated, stats.links_referenced,
        )
        return stats

    def _write_note(
        self,
        db: Session,
        owner_id: str,
        vault: Path,
        mem: Memory,
        all_links: list[MemoryLink],
        id_to_title: dict[str, str],
        stats: ExportStats,
    ) -> None:
        """Write a single memory node as a .md file."""
        # Determine file path
        clean_content = _strip_path_marker(mem.content)
        filepath = self._resolve_path(vault, mem, clean_content)

        # Build frontmatter
        title = mem.title or mem.content[:60]
        frontmatter = _build_frontmatter(
            title=title,
            kind=mem.kind,
            created_at=mem.created_at,
            updated_at=mem.updated_at,
            source=mem.source,
        )

        # Build wikilinks section
        wikilinks = self._get_wikilinks_for_node(mem.id, all_links, id_to_title)
        stats.links_referenced += len(wikilinks)

        # Build full markdown
        body_lines = [clean_content] if clean_content else []
        if wikilinks:
            body_lines.append("")
            body_lines.append("## Links")
            for target_title in wikilinks:
                body_lines.append(f"- [[{target_title}]]")

        full_md = frontmatter + "\n\n" + "\n".join(body_lines)

        # Write file
        filepath.parent.mkdir(parents=True, exist_ok=True)
        was_update = filepath.exists()
        filepath.write_text(full_md, encoding="utf-8")

        if was_update:
            stats.notes_updated += 1
            logger.debug("Updated: %s", filepath)
        else:
            stats.notes_written += 1
            logger.debug("Written: %s", filepath)

    def _resolve_path(self, vault: Path, mem: Memory, clean_content: str) -> Path:
        """Determine the file path for a memory node.

        Priority:
          1. Recover original vault path from import marker (for source="obsidian")
          2. Use title as filename in __sexta__ subfolder (for other sources)
        """
        if mem.source == "obsidian":
            original = _recover_vault_path(mem.content)
            if original:
                orig_path = Path(original)
                # Only use original path if it's inside the vault
                try:
                    orig_path.relative_to(vault)
                    return orig_path
                except ValueError:
                    pass  # not inside vault, fall through

        # Fallback: use title as filename in __sexta__ subfolder
        title = mem.title or mem.content[:60]
        filename = _slugify(title) + ".md"
        return vault / _BRAIN_FOLDER / filename

    @staticmethod
    def _get_wikilinks_for_node(
        node_id: str,
        all_links: list[MemoryLink],
        id_to_title: dict[str, str],
    ) -> list[str]:
        """Get sorted unique wikilink titles for a node."""
        titles: set[str] = set()
        for link in all_links:
            if link.source_id == node_id:
                title = id_to_title.get(link.target_id)
                if title:
                    titles.add(title)
            elif link.target_id == node_id:
                # Also include backlinks
                title = id_to_title.get(link.source_id)
                if title:
                    titles.add(title)
        return sorted(titles)


# ── Auto-export (called by cognition.py) ────────────────────────────


def export_auto_learned_fact(
    vault_path: str,
    title: str,
    content: str,
    kind: str = "fact",
) -> str | None:
    """Write an auto-learned fact as a .md note in the vault.

    Called by Cognition._auto_learn when the brain distils a fact from
    a conversation. Creates/updates a note under:
        vault/__sexta__/auto-learned/{slug}.md

    Args:
        vault_path: Absolute path to the Obsidian vault directory.
        title: The title of the note (the fact itself or a label).
        content: The markdown body of the note.
        kind: The kind tag (fact, preference, routine, etc.).

    Returns:
        The file path as string if written, None if vault_path is empty.
    """
    if not vault_path or not vault_path.strip():
        return None

    vault = Path(vault_path).resolve()
    if not vault.is_dir():
        logger.warning("Vault path does not exist, creating: %s", vault)
        vault.mkdir(parents=True, exist_ok=True)

    # Build the file path
    filename = _slugify(title) + ".md"
    filepath = vault / _BRAIN_FOLDER / _AUTO_FOLDER / filename

    # Build frontmatter
    now = datetime.now(timezone.utc)
    frontmatter = _build_frontmatter(
        title=title,
        kind=kind,
        created_at=now,
        updated_at=now,
        source="auto_learned",
    )

    # Build full markdown
    full_md = frontmatter + "\n\n" + content

    # Write file
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(full_md, encoding="utf-8")

    logger.info("Auto-exported fact to vault: %s", filepath)
    return str(filepath)


# ── Tests ────────────────────────────────────────────────────────────

def test_recover_vault_path() -> None:
    content = "Nota legal\n\n<!-- imported from: /vault/notes/minha-nota.md -->\n"
    assert _recover_vault_path(content) == "/vault/notes/minha-nota.md"


def test_recover_vault_path_none() -> None:
    assert _recover_vault_path("Nota sem marcador") is None


def test_strip_path_marker() -> None:
    content = "Corpo\n\n<!-- imported from: /path.md -->\n"
    assert _strip_path_marker(content) == "Corpo"


def test_strip_path_marker_clean() -> None:
    assert _strip_path_marker("Só texto") == "Só texto"


def test_build_frontmatter() -> None:
    fm = _build_frontmatter("Minha Nota", "note", source="obsidian")
    assert "title: \"Minha Nota\"" in fm
    assert "tags: [note]" in fm
    assert "source: obsidian" in fm
    assert fm.startswith("---")
    assert fm.endswith("---")


def test_build_frontmatter_with_dates() -> None:
    from datetime import datetime, timezone
    dt = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
    fm = _build_frontmatter("Teste", "fact", created_at=dt, updated_at=dt)
    assert "2024-01-15" in fm
    assert "10:30" in fm


def test_slugify() -> None:
    assert _slugify("Minha Nota Legal!") == "minha-nota-legal"
    assert _slugify("Projeto X") == "projeto-x"
    assert _slugify("Café") == "café"


def test_escape_yaml() -> None:
    assert _escape_yaml('Nota "especial"') == 'Nota \\"especial\\"'
    assert _escape_yaml("Normal") == "Normal"


def test_get_wikilinks_for_node() -> None:
    id_to_title = {
        "a": "Nota A",
        "b": "Nota B",
        "c": "Nota C",
    }
    links = [
        MemoryLink(id=str(uuid.uuid4()), source_id="a", target_id="b",
                    owner_id="owner", relation="wikilink"),
        MemoryLink(id=str(uuid.uuid4()), source_id="c", target_id="a",
                    owner_id="owner", relation="wikilink"),
    ]

    result = ObsidianExporter._get_wikilinks_for_node("a", links, id_to_title)
    assert "Nota B" in result   # forward link
    assert "Nota C" in result   # backlink
    assert len(result) == 2


def test_get_wikilinks_for_node_no_links() -> None:
    assert ObsidianExporter._get_wikilinks_for_node("x", [], {}) == []


def test_slugify_special_chars() -> None:
    assert _slugify("O que é JARVIS?") == "o-que-é-jarvis"
    assert _slugify("  espaços  ") == "espaços"


def test_export_auto_learned_fact_no_vault() -> None:
    """Should return None when vault_path is empty."""
    result = export_auto_learned_fact("", "test", "content")
    assert result is None


def test_export_auto_learned_fact_creates_file(tmp_path) -> None:
    """Should write a .md file with frontmatter in the vault."""
    vault = tmp_path / "my-vault"
    result = export_auto_learned_fact(
        vault_path=str(vault),
        title="Usuário gosta de café",
        content="O usuário prefere café forte pela manhã.",
        kind="preference",
    )
    assert result is not None
    filepath = Path(result)
    assert filepath.exists()
    assert filepath.suffix == ".md"

    content = filepath.read_text(encoding="utf-8")
    assert "title: \"Usuário gosta de café\"" in content
    assert "tags: [preference]" in content
    assert "source: auto_learned" in content
    assert "O usuário prefere café forte pela manhã." in content
    assert content.startswith("---")
    assert "auto-learned" in str(filepath)


def test_export_auto_learned_fact_creates_vault_dir(tmp_path) -> None:
    """Should create the vault directory if it doesn't exist."""
    vault = tmp_path / "nonexistent" / "vault"
    assert not vault.exists()
    result = export_auto_learned_fact(
        vault_path=str(vault),
        title="Fato novo",
        content="Um fato qualquer.",
    )
    assert result is not None
    assert vault.exists()
    assert Path(result).exists()


def test_export_auto_learned_fact_updates_existing(tmp_path) -> None:
    """Should overwrite existing file with same slug."""
    vault = tmp_path / "vault"
    export_auto_learned_fact(str(vault), "Mesmo título", "Versão 1")
    result = export_auto_learned_fact(str(vault), "Mesmo título", "Versão 2")
    assert result is not None
    content = Path(result).read_text(encoding="utf-8")
    assert "Versão 2" in content
    assert "Versão 1" not in content
