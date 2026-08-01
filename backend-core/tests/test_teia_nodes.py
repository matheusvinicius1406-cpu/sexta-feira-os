"""
The built-in node library.

Nodes are exercised through the real engine (so config resolution, validation and
port routing are all in play) with fake kernel services, so nothing here touches
Ollama, the network or a device.
"""
import asyncio
import json
from types import SimpleNamespace

import pytest

from app.automation.teia.domain.graph import Workflow
from app.automation.teia.engine import (
    ExecutionStatus,
    Orchestrator,
    RunContext,
    RunLimits,
    Services,
)
from app.automation.teia.nodes import catalogue
from app.automation.teia.nodes.core import compare
from app.automation.teia.nodes.files import PathNotAllowed, safe_path
from app.automation.teia.service import build_registry
from app.core.config import settings


def _null_session():
    """A Session stand-in for nodes that open one but whose service is faked."""
    class _Fake:
        def close(self):
            pass
    return _Fake()


def run_one(node_type: str, config: dict, *, services=None, payload=None, upstream=None):
    """Run a single node (optionally behind a `inicio`) and return its main items."""
    wf = Workflow(name="um-no")
    target = wf.add_node(node_type, config, id="alvo")
    if upstream is not None:
        start = wf.add_node("inicio", {"dados": upstream}, id="a")
        wf.connect(start, target)

    ctx = RunContext(
        workflow_id="wf", workflow_slug="teste", execution_id="e", owner_id="dono",
        services=services or Services(), session_factory=_null_session,
        trigger_payload=payload or {}, limits=RunLimits(),
    )
    result = asyncio.run(Orchestrator(build_registry()).run(wf, ctx))
    assert result.status is ExecutionStatus.COMPLETED, result.error
    return ctx.outputs["alvo"].get("main", [])


# ---------------------------------------------------------------- catalogue


def test_every_builtin_node_publishes_a_usable_schema():
    entries = catalogue()
    assert len(entries) >= 40
    for entry in entries:
        assert entry["type"] and entry["name"] and entry["category"]
        assert entry["description"], f"{entry['type']} está sem descrição"
        assert entry["config_schema"]["type"] == "object"


def test_node_types_are_unique():
    types = [e["type"] for e in catalogue()]
    assert len(types) == len(set(types))


# ---------------------------------------------------------------- comparisons


@pytest.mark.parametrize(
    ("left", "operator", "right", "expected"),
    [
        (5, "maior", 3, True),
        ("5", "maior", 3, True),                 # numeric coercion
        (3, "maior_igual", 3, True),
        ("abc", "igual", "abc", True),
        ("ABC", "contem", "b", True),            # case-insensitive
        ("abc", "nao_contem", "z", True),
        ("relatorio.pdf", "termina_com", ".PDF", True),
        ("2026-08-01", "regex", r"^\d{4}-", True),
        ("", "vazio", None, True),
        ([], "vazio", None, True),
        ("não", "verdadeiro", None, False),      # pt-BR falsy word
        ("b", "esta_em", "a,b,c", True),
        ("d", "esta_em", ["a", "b"], False),
    ],
)
def test_comparison_operators(left, operator, right, expected):
    assert compare(left, operator, right) is expected


def test_numeric_operator_on_text_is_an_error():
    with pytest.raises(ValueError, match="precisa de números"):
        compare("abc", "maior", 3)


def test_unknown_operator_is_rejected():
    with pytest.raises(ValueError, match="operador desconhecido"):
        compare(1, "quase_igual", 1)


# ---------------------------------------------------------------- data nodes


def test_template_builds_text_from_expressions():
    items = run_one("texto", {"texto": "Olá {{ trigger.nome }}"}, payload={"nome": "Matheus"})
    assert items == [{"texto": "Olá Matheus"}]


def test_json_parse_survives_a_fenced_reply():
    reply = 'Claro!\n```json\n{"titulo": "teste", "n": 2}\n```\nEspero ter ajudado.'
    items = run_one("json_ler", {"texto": reply})
    assert items == [{"titulo": "teste", "n": 2}]


def test_json_parse_rejects_text_without_json():
    wf = Workflow(name="json-ruim")
    wf.add_node("json_ler", {"texto": "não tem json aqui"}, id="alvo")
    ctx = RunContext(
        workflow_id="w", workflow_slug="t", execution_id="e", owner_id="d",
        services=Services(), session_factory=lambda: None,
    )
    result = asyncio.run(Orchestrator(build_registry()).run(wf, ctx))
    assert result.status is ExecutionStatus.FAILED


def test_filter_keeps_matching_items():
    wf = Workflow(name="filtro")
    start = wf.add_node("inicio", {}, id="a")
    # A node that emits several items: `meta_listar` via a fake planning service.
    goals = wf.add_node("meta_listar", {}, id="metas")
    keep = wf.add_node(
        "filtrar", {"campo": "prioridade", "operador": "maior", "valor": 2}, id="alvo"
    )
    wf.connect(start, goals).connect(goals, keep)

    planning = SimpleNamespace(list_goals=lambda db, owner, status: [
        SimpleNamespace(id="1", title="baixa", status="pending", priority=1,
                        progress=0.0, due_at=None),
        SimpleNamespace(id="2", title="alta", status="pending", priority=5,
                        progress=0.0, due_at=None),
    ])
    ctx = RunContext(
        workflow_id="w", workflow_slug="t", execution_id="e", owner_id="d",
        services=Services(planning=planning), session_factory=_null_session,
    )
    result = asyncio.run(Orchestrator(build_registry()).run(wf, ctx))
    assert result.status is ExecutionStatus.COMPLETED
    assert [i["titulo"] for i in ctx.outputs["alvo"]["main"]] == ["alta"]


def _run_over_goals(node_type: str, config: dict, goals: list[dict]) -> list:
    """Feed a list of items into one data node, via a faked `meta_listar`."""
    wf = Workflow(name="dados")
    start = wf.add_node("inicio", {}, id="a")
    source = wf.add_node("meta_listar", {}, id="fonte")
    target = wf.add_node(node_type, config, id="alvo")
    wf.connect(start, source).connect(source, target)

    planning = SimpleNamespace(list_goals=lambda db, owner, status: [
        SimpleNamespace(
            id=g["id"], title=g["titulo"], status="pending",
            priority=g["prioridade"], progress=0.0, due_at=None,
        )
        for g in goals
    ])
    ctx = RunContext(
        workflow_id="w", workflow_slug="t", execution_id="e", owner_id="d",
        services=Services(planning=planning), session_factory=_null_session,
    )
    result = asyncio.run(Orchestrator(build_registry()).run(wf, ctx))
    assert result.status is ExecutionStatus.COMPLETED, result.error
    return ctx.outputs["alvo"]["main"]


GOALS = [
    {"id": "1", "titulo": "media", "prioridade": 3},
    {"id": "2", "titulo": "alta", "prioridade": 5},
    {"id": "3", "titulo": "baixa", "prioridade": 1},
]


def test_aggregate_counts():
    assert _run_over_goals("agregar", {"operacao": "contar"}, GOALS)[0]["resultado"] == 3


def test_aggregate_sums_and_averages_a_field():
    total = _run_over_goals("agregar", {"operacao": "somar", "campo": "prioridade"}, GOALS)
    assert total[0]["resultado"] == 9
    mean = _run_over_goals("agregar", {"operacao": "media", "campo": "prioridade"}, GOALS)
    assert mean[0]["resultado"] == 3


def test_aggregate_joins_a_field():
    joined = _run_over_goals(
        "agregar", {"operacao": "juntar", "campo": "titulo", "separador": ", "}, GOALS
    )
    assert joined[0]["resultado"] == "media, alta, baixa"


def test_sort_orders_by_a_field():
    ordered = _run_over_goals(
        "ordenar", {"campo": "prioridade", "decrescente": True}, GOALS
    )
    assert [i["prioridade"] for i in ordered] == [5, 3, 1]


def test_limit_keeps_the_first_items():
    assert len(_run_over_goals("limitar", {"quantidade": 2}, GOALS)) == 2


def test_map_reshapes_items():
    mapped = _run_over_goals("mapear", {"campos": {"nome": "titulo"}}, GOALS)
    assert mapped == [{"nome": "media"}, {"nome": "alta"}, {"nome": "baixa"}]


def test_set_vars_are_visible_downstream():
    wf = Workflow(name="vars")
    setter = wf.add_node("definir_variaveis", {"variaveis": {"nome": "Sexta"}}, id="set")
    reader = wf.add_node("texto", {"texto": "oi {{ vars.nome }}"}, id="alvo")
    wf.connect(setter, reader)

    ctx = RunContext(
        workflow_id="w", workflow_slug="t", execution_id="e", owner_id="d",
        services=Services(), session_factory=lambda: None,
    )
    asyncio.run(Orchestrator(build_registry()).run(wf, ctx))
    assert ctx.outputs["alvo"]["main"] == [{"texto": "oi Sexta"}]


# ---------------------------------------------------------------- file nodes


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "teia_workspace", str(tmp_path))
    monkeypatch.setattr(settings, "teia_allowed_paths", [])
    monkeypatch.setattr(settings, "obsidian_vault_path", "")
    return tmp_path


def test_write_then_read_a_file(workspace):
    run_one("arquivo_escrever", {"caminho": "notas.md", "conteudo": "primeira linha\n"})
    run_one(
        "arquivo_escrever",
        {"caminho": "notas.md", "conteudo": "segunda linha\n", "modo": "acrescentar"},
    )
    items = run_one("arquivo_ler", {"caminho": "notas.md"})
    assert items[0]["conteudo"] == "primeira linha\nsegunda linha\n"


def test_read_as_lines(workspace):
    (workspace / "l.txt").write_text("a\nb\nc\n", encoding="utf-8")
    items = run_one("arquivo_ler", {"caminho": "l.txt", "formato": "linhas"})
    assert items == [{"linha": "a"}, {"linha": "b"}, {"linha": "c"}]


def test_relative_paths_land_in_the_workspace(workspace):
    run_one("arquivo_escrever", {"caminho": "sub/dir/a.txt", "conteudo": "oi"})
    assert (workspace / "sub" / "dir" / "a.txt").read_text(encoding="utf-8") == "oi"


def test_escaping_the_workspace_is_refused(workspace):
    with pytest.raises(PathNotAllowed):
        safe_path("../../../etc/passwd")
    with pytest.raises(PathNotAllowed):
        safe_path("sub/../../fora.txt")


def test_a_traversal_inside_a_workflow_fails_the_run(workspace):
    wf = Workflow(name="fuga")
    wf.add_node("arquivo_escrever", {"caminho": "../fora.txt", "conteudo": "x"}, id="alvo")
    ctx = RunContext(
        workflow_id="w", workflow_slug="t", execution_id="e", owner_id="d",
        services=Services(), session_factory=lambda: None,
    )
    result = asyncio.run(Orchestrator(build_registry()).run(wf, ctx))
    assert result.status is ExecutionStatus.FAILED
    assert "fora das pastas permitidas" in result.node_results[0].error


def test_extra_allowed_paths_are_honoured(tmp_path, monkeypatch):
    outside = tmp_path / "externo"
    outside.mkdir()
    monkeypatch.setattr(settings, "teia_workspace", str(tmp_path / "ws"))
    monkeypatch.setattr(settings, "teia_allowed_paths", [str(outside)])
    monkeypatch.setattr(settings, "obsidian_vault_path", "")
    assert safe_path(str(outside / "ok.txt")).parent == outside.resolve()


def test_file_exists_reports_absence_without_failing(workspace):
    items = run_one("arquivo_existe", {"caminho": "nao-existe.txt"})
    assert items[0]["existe"] is False


def test_list_dir(workspace):
    (workspace / "a.md").write_text("x", encoding="utf-8")
    (workspace / "b.txt").write_text("y", encoding="utf-8")
    items = run_one("pasta_listar", {"caminho": str(workspace), "padrao": "*.md"})
    assert [i["nome"] for i in items] == ["a.md"]


# ---------------------------------------------------------------- system nodes


def test_disk_usage_flags_the_alert(workspace):
    items = run_one("disco", {"caminho": str(workspace), "alerta_livre_gb": 0.0})
    assert items[0]["alerta"] is False
    assert items[0]["total_gb"] > 0

    items = run_one("disco", {"caminho": str(workspace), "alerta_livre_gb": 10 ** 9})
    assert items[0]["alerta"] is True


def test_running_programs_is_off_by_default(workspace, monkeypatch):
    monkeypatch.setattr(settings, "teia_shell_enabled", False)
    wf = Workflow(name="programa")
    wf.add_node("programa", {"programa": "echo", "argumentos": ["oi"]}, id="alvo")
    ctx = RunContext(
        workflow_id="w", workflow_slug="t", execution_id="e", owner_id="d",
        services=Services(), session_factory=lambda: None,
    )
    result = asyncio.run(Orchestrator(build_registry()).run(wf, ctx))
    assert result.status is ExecutionStatus.FAILED
    assert "TEIA_SHELL_ENABLED" in result.node_results[0].error


def test_enabled_shell_still_refuses_what_is_not_allowlisted(workspace, monkeypatch):
    monkeypatch.setattr(settings, "teia_shell_enabled", True)
    monkeypatch.setattr(settings, "teia_shell_allowlist", ["git"])
    wf = Workflow(name="programa")
    wf.add_node("programa", {"programa": "curl", "argumentos": []}, id="alvo")
    ctx = RunContext(
        workflow_id="w", workflow_slug="t", execution_id="e", owner_id="d",
        services=Services(), session_factory=lambda: None,
    )
    result = asyncio.run(Orchestrator(build_registry()).run(wf, ctx))
    assert result.status is ExecutionStatus.FAILED
    assert "TEIA_SHELL_ALLOWLIST" in result.node_results[0].error


# ---------------------------------------------------------------- kernel nodes


def test_notify_reaches_the_action_service():
    sent = {}

    async def dispatch(db, owner_id, selector, action, params):
        sent.update(device=selector, action=action, params=params)
        return {"ok": True, "device": "Pixel", "delivered": True}

    services = Services(actions=SimpleNamespace(dispatch=dispatch))
    items = run_one(
        "notificar", {"texto": "está na hora", "dispositivo": "celular"},
        services=services,
    )
    assert sent == {"device": "celular", "action": "notify", "params": {"text": "está na hora"}}
    assert items[0]["entregue"] is True


def test_notify_fails_loudly_when_no_device_is_paired():
    async def dispatch(db, owner_id, selector, action, params):
        return {"ok": False, "error": "Nenhum dispositivo 'celular' pareado."}

    wf = Workflow(name="avisar")
    wf.add_node("notificar", {"texto": "oi"}, id="alvo")
    ctx = RunContext(
        workflow_id="w", workflow_slug="t", execution_id="e", owner_id="d",
        services=Services(actions=SimpleNamespace(dispatch=dispatch)),
        session_factory=_null_session,
    )
    result = asyncio.run(Orchestrator(build_registry()).run(wf, ctx))
    assert result.status is ExecutionStatus.FAILED
    assert "pareado" in result.node_results[0].error


def test_a_missing_service_says_which_one():
    wf = Workflow(name="sem-servico")
    wf.add_node("notificar", {"texto": "oi"}, id="alvo")
    ctx = RunContext(
        workflow_id="w", workflow_slug="t", execution_id="e", owner_id="d",
        services=Services(), session_factory=_null_session,
    )
    result = asyncio.run(Orchestrator(build_registry()).run(wf, ctx))
    assert result.status is ExecutionStatus.FAILED
    assert "actions" in result.node_results[0].error


def test_ai_node_uses_the_local_brain():
    async def chat(messages, temperature=None, max_tokens=None):
        return f"resposta para: {messages[-1]['content']}"

    items = run_one(
        "ia_perguntar", {"prompt": "quanto é {{ trigger.n }} + 1?"},
        services=Services(brain=SimpleNamespace(chat=chat)),
        payload={"n": 2},
    )
    assert items[0]["resposta"] == "resposta para: quanto é 2 + 1?"


def test_ai_json_node_parses_a_messy_reply():
    async def chat(messages, temperature=None, max_tokens=None):
        return 'Aqui está:\n```json\n{"humor": "bom", "energia": 7}\n```'

    items = run_one(
        "ia_json", {"prompt": "avalie meu dia", "formato": '{"humor": "...", "energia": 0}'},
        services=Services(brain=SimpleNamespace(chat=chat)),
    )
    assert items[0] == {"humor": "bom", "energia": 7}


def test_secrets_are_redacted_from_what_gets_stored():
    """A secret that flows through an expression never lands in the audit trail."""
    async def chat(messages, temperature=None, max_tokens=None):
        return "ok"

    wf = Workflow(name="segredo")
    wf.add_node("ia_perguntar", {"prompt": "token: {{ secret.TOKEN }}"}, id="alvo")

    connectors = SimpleNamespace(get_secret_value=lambda db, owner, name: "sup3r-s3cr3t")
    ctx = RunContext(
        workflow_id="w", workflow_slug="t", execution_id="e", owner_id="d",
        services=Services(brain=SimpleNamespace(chat=chat), connectors=connectors),
        session_factory=_null_session,
    )
    asyncio.run(Orchestrator(build_registry()).run(wf, ctx))

    stored = json.dumps(ctx.redact(ctx.outputs["alvo"]), ensure_ascii=False)
    assert "sup3r-s3cr3t" not in stored
    assert "***" in stored
