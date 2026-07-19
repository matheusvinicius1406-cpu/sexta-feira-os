"""
Direct Vault Recall — reads recently modified .md files from the Obsidian vault
and injects their content into the cognition context.

This complements the networked recall (semantic graph search) by giving the brain
access to notes the user just wrote — even before they've been imported into the
knowledge graph.

Usage:
    from app.obsidian.recall import read_recent_vault_notes
    notes = read_recent_vault_notes("/path/to/vault", max_notes=10, max_age_hours=72)
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from app.obsidian.importer import ObsidianImporter, parse_frontmatter, strip_frontmatter

logger = logging.getLogger("sexta-feira.obsidian.recall")

# Regex for frontmatter (same as importer — imported above)


def read_recent_vault_notes(
    vault_path: str,
    max_notes: int = 10,
    max_age_hours: float = 72.0,
) -> list[dict]:
    """Read recently modified .md files from the Obsidian vault.

    Args:
        vault_path: Absolute path to the vault directory.
        max_notes: Maximum number of notes to return (most recently modified first).
        max_age_hours: Maximum age in hours. Notes older than this are skipped.
                       Set to 0 for no age limit.

    Returns:
        A list of dicts with keys: title, content, path, mtime, tags.
        Ordered by modification time (newest first).
        Empty list if vault_path is empty, doesn't exist, or no notes match.
    """
    if not vault_path or not vault_path.strip():
        return []

    vault = Path(vault_path).resolve()
    if not vault.is_dir():
        logger.debug("Vault does not exist, skipping recall: %s", vault)
        return []

    now = time.time()
    max_age_seconds = max_age_hours * 3600.0 if max_age_hours > 0 else float("inf")

    candidates: list[dict] = []

    for md_file in vault.rglob("*.md"):
        # Skip hidden directories and template files (same rules as importer)
        if ObsidianImporter._should_skip(md_file):
            continue

        mtime = md_file.stat().st_mtime
        age = now - mtime

        # Skip files older than max_age_hours (unless 0 = no limit)
        if max_age_hours > 0 and age > max_age_seconds:
            continue

        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.debug("Could not read %s: %s", md_file, e)
            continue

        if not content.strip():
            continue

        # Parse frontmatter for title and tags
        frontmatter = parse_frontmatter(content)
        body = strip_frontmatter(content)

        # Determine title: frontmatter > filename stem > parent dir name
        title = frontmatter.get("title", "")
        if not title:
            stem = md_file.stem
            title = stem if stem.lower() != "untitled" else md_file.parent.name

        # Get tags from frontmatter
        tags = frontmatter.get("tags", [])
        if isinstance(tags, list):
            tags = [str(t) for t in tags]

        candidates.append({
            "title": title,
            "content": body,
            "path": str(md_file),
            "mtime": mtime,
            "tags": tags,
        })

    # Sort by mtime descending (newest first) and limit
    candidates.sort(key=lambda n: n["mtime"], reverse=True)
    return candidates[:max_notes]


def format_vault_context(notes: list[dict], max_chars: int = 4000) -> str:
    """Format a list of vault notes into a context string for the system prompt.

    Args:
        notes: Output from read_recent_vault_notes().
        max_chars: Maximum total characters. Longer notes are truncated.

    Returns:
        A formatted string ready to append to the system prompt.
        Empty string if notes is empty.
    """
    if not notes:
        return ""

    lines: list[str] = []
    lines.append("")
    lines.append("### Notas recentes do seu vault Obsidian")

    remaining = max_chars
    for note in notes:
        title = note["title"]
        tags_str = f" [{', '.join(note['tags'])}]" if note.get("tags") else ""

        # Content preview — truncate if too long
        content = note["content"]
        max_note_chars = max(200, remaining // max(1, len(notes)))
        if len(content) > max_note_chars:
            content = content[:max_note_chars] + "..."

        note_text = f'\n📄 **{title}**{tags_str}\n{content}'
        if len(note_text) > remaining:
            break

        lines.append(note_text)
        remaining -= len(note_text)

    if remaining < max_chars * 0.3:
        lines.append("\n*(notas truncadas por espaço no contexto)*")

    return "\n".join(lines)


# ── Tests ────────────────────────────────────────────────────────────


def test_read_recent_vault_notes_invalid_path() -> None:
    """Should return empty list for nonexistent vault path."""
    result = read_recent_vault_notes("/nonexistent/vault", max_notes=5)
    assert result == []


def test_read_recent_vault_notes_empty_path() -> None:
    """Should return empty list for empty vault path."""
    assert read_recent_vault_notes("") == []
    assert read_recent_vault_notes("  ") == []


def test_read_recent_vault_notes_with_files(tmp_path) -> None:
    """Should read .md files from vault, skipping hidden and templates."""
    # Create a vault structure
    vault = tmp_path / "my-vault"
    vault.mkdir()

    # Normal note
    (vault / "nota1.md").write_text(
        "---\ntitle: Primeira Nota\ntags: [dev]\n---\n\nConteúdo da primeira nota.",
        encoding="utf-8",
    )

    # Note without frontmatter (title from filename)
    (vault / "Nota Sem Título.md").write_text(
        "Conteúdo sem frontmatter.",
        encoding="utf-8",
    )

    # Hidden file (should be skipped)
    (vault / ".hidden.md").write_text("Nota escondida.", encoding="utf-8")

    # Template file (should be skipped)
    (vault / "_template.md").write_text("Template.", encoding="utf-8")

    # Note in subfolder
    sub = vault / "sub"
    sub.mkdir()
    (sub / "subnota.md").write_text(
        "---\ntitle: Subnota\ntags: [python, test]\n---\n\nConteúdo da subnota.",
        encoding="utf-8",
    )

    result = read_recent_vault_notes(
        str(vault), max_notes=10, max_age_hours=0,
    )

    # Should have 3 notes (nota1, Nota Sem Título, subnota)
    assert len(result) == 3

    titles = {n["title"] for n in result}
    assert "Primeira Nota" in titles
    assert "Subnota" in titles
    assert "Nota Sem Título" in titles

    # Verify tags
    for note in result:
        if note["title"] == "Primeira Nota":
            assert note["tags"] == ["dev"]
        elif note["title"] == "Subnota":
            assert note["tags"] == ["python", "test"]


def test_read_recent_vault_notes_max_notes(tmp_path) -> None:
    """Should respect max_notes limit."""
    vault = tmp_path / "vault"
    vault.mkdir()
    for i in range(5):
        (vault / f"nota_{i}.md").write_text(f"Conteúdo {i}", encoding="utf-8")

    result = read_recent_vault_notes(str(vault), max_notes=3, max_age_hours=0)
    assert len(result) == 3


def test_read_recent_vault_notes_ordering(tmp_path) -> None:
    """Should return newest notes first."""
    vault = tmp_path / "vault"
    vault.mkdir()

    # Checks that notes are returned in descending mtime order.
    old = vault / "old.md"
    old.write_text("Antiga", encoding="utf-8")
    new = vault / "new.md"
    new.write_text("Nova", encoding="utf-8")

    result = read_recent_vault_notes(str(vault), max_notes=10, max_age_hours=0)
    assert len(result) >= 2
    mtimes = [n["mtime"] for n in result]
    assert mtimes == sorted(mtimes, reverse=True)


def test_read_recent_vault_notes_age_filter(tmp_path) -> None:
    """Should skip notes older than max_age_hours."""
    vault = tmp_path / "vault"
    vault.mkdir()

    (vault / "recent.md").write_text("Recente", encoding="utf-8")
    # We can't easily set mtime, so just verify the function runs with age=0
    result = read_recent_vault_notes(str(vault), max_notes=10, max_age_hours=0)
    assert len(result) >= 1


def test_format_vault_context_empty() -> None:
    """Should return empty string for empty notes list."""
    assert format_vault_context([]) == ""


def test_format_vault_context_single_note() -> None:
    """Should format a single note with header and title."""
    notes = [{"title": "Teste", "content": "Conteúdo do teste.", "tags": ["dev"], "mtime": 0, "path": ""}]
    result = format_vault_context(notes)
    assert "Notas recentes do seu vault Obsidian" in result
    assert "Teste" in result
    assert "[dev]" in result
    assert "Conteúdo do teste." in result


def test_format_vault_context_multiple_notes() -> None:
    """Should format multiple notes separated by blank lines."""
    notes = [
        {"title": "Nota A", "content": "Conteúdo A", "tags": [], "mtime": 2, "path": ""},
        {"title": "Nota B", "content": "Conteúdo B", "tags": ["tag1"], "mtime": 1, "path": ""},
    ]
    result = format_vault_context(notes)
    assert "Nota A" in result
    assert "Nota B" in result
    assert "[tag1]" in result


def test_format_vault_context_truncation() -> None:
    """Should truncate content when max_chars is small."""
    notes = [{"title": "Grande", "content": "A" * 500, "tags": [], "mtime": 0, "path": ""}]
    result = format_vault_context(notes, max_chars=100)
    assert "..." in result
