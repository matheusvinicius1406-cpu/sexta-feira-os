"""Shared fixtures: a throwaway factory rooted in a temp project tree."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from jarvis_mcp.core.config import load_config
from jarvis_mcp.core.context import Factory


def _write_config(tmp: Path, root: Path) -> Path:
    cfg = tmp / "factory.toml"
    cfg.write_text(
        textwrap.dedent(
            f"""
            [factory]
            name = "Test Factory"
            root = "{root.as_posix()}"
            audit_log = "{(tmp / 'audit.log').as_posix()}"
            memory_store = "{(tmp / 'memory').as_posix()}"
            critical_capabilities = ["github.merge", "fs.write"]

            [filesystem]
            allow = ["backend-core", "docs", "src"]
            deny = ["**/.env", "**/*.key", "**/.git/**"]
            max_read_bytes = 100000

            [testing]
            allow = ["python -m pytest", "echo ok"]
            timeout_seconds = 30
            [testing.cwd_map]
            python = "backend-core"

            [agents.architect]
            role = "arch"
            capabilities = ["core.read", "fs.read", "fs.search", "memory.read", "memory.write", "docs.read", "docs.write", "security.audit"]

            [agents.qa]
            role = "qa"
            capabilities = ["fs.read", "testing.run"]

            [agents.security]
            role = "sec"
            capabilities = ["fs.read", "fs.search", "security.scan", "security.audit"]
            """
        ),
        encoding="utf-8",
    )
    return cfg


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A minimal project tree with allowed and sensitive files."""
    root = tmp_path / "proj"
    (root / "backend-core").mkdir(parents=True)
    (root / "docs" / "ADR").mkdir(parents=True)
    (root / "src").mkdir()
    (root / "secret_stuff").mkdir()  # not in allow-list

    (root / "backend-core" / "app.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    (root / "backend-core" / "requirements.txt").write_text("fastapi==0.115.0\nrequests\n", encoding="utf-8")
    (root / "backend-core" / ".env").write_text("OWNER_TOKEN=supersecret\n", encoding="utf-8")
    (root / "docs" / "README.md").write_text("# Docs\n", encoding="utf-8")
    (root / "src" / "server.key").write_text("PRIVATE\n", encoding="utf-8")
    (root / "secret_stuff" / "passwords.txt").write_text("hunter2\n", encoding="utf-8")
    (root / "Cargo.toml").write_text('[dependencies]\ntokio = "1.40"\n', encoding="utf-8")
    return root


@pytest.fixture
def factory(tmp_path: Path, project: Path) -> Factory:
    cfg_path = _write_config(tmp_path, project)
    return Factory(load_config(cfg_path))
