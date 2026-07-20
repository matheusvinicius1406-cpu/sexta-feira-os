"""
Teia CLI — run and inspect workflow files from the terminal (Phase 2).

    python -m app.automation.teia.cli run     workflow.json
    python -m app.automation.teia.cli validate workflow.yaml
    python -m app.automation.teia.cli nodes

The file format is inferred from the extension (.json vs .yaml/.yml). Only the
built-in node catalog is available here; plugin discovery arrives in Phase 4.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer

from app.automation.teia.domain.errors import WorkflowValidationError
from app.automation.teia.domain.graph import Workflow
from app.automation.teia.engine.engine import Engine
from app.automation.teia.nodes.builtin import builtin_registry
from app.automation.teia.serialization import from_json, from_yaml

app = typer.Typer(help="Teia — Python-first automation platform (CLI).", no_args_is_help=True)


def _load(path: Path) -> Workflow:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return from_yaml(text)
    return from_json(text)


@app.command()
def run(
    file: Path = typer.Argument(..., exists=True, readable=True, help="Workflow .json/.yaml"),
    trigger_json: str = typer.Option(
        "", "--input", help="JSON array of items to seed the entry nodes."
    ),
) -> None:
    """Execute a workflow file and print the execution result as JSON."""
    workflow = _load(file)
    items = json.loads(trigger_json) if trigger_json else None
    engine = Engine(builtin_registry())
    try:
        result = asyncio.run(engine.run(workflow, trigger_items=items))
    except WorkflowValidationError as exc:
        typer.echo("workflow inválido:\n  - " + "\n  - ".join(exc.problems), err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(result.model_dump_json(indent=2))
    raise typer.Exit(code=0 if result.succeeded else 1)


@app.command()
def validate(
    file: Path = typer.Argument(..., exists=True, readable=True, help="Workflow .json/.yaml"),
) -> None:
    """Validate a workflow file against the built-in catalog."""
    workflow = _load(file)
    problems = workflow.validate_graph(builtin_registry())
    if problems:
        typer.echo("inválido:\n  - " + "\n  - ".join(problems), err=True)
        raise typer.Exit(code=1)
    typer.echo(f"ok: '{workflow.name}' ({len(workflow.nodes)} nós) é válido.")


@app.command()
def nodes() -> None:
    """List the available built-in node types."""
    for type_id in builtin_registry().node_types():
        typer.echo(type_id)


if __name__ == "__main__":
    app()
