"""
File nodes — reading and writing on the owner's disk, inside a fence.

Every path is resolved and then checked against a set of allowed roots (the Teia
workspace, the Obsidian vault, and anything the owner explicitly listed in
TEIA_ALLOWED_PATHS). A workflow therefore cannot walk out to `~/.ssh` with
`../../..`, whoever wrote it.
"""
from __future__ import annotations

import csv
import io
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.automation.teia.domain.execution import NodeInput, NodeOutput
from app.automation.teia.domain.node import Node, NodeMetadata
from app.core.config import settings

MAX_READ_BYTES = 2 * 1024 * 1024        # 2 MB — a workflow item, not a data lake


class PathNotAllowed(PermissionError):
    """The path resolves outside every allowed root."""


def allowed_roots() -> list[Path]:
    """The directories a workflow may touch. The workspace always exists."""
    roots: list[Path] = [Path(settings.teia_workspace).resolve()]
    if settings.obsidian_vault_path:
        vault = Path(settings.obsidian_vault_path).expanduser()
        if vault.exists():
            roots.append(vault.resolve())
    for extra in settings.teia_allowed_paths:
        candidate = Path(extra).expanduser()
        if candidate.exists():
            roots.append(candidate.resolve())
    return roots


def safe_path(raw: str, *, must_exist: bool = False) -> Path:
    """Resolve `raw` and prove it sits inside an allowed root."""
    if not raw or not raw.strip():
        raise ValueError("caminho vazio")
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = Path(settings.teia_workspace) / candidate
    resolved = candidate.resolve()

    roots = allowed_roots()
    if not any(resolved == root or root in resolved.parents for root in roots):
        raise PathNotAllowed(
            f"'{raw}' está fora das pastas permitidas. "
            f"Permitidas: {', '.join(str(r) for r in roots)}. "
            f"Adicione outras em TEIA_ALLOWED_PATHS no .env."
        )
    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"não existe: {resolved}")
    return resolved


class _ReadConfig(BaseModel):
    caminho: str = Field(..., min_length=1)
    formato: Literal["texto", "linhas", "csv"] = "texto"
    codificacao: str = "utf-8"


class ReadFileNode(Node):
    """Read a file: whole text, one item per line, or parsed CSV rows."""

    metadata = NodeMetadata(
        type="arquivo_ler", name="Ler arquivo", category="arquivos",
        description="Lê um arquivo de dentro das pastas permitidas.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _ReadConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        path = safe_path(self.config.caminho, must_exist=True)
        if path.stat().st_size > MAX_READ_BYTES:
            raise ValueError(
                f"{path.name} tem mais de {MAX_READ_BYTES // 1024} KB — "
                f"grande demais para um item de workflow"
            )
        text = path.read_text(encoding=self.config.codificacao, errors="replace")

        if self.config.formato == "linhas":
            lines = [{"linha": line} for line in text.splitlines()]
            return NodeOutput(items={"main": lines})
        if self.config.formato == "csv":
            rows = list(csv.DictReader(io.StringIO(text)))
            return NodeOutput(items={"main": rows})
        return NodeOutput.single(
            {"caminho": str(path), "conteudo": text, "bytes": path.stat().st_size}
        )


class _WriteConfig(BaseModel):
    caminho: str = Field(..., min_length=1)
    conteudo: str = ""
    modo: Literal["substituir", "acrescentar"] = "substituir"
    criar_pastas: bool = True
    codificacao: str = "utf-8"


class WriteFileNode(Node):
    """Write (or append to) a file inside an allowed root."""

    metadata = NodeMetadata(
        type="arquivo_escrever", name="Escrever arquivo", category="arquivos",
        description="Grava conteúdo em um arquivo nas pastas permitidas.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _WriteConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        path = safe_path(self.config.caminho)
        if self.config.criar_pastas:
            path.parent.mkdir(parents=True, exist_ok=True)

        mode = "a" if self.config.modo == "acrescentar" else "w"
        with path.open(mode, encoding=self.config.codificacao, newline="") as handle:
            handle.write(self.config.conteudo)

        context.log(f"arquivo {self.config.modo}: {path}")
        return NodeOutput.single(
            {"caminho": str(path), "bytes": path.stat().st_size, "modo": self.config.modo}
        )


class _ListDirConfig(BaseModel):
    caminho: str = Field(..., min_length=1)
    padrao: str = "*"
    recursivo: bool = False
    apenas_arquivos: bool = True
    limite: int = Field(default=200, ge=1, le=2000)


class ListDirNode(Node):
    """List a directory; emits one item per entry."""

    metadata = NodeMetadata(
        type="pasta_listar", name="Listar pasta", category="arquivos",
        description="Emite os arquivos de uma pasta permitida.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _ListDirConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        root = safe_path(self.config.caminho, must_exist=True)
        if not root.is_dir():
            raise NotADirectoryError(f"{root} não é uma pasta")

        matches = root.rglob(self.config.padrao) if self.config.recursivo \
            else root.glob(self.config.padrao)
        items = []
        for entry in matches:
            if self.config.apenas_arquivos and not entry.is_file():
                continue
            stat = entry.stat()
            items.append({
                "nome": entry.name,
                "caminho": str(entry),
                "bytes": stat.st_size,
                "modificado_em": int(stat.st_mtime),
                "pasta": entry.is_dir(),
            })
            if len(items) >= self.config.limite:
                break
        return NodeOutput(items={"main": items})


class _ExistsConfig(BaseModel):
    caminho: str = Field(..., min_length=1)


class FileExistsNode(Node):
    """Check whether a path exists. Emits `{existe, ...}` — never fails on absence."""

    metadata = NodeMetadata(
        type="arquivo_existe", name="Arquivo existe?", category="arquivos",
        description="Verifica se um caminho existe dentro das pastas permitidas.",
        inputs=["main"], outputs=["main", "error"],
    )
    config_model = _ExistsConfig

    async def execute(self, context, inputs: NodeInput) -> NodeOutput:
        path = safe_path(self.config.caminho)
        exists = path.exists()
        return NodeOutput.single({
            "caminho": str(path),
            "existe": exists,
            "bytes": path.stat().st_size if exists and path.is_file() else 0,
            "pasta": exists and path.is_dir(),
        })


def ensure_workspace() -> Path:
    """Create the Teia workspace on first use (the default allowed root)."""
    workspace = Path(settings.teia_workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    os.makedirs(workspace / "backups", exist_ok=True)
    return workspace


FILE_NODES = [ReadFileNode, WriteFileNode, ListDirNode, FileExistsNode]
