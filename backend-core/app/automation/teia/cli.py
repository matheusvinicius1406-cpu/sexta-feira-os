"""
Teia CLI — the same automations, from a terminal.

    python -m app.automation.teia.cli listar
    python -m app.automation.teia.cli rodar briefing-matinal
    python -m app.automation.teia.cli rodar captura-rapida --dados '{"texto":"uma ideia"}'
    python -m app.automation.teia.cli validar minha-automacao.yaml
    python -m app.automation.teia.cli importar minha-automacao.yaml --slug minha
    python -m app.automation.teia.cli exportar briefing-matinal --saida b.yaml
    python -m app.automation.teia.cli nos
    python -m app.automation.teia.cli historico backup-do-kernel

It runs OUTSIDE the FastAPI process, against the same database, so it works
whether or not the kernel is up. It builds the kernel services it needs directly;
anything a device would receive is queued in the database exactly as it would be
by the running kernel, and picked up when that device next connects.

Uses argparse from the standard library — no extra dependency for a tool whose
whole point is being available when nothing else is.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import yaml

from app.automation.teia import catalog as builtin_catalog
from app.automation.teia.domain.errors import WorkflowValidationError
from app.automation.teia.domain.graph import Workflow
from app.automation.teia.engine.context import Services
from app.automation.teia.engine.errors import WorkflowNotFound
from app.automation.teia.serialization import from_dict, to_yaml
from app.automation.teia.service import TeiaService
from app.db.database import SessionLocal
from app.models.models import Owner


def build_standalone_services() -> Services:
    """The kernel's services, constructed directly for a one-shot CLI process."""
    from app.action.bus import CommandBus
    from app.action.service import ActionService
    from app.brain.engine import LocalBrain
    from app.brain.memory import PersistentMemory
    from app.briefing.service import BriefingService
    from app.connectors.service import ConnectorService
    from app.connectors.vault import Vault
    from app.decision.service import DecisionEngine
    from app.events.bus import EventBus
    from app.journal.service import HabitService, JournalService
    from app.learning.service import LearningEngine
    from app.planning.service import PlanningEngine
    from app.schedule.service import Scheduler
    from app.timetrack.service import TimeTracker
    from app.world.service import WorldModel

    brain = LocalBrain()
    world = WorldModel()
    events = EventBus()
    memory = PersistentMemory(brain)
    planning = PlanningEngine(world=world, events=events)
    decision = DecisionEngine(planning=planning, world=world, events=events)
    learning = LearningEngine(memory=memory, world=world, events=events)
    briefing = BriefingService(
        world=world, planning=planning, decision=decision, events=events, learning=learning
    )
    actions = ActionService(CommandBus())
    return Services(
        memory=memory, world=world, events=events, brain=brain,
        planning=planning, decision=decision, learning=learning, briefing=briefing,
        actions=actions, connectors=ConnectorService(Vault()),
        scheduler=Scheduler(actions, events=events, briefing=briefing),
        journal=JournalService(events=events), habits=HabitService(world=world, events=events),
        timetracker=TimeTracker(world=world, events=events),
    )


def resolve_owner() -> str:
    db = SessionLocal()
    try:
        owner = db.query(Owner).first()
        if not owner:
            sys.exit(
                "Nenhum dono cadastrado ainda. Configure OWNER_EMAIL/OWNER_PASSWORD "
                "no .env e suba o kernel uma vez."
            )
        return owner.id
    finally:
        db.close()


def load_workflow(path: str) -> Workflow:
    text = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(text) if path.endswith((".yaml", ".yml")) else json.loads(text)
    if not isinstance(data, dict):
        sys.exit(f"{path} não descreve um workflow")
    return from_dict(data)


# ---------------------------------------------------------------- commands


def cmd_listar(teia: TeiaService, owner_id: str, args) -> int:
    db = SessionLocal()
    try:
        rows = teia.list(db, owner_id, query=args.busca)
    finally:
        db.close()
    if not rows:
        print("Nenhuma automação. Instale as prontas com: catalogo")
        return 0
    for row in rows:
        mark = "on " if row["enabled"] else "off"
        print(f"[{mark}] {row['slug']:24s} {row['description'] or row['name']}")
    return 0


def cmd_mostrar(teia: TeiaService, owner_id: str, args) -> int:
    db = SessionLocal()
    try:
        row = teia.store.get(db, owner_id, args.slug)
        if not row:
            sys.exit(f"automação '{args.slug}' não existe")
        print(to_yaml(teia.store.to_workflow(row)))
    finally:
        db.close()
    return 0


def cmd_rodar(teia: TeiaService, owner_id: str, args) -> int:
    payload = json.loads(args.dados) if args.dados else {}
    try:
        result = asyncio.run(teia.run_slug(owner_id, args.slug, payload))
    except WorkflowNotFound as e:
        sys.exit(str(e))

    print(result.summary())
    for node in result.node_results:
        marker = {"completed": "ok", "failed": "ERRO", "skipped": "--"}.get(node.status.value, "?")
        line = f"  {marker:>4}  {node.node_id} ({node.node_type})"
        print(f"{line} — {node.error}" if node.error else line)
    if result.output:
        print(json.dumps(result.output, ensure_ascii=False, indent=2, default=str))
    return 0 if result.ok else 1


def cmd_validar(teia: TeiaService, owner_id: str, args) -> int:
    problems = teia.validate(load_workflow(args.arquivo))
    if problems:
        print(f"{len(problems)} problema(s):")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("workflow válido")
    return 0


def cmd_importar(teia: TeiaService, owner_id: str, args) -> int:
    workflow = load_workflow(args.arquivo)
    db = SessionLocal()
    try:
        row = teia.save(
            db, owner_id, workflow, slug=args.slug,
            description=args.descricao, enabled=not args.desativada, source="imported",
        )
    except WorkflowValidationError as e:
        print("workflow inválido:")
        for problem in e.problems:
            print(f"  - {problem}")
        return 1
    finally:
        db.close()
    print(f"importada como '{row.slug}'")
    return 0


def cmd_exportar(teia: TeiaService, owner_id: str, args) -> int:
    db = SessionLocal()
    try:
        row = teia.store.get(db, owner_id, args.slug)
        if not row:
            sys.exit(f"automação '{args.slug}' não existe")
        text = to_yaml(teia.store.to_workflow(row))
    finally:
        db.close()

    if args.saida:
        Path(args.saida).write_text(text, encoding="utf-8")
        print(f"exportada para {args.saida}")
    else:
        print(text)
    return 0


def cmd_nos(teia: TeiaService, owner_id: str, args) -> int:
    by_category: dict[str, list[tuple[str, str]]] = {}
    for node in teia.node_types():
        by_category.setdefault(node["category"], []).append(
            (node["type"], node["description"])
        )
    for category in sorted(by_category):
        print(f"\n{category.upper()}")
        for node_type, description in sorted(by_category[category]):
            print(f"  {node_type:22s} {description}")
    print("\nGATILHOS")
    for trigger in teia.trigger_types():
        print(f"  {trigger['type']:22s} {trigger['description']}")
    return 0


def cmd_catalogo(teia: TeiaService, owner_id: str, args) -> int:
    db = SessionLocal()
    try:
        installed = builtin_catalog.seed(teia, db, owner_id, overwrite=args.sobrescrever)
    finally:
        db.close()
    print(f"{len(installed)} automação(ões) instalada(s)" if installed else "nada novo a instalar")
    for slug in installed:
        print(f"  + {slug}")
    return 0


def cmd_historico(teia: TeiaService, owner_id: str, args) -> int:
    db = SessionLocal()
    try:
        rows = teia.executions.list(db, owner_id, slug=args.slug, limit=args.limite)
    finally:
        db.close()
    if not rows:
        print("nenhuma execução registrada")
        return 0
    for row in rows:
        when = row.started_at.strftime("%d/%m %H:%M") if row.started_at else "?"
        line = f"{when}  {row.workflow_slug:24s} {row.status:10s} {row.duration_ms or 0:6d} ms"
        print(f"{line}  {row.error}" if row.error else line)
    return 0


# ---------------------------------------------------------------- entry point


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="teia", description="Automações da Sexta-Feira OS (Python-first)."
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    listar = sub.add_parser("listar", help="lista suas automações")
    listar.add_argument("--busca", default=None)
    listar.set_defaults(func=cmd_listar)

    mostrar = sub.add_parser("mostrar", help="mostra o grafo de uma automação (YAML)")
    mostrar.add_argument("slug")
    mostrar.set_defaults(func=cmd_mostrar)

    rodar = sub.add_parser("rodar", help="executa uma automação agora")
    rodar.add_argument("slug")
    rodar.add_argument("--dados", default=None, help="JSON de entrada")
    rodar.set_defaults(func=cmd_rodar)

    validar = sub.add_parser("validar", help="valida um arquivo sem salvar")
    validar.add_argument("arquivo")
    validar.set_defaults(func=cmd_validar)

    importar = sub.add_parser("importar", help="salva um arquivo como automação")
    importar.add_argument("arquivo")
    importar.add_argument("--slug", default=None)
    importar.add_argument("--descricao", default=None)
    importar.add_argument("--desativada", action="store_true")
    importar.set_defaults(func=cmd_importar)

    exportar = sub.add_parser("exportar", help="exporta uma automação para YAML")
    exportar.add_argument("slug")
    exportar.add_argument("--saida", default=None)
    exportar.set_defaults(func=cmd_exportar)

    nos = sub.add_parser("nos", help="lista os tipos de nó e de gatilho")
    nos.set_defaults(func=cmd_nos)

    catalogo = sub.add_parser("catalogo", help="instala as automações prontas")
    catalogo.add_argument("--sobrescrever", action="store_true")
    catalogo.set_defaults(func=cmd_catalogo)

    historico = sub.add_parser("historico", help="mostra as últimas execuções")
    historico.add_argument("slug", nargs="?", default=None)
    historico.add_argument("--limite", type=int, default=20)
    historico.set_defaults(func=cmd_historico)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    owner_id = resolve_owner()
    teia = TeiaService(build_standalone_services())
    return args.func(teia, owner_id, args)


if __name__ == "__main__":
    raise SystemExit(main())
