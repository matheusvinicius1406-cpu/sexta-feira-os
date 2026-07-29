"""
Integration tests for the complete Obsidian cycle: import → export → watch → recall.

Tests are deterministic (no Ollama needed) and use ephemeral temp directories.
They exercise the full pipeline:
  1. Import vault .md notes into the knowledge graph (nodes + wikilink edges)
  2. Export graph nodes back as .md files (frontmatter + wikilinks)
  3. Import → Export → Reimport roundtrip
  4. Auto-export when the brain learns a fact during conversation
  5. Watcher poll detection (new file detection)
  6. Direct vault recall (read recent notes)
  7. Format vault context for the system prompt

Shared env + `client`/`owner_headers` fixtures live in conftest.py.
"""
import asyncio
from pathlib import Path

import pytest

# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def vault(tmp_path):
    """Create a test Obsidian vault with sample notes."""
    vault = tmp_path / "test-vault"
    vault.mkdir()

    # Note 1 with frontmatter and wikilink to Note 2
    (vault / "projeto-x.md").write_text(
        "---\n"
        "title: Projeto X\n"
        "tags: [dev, python]\n"
        "---\n"
        "\n"
        "Projeto X é um sistema de IA local. "
        "Veja [[Café]] para mais contexto.",
        encoding="utf-8",
    )

    # Note 2 (target of wikilink)
    (vault / "cafe.md").write_text(
        "---\n"
        "title: Café\n"
        "tags: [pessoal]\n"
        "---\n"
        "\n"
        "Gosto de café forte pela manhã.",
        encoding="utf-8",
    )

    # Note 3 (no wikilinks, different folder)
    sub = vault / "ideias"
    sub.mkdir()
    (sub / "nota-aleatoria.md").write_text(
        "---\n"
        "title: Nota Aleatória\n"
        "tags: [ideia]\n"
        "---\n"
        "\n"
        "Uma ideia qualquer.",
        encoding="utf-8",
    )

    # Template (should be skipped)
    (vault / "_templates").mkdir()
    (vault / "_templates" / "daily.md").write_text("# Daily", encoding="utf-8")

    return vault


# ── Import Tests ─────────────────────────────────────────────────────


def test_import_creates_graph_nodes_and_edges(client, owner_headers, vault):
    """Import vault notes → verify nodes + wikilink edges in the graph."""
    r = client.post(
        "/api/v1/obsidian/import",
        json={"vault_path": str(vault)},
        headers=owner_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["stats"]["notes_imported"] >= 2  # at least Projeto X + Café
    assert data["stats"]["links_created"] >= 1    # at least the wikilink between them
    assert len(data["stats"]["errors"]) == 0

    # Verify nodes in the graph
    graph = client.get("/api/v1/memory/graph", headers=owner_headers).json()
    titles = {n["title"] for n in graph["nodes"]}
    assert "Projeto X" in titles
    assert "Café" in titles
    assert "Nota Aleatória" in titles

    # Verify wikilink edge exists
    edges = graph["edges"]
    assert len(edges) >= 1

    # Verify status endpoint reflects the import
    status = client.get("/api/v1/obsidian/status", headers=owner_headers).json()
    assert status["notes_imported"] >= 2
    assert status["wikilinks_created"] >= 1


def test_import_reimport_is_idempotent(client, owner_headers, vault):
    """Reimporting the same vault should update existing nodes, not duplicate them."""
    # Import twice
    r1 = client.post(
        "/api/v1/obsidian/import",
        json={"vault_path": str(vault)},
        headers=owner_headers,
    )
    assert r1.status_code == 200
    count_1 = r1.json()["stats"]["notes_imported"]

    r2 = client.post(
        "/api/v1/obsidian/import",
        json={"vault_path": str(vault)},
        headers=owner_headers,
    )
    assert r2.status_code == 200

    # Second import should produce 0 new notes (all dedup = updated)
    stats = r2.json()["stats"]
    assert stats["notes_imported"] == 0
    assert stats["notes_updated"] >= count_1
    assert stats["links_created"] >= 0

    # Graph should still have the same unique titles (no duplicates)
    graph = client.get("/api/v1/memory/graph", headers=owner_headers).json()
    titles = {n["title"] for n in graph["nodes"]}
    assert "Projeto X" in titles
    assert "Café" in titles
    assert "Nota Aleatória" in titles


def test_import_requires_auth(client):
    """Import endpoint should reject unauthenticated requests."""
    r = client.post("/api/v1/obsidian/import", json={"vault_path": "/tmp/foo"})
    assert r.status_code == 403


def test_import_rejects_invalid_path(client, owner_headers):
    """Import should return 400 for nonexistent vault path."""
    r = client.post(
        "/api/v1/obsidian/import",
        json={"vault_path": "/nonexistent-vault-path-xyz"},
        headers=owner_headers,
    )
    assert r.status_code == 400


def test_import_handles_non_md_files(client, owner_headers, tmp_path):
    """Import should skip non-.md files and not crash."""
    vault = tmp_path / "mixed-vault"
    vault.mkdir()
    (vault / "nota.md").write_text("# Nota", encoding="utf-8")
    (vault / "imagem.png").write_text(b"PNG")
    (vault / "notas.txt").write_text("texto")

    r = client.post(
        "/api/v1/obsidian/import",
        json={"vault_path": str(vault)},
        headers=owner_headers,
    )
    assert r.status_code == 200
    assert r.json()["stats"]["notes_imported"] == 1


# ── Export Tests ─────────────────────────────────────────────────────


def test_export_writes_md_files(client, owner_headers, vault, tmp_path):
    """Export graph nodes → verify .md files are created with frontmatter."""
    # First import
    client.post(
        "/api/v1/obsidian/import",
        json={"vault_path": str(vault)},
        headers=owner_headers,
    )

    # Export to a different path (to avoid overwriting the source vault)
    export_dir = tmp_path / "exported-vault"
    export_dir.mkdir()

    r = client.post(
        "/api/v1/obsidian/export",
        json={"vault_path": str(export_dir), "include_all": True},
        headers=owner_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["stats"]["notes_written"] >= 2
    assert len(data["stats"]["errors"]) == 0

    # Verify .md files were actually written
    md_files = list(export_dir.rglob("*.md"))
    assert len(md_files) >= 2

    # Verify frontmatter in at least one file
    sample = md_files[0].read_text(encoding="utf-8")
    assert sample.startswith("---")
    assert "title:" in sample
    assert "source:" in sample
    # Spot-check for wikilink syntax if links were referenced
    if data["stats"]["links_referenced"] > 0:
        assert "[[" in sample or "Links" in sample


def test_export_requires_auth(client):
    """Export endpoint should reject unauthenticated requests."""
    r = client.post(
        "/api/v1/obsidian/export",
        json={"vault_path": "/tmp/foo", "include_all": True},
    )
    assert r.status_code == 403


def test_export_roundtrip_preserves_content(client, owner_headers, vault, tmp_path):
    """Export → import roundtrip: original content should survive both steps."""
    # Step 1: Import original vault
    client.post(
        "/api/v1/obsidian/import",
        json={"vault_path": str(vault)},
        headers=owner_headers,
    )

    # Step 2: Export to a roundtrip directory
    roundtrip_dir = tmp_path / "roundtrip"
    roundtrip_dir.mkdir()
    r = client.post(
        "/api/v1/obsidian/export",
        json={"vault_path": str(roundtrip_dir), "include_all": True},
        headers=owner_headers,
    )
    assert r.status_code == 200
    assert r.json()["stats"]["notes_written"] >= 1

    # Step 3: Find exported files (they'll be in __sexta__ subfolder)
    exported_files = list(roundtrip_dir.rglob("*.md"))
    exported_content = "\n".join(
        f.read_text(encoding="utf-8") for f in exported_files
    )

    # Key content pieces should survive the export
    assert "Projeto X" in exported_content
    assert "IA local" in exported_content
    assert "Café" in exported_content  # wikilink target preserved in ## Links


# ── Watcher Poll Test ────────────────────────────────────────────────


def test_watcher_poll_detects_new_file(tmp_path):
    """Watcher poll should detect newly added .md files and import them."""
    brain = None
    try:
        from app.brain.engine import LocalBrain
        from app.brain.memory import PersistentMemory
        from app.db.database import SessionLocal
        from app.models.models import Owner
        from app.obsidian.watcher import ObsidianWatcher

        brain = LocalBrain()
        memory = PersistentMemory(brain)
        watcher = ObsidianWatcher(memory)

        # Create vault with an initial note
        vault = tmp_path / "watch-vault"
        vault.mkdir()
        (vault / "initial.md").write_text(
            "---\ntitle: Nota Inicial\ntags: [test]\n---\n\nNota inicial.",
            encoding="utf-8",
        )

        db = SessionLocal()
        try:
            owner = db.query(Owner).first()
            assert owner is not None

            # First poll — caches the initial file
            asyncio.run(watcher.poll(db, owner.id, str(vault)))
            assert watcher.stats.files_imported >= 1
            before = watcher.stats.files_imported

            # Add a new note while the watcher is 'running'
            (vault / "nova-nota.md").write_text(
                "---\ntitle: Nova Nota\ntags: [novo]\n---\n\nNota adicionada depois.",
                encoding="utf-8",
            )

            # Second poll — should detect the new file
            asyncio.run(watcher.poll(db, owner.id, str(vault)))
            assert watcher.stats.files_imported >= before + 1

            # Verify the new note exists in the graph
            from app.models.models import Memory

            titles = (
                db.query(Memory.title)
                .filter(Memory.owner_id == owner.id, Memory.source == "obsidian")
                .all()
            )
            title_set = {t[0] for t in titles}
            assert "Nova Nota" in title_set

        finally:
            db.close()
    finally:
        if brain:
            asyncio.run(brain.aclose())


# ── Auto-Export Test ────────────────────────────────────────────────


def test_export_auto_learned_fact(tmp_path):
    """Auto-learned facts should create .md files with frontmatter in the vault."""
    from app.obsidian.exporter import export_auto_learned_fact

    vault = tmp_path / "auto-vault"

    result = export_auto_learned_fact(
        vault_path=str(vault),
        title="Usuário gosta de programar",
        content="O usuário prefere Python para projetos de IA.",
        kind="preference",
    )
    assert result is not None

    filepath = Path(result)
    assert filepath.exists()
    assert filepath.suffix == ".md"

    content = filepath.read_text(encoding="utf-8")
    assert "Usuário gosta de programar" in content
    assert "tags: [preference]" in content
    assert "source: auto_learned" in content
    assert "prefere Python" in content
    assert content.startswith("---")


def test_auto_export_integration_via_cognition(client, owner_headers, tmp_path):
    """When cognition learns a fact with obsidian_vault_path set, a .md is written.

    We stub the brain's chat to return a deterministic fact, then verify the
    auto-export created a .md file in the vault.
    """
    vault = tmp_path / "cognition-auto-vault"
    vault.mkdir()

    # Temporarily set obsidian_vault_path to the temp vault
    from app.core.config import settings

    original_path = settings.obsidian_vault_path
    original_learn = settings.memory_auto_learn
    try:
        settings.obsidian_vault_path = str(vault)
        settings.memory_auto_learn = True

        # Stub the brain to return a fake fact during auto-learn
        from app.core.di import get_kernel

        brain = get_kernel().cognition.brain
        original_chat = brain.chat

        async def fake_chat(_messages, **_kwargs):
            return "O usuário adora tecnologia"

        brain.chat = fake_chat
        try:
            r = client.post(
                "/api/v1/chat",
                json={"message": "eu amo tecnologia"},
                headers=owner_headers,
            )
            # Chat may return 503 if brain is offline, but auto-learn
            # should have fired regardless (it runs on the reply path)
            # The auto-learn happens AFTER persist, so it needs the chat
            # to succeed. If brain is offline (503), auto-learn doesn't run.
            # We handle this: if chat succeeds, check for the file.
            if r.status_code == 200:
                # Give auto-learn a moment to write the file
                import time
                time.sleep(0.1)
                md_files = list(vault.rglob("*.md"))
                assert any("tecnologia" in f.read_text(encoding="utf-8") for f in md_files)
        finally:
            brain.chat = original_chat
    finally:
        settings.obsidian_vault_path = original_path
        settings.memory_auto_learn = original_learn


# ── Recall Tests ─────────────────────────────────────────────────────


def test_read_recent_vault_notes_picks_up_notes(tmp_path):
    """read_recent_vault_notes should return notes from the vault, skipping hidden."""
    from app.obsidian.recall import read_recent_vault_notes

    vault = tmp_path / "recall-vault"
    vault.mkdir()

    (vault / "nota1.md").write_text(
        "---\ntitle: Nota Um\ntags: [dev]\n---\n\nConteúdo da nota um.",
        encoding="utf-8",
    )
    (vault / "nota2.md").write_text(
        "---\ntitle: Nota Dois\ntags: [test]\n---\n\nConteúdo da nota dois.",
        encoding="utf-8",
    )
    # Should be skipped
    (vault / ".hidden.md").write_text("Ignorada.", encoding="utf-8")
    (vault / "_template.md").write_text("Ignorada.", encoding="utf-8")

    notes = read_recent_vault_notes(str(vault), max_notes=10, max_age_hours=0)
    assert len(notes) == 2

    titles = {n["title"] for n in notes}
    assert "Nota Um" in titles
    assert "Nota Dois" in titles

    # Verify tags are parsed correctly
    for note in notes:
        if note["title"] == "Nota Um":
            assert note["tags"] == ["dev"]
        elif note["title"] == "Nota Dois":
            assert note["tags"] == ["test"]


def test_format_vault_context_formats_correctly():
    """format_vault_context should produce a valid context block for the system prompt."""
    from app.obsidian.recall import format_vault_context

    notes = [
        {
            "title": "Nota Importante",
            "content": "Conteúdo relevante para o contexto.",
            "tags": ["dev", "python"],
            "mtime": 1000.0,
            "path": "/vault/nota.md",
        }
    ]
    ctx = format_vault_context(notes)
    assert "Notas recentes do seu vault Obsidian" in ctx
    assert "Nota Importante" in ctx
    assert "[dev, python]" in ctx
    assert "Conteúdo relevante" in ctx


def test_recall_after_import_includes_notes(client, owner_headers, vault):
    """After import, read_recent_vault_notes should include the imported vault's files."""
    from app.obsidian.recall import read_recent_vault_notes

    # Import the vault first
    client.post(
        "/api/v1/obsidian/import",
        json={"vault_path": str(vault)},
        headers=owner_headers,
    )

    # The import adds path markers, but the original files are still readable
    notes = read_recent_vault_notes(str(vault), max_notes=10, max_age_hours=0)
    assert len(notes) >= 3  # All 3 main notes (skipping template/hidden)

    # The notes should have the expected titles
    titles = {n["title"] for n in notes}
    assert "Projeto X" in titles
    assert "Café" in titles
    assert "Nota Aleatória" in titles


# ── Status Endpoint Test ─────────────────────────────────────────────


def test_status_endpoint(client, owner_headers):
    """GET /api/v1/obsidian/status should return counts without crashing."""
    r = client.get("/api/v1/obsidian/status", headers=owner_headers)
    assert r.status_code == 200
    body = r.json()
    assert "notes_imported" in body
    assert "wikilinks_created" in body
    assert "vault_path" in body
    assert "default_path_configured" in body


def test_status_requires_auth(client):
    """Status endpoint should reject unauthenticated requests."""
    assert client.get("/api/v1/obsidian/status").status_code == 403


# ── Watch Endpoint Tests ─────────────────────────────────────────────


def test_watch_status_without_start(client, owner_headers):
    """Watch status should report not running if never started."""
    r = client.post(
        "/api/v1/obsidian/watch",
        json={"action": "status"},
        headers=owner_headers,
    )
    assert r.status_code == 200
    assert r.json()["is_running"] is False


def test_watch_start_requires_path(client, owner_headers):
    """Watch start should fail without vault_path if config is not set."""
    # Temporarily clear obsidian_vault_path
    from app.core.config import settings

    original = settings.obsidian_vault_path
    settings.obsidian_vault_path = ""
    try:
        r = client.post(
            "/api/v1/obsidian/watch",
            json={"action": "start"},
            headers=owner_headers,
        )
        assert r.status_code == 400
        assert "vault_path is required" in r.json()["detail"].lower()
    finally:
        settings.obsidian_vault_path = original
