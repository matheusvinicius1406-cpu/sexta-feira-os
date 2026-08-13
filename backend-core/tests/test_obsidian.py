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
import os
import time
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
    assert r.status_code == 401


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
    (vault / "imagem.png").write_bytes(b"PNG")   # binary file: use write_bytes
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
    # Spot-check for wikilink syntax if links were referenced. Links live on the
    # linked node's file, which may not be md_files[0] — check across all files.
    if data["stats"]["links_referenced"] > 0:
        all_content = "\n".join(f.read_text(encoding="utf-8") for f in md_files)
        assert "[[" in all_content or "Links" in all_content


def test_export_requires_auth(client):
    """Export endpoint should reject unauthenticated requests."""
    r = client.post(
        "/api/v1/obsidian/export",
        json={"vault_path": "/tmp/foo", "include_all": True},
    )
    assert r.status_code == 401


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


def test_watcher_does_not_reimport_the_kernels_own_exported_notes(tmp_path):
    """A note the kernel wrote to __sexta__/ (export_auto_learned_fact) must
    not come back through the front door as a second source="obsidian" node
    on the watcher's very next poll — the kernel re-learning what it just
    wrote to tell itself, with a fresh embed paid for each time."""
    brain = None
    try:
        from app.brain.engine import LocalBrain
        from app.brain.memory import PersistentMemory
        from app.db.database import SessionLocal
        from app.models.models import Memory, Owner
        from app.obsidian import BRAIN_FOLDER
        from app.obsidian.watcher import ObsidianWatcher

        brain = LocalBrain()
        memory = PersistentMemory(brain)
        watcher = ObsidianWatcher(memory)

        vault = tmp_path / "sexta-owned-vault"
        vault.mkdir()
        mirrored = vault / BRAIN_FOLDER / "auto-learned" / "fato-aprendido.md"
        mirrored.parent.mkdir(parents=True)
        mirrored.write_text(
            "---\ntitle: Fato Aprendido\ntags: [preference]\nsource: auto_learned\n---\n\n"
            "O dono gosta de café forte.",
            encoding="utf-8",
        )

        db = SessionLocal()
        try:
            owner = db.query(Owner).first()
            assert owner is not None

            asyncio.run(watcher.poll(db, owner.id, str(vault)))

            assert watcher.stats.files_imported == 0, (
                "the watcher imported a file from inside its own BRAIN_FOLDER"
            )
            nodes = (
                db.query(Memory)
                .filter(Memory.owner_id == owner.id, Memory.title == "Fato Aprendido")
                .all()
            )
            assert nodes == [], "the mirrored note came back as a graph node"
        finally:
            db.close()
    finally:
        if brain:
            asyncio.run(brain.aclose())


def test_a_second_watcher_after_restart_re_embeds_nothing_unchanged(client, tmp_path):
    """ObsidianWatcher's mtime cache lives only in process memory, and a
    fresh instance is exactly what a kernel restart builds — the scenario
    this seeds for. Without seeding, a restart's first poll saw an empty
    cache, treated every already-imported note as brand new, and paid a
    fresh brain.embed() for the whole vault regardless of whether anything
    had actually changed since the last run.
    """

    class _SpyBrain:
        """Fake LocalBrain: counts embeds, gives every note the same vector
        so semantic auto-link has something to compare without needing Ollama."""

        def __init__(self) -> None:
            self.embed_calls = 0

        async def embed(self, text: str) -> list[float]:
            self.embed_calls += 1
            return [1.0, 0.0, 0.0]

        async def chat(self, messages, temperature=None, max_tokens=None) -> str:
            return "related"

    from app.brain.memory import PersistentMemory
    from app.db.database import SessionLocal
    from app.models.models import Owner
    from app.obsidian.watcher import ObsidianWatcher

    vault = tmp_path / "restart-vault"
    vault.mkdir()
    (vault / "nota-um.md").write_text(
        "---\ntitle: Nota Um\ntags: [dev]\n---\n\nConteúdo da primeira nota.",
        encoding="utf-8",
    )
    (vault / "nota-dois.md").write_text(
        "---\ntitle: Nota Dois\ntags: [dev]\n---\n\nConteúdo da segunda nota.",
        encoding="utf-8",
    )

    db = SessionLocal()
    try:
        owner = db.query(Owner).first()
        assert owner is not None

        # First "boot": imports both notes for the first time — embeds expected.
        first_brain = _SpyBrain()
        first_watcher = ObsidianWatcher(PersistentMemory(first_brain))
        asyncio.run(first_watcher.poll(db, owner.id, str(vault)))
        assert first_watcher.stats.files_imported == 2
        assert first_brain.embed_calls >= 2

        # "Restart": a BRAND NEW watcher (empty _mtime_cache), same vault,
        # NOTHING changed on disk since the first poll.
        second_brain = _SpyBrain()
        second_watcher = ObsidianWatcher(PersistentMemory(second_brain))
        asyncio.run(second_watcher.poll(db, owner.id, str(vault)))

        assert second_watcher.stats.files_imported == 0
        assert second_watcher.stats.files_updated == 0
        assert second_brain.embed_calls == 0, (
            "a restart with nothing changed still re-embedded the vault"
        )
    finally:
        db.close()


def test_a_file_modified_while_offline_is_still_caught_after_seeding(client, tmp_path):
    """The seed must not swallow a REAL change that happened while the
    kernel was down — only skip files that are genuinely unchanged."""
    from app.brain.memory import PersistentMemory
    from app.db.database import SessionLocal
    from app.models.models import Owner
    from app.obsidian.watcher import ObsidianWatcher

    class _SpyBrain:
        def __init__(self) -> None:
            self.embed_calls = 0

        async def embed(self, text: str) -> list[float]:
            self.embed_calls += 1
            return [1.0, 0.0, 0.0]

        async def chat(self, messages, temperature=None, max_tokens=None) -> str:
            return "related"

    vault = tmp_path / "offline-edit-vault"
    vault.mkdir()
    note = vault / "nota.md"
    note.write_text("---\ntitle: Nota\ntags: [dev]\n---\n\nVersão original.", encoding="utf-8")

    db = SessionLocal()
    try:
        owner = db.query(Owner).first()
        assert owner is not None

        first_watcher = ObsidianWatcher(PersistentMemory(_SpyBrain()))
        asyncio.run(first_watcher.poll(db, owner.id, str(vault)))
        assert first_watcher.stats.files_imported == 1

        # Simulate an edit made while the kernel was offline: touch the file
        # to a mtime clearly AFTER what got recorded, then seed+poll fresh.
        future = time.time() + 120
        os.utime(note, (future, future))
        note.write_text("---\ntitle: Nota\ntags: [dev]\n---\n\nVersão editada offline.", encoding="utf-8")
        os.utime(note, (future, future))

        second_brain = _SpyBrain()
        second_watcher = ObsidianWatcher(PersistentMemory(second_brain))
        asyncio.run(second_watcher.poll(db, owner.id, str(vault)))

        assert second_brain.embed_calls >= 1, (
            "a note edited while offline was skipped instead of re-synced"
        )
    finally:
        db.close()


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
    """A fact learned during a chat lands in the vault as a .md file.

    Both halves of the brain are stubbed, because the chat path uses two
    different methods: `chat_with_tools` produces the reply, `chat` is what the
    memory extractor probes with. The previous version stubbed only `chat` and
    fed it prose — but the extractor parses a JSON array, so nothing was ever
    extracted, nothing written, and the assertion sat inside `if status == 200`
    so the test passed by not running. Both are fixed here: deterministic
    stubs, and an assertion that always executes.
    """
    import json

    from app.core.config import settings
    from app.core.di import get_kernel

    vault = tmp_path / "cognition-auto-vault"
    vault.mkdir()

    cognition = get_kernel().cognition
    brain = cognition.brain
    original_path = settings.obsidian_vault_path
    original_learn = settings.memory_auto_learn
    original_chat = brain.chat
    original_tools = brain.chat_with_tools
    original_embed = brain.embed

    async def fake_chat(_messages, **_kwargs):
        # Exactly the shape MemoryExtractor._parse_candidates expects.
        return json.dumps([{
            "fato": "O dono adora tecnologia e programação",
            "tipo": "preference",
            "importancia": 0.8,
            "chave_perfil": "interesses",
        }], ensure_ascii=False)

    async def fake_tools(_messages, **_kwargs):
        return {"content": "Anotado.", "tool_calls": []}

    async def fake_embed(_text):
        # remember() awaits this unconditionally. Left unstubbed, it is a REAL
        # httpx call to OLLAMA_ENDPOINT — which tests pin unreachable (Step 1)
        # — and remember()'s own try/except only resolves that after paying
        # the full connect timeout. That cost used to be hidden inside the
        # synchronous request; now that auto-learn runs off the critical path
        # (Step 5), it would instead show up as this test hanging on drain().
        return [0.1, 0.2, 0.3]

    settings.obsidian_vault_path = str(vault)
    settings.memory_auto_learn = True
    brain.chat = fake_chat
    brain.chat_with_tools = fake_tools
    brain.embed = fake_embed
    try:
        r = client.post(
            "/api/v1/chat",
            json={"message": "eu amo tecnologia"},
            headers=owner_headers,
        )
        assert r.status_code == 200, r.text

        # Auto-learn now runs off the request's critical path (cognition.py
        # Cognition._spawn) — the HTTP response can (and, being the point of
        # that change, usually does) return before the background extraction
        # and its vault export have actually finished. The task lives on
        # TestClient's persistent portal loop (a dedicated background thread,
        # started in its __enter__ and reused across every call in this `with`
        # block — see starlette.testclient.TestClient._portal_factory), not
        # one this sync test can `await` into directly. `portal.call` runs a
        # coroutine ON that same loop and blocks this thread for the result,
        # which is the deterministic equivalent of `await cognition.drain()`.
        client.portal.call(cognition.drain)

        notes = list(vault.rglob("*.md"))
        assert notes, "auto-export não escreveu nenhum .md no vault"
        assert any(
            "tecnologia" in f.read_text(encoding="utf-8") for f in notes
        ), f"nenhuma nota menciona o fato aprendido: {[f.name for f in notes]}"
    finally:
        brain.chat, brain.chat_with_tools, brain.embed = original_chat, original_tools, original_embed
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


def test_direct_recall_is_bounded_to_the_watcher_lag_window(client, owner_headers, monkeypatch):
    """cognition.py's direct vault recall must ask for AT MOST ~2x the
    watcher's own poll interval, not a static 72-hour window — content older
    than that is the graph's job (recall_graph), not this synchronous,
    every-turn filesystem scan's. Also proves the char cap (1200) and that
    the scan runs off the event loop (asyncio.to_thread), by capturing the
    real arguments cognition.py passes rather than the file-mtime behavior
    read_recent_vault_notes/format_vault_context already test on their own.
    """
    import app.obsidian.recall as recall_module
    from app.core.config import settings

    captured: dict = {}

    def fake_read_recent_vault_notes(vault_path, max_notes=10, max_age_hours=72.0):
        captured["vault_path"] = vault_path
        captured["max_notes"] = max_notes
        captured["max_age_hours"] = max_age_hours
        return []

    def fake_format_vault_context(notes, max_chars=4000):
        captured["max_chars"] = max_chars
        return ""

    monkeypatch.setattr(recall_module, "read_recent_vault_notes", fake_read_recent_vault_notes)
    monkeypatch.setattr(recall_module, "format_vault_context", fake_format_vault_context)
    monkeypatch.setattr(settings, "obsidian_vault_path", "/fake/vault")
    monkeypatch.setattr(settings, "obsidian_vault_recall_max_notes", 7)
    monkeypatch.setattr(settings, "obsidian_watch_interval", 45)

    from app.core.di import get_kernel

    brain = get_kernel().cognition.brain
    original_tools = brain.chat_with_tools

    async def fake_tools(_messages, **_kwargs):
        return {"content": "ok", "tool_calls": []}

    brain.chat_with_tools = fake_tools
    try:
        r = client.post(
            "/api/v1/chat", json={"message": "oi"}, headers=owner_headers,
        )
        assert r.status_code == 200, r.text
    finally:
        brain.chat_with_tools = original_tools

    assert captured["max_notes"] == 7
    assert captured["max_age_hours"] == (2 * 45) / 3600
    assert captured["max_chars"] == 1200


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
    assert client.get("/api/v1/obsidian/status").status_code == 401


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
